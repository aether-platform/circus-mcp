"""
Regression tests for the 1.1.0 security changes: write tools are opt-in, the endpoint
is configurable but local-only by default, responses are JSON and failures set isError.
"""

import json
from unittest.mock import AsyncMock

import pytest
from mcp import types

from circus_mcp.mcp_server import (
    ADD_TOOLS,
    READ_TOOLS,
    WRITE_TOOLS,
    CircusMCPServer,
    EndpointNotAllowedError,
    env_flag,
    is_local_endpoint,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "CIRCUS_ENDPOINT",
        "CIRCUS_MCP_ALLOW_WRITE",
        "CIRCUS_MCP_ALLOW_ADD",
        "CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT",
    ):
        monkeypatch.delenv(var, raising=False)


async def _list_tools(server: CircusMCPServer) -> set[str]:
    handler = server.server.request_handlers[types.ListToolsRequest]
    result = await handler(types.ListToolsRequest(method="tools/list"))
    return {tool.name for tool in result.root.tools}


async def _call(server: CircusMCPServer, name: str, args: dict) -> types.CallToolResult:
    handler = server.server.request_handlers[types.CallToolRequest]
    request = types.CallToolRequest(
        method="tools/call", params=types.CallToolRequestParams(name=name, arguments=args)
    )
    result = await handler(request)
    return result.root


def _connected(server: CircusMCPServer) -> CircusMCPServer:
    server.manager.connect = AsyncMock(return_value=True)
    return server


@pytest.mark.asyncio
async def test_default_is_read_only():
    server = CircusMCPServer()
    assert await _list_tools(server) == set(READ_TOOLS)


@pytest.mark.asyncio
async def test_allow_write_exposes_lifecycle_but_not_add():
    server = CircusMCPServer(allow_write=True)
    assert await _list_tools(server) == set(READ_TOOLS | WRITE_TOOLS)


@pytest.mark.asyncio
async def test_allow_add_requires_its_own_flag():
    server = CircusMCPServer(allow_write=True, allow_add=True)
    assert await _list_tools(server) == set(READ_TOOLS | WRITE_TOOLS | ADD_TOOLS)


@pytest.mark.asyncio
async def test_env_flags(monkeypatch):
    monkeypatch.setenv("CIRCUS_MCP_ALLOW_WRITE", "1")
    server = CircusMCPServer()
    assert await _list_tools(server) == set(READ_TOOLS | WRITE_TOOLS)
    monkeypatch.setenv("CIRCUS_MCP_ALLOW_ADD", "true")
    server = CircusMCPServer()
    assert "add_process" in await _list_tools(server)


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "2"])
def test_env_flag_falsy(value):
    assert env_flag("X", {"X": value}) is False


@pytest.mark.parametrize(
    "tool,args",
    [
        ("add_process", {"name": "pwn", "command": "/bin/sh -c 'touch /tmp/x'"}),
        ("start_process", {"name": "pwn"}),
        ("stop_process", {"name": "pwn"}),
        ("restart_process", {"name": "pwn"}),
    ],
)
@pytest.mark.asyncio
async def test_disabled_write_tools_are_rejected_without_touching_circus(tool, args):
    server = _connected(CircusMCPServer())
    server.manager.add_process = AsyncMock()
    server.manager.start_process = AsyncMock()
    server.manager.stop_process = AsyncMock()
    server.manager.restart_process = AsyncMock()

    result = await _call(server, tool, args)

    assert result.isError is True
    assert "disabled" in result.content[0].text
    server.manager.connect.assert_not_called()
    server.manager.add_process.assert_not_called()
    server.manager.start_process.assert_not_called()


@pytest.mark.asyncio
async def test_add_still_rejected_with_only_allow_write():
    server = _connected(CircusMCPServer(allow_write=True))
    server.manager.add_process = AsyncMock()
    result = await _call(server, "add_process", {"name": "x", "command": "true"})
    assert result.isError is True
    assert "CIRCUS_MCP_ALLOW_ADD" in result.content[0].text
    server.manager.add_process.assert_not_called()


@pytest.mark.asyncio
async def test_read_tools_return_json():
    server = _connected(CircusMCPServer())
    server.manager.list_processes = AsyncMock(
        return_value={"status": "ok", "watchers": ["dummy"], "time": 1.0}
    )
    result = await _call(server, "list_processes", {})
    assert result.isError is False
    assert json.loads(result.content[0].text)["watchers"] == ["dummy"]


@pytest.mark.asyncio
async def test_circus_error_sets_is_error():
    server = _connected(CircusMCPServer(allow_write=True))
    server.manager.start_process = AsyncMock(
        return_value={"status": "error", "reason": "program nope not found"}
    )
    result = await _call(server, "start_process", {"name": "nope"})
    assert result.isError is True
    assert "not found" in result.content[0].text


@pytest.mark.asyncio
async def test_connection_failure_sets_is_error():
    server = CircusMCPServer()
    server.manager.connect = AsyncMock(return_value=False)
    result = await _call(server, "list_processes", {})
    assert result.isError is True


@pytest.mark.parametrize(
    "endpoint",
    [
        "tcp://127.0.0.1:5555",
        "tcp://127.0.0.2:5555",
        "tcp://localhost:5555",
        "tcp://[::1]:5555",
        "ipc:///tmp/circus.sock",
    ],
)
def test_local_endpoints_allowed(endpoint):
    assert is_local_endpoint(endpoint)
    assert CircusMCPServer(endpoint=endpoint).manager.endpoint == endpoint


@pytest.mark.parametrize(
    "endpoint",
    ["tcp://0.0.0.0:5555", "tcp://10.0.0.5:5555", "tcp://example.com:5555", "tcp://*:5555"],
)
def test_remote_endpoints_refused_by_default(endpoint):
    assert not is_local_endpoint(endpoint)
    with pytest.raises(EndpointNotAllowedError):
        CircusMCPServer(endpoint=endpoint)
    assert CircusMCPServer(endpoint=endpoint, allow_remote_endpoint=True).endpoint == endpoint


def test_endpoint_from_env(monkeypatch):
    monkeypatch.setenv("CIRCUS_ENDPOINT", "ipc:///run/circus/ctl.sock")
    assert CircusMCPServer().manager.endpoint == "ipc:///run/circus/ctl.sock"


def test_version_matches_metadata():
    from importlib.metadata import version

    import circus_mcp

    assert circus_mcp.__version__ == version("circus-mcp")
