"""
Tests for enhanced LogParser functionality.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from src.log_parser.parser import LogParser
from src.utils.exceptions import LogParserError


@pytest.fixture
def mock_pattern_manager():
    """Mock pattern manager."""
    mock = Mock()
    mock.validate_patterns.return_value = []
    mock.get_pattern_stats.return_value = {"patterns_loaded": 5}
    mock.reload_patterns = Mock()
    return mock


@pytest.fixture
def mock_classifier():
    """Mock log classifier."""
    mock = Mock()
    mock.classify_log_entry.return_value = {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "message": "Test log message",
        "process_name": "webapp1",
        "matched_patterns": ["info_pattern"],
    }
    mock.get_classification_stats.return_value = {"classifications": 100}
    mock.reset_stats = Mock()
    return mock


@pytest.fixture
def log_parser(mock_pattern_manager, mock_classifier):
    """Create LogParser instance with mocked dependencies."""
    with patch(
        "src.log_parser.parser.PatternManager", return_value=mock_pattern_manager
    ), patch("src.log_parser.parser.LogClassifier", return_value=mock_classifier):
        parser = LogParser()
        yield parser


class TestLogParserBasic:
    """Test basic log parser functionality."""

    async def test_parse_log_line_success(self, log_parser):
        """Test successful log line parsing."""
        log_line = "2024-01-01 10:00:00 INFO Test message"

        result = await log_parser.parse_log_line(log_line, "webapp1")

        assert result["level"] == "INFO"
        assert result["message"] == "Test log message"
        assert result["process_name"] == "webapp1"
        assert "matched_patterns" in result

    async def test_parse_log_line_empty(self, log_parser):
        """Test parsing empty log line."""
        result = await log_parser.parse_log_line("", "webapp1")
        assert result == {}

    async def test_parse_log_line_whitespace_only(self, log_parser):
        """Test parsing whitespace-only log line."""
        result = await log_parser.parse_log_line("   \n\t  ", "webapp1")
        assert result == {}

    async def test_parse_log_line_error_handling(self, log_parser):
        """Test error handling in log line parsing."""
        log_parser.classifier.classify_log_entry.side_effect = Exception(
            "Classification error"
        )

        with pytest.raises(LogParserError):
            await log_parser.parse_log_line("test log", "webapp1")

        # Check that error stats are updated
        assert log_parser._processing_stats["processing_errors"] == 1


class TestLogParserBatch:
    """Test batch processing functionality."""

    async def test_parse_log_batch_success(self, log_parser):
        """Test successful batch parsing."""
        log_lines = [
            "2024-01-01 10:00:00 INFO Message 1",
            "2024-01-01 10:00:01 ERROR Message 2",
            "2024-01-01 10:00:02 DEBUG Message 3",
        ]

        results = await log_parser.parse_log_batch(log_lines, "webapp1")

        assert len(results) == 3
        for result in results:
            assert "level" in result
            assert "message" in result

    async def test_parse_log_batch_with_errors(self, log_parser):
        """Test batch parsing with some errors."""
        log_lines = ["valid log", "another valid log"]

        # Make classifier fail on second call
        log_parser.classifier.classify_log_entry.side_effect = [
            {"level": "INFO", "message": "Valid"},
            Exception("Error"),
            {"level": "INFO", "message": "Valid again"},
        ]

        results = await log_parser.parse_log_batch_optimized(log_lines, "webapp1")

        # Should continue processing despite errors
        assert len(results) >= 1

    async def test_parse_log_batch_empty(self, log_parser):
        """Test batch parsing with empty list."""
        results = await log_parser.parse_log_batch([], "webapp1")
        assert results == []

    async def test_parse_log_batch_optimized_chunking(self, log_parser):
        """Test optimized batch parsing with chunking."""
        # Create a large batch to test chunking
        log_lines = [f"Log message {i}" for i in range(250)]

        results = await log_parser.parse_log_batch_optimized(log_lines, "webapp1")

        assert len(results) == 250


class TestLogParserStreaming:
    """Test streaming functionality."""

    async def test_parse_log_stream(self, log_parser):
        """Test log stream parsing."""
        # Mock stream reader
        mock_stream = AsyncMock()
        mock_stream.readline.side_effect = [
            b"Log line 1\n",
            b"Log line 2\n",
            b"",  # End of stream
        ]

        # Run stream parsing (should complete when stream ends)
        await log_parser.parse_log_stream(mock_stream, "webapp1")

        # Verify stream was read
        assert mock_stream.readline.call_count == 3

    async def test_parse_log_stream_cancellation(self, log_parser):
        """Test log stream parsing cancellation."""
        mock_stream = AsyncMock()
        mock_stream.readline.side_effect = asyncio.CancelledError()

        # Should handle cancellation gracefully
        await log_parser.parse_log_stream(mock_stream, "webapp1")


class TestLogParserCallbacks:
    """Test callback functionality."""

    async def test_add_remove_callback(self, log_parser):
        """Test adding and removing callbacks."""
        callback = Mock()

        log_parser.add_callback(callback)
        assert callback in log_parser._callbacks

        log_parser.remove_callback(callback)
        assert callback not in log_parser._callbacks

    async def test_callback_notification(self, log_parser):
        """Test callback notification."""
        callback = Mock()
        async_callback = AsyncMock()

        log_parser.add_callback(callback)
        log_parser.add_callback(async_callback)

        await log_parser.parse_log_line("test log", "webapp1")

        # Both callbacks should be called
        callback.assert_called_once()
        async_callback.assert_called_once()

    async def test_callback_error_handling(self, log_parser):
        """Test callback error handling."""
        error_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()

        log_parser.add_callback(error_callback)
        log_parser.add_callback(good_callback)

        # Should not raise exception despite callback error
        await log_parser.parse_log_line("test log", "webapp1")

        # Good callback should still be called
        good_callback.assert_called_once()


class TestLogParserFiltering:
    """Test log filtering functionality."""

    def test_filter_logs_by_level(self, log_parser):
        """Test filtering logs by level."""
        log_entries = [
            {
                "level": "INFO",
                "message": "Info message",
                "timestamp": "2024-01-01T10:00:00",
            },
            {
                "level": "ERROR",
                "message": "Error message",
                "timestamp": "2024-01-01T10:00:01",
            },
            {
                "level": "DEBUG",
                "message": "Debug message",
                "timestamp": "2024-01-01T10:00:02",
            },
        ]

        filtered = log_parser.filter_logs(log_entries, level="ERROR")

        assert len(filtered) == 1
        assert filtered[0]["level"] == "ERROR"

    def test_filter_logs_by_process(self, log_parser):
        """Test filtering logs by process name."""
        log_entries = [
            {"process_name": "webapp1", "message": "Message 1"},
            {"process_name": "webapp2", "message": "Message 2"},
            {"process_name": "webapp1", "message": "Message 3"},
        ]

        filtered = log_parser.filter_logs(log_entries, process_name="webapp1")

        assert len(filtered) == 2
        for entry in filtered:
            assert entry["process_name"] == "webapp1"

    def test_filter_logs_by_time_range(self, log_parser):
        """Test filtering logs by time range."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        log_entries = [
            {"timestamp": base_time.isoformat(), "message": "Message 1"},
            {
                "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
                "message": "Message 2",
            },
            {
                "timestamp": (base_time + timedelta(minutes=10)).isoformat(),
                "message": "Message 3",
            },
        ]

        start_time = base_time + timedelta(minutes=2)
        end_time = base_time + timedelta(minutes=8)

        filtered = log_parser.filter_logs(
            log_entries, start_time=start_time, end_time=end_time
        )

        assert len(filtered) == 1
        assert filtered[0]["message"] == "Message 2"


