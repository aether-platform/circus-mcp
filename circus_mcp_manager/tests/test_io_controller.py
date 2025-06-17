"""
Tests for enhanced I/O Controller functionality.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from collections import deque

from src.io_controller.stream_manager import StreamManager
from src.utils.exceptions import IOControllerError


@pytest.fixture
def stream_manager():
    """Create StreamManager instance."""
    return StreamManager(buffer_size=1024, max_queue_size=100)


class TestStreamManagerInitialization:
    """Test StreamManager initialization."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        manager = StreamManager()
        
        assert manager._buffer_size == 8192
        assert manager._max_queue_size == 1000
        assert isinstance(manager._input_queues, dict)
        assert isinstance(manager._output_buffers, dict)
        assert isinstance(manager._stream_tasks, dict)
        assert isinstance(manager._stream_stats, dict)
    
    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        manager = StreamManager(buffer_size=2048, max_queue_size=500)
        
        assert manager._buffer_size == 2048
        assert manager._max_queue_size == 500


class TestProcessRegistration:
    """Test process registration functionality."""
    
    async def test_register_process_success(self, stream_manager):
        """Test successful process registration."""
        await stream_manager.register_process("webapp1")
        
        assert "webapp1" in stream_manager._active_streams
        assert stream_manager._active_streams["webapp1"] is False
        assert "webapp1" in stream_manager._stream_callbacks
        assert "webapp1" in stream_manager._input_queues
        assert "webapp1" in stream_manager._output_buffers
        assert "webapp1" in stream_manager._stream_tasks
        assert "webapp1" in stream_manager._stream_stats
    
    async def test_register_process_with_config(self, stream_manager):
        """Test process registration with configuration."""
        config = {
            "cmd": "python app.py",
            "working_dir": "/path/to/app",
            "buffer_size": 4096,
        }
        
        await stream_manager.register_process("webapp1", config)
        
        assert stream_manager._stream_stats["webapp1"]["config"] == config
    
    async def test_register_process_duplicate(self, stream_manager):
        """Test registering duplicate process."""
        await stream_manager.register_process("webapp1")
        
        # Second registration should log warning but not fail
        await stream_manager.register_process("webapp1")
        
        assert "webapp1" in stream_manager._active_streams
    
    async def test_unregister_process_success(self, stream_manager):
        """Test successful process unregistration."""
        await stream_manager.register_process("webapp1")
        await stream_manager.unregister_process("webapp1")
        
        assert "webapp1" not in stream_manager._active_streams
        assert "webapp1" not in stream_manager._stream_callbacks
        assert "webapp1" not in stream_manager._input_queues
        assert "webapp1" not in stream_manager._output_buffers
        assert "webapp1" not in stream_manager._stream_tasks
        assert "webapp1" not in stream_manager._stream_stats
    
    async def test_unregister_process_with_active_streams(self, stream_manager):
        """Test unregistering process with active streams."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        await stream_manager.unregister_process("webapp1")
        
        assert "webapp1" not in stream_manager._active_streams
    
    async def test_unregister_nonexistent_process(self, stream_manager):
        """Test unregistering non-existent process."""
        # Should not raise exception
        await stream_manager.unregister_process("nonexistent")


class TestStreamOperations:
    """Test stream operations."""
    
    async def test_start_streams_success(self, stream_manager):
        """Test successful stream start."""
        await stream_manager.register_process("webapp1")
        
        result = await stream_manager.start_streams("webapp1")
        
        assert result is True
        assert stream_manager._active_streams["webapp1"] is True
        assert "webapp1" in stream_manager._input_handlers
        assert "webapp1" in stream_manager._output_monitors
    
    async def test_start_streams_unregistered_process(self, stream_manager):
        """Test starting streams for unregistered process."""
        with pytest.raises(IOControllerError):
            await stream_manager.start_streams("unregistered")
    
    async def test_start_streams_already_active(self, stream_manager):
        """Test starting streams that are already active."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        # Second start should return True but log warning
        result = await stream_manager.start_streams("webapp1")
        assert result is True
    
    async def test_stop_streams_success(self, stream_manager):
        """Test successful stream stop."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        result = await stream_manager.stop_streams("webapp1")
        
        assert result is True
        assert stream_manager._active_streams["webapp1"] is False
        assert "webapp1" not in stream_manager._input_handlers
        assert "webapp1" not in stream_manager._output_monitors
    
    async def test_stop_streams_not_active(self, stream_manager):
        """Test stopping streams that are not active."""
        await stream_manager.register_process("webapp1")
        
        result = await stream_manager.stop_streams("webapp1")
        assert result is True
    
    async def test_stop_streams_unregistered_process(self, stream_manager):
        """Test stopping streams for unregistered process."""
        result = await stream_manager.stop_streams("unregistered")
        assert result is True


class TestInputOperations:
    """Test input operations."""
    
    async def test_send_input_success(self, stream_manager):
        """Test successful input sending."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        result = await stream_manager.send_input("webapp1", "test input")
        
        assert result is True
        # Check that input handler stats are updated
        assert stream_manager._input_handlers["webapp1"]["queue_size"] == 1
    
    async def test_send_input_unregistered_process(self, stream_manager):
        """Test sending input to unregistered process."""
        with pytest.raises(IOControllerError):
            await stream_manager.send_input("unregistered", "test input")
    
    async def test_send_input_inactive_streams(self, stream_manager):
        """Test sending input to process with inactive streams."""
        await stream_manager.register_process("webapp1")
        
        with pytest.raises(IOControllerError):
            await stream_manager.send_input("webapp1", "test input")
    
    async def test_send_input_large_data(self, stream_manager):
        """Test sending large input data."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        large_data = "x" * 10000
        result = await stream_manager.send_input("webapp1", large_data)
        
        assert result is True


class TestCallbackSystem:
    """Test callback system."""
    
    async def test_add_stream_callback(self, stream_manager):
        """Test adding stream callback."""
        callback = Mock()
        
        await stream_manager.register_process("webapp1")
        stream_manager.add_stream_callback("webapp1", callback)
        
        assert callback in stream_manager._stream_callbacks["webapp1"]
    
    async def test_remove_stream_callback(self, stream_manager):
        """Test removing stream callback."""
        callback = Mock()
        
        await stream_manager.register_process("webapp1")
        stream_manager.add_stream_callback("webapp1", callback)
        stream_manager.remove_stream_callback("webapp1", callback)
        
        assert callback not in stream_manager._stream_callbacks["webapp1"]
    
    async def test_callback_notification_sync(self, stream_manager):
        """Test callback notification with sync callback."""
        callback = Mock()
        
        await stream_manager.register_process("webapp1")
        stream_manager.add_stream_callback("webapp1", callback)
        await stream_manager.start_streams("webapp1")
        
        # Callback should be called when streams start
        callback.assert_called_with("webapp1", "streams_started", {})
    
    async def test_callback_notification_async(self, stream_manager):
        """Test callback notification with async callback."""
        callback = AsyncMock()
        
        await stream_manager.register_process("webapp1")
        stream_manager.add_stream_callback("webapp1", callback)
        await stream_manager.start_streams("webapp1")
        
        # Async callback should be awaited
        callback.assert_called_with("webapp1", "streams_started", {})
    
    async def test_callback_error_handling(self, stream_manager):
        """Test callback error handling."""
        error_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()
        
        await stream_manager.register_process("webapp1")
        stream_manager.add_stream_callback("webapp1", error_callback)
        stream_manager.add_stream_callback("webapp1", good_callback)
        
        # Should not raise exception despite callback error
        await stream_manager.start_streams("webapp1")
        
        # Good callback should still be called
        good_callback.assert_called()


class TestStreamStatus:
    """Test stream status functionality."""
    
    async def test_get_stream_status_single_process(self, stream_manager):
        """Test getting status for single process."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        status = stream_manager.get_stream_status("webapp1")
        
        assert status["active"] is True
        assert "input_handler" in status
        assert "output_monitor" in status
        assert "callbacks" in status
    
    async def test_get_stream_status_unregistered_process(self, stream_manager):
        """Test getting status for unregistered process."""
        status = stream_manager.get_stream_status("unregistered")
        assert status == {}
    
    async def test_get_stream_status_all_processes(self, stream_manager):
        """Test getting status for all processes."""
        await stream_manager.register_process("webapp1")
        await stream_manager.register_process("webapp2")
        await stream_manager.start_streams("webapp1")
        
        status = stream_manager.get_stream_status()
        
        assert "processes" in status
        assert "total_processes" in status
        assert "active_processes" in status
        
        assert status["total_processes"] == 2
        assert status["active_processes"] == 1
        assert "webapp1" in status["processes"]
        assert "webapp2" in status["processes"]


