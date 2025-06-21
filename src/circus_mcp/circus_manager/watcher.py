"""
Process watcher for monitoring Circus processes.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum

from ..utils.exceptions import ProcessNotFoundError, CircusManagerError


logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Process status enumeration."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    UNKNOWN = "unknown"


class ProcessInfo:
    """Information about a process."""

    def __init__(
        self,
        name: str,
        pid: Optional[int] = None,
        status: ProcessStatus = ProcessStatus.UNKNOWN,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
        started_at: Optional[datetime] = None,
        **kwargs,
    ) -> None:
        self.name = name
        self.pid = pid
        self.status = status
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.started_at = started_at
        self.extra_info = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "pid": self.pid,
            "status": self.status.value,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "extra_info": self.extra_info,
        }


class ProcessWatcher:
    """Watches and monitors Circus processes."""

    def __init__(self) -> None:
        """Initialize process watcher."""
        self._processes: Dict[str, ProcessInfo] = {}
        self._callbacks: List[Callable[[str, ProcessInfo], None]] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 5.0  # seconds

    def add_process(
        self, process_name: str, initial_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a process to watch.

        Args:
            process_name: Name of the process
            initial_info: Initial process information
        """
        info = initial_info or {}
        self._processes[process_name] = ProcessInfo(name=process_name, **info)
        logger.info(f"Added process to watch: {process_name}")

    def remove_process(self, process_name: str) -> None:
        """
        Remove a process from watching.

        Args:
            process_name: Name of the process

        Raises:
            ProcessNotFoundError: If process is not being watched
        """
        if process_name not in self._processes:
            raise ProcessNotFoundError(process_name)

        del self._processes[process_name]
        logger.info(f"Removed process from watch: {process_name}")

    def get_process_info(self, process_name: str) -> ProcessInfo:
        """
        Get information about a specific process.

        Args:
            process_name: Name of the process

        Returns:
            Process information

        Raises:
            ProcessNotFoundError: If process is not being watched
        """
        if process_name not in self._processes:
            raise ProcessNotFoundError(process_name)

        return self._processes[process_name]

    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """
        Get information about all watched processes.

        Returns:
            Dictionary of process information
        """
        return self._processes.copy()

    def update_process_info(self, process_name: str, **kwargs) -> None:
        """
        Update process information.

        Args:
            process_name: Name of the process
            **kwargs: Information to update

        Raises:
            ProcessNotFoundError: If process is not being watched
        """
        if process_name not in self._processes:
            raise ProcessNotFoundError(process_name)

        process_info = self._processes[process_name]

        # Update known fields
        if "pid" in kwargs:
            process_info.pid = kwargs["pid"]
        if "status" in kwargs:
            if isinstance(kwargs["status"], str):
                try:
                    process_info.status = ProcessStatus(kwargs["status"])
                except ValueError:
                    process_info.status = ProcessStatus.UNKNOWN
            elif isinstance(kwargs["status"], ProcessStatus):
                process_info.status = kwargs["status"]
        if "cpu_percent" in kwargs:
            process_info.cpu_percent = float(kwargs["cpu_percent"])
        if "memory_percent" in kwargs:
            process_info.memory_percent = float(kwargs["memory_percent"])
        if "started_at" in kwargs:
            process_info.started_at = kwargs["started_at"]

        # Update extra info
        for key, value in kwargs.items():
            if key not in [
                "pid",
                "status",
                "cpu_percent",
                "memory_percent",
                "started_at",
            ]:
                process_info.extra_info[key] = value

        # Notify callbacks
        self._notify_callbacks(process_name, process_info)

    def add_callback(self, callback: Callable[[str, ProcessInfo], None]) -> None:
        """
        Add a callback for process updates.

        Args:
            callback: Callback function that receives (process_name, process_info)
        """
        self._callbacks.append(callback)
        logger.debug(f"Added process watcher callback: {callback.__name__}")

    def remove_callback(self, callback: Callable[[str, ProcessInfo], None]) -> None:
        """
        Remove a callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Removed process watcher callback: {callback.__name__}")

    def _notify_callbacks(self, process_name: str, process_info: ProcessInfo) -> None:
        """
        Notify all callbacks about process update.

        Args:
            process_name: Name of the process
            process_info: Updated process information
        """
        for callback in self._callbacks:
            try:
                callback(process_name, process_info)
            except Exception as e:
                logger.error(
                    f"Error in process watcher callback {callback.__name__}: {str(e)}"
                )

    async def start_monitoring(self, interval: float = 5.0) -> None:
        """
        Start monitoring processes.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring:
            logger.warning("Process monitoring is already running")
            return

        self._monitor_interval = interval
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Started process monitoring with {interval}s interval")

    async def stop_monitoring(self) -> None:
        """Stop monitoring processes."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("Stopped process monitoring")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self._update_all_processes()
                await asyncio.sleep(self._monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self._monitor_interval)

    async def _update_all_processes(self) -> None:
        """Update information for all processes."""
        # This is a placeholder implementation
        # In a real implementation, this would query Circus for actual process status
        for process_name in list(self._processes.keys()):
            try:
                # Simulate process status update
                # In real implementation, this would use circus client to get actual status
                current_info = self._processes[process_name]

                # For now, just update timestamp to show monitoring is working
                self.update_process_info(process_name, last_checked=datetime.now())

            except Exception as e:
                logger.error(f"Error updating process {process_name}: {str(e)}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get monitoring status information.

        Returns:
            Monitoring status dictionary
        """
        return {
            "monitoring": self._monitoring,
            "interval": self._monitor_interval,
            "watched_processes": len(self._processes),
            "callbacks": len(self._callbacks),
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_monitoring()