class TestLogParserStatistics:
    """Test statistics functionality."""

    def test_get_log_summary(self, log_parser):
        """Test log summary generation."""
        log_entries = [
            {
                "level": "INFO",
                "process_name": "webapp1",
                "timestamp": "2024-01-01T10:00:00",
            },
            {
                "level": "ERROR",
                "process_name": "webapp1",
                "timestamp": "2024-01-01T10:00:01",
            },
            {
                "level": "INFO",
                "process_name": "webapp2",
                "timestamp": "2024-01-01T10:00:02",
            },
        ]

        summary = log_parser.get_log_summary(log_entries)

        assert summary["total_entries"] == 3
        assert summary["level_distribution"]["INFO"] == 2
        assert summary["level_distribution"]["ERROR"] == 1
        assert summary["process_distribution"]["webapp1"] == 2
        assert summary["process_distribution"]["webapp2"] == 1
        assert "time_range" in summary

    def test_get_log_summary_empty(self, log_parser):
        """Test log summary with empty entries."""
        summary = log_parser.get_log_summary([])
        assert summary["total_entries"] == 0

    def test_get_parser_stats(self, log_parser):
        """Test parser statistics."""
        stats = log_parser.get_parser_stats()

        assert "total_processed" in stats
        assert "processing_errors" in stats
        assert "uptime_seconds" in stats
        assert "callbacks_registered" in stats
        assert "classification_stats" in stats
        assert "pattern_stats" in stats

    def test_reset_stats(self, log_parser):
        """Test statistics reset."""
        # Process some logs to generate stats
        log_parser._processing_stats["total_processed"] = 100
        log_parser._processing_stats["processing_errors"] = 5

        log_parser.reset_stats()

        assert log_parser._processing_stats["total_processed"] == 0
        assert log_parser._processing_stats["processing_errors"] == 0
        log_parser.classifier.reset_stats.assert_called_once()