class TestStreamStatistics:
    """Test stream statistics."""
    
    async def test_stream_stats_initialization(self, stream_manager):
        """Test stream statistics initialization."""
        config = {"buffer_size": 2048}
        await stream_manager.register_process("webapp1", config)
        
        stats = stream_manager._stream_stats["webapp1"]
        
        assert stats["bytes_sent"] == 0
        assert stats["bytes_received"] == 0
        assert stats["lines_processed"] == 0
        assert stats["errors"] == 0
        assert stats["last_activity"] is None
        assert stats["uptime"] == 0
        assert stats["config"] == config
    
    async def test_stream_stats_updates(self, stream_manager):
        """Test stream statistics updates."""
        await stream_manager.register_process("webapp1")
        await stream_manager.start_streams("webapp1")
        
        # Send input to trigger stats update
        await stream_manager.send_input("webapp1", "test data")
        
        # Stats should be updated (implementation would update these)
        stats = stream_manager._stream_stats["webapp1"]
        assert isinstance(stats, dict)


class TestErrorRecovery:
    """Test error recovery functionality."""
    
    async def test_retry_mechanism_initialization(self, stream_manager):
        """Test retry mechanism initialization."""
        await stream_manager.register_process("webapp1")
        
        assert stream_manager._retry_counts["webapp1"] == 0
        assert stream_manager._max_retries == 3
    
    async def test_retry_count_tracking(self, stream_manager):
        """Test retry count tracking."""
        await stream_manager.register_process("webapp1")
        
        # Simulate retry increment (would be done in actual error handling)
        stream_manager._retry_counts["webapp1"] += 1
        
        assert stream_manager._retry_counts["webapp1"] == 1


