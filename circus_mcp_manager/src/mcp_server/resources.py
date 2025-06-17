"""
MCP Resources implementation for Circus process management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.exceptions import MCPServerError, ProcessNotFoundError
from ..utils.helpers import get_system_info


logger = logging.getLogger(__name__)


class MCPResources:
    """MCP Resources implementation for process management data."""
    
    def __init__(self, circus_manager) -> None:
        """
        Initialize MCP Resources.
        
        Args:
            circus_manager: CircusManager instance
        """
        self.circus_manager = circus_manager
        self._resources_registry = self._register_resources()
    
    def _register_resources(self) -> Dict[str, Dict[str, Any]]:
        """Register available MCP resources."""
        return {
            "circus://processes": {
                "uri": "circus://processes",
                "name": "Process List",
                "description": "List of all managed processes",
                "mimeType": "application/json",
                "handler": self.get_process_list,
            },
            "circus://logs/{process_name}": {
                "uri": "circus://logs/{process_name}",
                "name": "Process Logs",
                "description": "Real-time log stream for a specific process",
                "mimeType": "text/plain",
                "handler": self.get_process_logs,
            },
            "circus://stats": {
                "uri": "circus://stats",
                "name": "System Statistics",
                "description": "System and process statistics",
                "mimeType": "application/json",
                "handler": self.get_system_stats,
            },
            "circus://config": {
                "uri": "circus://config",
                "name": "Configuration",
                "description": "Current Circus configuration",
                "mimeType": "application/json",
                "handler": self.get_configuration,
            },
        }
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """
        Get list of available resources.
        
        Returns:
            List of resource definitions
        """
        resources = []
        for resource_uri, resource_info in self._resources_registry.items():
            resources.append({
                "uri": resource_info["uri"],
                "name": resource_info["name"],
                "description": resource_info["description"],
                "mimeType": resource_info["mimeType"],
            })
        return resources
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        Get resource content by URI.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
            
        Raises:
            MCPServerError: If resource not found or access fails
        """
        # Handle parameterized URIs
        resource_key = self._match_resource_uri(uri)
        
        if not resource_key:
            raise MCPServerError(f"Resource not found: {uri}")
        
        resource_info = self._resources_registry[resource_key]
        handler = resource_info["handler"]
        
        try:
            logger.info(f"Getting resource: {uri}")
            
            # Extract parameters from URI if needed
            params = self._extract_uri_params(resource_key, uri)
            
            content = await handler(params)
            
            return {
                "uri": uri,
                "mimeType": resource_info["mimeType"],
                "content": content,
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource {uri}: {str(e)}")
            raise MCPServerError(f"Resource access failed: {str(e)}")
    
    def _match_resource_uri(self, uri: str) -> Optional[str]:
        """
        Match URI to registered resource pattern.
        
        Args:
            uri: URI to match
            
        Returns:
            Matching resource key or None
        """
        for resource_key in self._resources_registry.keys():
            if "{" in resource_key:
                # Handle parameterized URIs
                pattern = resource_key.replace("{process_name}", r"[^/]+")
                import re
                if re.match(pattern.replace("://", r"://"), uri):
                    return resource_key
            else:
                if uri == resource_key:
                    return resource_key
        return None
    
    def _extract_uri_params(self, resource_key: str, uri: str) -> Dict[str, str]:
        """
        Extract parameters from URI.
        
        Args:
            resource_key: Resource key pattern
            uri: Actual URI
            
        Returns:
            Extracted parameters
        """
        params = {}
        
        if "{process_name}" in resource_key:
            # Extract process name from URI
            import re
            pattern = resource_key.replace("{process_name}", r"([^/]+)")
            match = re.match(pattern.replace("://", r"://"), uri)
            if match:
                params["process_name"] = match.group(1)
        
        return params
    
    async def get_process_list(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Get list of all managed processes.
        
        Args:
            params: URI parameters (unused)
            
        Returns:
            Process list data
        """
        try:
            status = await self.circus_manager.get_process_status()
            
            processes = []
            for process_name, process_info in status.items():
                processes.append({
                    "name": process_name,
                    "status": process_info.get("status", "unknown"),
                    "pid": process_info.get("pid"),
                    "cpu_percent": process_info.get("cpu_percent", 0.0),
                    "memory_percent": process_info.get("memory_percent", 0.0),
                    "started_at": process_info.get("started_at"),
                })
            
            return {
                "processes": processes,
                "total_count": len(processes),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            raise MCPServerError(f"Failed to get process list: {str(e)}")
    
    async def get_process_logs(self, params: Dict[str, str]) -> str:
        """
        Get logs for a specific process.
        
        Args:
            params: URI parameters containing process_name
            
        Returns:
            Process logs as text
        """
        process_name = params.get("process_name")
        if not process_name:
            raise MCPServerError("Process name not specified in URI")
        
        try:
            # Check if process exists
            status = await self.circus_manager.get_process_status(process_name)
            if not status:
                raise ProcessNotFoundError(process_name)
            
            # For now, return mock log data
            # In a real implementation, this would read actual log files
            mock_logs = [
                f"[{datetime.now().isoformat()}] [INFO] Process {process_name} started",
                f"[{datetime.now().isoformat()}] [INFO] Process {process_name} is running",
                f"[{datetime.now().isoformat()}] [DEBUG] Process {process_name} debug message",
            ]
            
            return "\n".join(mock_logs)
            
        except ProcessNotFoundError:
            raise MCPServerError(f"Process '{process_name}' not found")
        except Exception as e:
            raise MCPServerError(f"Failed to get logs for {process_name}: {str(e)}")
    
    async def get_system_stats(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Get system and process statistics.
        
        Args:
            params: URI parameters (unused)
            
        Returns:
            System statistics data
        """
        try:
            # Get system information
            system_info = get_system_info()
            
            # Get process statistics
            process_status = await self.circus_manager.get_process_status()
            
            # Calculate process statistics
            total_processes = len(process_status)
            running_processes = sum(1 for info in process_status.values() 
                                  if info.get("status") == "running")
            stopped_processes = total_processes - running_processes
            
            # Get circus manager status
            circus_status = self.circus_manager.get_system_status()
            
            return {
                "system": system_info,
                "processes": {
                    "total": total_processes,
                    "running": running_processes,
                    "stopped": stopped_processes,
                    "details": process_status,
                },
                "circus_manager": circus_status.get("circus_manager", {}),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            raise MCPServerError(f"Failed to get system stats: {str(e)}")
    
    async def get_configuration(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Get current Circus configuration.
        
        Args:
            params: URI parameters (unused)
            
        Returns:
            Configuration data
        """
        try:
            config_summary = self.circus_manager.config_handler.get_config_summary()
            
            # Add additional configuration details
            circus_config = self.circus_manager.config_handler.get_circus_config()
            
            watchers_config = {}
            for watcher_name in self.circus_manager.config_handler.get_all_watchers():
                watcher_config = self.circus_manager.config_handler.get_watcher_config(watcher_name)
                if watcher_config:
                    watchers_config[watcher_name] = watcher_config
            
            return {
                "summary": config_summary,
                "circus": circus_config,
                "watchers": watchers_config,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            raise MCPServerError(f"Failed to get configuration: {str(e)}")
    
    async def list_resource_templates(self) -> List[Dict[str, Any]]:
        """
        List available resource URI templates.
        
        Returns:
            List of resource templates
        """
        templates = []
        
        for resource_uri, resource_info in self._resources_registry.items():
            template = {
                "uri_template": resource_uri,
                "name": resource_info["name"],
                "description": resource_info["description"],
                "mimeType": resource_info["mimeType"],
            }
            
            # Add parameter information for templated URIs
            if "{" in resource_uri:
                template["parameters"] = []
                if "{process_name}" in resource_uri:
                    template["parameters"].append({
                        "name": "process_name",
                        "description": "Name of the process",
                        "required": True,
                    })
            
            templates.append(template)
        
        return templates