class TestLogParserBackgroundProcessing:
    """Test background processing functionality."""

    async def test_start_stop_background_processing(self, log_parser):
        """Test starting and stopping background processing."""
        await log_parser.start_background_processing()
        assert log_parser._processing_task is not None
        assert not log_parser._processing_task.done()

        await log_parser.stop_background_processing()
        assert log_parser._processing_task is None

    async def test_queue_log_for_processing(self, log_parser):
        """Test queuing logs for background processing."""
        await log_parser.start_background_processing()

        result = await log_parser.queue_log_for_processing("test log", "webapp1")
        assert result is True

        await log_parser.stop_background_processing()

    async def test_queue_full_handling(self, log_parser):
        """Test handling of full processing queue."""
        # Fill up the queue
        for i in range(1001):  # Queue size is 1000
            try:
                await log_parser.queue_log_for_processing(f"log {i}", "webapp1")
            except:
                break

        # Next item should return False (queue full)
        result = await log_parser.queue_log_for_processing("overflow log", "webapp1")
        assert result is False


class TestLogParserBatchBuffer:
    """Test batch buffer functionality."""

    def test_add_to_batch_buffer(self, log_parser):
        """Test adding logs to batch buffer."""
        log_parser.add_to_batch_buffer("log 1", "webapp1")
        log_parser.add_to_batch_buffer("log 2", "webapp1")

        assert len(log_parser._batch_buffer) == 2
        assert log_parser._batch_process_name == "webapp1"

    async def test_batch_buffer_auto_flush(self, log_parser):
        """Test automatic batch buffer flushing."""
        # Set small batch size for testing
        log_parser._batch_size = 3

        # Add logs to trigger auto-flush
        for i in range(3):
            log_parser.add_to_batch_buffer(f"log {i}", "webapp1")

        # Give time for async processing
        await asyncio.sleep(0.1)

        # Buffer should be cleared after auto-flush
        assert len(log_parser._batch_buffer) == 0

    async def test_flush_batch_buffer_manual(self, log_parser):
        """Test manual batch buffer flushing."""
        log_parser.add_to_batch_buffer("log 1", "webapp1")
        log_parser.add_to_batch_buffer("log 2", "webapp1")

        await log_parser.flush_batch_buffer()

        assert len(log_parser._batch_buffer) == 0


class TestLogParserConfiguration:
    """Test configuration functionality."""

    def test_validate_configuration(self, log_parser):
        """Test configuration validation."""
        errors = log_parser.validate_configuration()

        # Should return empty list for valid config
        assert isinstance(errors, list)
        log_parser.pattern_manager.validate_patterns.assert_called_once()

    def test_reload_patterns(self, log_parser):
        """Test pattern reloading."""
        log_parser.reload_patterns()

        log_parser.pattern_manager.reload_patterns.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
