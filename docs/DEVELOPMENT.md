# Development Guide

## Development

### Setup Development Environment

```bash
git clone https://github.com/aether-platform/circus-mcp.git
cd circus-mcp

# Install with development dependencies
uv sync --extra dev

# Run tests
pytest

# Format code
black src/ tests/

# Type checking
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=circus_mcp --cov-report=html

# Run specific test categories
pytest tests/ -m "not slow"
pytest tests/ -m integration
```

## Contributing

We welcome contributions! Please see our [contributing guidelines](https://github.com/aether-platform/circus-mcp/blob/main/CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Architecture

### Package Structure

```
circus-mcp/
├── src/circus_mcp/
│   ├── __init__.py           # Package initialization
│   ├── manager.py            # Core Circus management
│   ├── cli.py                # CLI interface
│   ├── main.py               # Entry point
│   └── mcp_server.py         # MCP protocol server
├── circus.ini                # Default Circus configuration
├── mcp_config.json           # MCP integration config
└── tests/                    # Test suite
```

### Core Components

- **CircusManager**: Direct interface to Circus daemon
- **CLI**: Command-line interface with comprehensive process management
- **MCP Server**: Model Context Protocol implementation for AI agents
- **Configuration**: Simple, file-based configuration management

## MCP Protocol Integration

### Server Implementation

The MCP server provides the following tools for AI agents:

- `add_process` - Add a new process to Circus
- `start_process` - Start a process
- `stop_process` - Stop a process  
- `restart_process` - Restart a process
- `list_processes` - List all processes
- `get_process_status` - Get process status

### Integration Example

```python
from circus_mcp.mcp_server import CircusMCPServer

# Start MCP server
server = CircusMCPServer()
await server.run()
```

## Testing

### Test Structure

- `test_mcp_tools.py` - MCP protocol and tool testing
- Integration tests with actual Circus daemon
- Mock tests for isolated component testing

### Test Requirements

- Circus daemon should be running for integration tests
- Tests use temporary configurations
- Cleanup after test execution

## Build and Release

### Building the Package

```bash
# Build source distribution and wheel
uv build

# Check package
twine check dist/*
```

### Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag
4. Push tag to trigger automated release

```bash
# Update version and changelog, then:
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to v1.0.2"
git tag v1.0.2
git push origin main
git push origin v1.0.2
```

The GitHub Actions workflow will automatically:
- Run tests across multiple platforms
- Build the package
- Create GitHub Release with changelog
- Publish to PyPI

## Configuration

### Circus Configuration

Default `circus.ini` provides basic daemon setup:

```ini
[circus]
endpoint = tcp://127.0.0.1:5555
pubsub_endpoint = tcp://127.0.0.1:5556
stats_endpoint = tcp://127.0.0.1:5557

[watcher:dummy]
cmd = python -c "import time; [time.sleep(1) for _ in iter(int, 1)]"
numprocesses = 1
```

### MCP Configuration

For AI agent integration, use `mcp_config.json`:

```json
{
  "mcpServers": {
    "circus-mcp": {
      "command": "uv",
      "args": ["run", "circus-mcp", "mcp"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

## Dependencies

### Runtime Dependencies

- `circus>=0.18.0` - Process manager
- `pyzmq>=25.0.0` - ZeroMQ for Circus communication
- `mcp>=1.0.0` - Model Context Protocol
- `click>=8.1.0` - CLI framework  
- `psutil>=5.9.0` - System information

### Development Dependencies

- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `flake8>=6.0.0` - Linting
- `mypy>=1.5.0` - Type checking

## Troubleshooting

### Common Issues

1. **Circus daemon not running**
   ```bash
   uv run circus-mcp start-daemon
   ```

2. **Permission errors**
   - Check file permissions for configuration files
   - Ensure proper access to process working directories

3. **Connection issues**
   - Verify Circus endpoint configuration
   - Check firewall settings for ZeroMQ ports

4. **MCP integration problems**
   - Verify MCP server is running
   - Check client configuration
   - Review protocol compatibility

### Debug Mode

Enable debug logging:

```bash
export CIRCUS_MCP_DEBUG=1
uv run circus-mcp --help
```

### Log Files

- Circus daemon logs: Check `circusd` output
- Process logs: Available through `uv run circus-mcp logs` command
- MCP communication: Logged to stderr when in debug mode