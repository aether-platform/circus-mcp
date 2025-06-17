"""
Output monitor for capturing and processing process output.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from ..utils.exceptions import IOControllerError


logger = logging.getLogger(__name__)


class OutputMonitor:
    """Monitors standard output and error streams from processes."""
    
    def __init__(self, process_name: str) -> None:
        """
        Initialize output monitor.
        
        Args:
            process_name: Name of the target process
        """
        self.process_name = process_name
        self._monitoring = False
        self._stdout_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        
        # Output callbacks
        self._stdout_callbacks: List[Callable[[str], None]] = []
        self._stderr_callbacks: List[Callable[[str], None]] = []
        
        # Buffer for recent output
        self._stdout_buffer: List[str] = []
        self._stderr_buffer: List[str] = []
        self._buffer_max_size = 1000
        
        # Statistics
        self._stats = {
            "stdout_lines": 0,
            "stderr_lines": 0,
            "total_bytes_stdout": 0,
            "total_bytes_stderr": 0,
            "monitoring_start_time": None,
            "last_output_time": None,
        }
    
    async def start_monitoring(self) -> None:
        """Start monitoring process output."""
        if self._monitoring:
            logger.warning(f"Output monitor already running for {self.process_name}")
            return
        
        self._monitoring = True
        self._stats["monitoring_start_time"] = datetime.now().isoformat()
        
        # This is a placeholder implementation
        # In a real implementation, this would:
        # 1. Get process stdout and stderr pipes
        # 2. Start monitoring tasks for each stream
        
        logger.info(f"Started output monitoring for {self.process_name}")
        
        # Start monitoring tasks (placeholder)
        self._stdout_task = asyncio.create_task(self._monitor_stdout())
        self._stderr_task = asyncio.create_task(self._monitor_stderr())
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring process output."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        # Cancel monitoring tasks
        if self._stdout_task:
            self._stdout_task.cancel()
            try:
                await self._stdout_task
            except asyncio.CancelledError:
                pass
            self._stdout_task = None
        
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
            self._stderr_task = None
        
        logger.info(f"Stopped output monitoring for {self.process_name}")
    
    async def _monitor_stdout(self) -> None:
        """Monitor stdout stream."""
        try:
            while self._monitoring:
                # This is a placeholder implementation
                # In a real implementation, this would read from process.stdout
                
                # Simulate reading output
                await asyncio.sleep(1.0)
                
                # Mock output for demonstration
                if self._monitoring:
                    mock_output = f"[{datetime.now().isoformat()}] Mock stdout output from {self.process_name}"
                    await self._process_stdout_line(mock_output)
                
        except asyncio.CancelledError:
            logger.debug(f"Stdout monitoring cancelled for {self.process_name}")
        except Exception as e:
            logger.error(f"Error monitoring stdout for {self.process_name}: {str(e)}")
    
    async def _monitor_stderr(self) -> None:
        """Monitor stderr stream."""
        try:
            while self._monitoring:
                # This is a placeholder implementation
                # In a real implementation, this would read from process.stderr
                
                # Simulate reading error output occasionally
                await asyncio.sleep(5.0)
                
                # Mock error output for demonstration
                if self._monitoring:
                    mock_error = f"[{datetime.now().isoformat()}] Mock stderr output from {self.process_name}"
                    await self._process_stderr_line(mock_error)
                
        except asyncio.CancelledError:
            logger.debug(f"Stderr monitoring cancelled for {self.process_name}")
        except Exception as e:
            logger.error(f"Error monitoring stderr for {self.process_name}: {str(e)}")
    
    async def _process_stdout_line(self, line: str) -> None:
        """
        Process a line from stdout.
        
        Args:
            line: Output line
        """
        try:
            # Update statistics
            self._stats["stdout_lines"] += 1
            self._stats["total_bytes_stdout"] += len(line.encode('utf-8'))
            self._stats["last_output_time"] = datetime.now().isoformat()
            
            # Add to buffer
            self._add_to_buffer(self._stdout_buffer, line)
            
            # Notify callbacks
            await self._notify_stdout_callbacks(line)
            
        except Exception as e:
            logger.error(f"Error processing stdout line: {str(e)}")
    
    async def _process_stderr_line(self, line: str) -> None:
        """
        Process a line from stderr.
        
        Args:
            line: Error output line
        """
        try:
            # Update statistics
            self._stats["stderr_lines"] += 1
            self._stats["total_bytes_stderr"] += len(line.encode('utf-8'))
            self._stats["last_output_time"] = datetime.now().isoformat()
            
            # Add to buffer
            self._add_to_buffer(self._stderr_buffer, line)
            
            # Notify callbacks
            await self._notify_stderr_callbacks(line)
            
        except Exception as e:
            logger.error(f"Error processing stderr line: {str(e)}")
    
    def _add_to_buffer(self, buffer: List[str], line: str) -> None:
        """
        Add line to buffer with size limit.
        
        Args:
            buffer: Buffer to add to
            line: Line to add
        """
        buffer.append(line)
        
        # Maintain buffer size limit
        if len(buffer) > self._buffer_max_size:
            buffer.pop(0)
    
    async def _notify_stdout_callbacks(self, line: str) -> None:
        """
        Notify stdout callbacks.
        
        Args:
            line: Output line
        """
        for callback in self._stdout_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(line)
                else:
                    callback(line)
            except Exception as e:
                logger.error(f"Error in stdout callback: {str(e)}")
    
    async def _notify_stderr_callbacks(self, line: str) -> None:
        """
        Notify stderr callbacks.
        
        Args:
            line: Error output line
        """
        for callback in self._stderr_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(line)
                else:
                    callback(line)
            except Exception as e:
                logger.error(f"Error in stderr callback: {str(e)}")
    
    def add_stdout_callback(self, callback: Callable[[str], None]) -> None:
        """
        Add callback for stdout output.
        
        Args:
            callback: Callback function
        """
        self._stdout_callbacks.append(callback)
        logger.debug(f"Added stdout callback for {self.process_name}")
    
    def add_stderr_callback(self, callback: Callable[[str], None]) -> None:
        """
        Add callback for stderr output.
        
        Args:
            callback: Callback function
        """
        self._stderr_callbacks.append(callback)
        logger.debug(f"Added stderr callback for {self.process_name}")
    
    def remove_stdout_callback(self, callback: Callable[[str], None]) -> None:
        """
        Remove stdout callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._stdout_callbacks:
            self._stdout_callbacks.remove(callback)
            logger.debug(f"Removed stdout callback for {self.process_name}")
    
    def remove_stderr_callback(self, callback: Callable[[str], None]) -> None:
        """
        Remove stderr callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._stderr_callbacks:
            self._stderr_callbacks.remove(callback)
            logger.debug(f"Removed stderr callback for {self.process_name}")
    
    def get_recent_stdout(self, lines: int = 100) -> List[str]:
        """
        Get recent stdout lines.
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of recent stdout lines
        """
        return self._stdout_buffer[-lines:] if lines > 0 else self._stdout_buffer.copy()
    
    def get_recent_stderr(self, lines: int = 100) -> List[str]:
        """
        Get recent stderr lines.
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of recent stderr lines
        """
        return self._stderr_buffer[-lines:] if lines > 0 else self._stderr_buffer.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get output monitoring statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        stats.update({
            "process_name": self.process_name,
            "monitoring": self._monitoring,
            "stdout_callbacks": len(self._stdout_callbacks),
            "stderr_callbacks": len(self._stderr_callbacks),
            "stdout_buffer_size": len(self._stdout_buffer),
            "stderr_buffer_size": len(self._stderr_buffer),
        })
        return stats
    
    def clear_buffers(self) -> None:
        """Clear output buffers."""
        stdout_cleared = len(self._stdout_buffer)
        stderr_cleared = len(self._stderr_buffer)
        
        self._stdout_buffer.clear()
        self._stderr_buffer.clear()
        
        logger.info(f"Cleared output buffers for {self.process_name}: "
                   f"{stdout_cleared} stdout, {stderr_cleared} stderr lines")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_monitoring()