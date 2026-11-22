"""
End-to-end test over stdio against a real circusd.

Checks on the wire that:
  * by default only read tools are listed and add_process/start_process are refused
    (so the add -> start command-execution path is closed)
  * --allow-write / --allow-add (via env) opt in as documented
  * every stdout line is JSON-RPC and tool results are JSON
  * a non-loopback endpoint is refused at startup

Skipped on Windows (circusd is POSIX-only) or when circusd is not installed.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform == "win32", reason="circusd requires POSIX"),
]

CIRCUSD = shutil.which("circusd") or str(Path(sys.executable).with_name("circusd"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def circusd(tmp_path: Path):
    if not Path(CIRCUSD).exists():
        pytest.skip("circusd executable not found")
    endpoint = f"tcp://127.0.0.1:{_free_port()}"
    ini = tmp_path / "circus.ini"
    ini.write_text(
        f"""
[circus]
endpoint = {endpoint}
pubsub_endpoint = tcp://127.0.0.1:{_free_port()}
statsd = false

[watcher:dummy]
cmd = {sys.executable} -c "import time; time.sleep(3600)"
numprocesses = 1
"""
    )
    proc = subprocess.Popen(
        [CIRCUSD, str(ini)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=tmp_path,
    )
    from circus.client import CircusClient

    client = CircusClient(endpoint=endpoint, timeout=1)
    deadline = time.time() + 30
    while True:
        try:
            if client.call({"command": "list"}).get("status") == "ok":
                break
        except Exception:
            pass
        if time.time() > deadline or proc.poll() is not None:
            proc.kill()
            pytest.fail("circusd did not become ready")
        time.sleep(0.2)
    yield endpoint, tmp_path
    try:
        client.call({"command": "quit"})
    except Exception:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    client.stop()


class StdioClient:
    def __init__(self, env: dict[str, str], cwd: Path):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "circus_mcp.main", "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **env},
            cwd=cwd,
            text=True,
        )
        self._id = 0

    def send(self, method: str, params: dict | None = None, notify: bool = False) -> dict | None:
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._id += 1
            msg["id"] = self._id
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        if notify:
            return None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise AssertionError("server closed stdout")
            data = json.loads(line)  # every stdout line must be JSON-RPC
            assert data.get("jsonrpc") == "2.0", line[:200]
            if data.get("id") == self._id:
                return data

    def start(self) -> set[str]:
        self.send(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        )
        self.send("notifications/initialized", notify=True)
        tools = self.send("tools/list")
        assert tools is not None
        return {t["name"] for t in tools["result"]["tools"]}

    def call(self, name: str, arguments: dict) -> dict:
        resp = self.send("tools/call", {"name": name, "arguments": arguments})
        assert resp is not None and "result" in resp, resp
        return resp["result"]

    def close(self) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def _clean_env(endpoint: str, **flags: str) -> dict[str, str]:
    env = {
        "CIRCUS_ENDPOINT": endpoint,
        "CIRCUS_MCP_ALLOW_WRITE": "",
        "CIRCUS_MCP_ALLOW_ADD": "",
        "CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT": "",
    }
    env.update(flags)
    return env


def test_default_read_only_blocks_command_execution(circusd):
    endpoint, tmp_path = circusd
    marker = tmp_path / "injected.txt"
    client = StdioClient(_clean_env(endpoint), cwd=tmp_path)
    try:
        assert client.start() == {"list_processes", "get_process_status"}

        listing = client.call("list_processes", {})
        assert listing["isError"] is False
        assert "dummy" in json.loads(listing["content"][0]["text"])["watchers"]

        status = client.call("get_process_status", {"name": "dummy"})
        assert status["isError"] is False
        assert json.loads(status["content"][0]["text"])["status"] == "active"

        add = client.call(
            "add_process",
            {"name": "pwn", "command": f"/bin/sh -c 'echo pwned > {marker}'"},
        )
        assert add["isError"] is True
        start = client.call("start_process", {"name": "pwn"})
        assert start["isError"] is True
        stop = client.call("stop_process", {"name": "dummy"})
        assert stop["isError"] is True
    finally:
        client.close()

    time.sleep(0.5)
    assert not marker.exists()
    from circus.client import CircusClient

    watchers = CircusClient(endpoint=endpoint, timeout=2).call({"command": "list"})["watchers"]
    assert "pwn" not in watchers


def test_allow_write_controls_lifecycle_but_not_add(circusd):
    endpoint, tmp_path = circusd
    client = StdioClient(_clean_env(endpoint, CIRCUS_MCP_ALLOW_WRITE="1"), cwd=tmp_path)
    try:
        tools = client.start()
        assert "stop_process" in tools and "add_process" not in tools
        assert client.call("stop_process", {"name": "dummy"})["isError"] is False
        # circus stops asynchronously; wait until the watcher reports "stopped"
        deadline = time.time() + 20
        while True:
            status = client.call("get_process_status", {"name": "dummy"})
            if json.loads(status["content"][0]["text"]).get("status") == "stopped":
                break
            assert time.time() < deadline, status
            time.sleep(0.2)
        started = client.call("start_process", {"name": "dummy"})
        assert started["isError"] is False, started
        missing = client.call("start_process", {"name": "does-not-exist"})
        assert missing["isError"] is True
        assert client.call("add_process", {"name": "x", "command": "true"})["isError"] is True
    finally:
        client.close()


def test_allow_add_opt_in(circusd):
    endpoint, tmp_path = circusd
    env = _clean_env(endpoint, CIRCUS_MCP_ALLOW_WRITE="1", CIRCUS_MCP_ALLOW_ADD="1")
    client = StdioClient(env, cwd=tmp_path)
    try:
        assert "add_process" in client.start()
        added = client.call(
            "add_process",
            {"name": "sleeper", "command": f'{sys.executable} -c "import time; time.sleep(60)"'},
        )
        assert added["isError"] is False, added
        assert json.loads(added["content"][0]["text"])["status"] == "ok"
    finally:
        client.close()


def test_remote_endpoint_refused_at_startup(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "circus_mcp.main", "mcp"],
        env={**os.environ, **_clean_env("tcp://0.0.0.0:5555")},
        input="",
        capture_output=True,
        text=True,
        timeout=60,
        cwd=tmp_path,
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT" in proc.stderr
