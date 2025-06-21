# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CircusMCP is a Domain-Driven Design (DDD) process management system that integrates Circus process manager with the Model Context Protocol (MCP). It enables AI agents to control development applications through standardized MCP tools and resources.

## Architecture

The system follows a layered DDD architecture:

```
Controller → Service → Domain ← Infrastructure
```

- **Controller Layer** (`src/controller/`): MCP protocol handling and external interfaces
- **Service Layer** (`src/service/`): Application logic and use cases
- **Domain Layer** (`src/domain/`): Business logic and domain models (framework-independent)
- **Infrastructure Layer** (`src/infrastructure/`): Data access and external system integration

Key components:
- **ProcessService**: Manages Circus watchers and process lifecycle
- **LogService**: Background log processing with pattern classification
- **MCPController**: JSON-RPC 2.0 protocol implementation for AI agent communication
- **Repository Pattern**: Abstracted data access (currently in-memory, extensible to file/database)

## Development Commands

### Installation and Setup
```bash
# Install dependencies with uv
uv sync

# Install development dependencies
uv sync --extra dev

# Initialize project structure
uv run python main.py init --create-dirs

# Validate configuration
uv run python main.py validate

# Start Circus daemon (in separate terminal)
uv run circusd config/circus.ini
```

### Running the Application
```bash
# Start MCP server (main application)
uv run python app.py

# Alternative CLI interface
uv run python main.py start

# Check status
uv run python main.py status
```

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_new_architecture.py -v
uv run pytest tests/ -m "not slow"
uv run pytest tests/ -m integration

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run single test
uv run pytest tests/test_new_architecture.py::TestNewArchitectureIntegration::test_full_stack_integration -v
```

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Type checking
uv run mypy src/

# Linting
uv run flake8 src/ tests/
```

## Configuration

- **`config/circus.ini`**: Circus daemon configuration with process watchers
- **`config/config.yaml`**: Main application configuration (DDD architecture settings)
- **`config/mcp_config.json`**: MCP protocol server configuration
- **`config/log_patterns.yaml`**: Log classification patterns for automated parsing

Critical configuration sections:
- `circus.endpoint`: ZeroMQ connection to Circus daemon
- `logging.background_processing`: Async log processing settings
- `security.allowed_commands`: Whitelist for process commands
- `performance.memory.max_log_entries`: Memory management limits

## Key Development Patterns

### Dependency Injection
The application uses constructor-based DI in `app.py`. All dependencies flow from Infrastructure → Domain ← Service ← Controller.

### Async Processing
- All I/O operations are async
- Background log processing with configurable batch sizes
- Graceful shutdown handling with cleanup tasks

### Error Handling
Domain-specific exceptions in `src/utils/exceptions.py`:
- `CircusManagerError`: Process management failures
- `MCPServerError`: Protocol communication issues
- `ConfigurationError`: Invalid configuration states

### Repository Pattern
Abstract interfaces in Domain layer with concrete implementations in Infrastructure. Supports multiple storage backends (memory, file, future database support).

## MCP Integration

The system exposes MCP tools for AI agents:
- **Process Control**: `add_process`, `start_process`, `stop_process`, `restart_process`
- **Status Monitoring**: `get_processes`, `get_process_status`, `get_system_stats`
- **Log Management**: `get_logs`, `get_log_summary`

MCP resources provide real-time data:
- `process://[name]/info`: Process information
- `logs://[name]/recent`: Recent log entries

## Testing Strategy

- **Integration Tests**: Full-stack testing through MCP protocol
- **Domain Tests**: Business logic validation
- **Performance Tests**: Async processing and memory management
- **Architecture Boundary Tests**: Layer separation enforcement

The test suite validates the entire DDD architecture from MCP requests through to Circus process management.