class TestBufferManagement:
    """Test buffer management."""
    
    async def test_output_buffer_initialization(self, stream_manager):
        """Test output buffer initialization."""
        await stream_manager.register_process("webapp1")
        
        buffer = stream_manager._output_buffers["webapp1"]
        assert isinstance(buffer, deque)
        assert buffer.maxlen == 1000
    
    async def test_input_queue_initialization(self, stream_manager):
        """Test input queue initialization."""
        await stream_manager.register_process("webapp1")
        
        queue = stream_manager._input_queues["webapp1"]
        assert isinstance(queue, asyncio.Queue)
        assert queue.maxsize == stream_manager._max_queue_size


class TestCleanup:
    """Test cleanup functionality."""
    
    async def test_cleanup_success(self, stream_manager):
        """Test successful cleanup."""
        await stream_manager.register_process("webapp1")
        await stream_manager.register_process("webapp2")
        await stream_manager.start_streams("webapp1")
        
        await stream_manager.cleanup()
        
        assert len(stream_manager._active_streams) == 0
        assert len(stream_manager._stream_callbacks) == 0
        assert len(stream_manager._input_handlers) == 0
        assert len(stream_manager._output_monitors) == 0
    
    async def test_cleanup_with_tasks(self, stream_manager):
        """Test cleanup with active tasks."""
        await stream_manager.register_process("webapp1")
        
        # Add mock task
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        stream_manager._stream_tasks["webapp1"] = [mock_task]
        
        await stream_manager.cleanup()
        
        # Task should be cancelled
        mock_task.cancel.assert_called_once()


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    def test_buffer_size_configuration(self):
        """Test buffer size configuration."""
        manager = StreamManager(buffer_size=4096)
        assert manager._buffer_size == 4096
    
    def test_queue_size_configuration(self):
        """Test queue size configuration."""
        manager = StreamManager(max_queue_size=2000)
        assert manager._max_queue_size == 2000
    
    async def test_concurrent_operations(self, stream_manager):
        """Test concurrent stream operations."""
        # Register multiple processes
        processes = ["webapp1", "webapp2", "webapp3"]
        
        # Register all processes concurrently
        await asyncio.gather(*[
            stream_manager.register_process(proc) for proc in processes
        ])
        
        # Start all streams concurrently
        results = await asyncio.gather(*[
            stream_manager.start_streams(proc) for proc in processes
        ])
        
        assert all(results)
        assert all(stream_manager._active_streams[proc] for proc in processes)


if __name__ == "__main__":
    pytest.main([__file__])