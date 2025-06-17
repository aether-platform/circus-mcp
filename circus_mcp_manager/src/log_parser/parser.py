"""
Main log parser implementation.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path

from ..utils.exceptions import LogParserError
from .patterns import PatternManager
from .classifier import LogClassifier


logger = logging.getLogger(__name__)


class LogParser:
    """Main log parser for processing and classifying logs."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize log parser.

        Args:
            config_path: Path to log patterns configuration
        """
        self.pattern_manager = PatternManager(config_path)
        self.classifier = LogClassifier(self.pattern_manager)

        # Parser state
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._processing_stats = {
            "total_processed": 0,
            "processing_errors": 0,
            "start_time": datetime.now(),
            "level_counts": {},
            "process_counts": {},
            "pattern_matches": {},
            "processing_rate": 0.0,
        }

        # Batch processing
        self._batch_size = 100
        self._batch_buffer: List[str] = []
        self._batch_process_name = ""

        # Performance optimization
        self._last_stats_update = datetime.now()
        self._processing_queue = asyncio.Queue(maxsize=1000)
        self._processing_task: Optional[asyncio.Task] = None

    async def parse_log_line(
        self,
        log_line: str,
        process_name: str = "unknown",
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Parse and classify a single log line.

        Args:
            log_line: Raw log line
            process_name: Name of the process that generated the log
            timestamp: Log timestamp

        Returns:
            Parsed and classified log entry
        """
        try:
            # Clean up log line
            cleaned_line = log_line.strip()
            if not cleaned_line:
                return {}

            # Classify the log entry
            classified_entry = self.classifier.classify_log_entry(
                cleaned_line, process_name, timestamp
            )

            # Update processing stats
            self._processing_stats["total_processed"] += 1
            self._update_detailed_stats(classified_entry)

            # Notify callbacks
            await self._notify_callbacks(classified_entry)

            return classified_entry

        except Exception as e:
            self._processing_stats["processing_errors"] += 1
            logger.error(f"Error parsing log line: {str(e)}")
            raise LogParserError(f"Failed to parse log line: {str(e)}")

    async def parse_log_batch(
        self, log_lines: List[str], process_name: str = "unknown"
    ) -> List[Dict[str, Any]]:
        """
        Parse and classify a batch of log lines.

        Args:
            log_lines: List of raw log lines
            process_name: Name of the process that generated the logs

        Returns:
            List of parsed and classified log entries
        """
        parsed_entries = []

        for line in log_lines:
            try:
                parsed_entry = await self.parse_log_line(line, process_name)
                if parsed_entry:  # Skip empty entries
                    parsed_entries.append(parsed_entry)
            except LogParserError as e:
                logger.error(f"Error in batch parsing: {str(e)}")
                # Continue processing other lines
                continue

        return parsed_entries

    async def parse_log_stream(
        self, log_stream: asyncio.StreamReader, process_name: str = "unknown"
    ) -> None:
        """
        Parse logs from a stream continuously.

        Args:
            log_stream: Async stream reader
            process_name: Name of the process
        """
        try:
            while True:
                line = await log_stream.readline()
                if not line:
                    break

                try:
                    decoded_line = line.decode("utf-8", errors="replace")
                    await self.parse_log_line(decoded_line, process_name)
                except Exception as e:
                    logger.error(f"Error processing stream line: {str(e)}")
                    continue

        except asyncio.CancelledError:
            logger.info(f"Log stream parsing cancelled for {process_name}")
        except Exception as e:
            logger.error(f"Error in log stream parsing: {str(e)}")
            raise LogParserError(f"Stream parsing failed: {str(e)}")

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback for processed log entries.

        Args:
            callback: Callback function that receives parsed log entry
        """
        self._callbacks.append(callback)
        logger.debug(f"Added log parser callback: {callback.__name__}")

    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Removed log parser callback: {callback.__name__}")

    async def _notify_callbacks(self, log_entry: Dict[str, Any]) -> None:
        """
        Notify all callbacks about a processed log entry.

        Args:
            log_entry: Processed log entry
        """
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(log_entry)
                else:
                    callback(log_entry)
            except Exception as e:
                logger.error(
                    f"Error in log parser callback {callback.__name__}: {str(e)}"
                )

    def _update_detailed_stats(self, log_entry: Dict[str, Any]) -> None:
        """
        Update detailed processing statistics.

        Args:
            log_entry: Processed log entry
        """
        # Update level counts
        level = log_entry.get("level", "unknown")
        self._processing_stats["level_counts"][level] = (
            self._processing_stats["level_counts"].get(level, 0) + 1
        )

        # Update process counts
        process_name = log_entry.get("process_name", "unknown")
        self._processing_stats["process_counts"][process_name] = (
            self._processing_stats["process_counts"].get(process_name, 0) + 1
        )

        # Update pattern match counts
        matched_patterns = log_entry.get("matched_patterns", [])
        for pattern in matched_patterns:
            self._processing_stats["pattern_matches"][pattern] = (
                self._processing_stats["pattern_matches"].get(pattern, 0) + 1
            )

        # Update processing rate (every 10 seconds)
        now = datetime.now()
        if (now - self._last_stats_update).total_seconds() >= 10:
            elapsed = (now - self._processing_stats["start_time"]).total_seconds()
            if elapsed > 0:
                self._processing_stats["processing_rate"] = (
                    self._processing_stats["total_processed"] / elapsed
                )
            self._last_stats_update = now

    async def start_background_processing(self) -> None:
        """Start background processing task for better performance."""
        if self._processing_task and not self._processing_task.done():
            logger.warning("Background processing already running")
            return

        self._processing_task = asyncio.create_task(self._background_processor())
        logger.info("Started background log processing")

    async def stop_background_processing(self) -> None:
        """Stop background processing task."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Stopped background log processing")

    async def _background_processor(self) -> None:
        """Background processing loop for high-throughput scenarios."""
        try:
            while True:
                try:
                    # Get log entry from queue with timeout
                    log_data = await asyncio.wait_for(
                        self._processing_queue.get(), timeout=1.0
                    )

                    log_line, process_name, timestamp = log_data

                    # Process the log entry
                    await self.parse_log_line(log_line, process_name, timestamp)

                    # Mark task as done
                    self._processing_queue.task_done()

                except asyncio.TimeoutError:
                    # Timeout is normal, continue processing
                    continue
                except Exception as e:
                    logger.error(f"Error in background processor: {str(e)}")
                    continue

        except asyncio.CancelledError:
            logger.info("Background processor cancelled")
        except Exception as e:
            logger.error(f"Background processor error: {str(e)}")

    async def queue_log_for_processing(
        self,
        log_line: str,
        process_name: str = "unknown",
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Queue a log line for background processing.

        Args:
            log_line: Raw log line
            process_name: Name of the process
            timestamp: Log timestamp

        Returns:
            True if queued successfully
        """
        try:
            # Try to put in queue without blocking
            self._processing_queue.put_nowait((log_line, process_name, timestamp))
            return True
        except asyncio.QueueFull:
            logger.warning("Processing queue is full, dropping log entry")
            return False

    async def parse_log_batch_optimized(
        self, log_lines: List[str], process_name: str = "unknown"
    ) -> List[Dict[str, Any]]:
        """
        Optimized batch parsing with parallel processing.

        Args:
            log_lines: List of raw log lines
            process_name: Name of the process

        Returns:
            List of parsed and classified log entries
        """
        if not log_lines:
            return []

        # Process in chunks for better memory management
        chunk_size = min(self._batch_size, len(log_lines))
        parsed_entries = []

        for i in range(0, len(log_lines), chunk_size):
            chunk = log_lines[i : i + chunk_size]

            # Process chunk in parallel
            tasks = [self.parse_log_line(line, process_name) for line in chunk]

            try:
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and empty entries
                for result in chunk_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error in batch parsing: {str(result)}")
                        continue
                    if result:  # Skip empty entries
                        parsed_entries.append(result)

            except Exception as e:
                logger.error(f"Error in optimized batch parsing: {str(e)}")
                continue

        return parsed_entries

    def add_to_batch_buffer(self, log_line: str, process_name: str = "unknown") -> None:
        """
        Add log line to batch buffer for efficient processing.

        Args:
            log_line: Raw log line
            process_name: Name of the process
        """
        self._batch_buffer.append(log_line)
        self._batch_process_name = process_name

        # Process batch when buffer is full
        if len(self._batch_buffer) >= self._batch_size:
            asyncio.create_task(self._process_batch_buffer())

    async def _process_batch_buffer(self) -> None:
        """Process the current batch buffer."""
        if not self._batch_buffer:
            return

        try:
            # Process the batch
            await self.parse_log_batch_optimized(
                self._batch_buffer.copy(), self._batch_process_name
            )

            # Clear buffer
            self._batch_buffer.clear()

        except Exception as e:
            logger.error(f"Error processing batch buffer: {str(e)}")
            # Clear buffer even on error to prevent memory leak
            self._batch_buffer.clear()

    async def flush_batch_buffer(self) -> None:
        """Flush any remaining entries in the batch buffer."""
        if self._batch_buffer:
            await self._process_batch_buffer()

    def filter_logs(
        self,
        log_entries: List[Dict[str, Any]],
        level: Optional[str] = None,
        process_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter log entries based on criteria.

        Args:
            log_entries: List of log entries to filter
            level: Log level filter
            process_name: Process name filter
            start_time: Start time filter
            end_time: End time filter

        Returns:
            Filtered log entries
        """
        filtered_entries = []

        for entry in log_entries:
            # Level filter
            if level and entry.get("level") != level:
                continue

            # Process name filter
            if process_name and entry.get("process_name") != process_name:
                continue

            # Time range filter
            if start_time or end_time:
                entry_time_str = entry.get("timestamp")
                if entry_time_str:
                    try:
                        entry_time = datetime.fromisoformat(entry_time_str)
                        if start_time and entry_time < start_time:
                            continue
                        if end_time and entry_time > end_time:
                            continue
                    except ValueError:
                        # Skip entries with invalid timestamps
                        continue

            filtered_entries.append(entry)

        return filtered_entries

    def get_log_summary(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for log entries.

        Args:
            log_entries: List of log entries

        Returns:
            Log summary statistics
        """
        if not log_entries:
            return {"total_entries": 0}

        # Count by level
        level_counts = {}
        process_counts = {}

        earliest_time = None
        latest_time = None

        for entry in log_entries:
            # Count by level
            level = entry.get("level", "unknown")
            level_counts[level] = level_counts.get(level, 0) + 1

            # Count by process
            process = entry.get("process_name", "unknown")
            process_counts[process] = process_counts.get(process, 0) + 1

            # Track time range
            timestamp_str = entry.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if earliest_time is None or timestamp < earliest_time:
                        earliest_time = timestamp
                    if latest_time is None or timestamp > latest_time:
                        latest_time = timestamp
                except ValueError:
                    continue

        return {
            "total_entries": len(log_entries),
            "level_distribution": level_counts,
            "process_distribution": process_counts,
            "time_range": {
                "earliest": earliest_time.isoformat() if earliest_time else None,
                "latest": latest_time.isoformat() if latest_time else None,
            },
        }

    def get_parser_stats(self) -> Dict[str, Any]:
        """
        Get parser statistics.

        Returns:
            Parser statistics
        """
        current_time = datetime.now()
        uptime = current_time - self._processing_stats["start_time"]

        stats = self._processing_stats.copy()
        stats.update(
            {
                "uptime_seconds": uptime.total_seconds(),
                "callbacks_registered": len(self._callbacks),
                "classification_stats": self.classifier.get_classification_stats(),
                "pattern_stats": self.pattern_manager.get_pattern_stats(),
            }
        )

        return stats

    def reset_stats(self) -> None:
        """Reset parser statistics."""
        self._processing_stats = {
            "total_processed": 0,
            "processing_errors": 0,
            "start_time": datetime.now(),
        }
        self.classifier.reset_stats()
        logger.info("Parser statistics reset")

    def reload_patterns(self) -> None:
        """Reload log patterns from configuration."""
        self.pattern_manager.reload_patterns()
        logger.info("Log patterns reloaded")

    def validate_configuration(self) -> List[str]:
        """
        Validate parser configuration.

        Returns:
            List of validation errors
        """
        errors = []

        # Validate patterns
        pattern_errors = self.pattern_manager.validate_patterns()
        errors.extend(pattern_errors)

        return errors
