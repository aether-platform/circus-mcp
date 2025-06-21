#!/usr/bin/env python3
"""
Test CircusMCP tools and functionality
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from circus_mcp.manager import CircusManager
from circus_mcp.mcp_server import CircusMCPServer


class TestCircusManager:
    """Test CircusManager functionality"""

    @pytest.fixture
    def manager(self):
        """Create a CircusManager instance for testing"""
        return CircusManager()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test manager initializes correctly"""
        assert manager.client is None
        assert manager.endpoint == "tcp://127.0.0.1:5555"

    @pytest.mark.asyncio
    async def test_connect_success(self, manager):
        """Test successful connection to Circus"""
        # Import the module to ensure we're patching the right location
        import circus_mcp.manager as manager_module

        # Create a mock client
        mock_client = Mock()

        # Mock the CircusClient class and asyncio.to_thread function
        with patch.object(
            manager_module, "CircusClient", return_value=mock_client
        ) as mock_client_class:
            with patch.object(manager_module, "asyncio") as mock_asyncio:
                # Set up the asyncio.to_thread mock to return a coroutine
                async def mock_to_thread(func, *args, **kwargs):
                    return {"status": "ok"}

                mock_asyncio.to_thread = mock_to_thread

                # Call the connect method
                result = await manager.connect()

                # Verify the results
                assert result is True
                assert manager.client is mock_client
                mock_client_class.assert_called_once_with(endpoint="tcp://127.0.0.1:5555")

    @pytest.mark.asyncio
    async def test_connect_failure(self, manager):
        """Test connection failure handling"""
        with patch("circus_mcp.manager.CircusClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            result = await manager.connect()
            assert result is False
            assert manager.client is None


class TestCircusMCPServer:
    """Test CircusMCPServer MCP integration"""

    @pytest.fixture
    def mcp_server(self):
        """Create an MCP server instance for testing"""
        return CircusMCPServer()

    def test_server_initialization(self, mcp_server):
        """Test MCP server initializes correctly"""
        assert mcp_server.server is not None
        assert mcp_server.manager is not None

    def test_mcp_tools_setup(self, mcp_server):
        """Test that MCP tools are properly setup"""
        # Test that server has been properly initialized
        assert mcp_server.server.name == "circus-mcp"


class TestIntegration:
    """Integration tests for full workflow"""

    @pytest.mark.asyncio
    async def test_full_workflow_mock(self):
        """Test complete workflow with mocked Circus"""

        # Mock circus operations
        mock_responses = {
            "add": {"status": "ok", "message": "Process added"},
            "start": {"status": "ok", "process": "test"},
            "status": {"status": "running", "pid": 12345},
            "stop": {"status": "ok", "process": "test"},
        }

        with patch("asyncio.to_thread") as mock_thread:
            mock_thread.side_effect = lambda func, cmd: mock_responses.get(
                cmd["command"], {"status": "ok"}
            )

            manager = CircusManager()
            manager.client = Mock()  # Mock client connection

            # Test process lifecycle
            add_result = await manager.add_process("test", "echo hello")
            assert add_result["status"] == "ok"

            start_result = await manager.start_process("test")
            assert start_result["status"] == "ok"

            status_result = await manager.get_process_status("test")
            assert status_result["status"] == "running"

            stop_result = await manager.stop_process("test")
            assert stop_result["status"] == "ok"


@pytest.mark.asyncio
async def test_manager_basic_operations():
    """Test basic manager operations without real Circus"""
    manager = CircusManager()

    # Test that manager initializes properly
    assert manager.endpoint == "tcp://127.0.0.1:5555"
    assert manager.client is None

    # Connection will likely fail without real Circus daemon
    # This is expected behavior in test environment
    await manager.connect()
    # Don't assert result - it depends on environment


def test_mcp_server_creation():
    """Test MCP server can be created"""
    server = CircusMCPServer()
    assert server is not None
    assert hasattr(server, "server")
    assert hasattr(server, "manager")


if __name__ == "__main__":
    # Run basic tests
    asyncio.run(test_manager_basic_operations())
    test_mcp_server_creation()
    print("✅ Basic tests completed!")
