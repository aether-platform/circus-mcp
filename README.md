# Circus MCP

[![PyPI version](https://badge.fury.io/py/circus-mcp.svg)](https://badge.fury.io/py/circus-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Cut 75-80% of AI agent debugging tokens in development cycle. Process management via MCP — structured tools replace shell commands.**

## 75-80% Token Reduction for AI Agent Debugging in Development Cycle

AI agents debugging processes via raw shell commands (`supervisorctl`, `ps`, `journalctl`) burn most of their tokens on unstructured output parsing, repeated commands, and inter-step reasoning. Circus MCP replaces this with structured, bounded MCP tool responses.

|                              | Raw Commands | Circus MCP | Reduction  |
| ---------------------------- | ------------ | ---------- | ---------- |
| Tool calls per investigation | 8-12         | 3-5        | **60-70%** |
| Tokens per investigation     | 2,900-9,400  | 935-1,535  | **~75%**   |
| With retries (typical)       | ~10,000+     | ~2,000     | **~80%**   |
| Retry cost scaling           | Exponential  | Linear     | —          |

## Process Management via MCP

Circus MCP exposes process lifecycle operations as MCP tools. AI agents call structured tools instead of parsing shell output.

| Tool                 | Parameters                                         | Description                   |
| -------------------- | -------------------------------------------------- | ----------------------------- |
| `list_processes`     | —                                                  | List all managed processes    |
| `get_process_status` | `name`                                             | Process state and PID         |
| `start_process`      | `name`                                             | Start a process (opt-in: write) |
| `stop_process`       | `name`                                             | Stop a process (opt-in: write) |
| `restart_process`    | `name`                                             | Restart a process (opt-in: write) |
| `add_process`        | `name`, `command`, `numprocesses?`, `working_dir?` | Add a new process dynamically (opt-in: add) |

**Since 1.1.0 the server is read-only by default.** Only `list_processes` and `get_process_status` are exposed unless you opt in:

| To enable | Environment variable | CLI flag |
| --------- | -------------------- | -------- |
| `start_process`, `stop_process`, `restart_process` | `CIRCUS_MCP_ALLOW_WRITE=1` | `--allow-write` |
| `add_process` | `CIRCUS_MCP_ALLOW_ADD=1` | `--allow-add` |

Results are JSON and failures are returned with `isError: true`.

> **MCP SDK requirement:** 1.1.0 and later depend on `mcp>=1.30,<2`, so `uvx circus-mcp mcp` works without extra pins. Support for `mcp` 2.x is planned for 2.0.0. *Only if you are still on 1.0.x:* it does not cap `mcp`, so a fresh install resolves `mcp` 2.x and crashes with `AttributeError: 'Server' object has no attribute 'list_tools'`; upgrade, or launch with `uvx --with 'mcp<2' circus-mcp mcp`.

### Claude Code

```bash
# read-only (default)
claude mcp add circus-mcp -- uvx circus-mcp mcp

# allow start/stop/restart
claude mcp add circus-mcp -e CIRCUS_MCP_ALLOW_WRITE=1 -- uvx circus-mcp mcp
```

### VS Code / Cursor

`.vscode/mcp.json`:

```json
{
  "servers": {
    "circus-mcp": {
      "command": "uv",
      "args": ["run", "circus-mcp", "mcp"],
      "env": {
        "CIRCUS_ENDPOINT": "tcp://127.0.0.1:5555",
        "CIRCUS_MCP_ALLOW_WRITE": "1"
      }
    }
  }
}
```

## Security Notes

- **The Circus control socket has no authentication.** Anyone who can reach the endpoint can add, start, stop or kill processes and quit circusd — regardless of this MCP server's settings. Keep `endpoint` on `127.0.0.1` (as in the bundled `circus.ini`) or use an `ipc://` socket protected by file permissions; never bind it to `0.0.0.0`.
- The MCP server enforces this on its side: `CIRCUS_ENDPOINT` (or `--endpoint`) must be `ipc://…` or a loopback `tcp://` address. A remote endpoint is refused unless `CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT=1` is set.
- **`add_process` is arbitrary command execution** as the circusd user. A prompt injection (e.g. text in a log or issue the agent reads) could chain `add_process` → `start_process`. Enable `CIRCUS_MCP_ALLOW_ADD` only in disposable environments.
- Write tools (`start_process`, `stop_process`, `restart_process`) are off by default; enable them with `CIRCUS_MCP_ALLOW_WRITE=1`.

## Circus MCP vs Supervisord MCP

|                           | Circus MCP                          | [Supervisord MCP](https://github.com/aether-platform/supervisord-mcp) |
| ------------------------- | ----------------------------------- | --------------------------------------------------------------------- |
| Dynamic process addition  | Via API                             | Not supported (requires config file edit + reload)                    |
| Log retrieval             | stdout + stderr in one call         | Separate calls                                                        |
| System stats (CPU/memory) | Available                           | Not available                                                         |
| Idempotent operations     | `ensure_started` / `ensure_stopped` | Throws error if already running                                       |
| Transport                 | ZeroMQ (async)                      | HTTP XML-RPC (sync)                                                   |
| Best for                  | **AI agent workflows**              | Existing Supervisord environments                                     |

## Documentation

- [AI Token Reduction Solution](https://docs.aether-platform.com/en/solutions/ai-token-reduction/) — Token cost analysis, team-scale projections, research references
- [AI & MCP Technical Background](https://docs.aether-platform.com/en/technology/llm-mcp/) — Architecture, MCP hosting, tenant isolation
- [Installation & CLI Reference](https://docs.aether-platform.com/en/technology/llm-mcp/) — Setup, configuration, full command reference

## License

MIT — see [LICENSE](LICENSE). Built on [Circus](https://circus.readthedocs.io/).
