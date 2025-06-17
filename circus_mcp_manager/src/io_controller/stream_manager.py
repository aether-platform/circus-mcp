"""
Stream manager for coordinating I/O operations.
"""

import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from collections import deque

from ..utils.exceptions import IOControllerError, StreamError


logger = logging.getLogger(__name__)


class StreamManager:
    """Manages input/output streams for processes."""
    
    def __init__(self, buffer_size: int = 8192, max_queue_size: int = 1000) -> None:
        """Initialize stream manager."""
        self._input_handlers: Dict[str, Any] = {}
        self._output_monitors: Dict[str, Any] = {}
        self._stream_callbacks: Dict[str, List[Callable]] = {}
        self._active_streams: Dict[str, bool] = {}
        
        # Enhanced buffering and streaming
        self._buffer_size = buffer_size
        self._max_queue_size = max_queue_size
        self._input_queues: Dict[str, asyncio.Queue] = {}
        self._output_buffers: Dict[str, deque] = {}
        self._stream_tasks: Dict[str, List[asyncio.Task]] = {}
        
        # Performance monitoring
        self._stream_stats: Dict[str, Dict[str, Any]] = {}
        
        # Error recovery
        self._retry_counts: Dict[str, int] = {}
        self._max_retries = 3
    
    async def register_process(self, process_name: str, process_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a process for stream management.
        
        Args:
            process_name: Name of the process
            process_config: Process configuration
        """
        if process_name in self._active_streams:
            logger.warning(f"Process {process_name} already registered")
            return
        
        self._active_streams[process_name] = False
        self._stream_callbacks[process_name] = []
        self._input_queues[process_name] = asyncio.Queue(maxsize=self._max_queue_size)
        self._output_buffers[process_name] = deque(maxlen=1000)  # Keep last 1000 output lines
        self._stream_tasks[process_name] = []
        self._retry_counts[process_name] = 0
        
        # Initialize stream statistics
        self._stream_stats[process_name] = {
            "bytes_sent": 0,
            "bytes_received": 0,
            "lines_processed": 0,
            "errors": 0,
            "last_activity": None,
            "uptime": 0,
            "config": process_config or {},
        }
        
        logger.info(f"Registered process for stream management: {process_name}")
    
    async def unregister_process(self, process_name: str) -> None:
        """
        Unregister a process from stream management.
        
        Args:
            process_name: Name of the process
        """
        if process_name not in self._active_streams:
            return
        
        # Stop streams if active
        if self._active_streams[process_name]:
            await self.stop_streams(process_name)
        
        # Cancel all tasks for this process
        tasks = self._stream_tasks.get(process_name, [])
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Clean up
        self._active_streams.pop(process_name, None)
        self._stream_callbacks.pop(process_name, None)
        self._input_handlers.pop(process_name, None)
        self._output_monitors.pop(process_name, None)
        self._input_queues.pop(process_name, None)
        self._output_buffers.pop(process_name, None)
        self._stream_tasks.pop(process_name, None)
        self._stream_stats.pop(process_name, None)
        self._retry_counts.pop(process_name, None)
        
        logger.info(f"Unregistered process from stream management: {process_name}")
    
    async def start_streams(self, process_name: str) -> bool:
        """
        Start I/O streams for a process.
        
        Args:
            process_name: Name of the process
            
        Returns:
            True if streams started successfully
        """
        if process_name not in self._active_streams:
            raise IOControllerError(f"Process {process_name} not registered")
        
        if self._active_streams[process_name]:
            logger.warning(f"Streams already active for process {process_name}")
            return True
        
        try:
            # This is a placeholder implementation
            # In a real implementation, this would:
            # 1. Create input handler for the process
            # 2. Create output monitor for the process
            # 3. Start monitoring streams
            
            logger.info(f"Starting streams for process: {process_name}")
            
            # Mock stream initialization
            self._input_handlers[process_name] = {
                "initialized": True,
                "queue_size": 0,
            }
            
            self._output_monitors[process_name] = {
                "initialized": True,
                "lines_processed": 0,
            }
            
            self._active_streams[process_name] = True
            
            # Notify callbacks
            await self._notify_callbacks(process_name, "streams_started", {})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streams for {process_name}: {str(e)}")
            return False
    
    async def stop_streams(self, process_name: str) -> bool:
        """
        Stop I/O streams for a process.
        
        Args:
            process_name: Name of the process
            
        Returns:
            True if streams stopped successfully
        """
        if process_name not in self._active_streams:
            return True
        
        if not self._active_streams[process_name]:
            return True
        
        try:
            logger.info(f"Stopping streams for process: {process_name}")
            
            # Clean up handlers and monitors
            self._input_handlers.pop(process_name, None)
            self._output_monitors.pop(process_name, None)
            
            self._active_streams[process_name] = False
            
            # Notify callbacks
            await self._notify_callbacks(process_name, "streams_stopped", {})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop streams for {process_name}: {str(e)}")
            return False
    
    async def send_input(self, process_name: str, data: str) -> bool:
        """
        Send input to a process.
        
        Args:
            process_name: Name of the process
            data: Data to send
            
        Returns:
            True if input sent successfully
        """
        if process_name not in self._active_streams:
            raise IOControllerError(f"Process {process_name} not registered")
        
        if not self._active_streams[process_name]:
            raise IOControllerError(f"Streams not active for process {process_name}")
        
        try:
            # This is a placeholder implementation
            # In a real implementation, this would send data to the process stdin
            
            logger.debug(f"Sending input to {process_name}: {data[:100]}...")
            
            # Update input handler stats
            if process_name in self._input_handlers:
                self._input_handlers[process_name]["queue_size"] += 1
            
            # Notify callbacks
            await self._notify_callbacks(process_name, "input_sent", {
                "data_length": len(data),
                "timestamp": datetime.now().isoformat(),
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send input to {process_name}: {str(e)}")
            return False
    
    def add_stream_callback(
        self, 
        process_name: str, 
        callback: Callable[[str, str, Dict[str, Any]], None]
    ) -> None:
        """
        Add a callback for stream events.
        
        Args:
            process_name: Name of the process
            callback: Callback function (process_name, event_type, data)
        """
        if process_name not in self._stream_callbacks:
            self._stream_callbacks[process_name] = []
        
        self._stream_callbacks[process_name].append(callback)
        logger.debug(f"Added stream callback for {process_name}")
    
    def remove_stream_callback(
        self, 
        process_name: str, 
        callback: Callable[[str, str, Dict[str, Any]], None]
    ) -> None:
        """
        Remove a stream callback.
        
        Args:
            process_name: Name of the process
            callback: Callback function to remove
        """
        if process_name in self._stream_callbacks:
            callbacks = self._stream_callbacks[process_name]
            if callback in callbacks:
                callbacks.remove(callback)
                logger.debug(f"Removed stream callback for {process_name}")
    
    async def _notify_callbacks(
        self, 
        process_name: str, 
        event_type: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        Notify callbacks about stream events.
        
        Args:
            process_name: Name of the process
            event_type: Type of event
            data: Event data
        """
        callbacks = self._stream_callbacks.get(process_name, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(process_name, event_type, data)
                else:
                    callback(process_name, event_type, data)
            except Exception as e:
                logger.error(f"Error in stream callback: {str(e)}")
    
    def get_stream_status(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get stream status information.
        
        Args:
            process_name: Specific process name, or None for all processes
            
        Returns:
            Stream status information
        """
        if process_name:
            if process_name not in self._active_streams:
                return {}
            
            return {
                "active": self._active_streams[process_name],
                "input_handler": self._input_handlers.get(process_name, {}),
                "output_monitor": self._output_monitors.get(process_name, {}),
                "callbacks": len(self._stream_callbacks.get(process_name, [])),
            }
        else:
            # Return status for all processes
            status = {}
            for proc_name in self._active_streams:
                status[proc_name] = self.get_stream_status(proc_name)
            
            return {
                "processes": status,
                "total_processes": len(self._active_streams),
                "active_processes": sum(1 for active in self._active_streams.values() if active),
            }
    
    async def cleanup(self) -> None:
        """Clean up all streams and resources."""
        try:
            # Stop all active streams
            for process_name in list(self._active_streams.keys()):
                if self._active_streams[process_name]:
                    await self.stop_streams(process_name)
            
            # Clear all data structures
            self._active_streams.clear()
            self._stream_callbacks.clear()
            self._input_handlers.clear()
            self._output_monitors.clear()
            
            logger.info("Stream manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during stream manager cleanup: {str(e)}")