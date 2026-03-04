# Circus MCP

[![PyPI version](https://badge.fury.io/py/circus-mcp.svg)](https://badge.fury.io/py/circus-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Process management for AI coding agents via the Model Context Protocol (MCP).**

## Reduce Tokens, Agents Work Faster

AI agents debugging processes via raw shell commands (`supervisorctl`, `ps`, `journalctl`) waste **60-85% of tokens** on unstructured output parsing, repeated commands, and inter-step reasoning. Circus MCP eliminates this by providing structured, bounded MCP tool responses.

| | Raw Commands | Circus MCP |
|--|-------------|------------|
| Tool calls per investigation | 8-12 | 3-5 |
| Tokens per investigation | 2,900-9,400 | 935-1,535 |
| Retry cost scaling | Exponential | Linear |

## Process Management via MCP

Circus MCP exposes process lifecycle operations as MCP tools. AI agents call structured tools instead of parsing shell output.

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_processes` | — | List all managed processes |
| `get_process_status` | `name` | Process state and PID |
| `start_process` | `name` | Start a process |
| `stop_process` | `name` | Stop a process |
| `restart_process` | `name` | Restart a process |
| `add_process` | `name`, `command`, `numprocesses?`, `working_dir?` | Add a new process dynamically |

### Claude Code

```bash
claude mcp add circus-mcp -- uv run circus-mcp mcp
```

### VS Code / Cursor

`.vscode/mcp.json`:
```json
{
  "servers": {
    "circus-mcp": {
      "command": "uv",
      "args": ["run", "circus-mcp", "mcp"]
    }
  }
}
```

## Circus MCP vs Supervisord MCP

| | Circus MCP | [Supervisord MCP](https://github.com/aether-platform/supervisord-mcp) |
|--|-----------|---------------|
| Dynamic process addition | Via API | Not supported (requires config file edit + reload) |
| Log retrieval | stdout + stderr in one call | Separate calls |
| System stats (CPU/memory) | Available | Not available |
| Idempotent operations | `ensure_started` / `ensure_stopped` | Throws error if already running |
| Transport | ZeroMQ (async) | HTTP XML-RPC (sync) |
| Best for | **AI agent workflows** | Existing Supervisord environments |

## Documentation

- [AI Token Reduction Solution](https://docs.aether-platform.com/en/solutions/ai-token-reduction/) — Token cost analysis, team-scale projections, research references
- [AI & MCP Technical Background](https://docs.aether-platform.com/en/technology/llm-mcp/) — Architecture, MCP hosting, tenant isolation
- [Installation & CLI Reference](https://docs.aether-platform.com/en/technology/llm-mcp/) — Setup, configuration, full command reference

## License

MIT — see [LICENSE](LICENSE). Built on [Circus](https://circus.readthedocs.io/).
