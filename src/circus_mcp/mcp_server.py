"""
MCP Server for Circus process management.
"""

from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .manager import CircusManager


class CircusMCPServer:
    """MCP Server for Circus process management."""

    def __init__(self):
        self.server = Server("circus-mcp")
        self.manager = CircusManager()
        self._setup_tools()

    def _setup_tools(self):
        """Setup MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="add_process",
                    description="Add a new process to Circus",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Process name"},
                            "command": {"type": "string", "description": "Command to run"},
                            "numprocesses": {
                                "type": "integer",
                                "default": 1,
                                "description": "Number of processes",
                            },
                            "working_dir": {"type": "string", "description": "Working directory"},
                        },
                        "required": ["name", "command"],
                    },
                ),
                Tool(
                    name="start_process",
                    description="Start a process",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string", "description": "Process name"}},
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="stop_process",
                    description="Stop a process",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string", "description": "Process name"}},
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="restart_process",
                    description="Restart a process",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string", "description": "Process name"}},
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="list_processes",
                    description="List all processes",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="get_process_status",
                    description="Get process status",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string", "description": "Process name"}},
                        "required": ["name"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""

            # Ensure connection
            if not await self.manager.connect():
                return [TextContent(type="text", text="Failed to connect to Circus daemon")]

            try:
                if name == "add_process":
                    result = await self.manager.add_process(
                        arguments["name"],
                        arguments["command"],
                        numprocesses=arguments.get("numprocesses", 1),
                        working_dir=arguments.get("working_dir"),
                    )
                elif name == "start_process":
                    result = await self.manager.start_process(arguments["name"])
                elif name == "stop_process":
                    result = await self.manager.stop_process(arguments["name"])
                elif name == "restart_process":
                    result = await self.manager.restart_process(arguments["name"])
                elif name == "list_processes":
                    result = await self.manager.list_processes()
                elif name == "get_process_status":
                    result = await self.manager.get_process_status(arguments["name"])
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

                return [TextContent(type="text", text=str(result))]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1], self.server.create_initialization_options()
            )
