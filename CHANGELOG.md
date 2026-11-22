# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-22

### Security
- **Write tools are disabled by default.** The MCP server now exposes only
  `list_processes` and `get_process_status` unless explicitly enabled:
  `CIRCUS_MCP_ALLOW_WRITE=1` / `--allow-write` for `start_process`, `stop_process`,
  `restart_process`, and a separate `CIRCUS_MCP_ALLOW_ADD=1` / `--allow-add` for
  `add_process` (which runs arbitrary commands as the circusd user). Disabled tools are
  hidden from `tools/list` and rejected with `isError: true`.
- The Circus endpoint must be `ipc://` or loopback `tcp://`; other endpoints are refused
  unless `CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT=1`, since the Circus control socket is
  unauthenticated. README documents the threat model.

### Fixed
- Pin the MCP SDK to `mcp>=1.30,<2`. Without an upper bound a fresh install resolved
  `mcp` 2.x and the server crashed on startup (`'Server' object has no attribute 'list_tools'`).
- `__version__` reported 1.0.0; it is now read from the installed package metadata.
- Tool failures are returned with `isError: true` instead of a success result.

### Added
- `CIRCUS_ENDPOINT` / `--endpoint` to select the Circus endpoint for the MCP server.
- Regression tests, including an end-to-end stdio test against a real circusd.

### Changed
- Tool results are JSON instead of Python `repr`.
- `mcp_config.json` example no longer contains a developer-local path.

### Removed
- Unused `logging` extra.

### Breaking (behavioural)
- Clients that relied on `start_process` / `stop_process` / `restart_process` /
  `add_process` must now set the corresponding opt-in variable.

## [1.0.7] - 2024-12-21

### Fixed
- Use patch.object for more reliable module-level mocking
- Improve cross-environment test compatibility
- Enhance asyncio.to_thread mocking with explicit module imports
- Resolve CI/CD environment-specific test failures

## [1.0.6] - 2024-12-21

### Fixed
- Improved mock setup with explicit module patching for CI/CD reliability
- Enhanced test robustness across different Python environments
- Added comprehensive mock validation and assertions
- Resolved cross-platform test execution issues

## [1.0.5] - 2024-12-21

### Fixed
- Fixed CI/CD test failures with improved mock setup
- Enhanced test isolation and reliability
- Added proper mock assertions for better test coverage

## [1.0.4] - 2024-12-21

### Added
- Ruff integration for modern Python linting and formatting
- Pre-commit hooks for automated code quality
- Comprehensive ruff configuration with isort integration

### Changed
- Replaced Black and Flake8 with Ruff for unified tooling
- Updated CI/CD pipeline to use Ruff
- Improved development workflow with pre-commit automation

### Removed
- Black and Flake8 dependencies (replaced by Ruff)

## [1.0.3] - 2024-12-21

### Fixed
- Fixed test suite to work with current simplified architecture
- Removed outdated test dependencies and imports
- Updated MCP library dependency version
- Fixed CI/CD pipeline test failures

### Added
- Comprehensive test coverage for CircusManager
- MCP server integration tests
- Mock-based testing for isolated unit tests

## [1.0.2] - 2024-12-21

### Added
- Acknowledgments to Circus development team
- MCP stdio transport recommendations in documentation
- Security guidance for local development use

### Changed
- Emphasized MCP stdio as recommended transport method
- Added references to official MCP documentation

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
