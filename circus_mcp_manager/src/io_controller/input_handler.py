"""
Input handler for managing process standard input.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Queue
from datetime import datetime

from ..utils.exceptions import IOControllerError
from ..utils.helpers import sanitize_input


logger = logging.getLogger(__name__)


class InputHandler:
    """Handles standard input for processes."""

    def __init__(self, process_name: str) -> None:
        """
        Initialize input handler.

        Args:
            process_name: Name of the target process
        """
        self.process_name = process_name
        self._input_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._processor_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            "total_inputs": 0,
            "queue_size": 0,
            "processing_errors": 0,
            "last_input_time": None,
        }

    async def start(self) -> None:
        """Start input processing."""
        if self._processing:
            logger.warning(f"Input handler already running for {self.process_name}")
            return

        self._processing = True
        self._processor_task = asyncio.create_task(self._process_input_queue())
        logger.info(f"Started input handler for {self.process_name}")

    async def stop(self) -> None:
        """Stop input processing."""
        if not self._processing:
            return

        self._processing = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None

        logger.info(f"Stopped input handler for {self.process_name}")

    async def send_input(self, data: str) -> bool:
        """
        Queue input data to be sent to the process.

        Args:
            data: Input data to send

        Returns:
            True if input was queued successfully
        """
        try:
            # Sanitize input
            sanitized_data = sanitize_input(data)

            # Add to queue
            await self._input_queue.put(
                {
                    "data": sanitized_data,
                    "timestamp": datetime.now(),
                    "original_length": len(data),
                    "sanitized_length": len(sanitized_data),
                }
            )

            # Update statistics
            self._stats["total_inputs"] += 1
            self._stats["queue_size"] = self._input_queue.qsize()
            self._stats["last_input_time"] = datetime.now().isoformat()

            logger.debug(
                f"Queued input for {self.process_name}: {len(sanitized_data)} chars"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to queue input for {self.process_name}: {str(e)}")
            self._stats["processing_errors"] += 1
            return False

    async def _process_input_queue(self) -> None:
        """Process queued input data."""
        while self._processing:
            try:
                # Wait for input with timeout
                try:
                    input_item = await asyncio.wait_for(
                        self._input_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process the input
                await self._send_to_process(input_item)

                # Update queue size
                self._stats["queue_size"] = self._input_queue.qsize()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error processing input queue for {self.process_name}: {str(e)}"
                )
                self._stats["processing_errors"] += 1
                await asyncio.sleep(0.1)  # Brief pause on error

    async def _send_to_process(self, input_item: Dict[str, Any]) -> None:
        """
        Send input data to the actual process.

        Args:
            input_item: Input item from queue
        """
        try:
            data = input_item["data"]

            # This is a placeholder implementation
            # In a real implementation, this would:
            # 1. Get the process stdin pipe
            # 2. Write data to the pipe
            # 3. Flush the pipe

            logger.debug(f"Sending input to {self.process_name}: {data[:50]}...")

            # Simulate sending to process
            # In real implementation: process.stdin.write(data.encode() + b'\n')
            # await process.stdin.drain()

        except Exception as e:
            logger.error(
                f"Failed to send input to process {self.process_name}: {str(e)}"
            )
            raise IOControllerError(f"Input send failed: {str(e)}")

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._input_queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get input handler statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        stats.update(
            {
                "process_name": self.process_name,
                "processing": self._processing,
                "current_queue_size": self._input_queue.qsize(),
            }
        )
        return stats

    def clear_queue(self) -> int:
        """
        Clear the input queue.

        Returns:
            Number of items cleared
        """
        cleared_count = 0

        try:
            while not self._input_queue.empty():
                try:
                    self._input_queue.get_nowait()
                    cleared_count += 1
                except asyncio.QueueEmpty:
                    break
        except Exception as e:
            logger.error(f"Error clearing input queue: {str(e)}")

        self._stats["queue_size"] = 0
        logger.info(
            f"Cleared {cleared_count} items from input queue for {self.process_name}"
        )

        return cleared_count

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
