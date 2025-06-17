"""
MCP Server implementation for Circus process management.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..utils.exceptions import MCPServerError, ConfigurationError
from ..utils.helpers import load_config
from .tools import MCPTools
from .resources import MCPResources


logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for Circus process management."""

    def __init__(self, circus_manager, config_path: Optional[Path] = None) -> None:
        """
        Initialize MCP Server.

        Args:
            circus_manager: CircusManager instance
            config_path: Path to MCP configuration file
        """
        self.circus_manager = circus_manager
        self.config_path = config_path or Path("config/mcp_config.json")

        # Load MCP configuration
        self.config = self._load_mcp_config()

        # Initialize tools and resources
        self.tools = MCPTools(circus_manager)
        self.resources = MCPResources(circus_manager)

        # Server state
        self._running = False
        self._client_capabilities: Optional[Dict[str, Any]] = None

        # Message handlers
        self._handlers = self._register_handlers()

    def _load_mcp_config(self) -> Dict[str, Any]:
        """Load MCP configuration."""
        try:
            if self.config_path.exists():
                config = load_config(self.config_path, "json")
                logger.info(f"Loaded MCP configuration from {self.config_path}")
                return config
            else:
                logger.warning(f"MCP config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            raise ConfigurationError(f"Failed to load MCP configuration: {str(e)}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default MCP configuration."""
        return {
            "server": {
                "name": "circus-mcp-manager",
                "version": "1.0.0",
                "description": "Circus Process Manager with MCP Protocol Support",
            },
            "transport": {"type": "stdio"},
        }

    def _register_handlers(self) -> Dict[str, Any]:
        """Register MCP message handlers."""
        return {
            # Initialization
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            # Tools
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            # Resources
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "resources/templates/list": self._handle_resources_templates_list,
            # Prompts (not implemented in this phase)
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            # Logging
            "logging/setLevel": self._handle_logging_set_level,
        }

    async def start(self) -> None:
        """Start the MCP server."""
        if self._running:
            logger.warning("MCP Server is already running")
            return

        self._running = True
        logger.info("Starting MCP Server")

        try:
            # Start the main message loop
            await self._message_loop()
        except Exception as e:
            logger.error(f"MCP Server error: {str(e)}")
            raise MCPServerError(f"Server error: {str(e)}")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the MCP server."""
        self._running = False
        logger.info("MCP Server stopped")

    async def _message_loop(self) -> None:
        """Main message processing loop."""
        while self._running:
            try:
                # Read message from stdin
                line = await self._read_message()
                if not line:
                    break

                # Parse JSON-RPC message
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as e:
                    await self._send_error_response(
                        None, -32700, f"Parse error: {str(e)}"
                    )
                    continue

                # Process message
                await self._process_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message loop: {str(e)}")
                await self._send_error_response(
                    None, -32603, f"Internal error: {str(e)}"
                )

    async def _read_message(self) -> Optional[str]:
        """Read a message from stdin."""
        try:
            # Read from stdin in a non-blocking way
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, sys.stdin.readline)
            return line.strip() if line else None
        except Exception as e:
            logger.error(f"Error reading message: {str(e)}")
            return None

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process an incoming MCP message."""
        message_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if not method:
            await self._send_error_response(
                message_id, -32600, "Invalid request: missing method"
            )
            return

        # Find handler
        handler = self._handlers.get(method)
        if not handler:
            await self._send_error_response(
                message_id, -32601, f"Method not found: {method}"
            )
            return

        try:
            # Execute handler
            result = await handler(params)

            # Send response
            if message_id is not None:  # Don't respond to notifications
                await self._send_response(message_id, result)

        except Exception as e:
            logger.error(f"Handler error for {method}: {str(e)}")
            await self._send_error_response(
                message_id, -32603, f"Internal error: {str(e)}"
            )

    async def _send_response(self, message_id: Any, result: Any) -> None:
        """Send a successful response."""
        response = {"jsonrpc": "2.0", "id": message_id, "result": result}
        await self._send_message(response)

    async def _send_error_response(
        self, message_id: Any, code: int, message: str
    ) -> None:
        """Send an error response."""
        response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code, "message": message},
        }
        await self._send_message(response)

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to stdout."""
        try:
            json_str = json.dumps(message)
            print(json_str, flush=True)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    # Message Handlers

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        self._client_capabilities = params.get("capabilities", {})

        server_config = self.config.get("server", {})

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
                "logging": {},
            },
            "serverInfo": {
                "name": server_config.get("name", "circus-mcp-manager"),
                "version": server_config.get("version", "1.0.0"),
            },
        }

    async def _handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle initialized notification."""
        logger.info("MCP Server initialized")

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self.tools.get_available_tools()
        return {"tools": tools}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise MCPServerError("Tool name is required")

        result = await self.tools.execute_tool(tool_name, arguments)

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = self.resources.get_available_resources()
        return {"resources": resources}

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")

        if not uri:
            raise MCPServerError("Resource URI is required")

        resource_data = await self.resources.get_resource(uri)

        return {
            "contents": [
                {
                    "uri": resource_data["uri"],
                    "mimeType": resource_data["mimeType"],
                    "text": json.dumps(resource_data["content"], indent=2)
                    if resource_data["mimeType"] == "application/json"
                    else resource_data["content"],
                }
            ]
        }

    async def _handle_resources_templates_list(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle resources/templates/list request."""
        templates = await self.resources.list_resource_templates()
        return {"resourceTemplates": templates}

    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request."""
        # Not implemented in this phase
        return {"prompts": []}

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        # Not implemented in this phase
        raise MCPServerError("Prompts not implemented")

    async def _handle_logging_set_level(self, params: Dict[str, Any]) -> None:
        """Handle logging/setLevel request."""
        level = params.get("level", "INFO")

        # Set logging level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger().setLevel(numeric_level)

        logger.info(f"Logging level set to {level}")

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        server_config = self.config.get("server", {})

        return {
            "name": server_config.get("name", "circus-mcp-manager"),
            "version": server_config.get("version", "1.0.0"),
            "description": server_config.get("description", ""),
            "running": self._running,
            "client_capabilities": self._client_capabilities,
            "available_tools": len(self.tools.get_available_tools()),
            "available_resources": len(self.resources.get_available_resources()),
        }
