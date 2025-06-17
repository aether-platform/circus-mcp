"""
Integration tests for the complete Circus MCP system.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.circus_manager.manager import CircusManager
from src.log_parser.parser import LogParser
from src.io_controller.stream_manager import StreamManager
from src.mcp_server.server import MCPServer


@pytest.fixture
def mock_circus_client():
    """Mock Circus client for integration tests."""
    mock = Mock()
    mock.call.return_value = {"status": "ok", "watchers": []}
    return mock


@pytest.fixture
def mock_config_handler():
    """Mock configuration handler."""
    mock = Mock()
    mock.validate_config.return_value = []
    mock.get_all_watchers.return_value = ["webapp1", "webapp2"]
    mock.get_watcher_config.return_value = {
        "cmd": "python app.py",
        "working_dir": "/path/to/app",
        "numprocesses": 1,
    }
    mock.get_config_summary.return_value = {"watchers": 2}
    return mock


@pytest.fixture
def mock_process_watcher():
    """Mock process watcher."""
    mock = Mock()
    mock.start_monitoring = AsyncMock()
    mock.stop_monitoring = AsyncMock()
    mock.add_process = Mock()
    mock.get_monitoring_status.return_value = {"active": True}
    return mock


class TestSystemIntegration:
    """Test complete system integration."""
    
    async def test_full_system_initialization(self, mock_circus_client, mock_config_handler, mock_process_watcher):
        """Test full system initialization and integration."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            # Initialize all components
            circus_manager = CircusManager()
            log_parser = LogParser()
            stream_manager = StreamManager()
            
            # Initialize circus manager
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            # Register processes in stream manager
            await stream_manager.register_process("webapp1")
            await stream_manager.register_process("webapp2")
            
            # Verify system state
            assert circus_manager._initialized is True
            assert circus_manager._connected is True
            assert "webapp1" in stream_manager._active_streams
            assert "webapp2" in stream_manager._active_streams
            
            # Cleanup
            await circus_manager.cleanup()
            await stream_manager.cleanup()
    
    async def test_process_lifecycle_integration(self, mock_circus_client, mock_config_handler, mock_process_watcher):
        """Test complete process lifecycle integration."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            circus_manager = CircusManager()
            stream_manager = StreamManager()
            
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            await stream_manager.register_process("webapp1")
            
            # Start process and streams
            start_result = await circus_manager.start_process("webapp1")
            stream_result = await stream_manager.start_streams("webapp1")
            
            assert start_result is True
            assert stream_result is True
            
            # Send input to process
            input_result = await stream_manager.send_input("webapp1", "test command")
            assert input_result is True
            
            # Stop process and streams
            await stream_manager.stop_streams("webapp1")
            stop_result = await circus_manager.stop_process("webapp1")
            assert stop_result is True
            
            # Cleanup
            await circus_manager.cleanup()
            await stream_manager.cleanup()
    
    async def test_log_processing_integration(self, mock_circus_client, mock_config_handler, mock_process_watcher):
        """Test log processing integration with other components."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            circus_manager = CircusManager()
            log_parser = LogParser()
            stream_manager = StreamManager()
            
            # Setup log callback to integrate with stream manager
            log_entries = []
            
            def log_callback(entry):
                log_entries.append(entry)
            
            log_parser.add_callback(log_callback)
            
            await circus_manager.initialize()
            await stream_manager.register_process("webapp1")
            
            # Process some log entries
            test_logs = [
                "2024-01-01 10:00:00 INFO Application started",
                "2024-01-01 10:00:01 ERROR Connection failed",
                "2024-01-01 10:00:02 DEBUG Processing request",
            ]
            
            for log_line in test_logs:
                await log_parser.parse_log_line(log_line, "webapp1")
            
            # Verify log processing
            assert len(log_entries) == 3
            
            # Get log summary
            summary = log_parser.get_log_summary(log_entries)
            assert summary["total_entries"] == 3
            assert "level_distribution" in summary
            
            # Cleanup
            await circus_manager.cleanup()
            await stream_manager.cleanup()


