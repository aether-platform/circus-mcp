"""
Tests for CircusManager using Circus client library.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.circus_manager.manager import CircusManager
from src.utils.exceptions import (
    CircusManagerError,
    ProcessNotFoundError,
    ProcessAlreadyRunningError,
    ConfigurationError,
)


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


@pytest.fixture
def mock_circus_client():
    """Mock Circus client."""
    mock = Mock()
    mock.call.return_value = {"status": "ok"}
    return mock


@pytest.fixture
async def circus_manager(mock_config_handler, mock_process_watcher):
    """Create CircusManager instance with mocked dependencies."""
    with patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
         patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher):
        manager = CircusManager()
        yield manager
        await manager.cleanup()


class TestCircusManagerInitialization:
    """Test CircusManager initialization."""
    
    async def test_initialization_success(self, circus_manager, mock_circus_client):
        """Test successful initialization."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            assert circus_manager._initialized is True
            assert circus_manager._circus_client is not None
    
    async def test_initialization_config_error(self, circus_manager):
        """Test initialization with configuration error."""
        circus_manager.config_handler.validate_config.return_value = ["Invalid config"]
        
        with pytest.raises(CircusManagerError):
            await circus_manager.initialize()
    
    async def test_double_initialization(self, circus_manager, mock_circus_client):
        """Test double initialization warning."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            # Second initialization should log warning but not fail
            await circus_manager.initialize()
            assert circus_manager._initialized is True


class TestCircusConnection:
    """Test Circus connection functionality."""
    
    async def test_connect_success(self, circus_manager, mock_circus_client):
        """Test successful connection to Circus."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            result = await circus_manager.connect_to_circus()
            assert result is True
            assert circus_manager._connected is True
    
    async def test_connect_not_initialized(self, circus_manager):
        """Test connection attempt without initialization."""
        with pytest.raises(CircusManagerError):
            await circus_manager.connect_to_circus()
    
    async def test_connect_failure(self, circus_manager, mock_circus_client):
        """Test connection failure."""
        mock_circus_client.call.side_effect = Exception("Connection failed")
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            result = await circus_manager.connect_to_circus()
            assert result is False
            assert circus_manager._connected is False


class TestProcessControl:
    """Test process control operations."""
    
    async def test_start_process_success(self, circus_manager, mock_circus_client):
        """Test successful process start."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            result = await circus_manager.start_process("webapp1")
            assert result is True
            
            # Verify command was called
            mock_circus_client.call.assert_called()
    
    async def test_start_process_not_found(self, circus_manager, mock_circus_client):
        """Test starting non-existent process."""
        circus_manager.config_handler.get_all_watchers.return_value = []
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            with pytest.raises(ProcessNotFoundError):
                await circus_manager.start_process("nonexistent")
    
    async def test_stop_process_success(self, circus_manager, mock_circus_client):
        """Test successful process stop."""
        # Mock process info
        mock_process_info = Mock()
        mock_process_info.status = Mock()
        mock_process_info.status.STOPPED = False
        circus_manager.process_watcher.get_process_info.return_value = mock_process_info
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            result = await circus_manager.stop_process("webapp1")
            assert result is True
    
    async def test_restart_process_success(self, circus_manager, mock_circus_client):
        """Test successful process restart."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            result = await circus_manager.restart_process("webapp1")
            assert result is True


class TestProcessStatus:
    """Test process status operations."""
    
    async def test_get_process_status_single(self, circus_manager, mock_circus_client):
        """Test getting status for single process."""
        mock_process_info = Mock()
        mock_process_info.to_dict.return_value = {"status": "running"}
        circus_manager.process_watcher.get_process_info.return_value = mock_process_info
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            status = await circus_manager.get_process_status("webapp1")
            assert "webapp1" in status
            assert status["webapp1"]["status"] == "running"
    
    async def test_get_process_status_all(self, circus_manager, mock_circus_client):
        """Test getting status for all processes."""
        mock_processes = {
            "webapp1": Mock(),
            "webapp2": Mock(),
        }
        for name, mock_proc in mock_processes.items():
            mock_proc.to_dict.return_value = {"status": "running"}
        
        circus_manager.process_watcher.get_all_processes.return_value = mock_processes
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            status = await circus_manager.get_process_status()
            assert len(status) == 2
            assert "webapp1" in status
            assert "webapp2" in status
    
    async def test_get_process_stats(self, circus_manager, mock_circus_client):
        """Test getting detailed process statistics."""
        mock_circus_client.call.return_value = {
            "status": "ok",
            "info": {
                "pid": 1234,
                "cpu": 10.5,
                "memory": 50.2,
            }
        }
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            stats = await circus_manager.get_process_stats("webapp1")
            assert stats is not None
            assert "info" in stats


class TestSystemStatus:
    """Test system status functionality."""
    
    async def test_get_system_status(self, circus_manager, mock_circus_client):
        """Test getting overall system status."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client), \
             patch('src.circus_manager.manager.get_system_info', return_value={"cpu": "x86_64"}):
            await circus_manager.initialize()
            
            status = circus_manager.get_system_status()
            
            assert "circus_manager" in status
            assert "configuration" in status
            assert "process_watcher" in status
            assert "performance_stats" in status
            assert "system_info" in status
            
            assert status["circus_manager"]["initialized"] is True


class TestCleanup:
    """Test cleanup functionality."""
    
    async def test_cleanup_success(self, circus_manager, mock_circus_client):
        """Test successful cleanup."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            await circus_manager.cleanup()
            
            assert circus_manager._initialized is False
            assert circus_manager._connected is False
            assert circus_manager._circus_client is None
    
    async def test_context_manager(self, mock_config_handler, mock_process_watcher):
        """Test async context manager functionality."""
        with patch('src.circus_manager.manager.ConfigHandler', return_value=mock_config_handler), \
             patch('src.circus_manager.manager.ProcessWatcher', return_value=mock_process_watcher), \
             patch('src.circus_manager.manager.CircusClient'):
            
            async with CircusManager() as manager:
                assert manager._initialized is True
            
            # After context exit, should be cleaned up
            assert manager._initialized is False


class TestPerformanceStats:
    """Test performance statistics."""
    
    async def test_performance_stats_tracking(self, circus_manager, mock_circus_client):
        """Test that performance stats are tracked correctly."""
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            await circus_manager.connect_to_circus()
            
            # Execute some commands
            await circus_manager.start_process("webapp1")
            await circus_manager.get_process_stats("webapp1")
            
            stats = circus_manager._performance_stats
            assert stats["commands_sent"] >= 2  # At least connect + start + stats
            assert stats["last_activity"] is not None
    
    async def test_performance_stats_error_tracking(self, circus_manager, mock_circus_client):
        """Test that failed commands are tracked in stats."""
        mock_circus_client.call.side_effect = Exception("Command failed")
        
        with patch('src.circus_manager.manager.CircusClient', return_value=mock_circus_client):
            await circus_manager.initialize()
            
            # This should fail and increment error count
            result = await circus_manager.connect_to_circus()
            assert result is False
            
            stats = circus_manager._performance_stats
            assert stats["commands_failed"] > 0


if __name__ == "__main__":
    pytest.main([__file__])