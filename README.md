# Circus MCP

[![PyPI version](https://badge.fury.io/py/circus-mcp.svg)](https://badge.fury.io/py/circus-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A simple and powerful process management tool that combines Circus process manager with AI agent integration through the Model Context Protocol (MCP).

## What is Circus MCP?

In today's complex microservices development landscape, Circus MCP enables AI coding agents to work more efficiently, contributing to society through better development productivity.

Circus MCP provides direct process control through the Model Context Protocol, eliminating the overhead of shell commands and reducing token consumption for AI agents managing development environments.

**Core Features**:
- **AI Integration**: Built-in MCP protocol support for coding agents
- **Simple Commands**: Easy-to-use CLI for developers
- **Smart Operations**: Idempotent commands that work reliably
- **Microservices Ready**: Manage multiple services effortlessly

## Quick Start

### Installation

```bash
uv add circus-mcp
```

### Basic Usage

```bash
# Start the daemon
uv run circus-mcp start-daemon

# Add and start a web application
uv run circus-mcp add webapp "python app.py"
uv run circus-mcp start webapp

# Check what's running
uv run circus-mcp overview

# View logs
uv run circus-mcp logs webapp
```

That's it! Your process is now managed by Circus MCP.

## Key Features

### 🚀 Process Management Made Easy

```bash
# Add processes with options
uv run circus-mcp add api "uvicorn app:api" --numprocesses 4 --working-dir /app

# Smart operations (won't fail if already running)
uv run circus-mcp ensure-started api

# Bulk operations
uv run circus-mcp start-all
uv run circus-mcp restart-all
```

### 📊 Comprehensive Monitoring

```bash
# Beautiful overview of all services
uv run circus-mcp overview

# Detailed status information
uv run circus-mcp status-all

# Real-time log viewing
uv run circus-mcp tail api
uv run circus-mcp logs-all
```

### 🤖 AI Agent Integration

Circus MCP includes built-in MCP protocol support, allowing AI agents to manage your processes:

```bash
# Start MCP server for AI integration
uv run circus-mcp mcp
```

Configure in your AI agent:
```json
{
  "mcpServers": {
    "circus-mcp": {
      "command": "uv",
      "args": ["run", "circus-mcp", "mcp"]
    }
  }
}
```

## Common Use Cases

### Web Application Management

```bash
# Production web app with multiple workers
uv run circus-mcp add webapp "gunicorn app:application" --numprocesses 4
uv run circus-mcp add worker "celery worker -A app" --numprocesses 2
uv run circus-mcp ensure-started all
```

### Development Environment

```bash
# Start your development stack
uv run circus-mcp add frontend "npm run dev" --working-dir /app/frontend
uv run circus-mcp add backend "python manage.py runserver" --working-dir /app/backend
uv run circus-mcp add redis "redis-server"
uv run circus-mcp start-all
```

### Microservices

```bash
# Manage multiple services
uv run circus-mcp add auth-service "python auth_service.py"
uv run circus-mcp add user-service "python user_service.py"  
uv run circus-mcp add notification-service "python notification_service.py"
uv run circus-mcp ensure-started all
```

## Why Circus MCP?

### vs. Docker Compose
- **Lighter**: No containers needed, just process management
- **Faster**: Direct process execution, no container overhead
- **Simpler**: One command to rule them all

### vs. systemd
- **User-friendly**: Simple commands instead of unit files
- **Cross-platform**: Works on any system with Python
- **AI-ready**: Built-in MCP support for automation

### vs. PM2
- **Python-native**: Perfect for Python applications
- **AI integration**: MCP protocol support out of the box
- **Comprehensive**: Process + log management in one tool

## Advanced Features

### Intelligent State Management

```bash
# These commands are safe to run multiple times
uv run circus-mcp ensure-started webapp    # Only starts if not running
uv run circus-mcp ensure-stopped worker    # Only stops if running
```

### Bulk Operations

```bash
# Work with all processes at once
uv run circus-mcp start-all     # Start everything
uv run circus-mcp stop-all      # Stop everything  
uv run circus-mcp restart-all   # Restart everything
uv run circus-mcp logs-all      # See all logs
```

### Log Management

```bash
# View logs with filtering
uv run circus-mcp logs webapp --lines 100 --stream stderr
uv run circus-mcp tail webapp --stream stdout

# See recent activity across all services
uv run circus-mcp logs-all
```

## Installation & Setup

### System Requirements

- Python 3.10 or higher
- Any operating system (Linux, macOS, Windows)

### Installation Options

```bash
# From PyPI (recommended)
uv add circus-mcp

# With pip (alternative)
pip install circus-mcp

# From source
git clone https://github.com/aether-platform/circus-mcp.git
cd circus-mcp
uv sync
```

### Verify Installation

```bash
uv run circus-mcp --help
uv run circus-mcp daemon-status
```

## Configuration

Circus MCP works out of the box with sensible defaults. For advanced usage:

### Custom Circus Configuration

```bash
# Use your own circus.ini
uv run circus-mcp start-daemon -c /path/to/your/circus.ini
```

### Process Configuration

```bash
# Add processes with full configuration
uv run circus-mcp add myapp "python app.py" \
  --numprocesses 4 \
  --working-dir /app \
```

## Getting Help

### Documentation

- **[Development Guide](docs/DEVELOPMENT.md)** - For contributors and advanced usage
- **[API Reference](docs/API.md)** - Complete command and API documentation

### Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/aether-platform/circus-mcp/issues)
- **Discussions**: [Join the community](https://github.com/aether-platform/circus-mcp/discussions)

### Quick Command Reference

```bash
# Daemon
uv run circus-mcp start-daemon
uv run circus-mcp stop-daemon
uv run circus-mcp daemon-status

# Process Management  
uv run circus-mcp add <name> <command>
uv run circus-mcp start/stop/restart <name>
uv run circus-mcp ensure-started/ensure-stopped <name>

# Monitoring
uv run circus-mcp overview
uv run circus-mcp status-all
uv run circus-mcp logs <name>

# AI Integration
uv run circus-mcp mcp
```

## Examples Repository

Check out our [examples repository](https://github.com/aether-platform/circus-mcp-examples) for real-world usage patterns:

- Django + Celery setup
- FastAPI microservices
- React + Node.js development stack
- Machine learning pipeline management

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- **[Circus](https://circus.readthedocs.io/)** - The underlying process manager
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - AI agent communication standard  
- **[AetherPlatform](https://github.com/aether-platform)** - Cloud-native development tools

---

**Made with ❤️ by [AetherPlatform](https://github.com/aether-platform)**

*Circus MCP: Simple process management, powerful automation.*