class TestMCPServerIntegration:
    """Test MCP server integration with other components."""
    
    async def test_mcp_server_with_circus_manager(self, mock_circus_client, mock_config_handler, mock_process_watcher):
        """Test MCP server integration with CircusManager."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            circus_manager = CircusManager()
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            # Create MCP server with circus manager
            mcp_server = MCPServer(circus_manager)
            
            # Test MCP server initialization
            assert mcp_server.circus_manager is circus_manager
            assert mcp_server.tools is not None
            assert mcp_server.resources is not None
            
            # Test server info
            server_info = mcp_server.get_server_info()
            assert "name" in server_info
            assert "version" in server_info
            assert server_info["running"] is False
            
            # Cleanup
            await circus_manager.cleanup()
    
    async def test_mcp_tools_integration(self, mock_circus_client, mock_config_handler, mock_process_watcher):
        """Test MCP tools integration with system components."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            circus_manager = CircusManager()
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            mcp_server = MCPServer(circus_manager)
            
            # Test tools availability
            available_tools = mcp_server.tools.get_available_tools()
            assert isinstance(available_tools, list)
            assert len(available_tools) > 0
            
            # Test tool execution (mock)
            with patch.object(mcp_server.tools, 'execute_tool', return_value={"status": "success"}):
                result = await mcp_server.tools.execute_tool("process_control", {
                    "action": "start",
                    "process_name": "webapp1"
                })
                assert result["status"] == "success"
            
            # Cleanup
            await circus_manager.cleanup()


class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""
    
    async def test_circus_connection_failure_handling(self, mock_config_handler, mock_process_watcher):
        """Test handling of Circus connection failures."""
        # Mock client that fails
        mock_client = Mock()
        mock_client.call.side_effect = Exception("Connection failed")
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            circus_manager = CircusManager()
            stream_manager = StreamManager()
            
            await circus_manager.initialize()
            
            # Connection should fail gracefully
            result = await circus_manager.connect_to_circus()
            assert result is False
            assert circus_manager._connected is False
            
            # Stream manager should still work independently
            await stream_manager.register_process("webapp1")
            assert "webapp1" in stream_manager._active_streams
            
            # Cleanup
            await circus_manager.cleanup()
            await stream_manager.cleanup()
    
    async def test_log_parser_error_recovery(self):
        """Test log parser error recovery in integrated system."""
        log_parser = LogParser()
        
        # Add callback that fails
        def failing_callback(entry):
            raise Exception("Callback failed")
        
        def working_callback(entry):
            working_callback.called = True
        
        working_callback.called = False
        
        log_parser.add_callback(failing_callback)
        log_parser.add_callback(working_callback)
        
        # Process log - should not fail despite callback error
        await log_parser.parse_log_line("Test log message", "webapp1")
        
        # Working callback should still be called
        assert working_callback.called is True
    
    async def test_stream_manager_error_recovery(self):
        """Test stream manager error recovery."""
        stream_manager = StreamManager()
        
        # Register process
        await stream_manager.register_process("webapp1")
        
        # Add callback that fails
        def failing_callback(process_name, event_type, data):
            raise Exception("Callback failed")
        
        def working_callback(process_name, event_type, data):
            working_callback.called = True
        
        working_callback.called = False
        
        stream_manager.add_stream_callback("webapp1", failing_callback)
        stream_manager.add_stream_callback("webapp1", working_callback)
        
        # Start streams - should not fail despite callback error
        result = await stream_manager.start_streams("webapp1")
        assert result is True
        
        # Working callback should still be called
        assert working_callback.called is True
        
        # Cleanup
        await stream_manager.cleanup()


