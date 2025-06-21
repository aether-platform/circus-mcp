"""
Simple Circus process manager.
"""

import asyncio
import os
import signal
import subprocess
from typing import Any

from circus.client import CircusClient


class CircusManager:
    """Simple Circus process manager."""

    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555", config_file: str = "circus.ini"):
        """Initialize manager with Circus endpoint."""
        self.endpoint = endpoint
        self.config_file = config_file
        self.client: CircusClient | None = None
        self.daemon_process: subprocess.Popen | None = None

    async def connect(self) -> bool:
        """Connect to Circus daemon."""
        try:
            self.client = CircusClient(endpoint=self.endpoint)
            # Test connection
            await asyncio.to_thread(self.client.call, {"command": "list"})
            return True
        except Exception:
            return False

    async def add_process(self, name: str, command: str, **kwargs) -> dict[str, Any]:
        """Add a new process to Circus."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "add", "properties": {"name": name, "cmd": command, **kwargs}}

        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def start_process(self, name: str) -> dict[str, Any]:
        """Start a process."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "start", "properties": {"name": name}}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def stop_process(self, name: str) -> dict[str, Any]:
        """Stop a process."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "stop", "properties": {"name": name}}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def list_processes(self) -> dict[str, Any]:
        """List all processes."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "list"}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def get_process_status(self, name: str) -> dict[str, Any]:
        """Get process status."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "status", "properties": {"name": name}}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def restart_process(self, name: str) -> dict[str, Any]:
        """Restart a process."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "restart", "properties": {"name": name}}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def remove_process(self, name: str) -> dict[str, Any]:
        """Remove a process."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "rm", "properties": {"name": name}}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def ensure_started(self, name: str) -> dict[str, Any]:
        """Ensure process is in started state (start if not running)."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        # Check current status first
        status_cmd = {"command": "status", "properties": {"name": name}}
        status_result = await asyncio.to_thread(self.client.call, status_cmd)

        if status_result.get("status") == "active":
            return {"status": "ok", "message": f"Process '{name}' is already running"}

        # Start the process
        return await self.start_process(name)

    async def ensure_stopped(self, name: str) -> dict[str, Any]:
        """Ensure process is in stopped state (stop if running)."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        # Check current status first
        status_cmd = {"command": "status", "properties": {"name": name}}
        status_result = await asyncio.to_thread(self.client.call, status_cmd)

        if status_result.get("status") == "stopped":
            return {"status": "ok", "message": f"Process '{name}' is already stopped"}

        # Stop the process
        return await self.stop_process(name)

    async def start_all(self) -> dict[str, Any]:
        """Start all processes."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "start"}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def stop_all(self) -> dict[str, Any]:
        """Stop all processes."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "stop"}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def restart_all(self) -> dict[str, Any]:
        """Restart all processes."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "restart"}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def get_all_status(self) -> dict[str, Any]:
        """Get status of all processes."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        # First get list of all processes
        list_result = await self.list_processes()
        if list_result.get("status") != "ok":
            return list_result

        watchers = list_result.get("watchers", [])
        status_info = {}

        # Get status for each process
        for watcher in watchers:
            try:
                status_cmd = {"command": "status", "properties": {"name": watcher}}
                status_result = await asyncio.to_thread(self.client.call, status_cmd)
                status_info[watcher] = status_result
            except Exception as e:
                status_info[watcher] = {"status": "error", "message": str(e)}

        return {"status": "ok", "processes": status_info}

    async def get_stats(self) -> dict[str, Any]:
        """Get system statistics."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {"command": "stats"}
        result = await asyncio.to_thread(self.client.call, cmd)
        return result

    async def get_process_logs(self, name: str, lines: int = 100) -> dict[str, Any]:
        """Get process logs."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        # Get stdout logs
        stdout_cmd = {
            "command": "logs",
            "properties": {"name": name, "stream": "stdout", "lines": lines},
        }

        try:
            stdout_result = await asyncio.to_thread(self.client.call, stdout_cmd)

            # Get stderr logs
            stderr_cmd = {
                "command": "logs",
                "properties": {"name": name, "stream": "stderr", "lines": lines},
            }
            stderr_result = await asyncio.to_thread(self.client.call, stderr_cmd)

            return {
                "status": "ok",
                "process": name,
                "stdout": stdout_result.get("logs", []),
                "stderr": stderr_result.get("logs", []),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def tail_process_logs(self, name: str, stream: str = "stdout") -> dict[str, Any]:
        """Tail process logs (get recent logs)."""
        if not self.client:
            raise RuntimeError("Not connected to Circus")

        cmd = {
            "command": "logs",
            "properties": {
                "name": name,
                "stream": stream,
                "lines": 50,  # Get last 50 lines
            },
        }

        try:
            result = await asyncio.to_thread(self.client.call, cmd)
            return {
                "status": "ok",
                "process": name,
                "stream": stream,
                "logs": result.get("logs", []),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def start_daemon(self, config_file: str | None = None) -> bool:
        """Start Circus daemon."""
        config = config_file or self.config_file

        try:
            # Check if daemon is already running
            if self.is_daemon_running():
                return True

            # Start daemon
            self.daemon_process = subprocess.Popen(
                ["circusd", config],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )

            # Wait a bit for daemon to start
            import time

            time.sleep(2)

            return self.is_daemon_running()
        except Exception:
            return False

    def stop_daemon(self) -> bool:
        """Stop Circus daemon."""
        try:
            if self.daemon_process:
                # Send SIGTERM to process group
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(self.daemon_process.pid), signal.SIGTERM)
                else:
                    self.daemon_process.terminate()

                # Wait for process to end
                self.daemon_process.wait(timeout=10)
                self.daemon_process = None
                return True
            else:
                # Try to find and kill circusd process
                import psutil

                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        if proc.info["name"] == "circusd" or (
                            proc.info["cmdline"] and "circusd" in proc.info["cmdline"][0]
                        ):
                            proc.terminate()
                            proc.wait(timeout=10)
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        continue
                return False
        except Exception:
            return False

    def is_daemon_running(self) -> bool:
        """Check if Circus daemon is running."""
        try:
            # Try to connect to check if daemon is running
            temp_client = CircusClient(endpoint=self.endpoint)
            temp_client.call({"command": "list"})
            return True
        except Exception:
            return False
