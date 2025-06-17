"""
Main Circus Manager implementation using Circus client library.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from circus.client import CircusClient
from circus.exc import CallError

from ..utils.exceptions import (
    CircusManagerError,
    ProcessNotFoundError,
    ProcessAlreadyRunningError,
    ProcessNotRunningError,
    ConfigurationError,
)
from ..utils.helpers import validate_process_name, get_system_info
from .config_handler import ConfigHandler
from .watcher import ProcessWatcher, ProcessInfo, ProcessStatus


logger = logging.getLogger(__name__)


class CircusManager:
    """Main manager for Circus process control."""
    
    def __init__(self, config_path: Optional[Path] = None, endpoint: str = "tcp://127.0.0.1:5555") -> None:
        """
        Initialize Circus Manager using official Circus client.
        
        Args:
            config_path: Path to circus configuration file
            endpoint: Circus daemon endpoint
        """
        self.config_handler = ConfigHandler(config_path)
        self.process_watcher = ProcessWatcher()
        
        # Circus client - much simpler than manual ZMQ
        self._circus_client: Optional[CircusClient] = None
        self._endpoint = endpoint
        
        # Connection status
        self._connected = False
        self._initialized = False
        
        # Event handling
        self._event_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Performance monitoring
        self._performance_stats = {
            "commands_sent": 0,
            "commands_failed": 0,
            "last_activity": None,
        }
    
    async def initialize(self) -> None:
        """Initialize the manager and connect to Circus."""
        if self._initialized:
            logger.warning("CircusManager already initialized")
            return
        
        try:
            # Validate configuration
            config_errors = self.config_handler.validate_config()
            if config_errors:
                raise ConfigurationError(f"Configuration errors: {config_errors}")
            
            # Create Circus client - much simpler!
            self._circus_client = CircusClient(endpoint=self._endpoint)
            
            # Initialize process watcher with configured processes
            await self._initialize_watchers()
            
            # Start monitoring
            await self.process_watcher.start_monitoring()
            
            self._initialized = True
            logger.info("CircusManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CircusManager: {str(e)}")
            await self.cleanup()
            raise CircusManagerError(f"Initialization failed: {str(e)}")
    
    async def _initialize_watchers(self) -> None:
        """Initialize process watchers for configured processes."""
        watchers = self.config_handler.get_all_watchers()
        
        for watcher_name in watchers:
            watcher_config = self.config_handler.get_watcher_config(watcher_name)
            if watcher_config:
                self.process_watcher.add_process(watcher_name, {
                    'status': ProcessStatus.STOPPED,
                    'config': watcher_config,
                })
        
        logger.info(f"Initialized {len(watchers)} process watchers")
    
    async def connect_to_circus(self) -> bool:
        """
        Connect to Circus daemon using the client library.
        
        Returns:
            True if connected successfully
        """
        if not self._initialized:
            raise CircusManagerError("Manager not initialized")
        
        if not self._circus_client:
            raise CircusManagerError("Circus client not initialized")
        
        try:
            # Test connection by getting status - much simpler with client!
            status = await self._execute_circus_command("status")
            if status:
                self._connected = True
                logger.info("Connected to Circus daemon")
                return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Circus: {str(e)}")
            self._connected = False
        
        return False
    
    async def _execute_circus_command(self, command: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Execute command using Circus client library - much simpler!
        
        Args:
            command: Command to send
            **kwargs: Command arguments
            
        Returns:
            Command response or None if failed
        """
        if not self._circus_client:
            raise CircusManagerError("Circus client not initialized")
        
        try:
            logger.debug(f"Executing Circus command: {command} with args: {kwargs}")
            
            # Use the client's call method - handles all the ZMQ complexity
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._circus_client.call({"command": command, **kwargs})
            )
            
            # Update performance stats
            self._performance_stats["commands_sent"] += 1
            self._performance_stats["last_activity"] = datetime.now()
            
            logger.debug(f"Command {command} response: {response}")
            return response
                
        except CallError as e:
            self._performance_stats["commands_failed"] += 1
            logger.error(f"Circus command error: {str(e)}")
            return None
        except Exception as e:
            self._performance_stats["commands_failed"] += 1
            logger.error(f"Failed to execute command {command}: {str(e)}")
            return None
    
    async def start_process(self, process_name: str) -> bool:
        """
        Start a process.
        
        Args:
            process_name: Name of the process to start
            
        Returns:
            True if started successfully
            
        Raises:
            ProcessNotFoundError: If process is not configured
            ProcessAlreadyRunningError: If process is already running
        """
        validate_process_name(process_name)
        
        # Check if process is configured
        if process_name not in self.config_handler.get_all_watchers():
            raise ProcessNotFoundError(process_name)
        
        # Check current status
        try:
            process_info = self.process_watcher.get_process_info(process_name)
            if process_info.status == ProcessStatus.RUNNING:
                raise ProcessAlreadyRunningError(process_name)
        except ProcessNotFoundError:
            # Process not in watcher yet, add it
            self.process_watcher.add_process(process_name)
        
        # Send start command
        response = await self._execute_circus_command("start", name=process_name)
        
        if response and response.get("status") == "ok":
            # Update process status
            self.process_watcher.update_process_info(
                process_name,
                status=ProcessStatus.STARTING,
                started_at=datetime.now()
            )
            logger.info(f"Started process: {process_name}")
            return True
        
        logger.error(f"Failed to start process: {process_name}")
        return False
    
    async def stop_process(self, process_name: str) -> bool:
        """
        Stop a process.
        
        Args:
            process_name: Name of the process to stop
            
        Returns:
            True if stopped successfully
            
        Raises:
            ProcessNotFoundError: If process is not found
            ProcessNotRunningError: If process is not running
        """
        validate_process_name(process_name)
        
        # Check if process exists
        try:
            process_info = self.process_watcher.get_process_info(process_name)
            if process_info.status == ProcessStatus.STOPPED:
                raise ProcessNotRunningError(process_name)
        except ProcessNotFoundError:
            raise ProcessNotFoundError(process_name)
        
        # Send stop command
        response = await self._execute_circus_command("stop", name=process_name)
        
        if response and response.get("status") == "ok":
            # Update process status
            self.process_watcher.update_process_info(
                process_name,
                status=ProcessStatus.STOPPING
            )
            logger.info(f"Stopped process: {process_name}")
            return True
        
        logger.error(f"Failed to stop process: {process_name}")
        return False
    
    async def restart_process(self, process_name: str) -> bool:
        """
        Restart a process.
        
        Args:
            process_name: Name of the process to restart
            
        Returns:
            True if restarted successfully
        """
        validate_process_name(process_name)
        
        # Send restart command
        response = await self._execute_circus_command("restart", name=process_name)
        
        if response and response.get("status") == "ok":
            # Update process status
            self.process_watcher.update_process_info(
                process_name,
                status=ProcessStatus.RESTARTING,
                started_at=datetime.now()
            )
            logger.info(f"Restarted process: {process_name}")
            return True
        
        logger.error(f"Failed to restart process: {process_name}")
        return False
    
    async def get_process_status(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of processes.
        
        Args:
            process_name: Specific process name, or None for all processes
            
        Returns:
            Process status information
        """
        if process_name:
            validate_process_name(process_name)
            try:
                process_info = self.process_watcher.get_process_info(process_name)
                return {process_name: process_info.to_dict()}
            except ProcessNotFoundError:
                return {}
        else:
            # Return all processes
            all_processes = self.process_watcher.get_all_processes()
            return {name: info.to_dict() for name, info in all_processes.items()}
    
    async def add_process(self, process_name: str, config: Dict[str, Any]) -> bool:
        """
        Add a new process configuration.
        
        Args:
            process_name: Name of the process
            config: Process configuration
            
        Returns:
            True if added successfully
        """
        try:
            # Add to configuration
            self.config_handler.add_watcher(process_name, config)
            
            # Add to watcher
            self.process_watcher.add_process(process_name, {
                'status': ProcessStatus.STOPPED,
                'config': config,
            })
            
            # Save configuration
            self.config_handler.save_config()
            
            logger.info(f"Added new process: {process_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add process {process_name}: {str(e)}")
            return False
    
    async def remove_process(self, process_name: str) -> bool:
        """
        Remove a process configuration.
        
        Args:
            process_name: Name of the process to remove
            
        Returns:
            True if removed successfully
        """
        try:
            # Stop process if running
            try:
                process_info = self.process_watcher.get_process_info(process_name)
                if process_info.status == ProcessStatus.RUNNING:
                    await self.stop_process(process_name)
            except ProcessNotFoundError:
                pass
            
            # Remove from configuration
            self.config_handler.remove_watcher(process_name)
            
            # Remove from watcher
            self.process_watcher.remove_process(process_name)
            
            # Save configuration
            self.config_handler.save_config()
            
            logger.info(f"Removed process: {process_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove process {process_name}: {str(e)}")
            return False
    
    async def get_process_stats(self, process_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed process statistics from Circus.
        
        Args:
            process_name: Name of the process
            
        Returns:
            Process statistics or None if failed
        """
        try:
            stats = await self._execute_circus_command("stats", name=process_name)
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats for {process_name}: {str(e)}")
            return None
    
    async def get_all_process_info(self) -> Dict[str, Any]:
        """
        Get information about all processes from Circus.
        
        Returns:
            Dictionary with process information
        """
        try:
            # Get list of watchers
            list_response = await self._execute_circus_command("list")
            if not list_response:
                return {}
            
            watchers = list_response.get("watchers", [])
            process_info = {}
            
            # Get detailed info for each watcher
            for watcher in watchers:
                watcher_name = watcher.get("name")
                if watcher_name:
                    stats = await self.get_process_stats(watcher_name)
                    if stats:
                        process_info[watcher_name] = {
                            "watcher_info": watcher,
                            "stats": stats
                        }
            
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to get all process info: {str(e)}")
            return {}
    
    def add_event_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add an event callback."""
        self._event_callbacks.append(callback)
        logger.debug(f"Added event callback: {callback.__name__}")
    
    def remove_event_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove an event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
            logger.debug(f"Removed event callback: {callback.__name__}")
    
    async def _notify_event_callbacks(self, event: Dict[str, Any]) -> None:
        """Notify event callbacks."""
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {str(e)}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.
        
        Returns:
            System status information
        """
        return {
            "circus_manager": {
                "initialized": self._initialized,
                "connected": self._connected,
                "endpoint": self._endpoint,
            },
            "configuration": self.config_handler.get_config_summary(),
            "process_watcher": self.process_watcher.get_monitoring_status(),
            "performance_stats": self._performance_stats.copy(),
            "system_info": get_system_info(),
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources - much simpler with Circus client."""
        try:
            # Stop process monitoring
            if hasattr(self, 'process_watcher'):
                await self.process_watcher.stop_monitoring()
            
            # Close Circus client connection
            if self._circus_client:
                # CircusClient handles cleanup automatically
                self._circus_client = None
            
            self._connected = False
            self._initialized = False
            
            logger.info("CircusManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()