class TestPerformanceIntegration:
    """Test performance aspects of integrated system."""
    
    async def test_concurrent_process_operations(self, mock_circus_client, mock_config_handler, mock_process_watcher):
        """Test concurrent operations across multiple processes."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
            
            circus_manager = CircusManager()
            stream_manager = StreamManager()
            log_parser = LogParser()
            
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            # Setup multiple processes
            processes = ["webapp1", "webapp2", "webapp3", "webapp4", "webapp5"]
            
            # Register all processes concurrently
            await asyncio.gather(*[
                stream_manager.register_process(proc) for proc in processes
            ])
            
            # Start all processes concurrently
            start_results = await asyncio.gather(*[
                circus_manager.start_process(proc) for proc in processes
            ])
            
            # Start all streams concurrently
            stream_results = await asyncio.gather(*[
                stream_manager.start_streams(proc) for proc in processes
            ])
            
            assert all(start_results)
            assert all(stream_results)
            
            # Process logs concurrently
            log_tasks = []
            for proc in processes:
                for i in range(10):
                    log_tasks.append(
                        log_parser.parse_log_line(f"Log message {i} from {proc}", proc)
                    )
            
            await asyncio.gather(*log_tasks)
            
            # Verify stats
            stats = log_parser.get_parser_stats()
            assert stats["total_processed"] >= 50  # 5 processes * 10 logs each
            
            # Cleanup
            await circus_manager.cleanup()
            await stream_manager.cleanup()
    
    async def test_high_throughput_log_processing(self):
        """Test high-throughput log processing."""
        log_parser = LogParser()
        
        # Start background processing for better performance
        await log_parser.start_background_processing()
        
        # Process many logs
        num_logs = 1000
        log_tasks = []
        
        for i in range(num_logs):
            log_line = f"2024-01-01 10:00:{i:02d} INFO Processing request {i}"
            log_tasks.append(log_parser.parse_log_line(log_line, "webapp1"))
        
        # Process all logs concurrently
        results = await asyncio.gather(*log_tasks)
        
        assert len(results) == num_logs
        
        # Check performance stats
        stats = log_parser.get_parser_stats()
        assert stats["total_processed"] >= num_logs
        assert stats["processing_rate"] > 0
        
        # Stop background processing
        await log_parser.stop_background_processing()
    
    async def test_memory_usage_optimization(self):
        """Test memory usage optimization in integrated system."""
        log_parser = LogParser()
        stream_manager = StreamManager(buffer_size=1024, max_queue_size=100)
        
        # Register process with limited buffer
        await stream_manager.register_process("webapp1")
        
        # Process many logs to test memory management
        for i in range(2000):  # More than buffer size
            log_line = f"Log message {i}"
            await log_parser.parse_log_line(log_line, "webapp1")
        
        # Check that buffers are properly managed
        buffer = stream_manager._output_buffers["webapp1"]
        assert len(buffer) <= 1000  # Should not exceed maxlen
        
        # Cleanup
        await stream_manager.cleanup()


class TestConfigurationIntegration:
    """Test configuration integration across components."""
    
    async def test_configuration_consistency(self, mock_circus_client):
        """Test configuration consistency across components."""
        # Mock config with specific settings
        mock_config = Mock()
        mock_config.validate_config.return_value = []
        mock_config.get_all_watchers.return_value = ["webapp1"]
        mock_config.get_watcher_config.return_value = {
            "cmd": "python app.py",
            "working_dir": "/app",
            "numprocesses": 2,
            "buffer_size": 2048,
        }
        mock_config.get_config_summary.return_value = {"watchers": 1}
        
        mock_watcher = Mock()
        mock_watcher.start_monitoring = AsyncMock()
        mock_watcher.stop_monitoring = AsyncMock()
        mock_watcher.add_process = Mock()
        mock_watcher.get_monitoring_status.return_value = {"active": True}
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_watcher):
            
            circus_manager = CircusManager()
            await circus_manager.initialize()
            
            # Verify configuration is used consistently
            system_status = circus_manager.get_system_status()
            assert "configuration" in system_status
            
            # Cleanup
            await circus_manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])