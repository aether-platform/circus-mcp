"""
MCP Server for Circus process management.

Security model (1.1.0):
  * Read-only tools (``list_processes``, ``get_process_status``) are always available.
  * Lifecycle tools (``start_process``, ``stop_process``, ``restart_process``) are only
    exposed when ``CIRCUS_MCP_ALLOW_WRITE=1`` (or ``--allow-write``).
  * ``add_process`` lets the caller run an arbitrary command as the circusd user, so it
    needs its own opt-in: ``CIRCUS_MCP_ALLOW_ADD=1`` (or ``--allow-add``).
  * Circus' control socket (ZeroMQ) has no authentication. The endpoint therefore must be
    ``ipc://`` or loopback ``tcp://`` unless ``CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT=1``.
"""

import ipaddress
import json
import os
import urllib.parse
from collections.abc import Mapping
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .manager import CircusManager

DEFAULT_ENDPOINT = "tcp://127.0.0.1:5555"

ENV_ENDPOINT = "CIRCUS_ENDPOINT"
ENV_ALLOW_WRITE = "CIRCUS_MCP_ALLOW_WRITE"
ENV_ALLOW_ADD = "CIRCUS_MCP_ALLOW_ADD"
ENV_ALLOW_REMOTE = "CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT"

READ_TOOLS = frozenset({"list_processes", "get_process_status"})
WRITE_TOOLS = frozenset({"start_process", "stop_process", "restart_process"})
ADD_TOOLS = frozenset({"add_process"})

_TRUTHY = {"1", "true", "yes", "on"}


class ToolError(Exception):
    """Raised from a tool handler; the MCP SDK reports it with isError=true."""


class EndpointNotAllowedError(ValueError):
    """The configured Circus endpoint is not local and remote use was not allowed."""


def env_flag(name: str, environ: Mapping[str, str] | None = None) -> bool:
    """Interpret an environment variable as a boolean opt-in flag."""
    env = os.environ if environ is None else environ
    return env.get(name, "").strip().lower() in _TRUTHY


def is_local_endpoint(endpoint: str) -> bool:
    """True for ipc:// endpoints and tcp:// endpoints on a loopback address."""
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme == "ipc":
        return True
    if parsed.scheme != "tcp":
        return False
    host = parsed.hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_endpoint(endpoint: str, allow_remote: bool) -> str:
    """Validate the endpoint against the local-only policy."""
    if not allow_remote and not is_local_endpoint(endpoint):
        raise EndpointNotAllowedError(
            f"Refusing to use Circus endpoint {endpoint!r}: the Circus control socket has no "
            "authentication, so only ipc:// or loopback tcp:// endpoints are allowed. "
            f"Set {ENV_ALLOW_REMOTE}=1 to override."
        )
    return endpoint


def _name_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Process name"}},
        "required": ["name"],
    }


TOOL_DEFINITIONS: dict[str, Tool] = {
    "list_processes": Tool(
        name="list_processes",
        description="List all processes",
        inputSchema={"type": "object", "properties": {}},
    ),
    "get_process_status": Tool(
        name="get_process_status",
        description="Get process status",
        inputSchema=_name_schema(),
    ),
    "start_process": Tool(
        name="start_process",
        description="Start a process",
        inputSchema=_name_schema(),
    ),
    "stop_process": Tool(
        name="stop_process",
        description="Stop a process",
        inputSchema=_name_schema(),
    ),
    "restart_process": Tool(
        name="restart_process",
        description="Restart a process",
        inputSchema=_name_schema(),
    ),
    "add_process": Tool(
        name="add_process",
        description=(
            "Add a new process to Circus. The command runs with the privileges of circusd."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Process name"},
                "command": {"type": "string", "description": "Command to run"},
                "numprocesses": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Number of processes",
                },
                "working_dir": {"type": "string", "description": "Working directory"},
            },
            "required": ["name", "command"],
        },
    ),
}


class CircusMCPServer:
    """MCP Server for Circus process management."""

    def __init__(
        self,
        endpoint: str | None = None,
        allow_write: bool | None = None,
        allow_add: bool | None = None,
        allow_remote_endpoint: bool | None = None,
    ):
        """Create the server.

        Arguments left as ``None`` are read from the environment
        (``CIRCUS_ENDPOINT``, ``CIRCUS_MCP_ALLOW_WRITE``, ``CIRCUS_MCP_ALLOW_ADD``,
        ``CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT``). Write tools are disabled by default.
        """
        if endpoint is None:
            endpoint = os.environ.get(ENV_ENDPOINT) or DEFAULT_ENDPOINT
        if allow_write is None:
            allow_write = env_flag(ENV_ALLOW_WRITE)
        if allow_add is None:
            allow_add = env_flag(ENV_ALLOW_ADD)
        if allow_remote_endpoint is None:
            allow_remote_endpoint = env_flag(ENV_ALLOW_REMOTE)

        self.endpoint = check_endpoint(endpoint, allow_remote_endpoint)
        self.allow_write = allow_write
        self.allow_add = allow_add

        enabled = set(READ_TOOLS)
        if allow_write:
            enabled |= WRITE_TOOLS
        if allow_add:
            enabled |= ADD_TOOLS
        self.enabled_tools = frozenset(enabled)

        from . import __version__

        self.server = Server("circus-mcp", version=__version__)
        self.manager = CircusManager(endpoint=self.endpoint)
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Setup MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List the tools enabled by the current configuration."""
            return [tool for name, tool in TOOL_DEFINITIONS.items() if name in self.enabled_tools]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls. Failures raise ToolError, reported as isError=true."""
            try:
                return await self._handle_tool(name, arguments or {})
            except ToolError:
                raise
            except Exception as e:
                raise ToolError(f"{type(e).__name__}: {e}") from None

    def _disabled_message(self, name: str) -> str:
        if name in ADD_TOOLS:
            return (
                f"Tool '{name}' is disabled. It runs arbitrary commands as the circusd user; "
                f"enable it explicitly with {ENV_ALLOW_ADD}=1 (or --allow-add)."
            )
        return (
            f"Tool '{name}' is disabled (read-only mode). "
            f"Enable process control with {ENV_ALLOW_WRITE}=1 (or --allow-write)."
        )

    async def _handle_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name not in TOOL_DEFINITIONS:
            raise ToolError(f"Unknown tool: {name}")
        if name not in self.enabled_tools:
            raise ToolError(self._disabled_message(name))

        if not await self.manager.connect():
            raise ToolError(f"Failed to connect to Circus daemon at {self.endpoint}")

        if name == "add_process":
            kwargs: dict[str, Any] = {"numprocesses": arguments.get("numprocesses", 1)}
            if arguments.get("working_dir"):
                kwargs["working_dir"] = arguments["working_dir"]
            result = await self.manager.add_process(
                arguments["name"], arguments["command"], **kwargs
            )
        elif name == "start_process":
            result = await self.manager.start_process(arguments["name"])
        elif name == "stop_process":
            result = await self.manager.stop_process(arguments["name"])
        elif name == "restart_process":
            result = await self.manager.restart_process(arguments["name"])
        elif name == "list_processes":
            result = await self.manager.list_processes()
        else:  # get_process_status
            result = await self.manager.get_process_status(arguments["name"])

        if isinstance(result, dict) and result.get("status") == "error":
            raise ToolError(str(result.get("reason") or result.get("message") or result))

        return [TextContent(type="text", text=json.dumps(result, default=str))]

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1], self.server.create_initialization_options()
            )
