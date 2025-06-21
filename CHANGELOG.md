# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2024-12-21

### Changed
- Updated all documentation to use `uv` instead of `pip` for modern Python development
- Changed installation examples to `uv add circus-mcp`
- Updated all command examples to use `uv run circus-mcp`
- Modified MCP configuration examples to use `uv run`
- Made documentation consistent with modern Python tooling practices

### Added
- GitHub Actions CI/CD pipeline
- Automated PyPI releases on git tags
- GitHub Releases with automatic changelog generation

## [1.0.0] - 2024-12-21

### Added
- Initial release of Circus MCP
- Simple process management tool combining Circus with MCP protocol
- CLI interface with comprehensive process management commands
- MCP server for AI agent integration
- Support for idempotent operations (ensure-started, ensure-stopped)
- Bulk operations (start-all, stop-all, restart-all)
- Log management and monitoring features
- Cross-platform compatibility (Linux, macOS, Windows)
- Environment compatibility with nvm, uv, poetry, pipenv

### Features
- **Process Management**: Add, start, stop, restart, remove processes
- **Smart Operations**: Idempotent commands that won't fail if already in desired state
- **Monitoring**: Comprehensive overview, status checking, and statistics
- **Log Management**: View, tail, and filter process logs
- **AI Integration**: Built-in MCP protocol support for coding agents
- **Bulk Operations**: Manage all processes at once
- **Configuration**: Simple file-based configuration with sensible defaults

### Technical Details
- Built on Circus process manager
- ZeroMQ communication with Circus daemon
- Async/await patterns for efficient I/O
- Click framework for CLI interface
- Model Context Protocol (MCP) for AI agent communication
- Python 3.10+ support