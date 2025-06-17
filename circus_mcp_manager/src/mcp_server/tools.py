"""
MCP Tools implementation for Circus process control.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..utils.exceptions import MCPServerError, ProcessNotFoundError
from ..utils.helpers import validate_process_name, sanitize_input


logger = logging.getLogger(__name__)


class ProcessControlRequest(BaseModel):
    """Request model for process control operations."""
    action: str = Field(..., description="Action to perform (start, stop, restart, reload)")
    process_name: str = Field(..., description="Name of the process to control")


class GetStatusRequest(BaseModel):
    """Request model for getting process status."""
    process_name: Optional[str] = Field(None, description="Name of the process (optional)")


class SendInputRequest(BaseModel):
    """Request model for sending input to process."""
    process_name: str = Field(..., description="Name of the target process")
    input_data: str = Field(..., description="Data to send to the process")


class GetLogsRequest(BaseModel):
    """Request model for getting process logs."""
    process_name: str = Field(..., description="Name of the process")
    lines: Optional[int] = Field(100, description="Number of lines to retrieve")
    level: Optional[str] = Field(None, description="Log level filter")


class MCPTools:
    """MCP Tools implementation for process management."""
    
    def __init__(self, circus_manager) -> None:
        """
        Initialize MCP Tools.
        
        Args:
            circus_manager: CircusManager instance
        """
        self.circus_manager = circus_manager
        self._tools_registry = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register available MCP tools."""
        return {
            "process_control": {
                "name": "process_control",
                "description": "Control processes (start, stop, restart, reload)",
                "handler": self.process_control,
                "schema": ProcessControlRequest.model_json_schema(),
            },
            "get_status": {
                "name": "get_status", 
                "description": "Get status of processes",
                "handler": self.get_status,
                "schema": GetStatusRequest.model_json_schema(),
            },
            "send_input": {
                "name": "send_input",
                "description": "Send input to a process",
                "handler": self.send_input,
                "schema": SendInputRequest.model_json_schema(),
            },
            "get_logs": {
                "name": "get_logs",
                "description": "Get logs from processes",
                "handler": self.get_logs,
                "schema": GetLogsRequest.model_json_schema(),
            },
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools.
        
        Returns:
            List of tool definitions
        """
        tools = []
        for tool_name, tool_info in self._tools_registry.items():
            tools.append({
                "name": tool_info["name"],
                "description": tool_info["description"],
                "inputSchema": tool_info["schema"],
            })
        return tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            MCPServerError: If tool execution fails
        """
        if tool_name not in self._tools_registry:
            raise MCPServerError(f"Unknown tool: {tool_name}")
        
        tool_info = self._tools_registry[tool_name]
        handler = tool_info["handler"]
        
        try:
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
            result = await handler(arguments)
            logger.debug(f"Tool {tool_name} executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {str(e)}")
            raise MCPServerError(f"Tool execution failed: {str(e)}")
    
    async def process_control(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle process control operations.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Operation result
        """
        try:
            request = ProcessControlRequest(**arguments)
        except Exception as e:
            raise MCPServerError(f"Invalid arguments: {str(e)}")
        
        # Validate process name
        try:
            validate_process_name(request.process_name)
        except Exception as e:
            raise MCPServerError(f"Invalid process name: {str(e)}")
        
        # Execute action
        try:
            if request.action == "start":
                success = await self.circus_manager.start_process(request.process_name)
                action_msg = "started"
            elif request.action == "stop":
                success = await self.circus_manager.stop_process(request.process_name)
                action_msg = "stopped"
            elif request.action == "restart":
                success = await self.circus_manager.restart_process(request.process_name)
                action_msg = "restarted"
            elif request.action == "reload":
                # For now, reload is same as restart
                success = await self.circus_manager.restart_process(request.process_name)
                action_msg = "reloaded"
            else:
                raise MCPServerError(f"Unknown action: {request.action}")
            
            if success:
                return {
                    "success": True,
                    "message": f"Process '{request.process_name}' {action_msg} successfully",
                    "process_name": request.process_name,
                    "action": request.action,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to {request.action} process '{request.process_name}'",
                    "process_name": request.process_name,
                    "action": request.action,
                }
                
        except ProcessNotFoundError:
            raise MCPServerError(f"Process '{request.process_name}' not found")
        except Exception as e:
            raise MCPServerError(f"Process control failed: {str(e)}")
    
    async def get_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle get status operations.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Status information
        """
        try:
            request = GetStatusRequest(**arguments)
        except Exception as e:
            raise MCPServerError(f"Invalid arguments: {str(e)}")
        
        try:
            if request.process_name:
                validate_process_name(request.process_name)
                status = await self.circus_manager.get_process_status(request.process_name)
            else:
                status = await self.circus_manager.get_process_status()
            
            return {
                "success": True,
                "processes": status,
                "timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord(
                    "", 0, "", 0, "", (), None
                )) if logger.handlers else None,
            }
            
        except Exception as e:
            raise MCPServerError(f"Failed to get status: {str(e)}")
    
    async def send_input(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle send input operations.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Operation result
        """
        try:
            request = SendInputRequest(**arguments)
        except Exception as e:
            raise MCPServerError(f"Invalid arguments: {str(e)}")
        
        # Validate process name
        try:
            validate_process_name(request.process_name)
        except Exception as e:
            raise MCPServerError(f"Invalid process name: {str(e)}")
        
        # Sanitize input data
        sanitized_input = sanitize_input(request.input_data)
        
        try:
            # For now, this is a placeholder implementation
            # In a real implementation, this would send input to the actual process
            logger.info(f"Sending input to process {request.process_name}: {sanitized_input}")
            
            # Check if process exists and is running
            status = await self.circus_manager.get_process_status(request.process_name)
            if not status:
                raise ProcessNotFoundError(request.process_name)
            
            process_info = status.get(request.process_name)
            if not process_info or process_info.get("status") != "running":
                raise MCPServerError(f"Process '{request.process_name}' is not running")
            
            return {
                "success": True,
                "message": f"Input sent to process '{request.process_name}'",
                "process_name": request.process_name,
                "input_length": len(sanitized_input),
            }
            
        except ProcessNotFoundError:
            raise MCPServerError(f"Process '{request.process_name}' not found")
        except Exception as e:
            raise MCPServerError(f"Failed to send input: {str(e)}")
    
    async def get_logs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle get logs operations.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Log data
        """
        try:
            request = GetLogsRequest(**arguments)
        except Exception as e:
            raise MCPServerError(f"Invalid arguments: {str(e)}")
        
        # Validate process name
        try:
            validate_process_name(request.process_name)
        except Exception as e:
            raise MCPServerError(f"Invalid process name: {str(e)}")
        
        try:
            # Check if process exists
            status = await self.circus_manager.get_process_status(request.process_name)
            if not status:
                raise ProcessNotFoundError(request.process_name)
            
            # For now, this is a placeholder implementation
            # In a real implementation, this would retrieve actual logs
            logger.info(f"Getting logs for process {request.process_name}")
            
            # Mock log data
            mock_logs = [
                f"[INFO] Process {request.process_name} log entry 1",
                f"[INFO] Process {request.process_name} log entry 2",
                f"[DEBUG] Process {request.process_name} debug message",
            ]
            
            # Apply line limit
            if request.lines:
                mock_logs = mock_logs[-request.lines:]
            
            # Apply level filter
            if request.level:
                level_upper = request.level.upper()
                mock_logs = [log for log in mock_logs if f"[{level_upper}]" in log]
            
            return {
                "success": True,
                "process_name": request.process_name,
                "logs": mock_logs,
                "total_lines": len(mock_logs),
                "level_filter": request.level,
                "line_limit": request.lines,
            }
            
        except ProcessNotFoundError:
            raise MCPServerError(f"Process '{request.process_name}' not found")
        except Exception as e:
            raise MCPServerError(f"Failed to get logs: {str(e)}")