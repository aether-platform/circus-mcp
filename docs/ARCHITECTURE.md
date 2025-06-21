# Architecture Design & Rationale

## Why Circus MCP Exists

**Mission**: Enable more efficient AI-assisted development in complex microservices environments, contributing to societal productivity.

**Challenge**: Modern development involves managing multiple microservices, and AI coding agents need efficient tools to handle this complexity without excessive token consumption.

**Solution**: Direct process management through MCP protocol, optimized for AI agents working with microservices architectures.

## Architecture Philosophy

### Simplicity First

We chose the simplest architecture that solves the problem effectively:

```
src/circus_mcp/
├── manager.py          # Core Circus operations
├── cli.py              # CLI interface
├── mcp_server.py       # MCP protocol for AI agents
└── main.py             # Entry point
```

**Why Simple?**
- **AI Agent Efficiency**: Less complexity means more reliable AI integration
- **Token Conservation**: Direct operations instead of parsing shell outputs
- **Maintenance**: Easy to understand and extend

### Key Design Decisions

#### 1. Direct Circus Integration
```python
# Direct ZeroMQ communication - no shell commands
from circus.client import CircusClient
result = await asyncio.to_thread(client.call, {"command": "start", "properties": {"name": name}})
```

**Benefits for AI Agents**:
- Structured JSON responses instead of parsing text output
- Immediate status feedback without multiple command executions
- Reliable error handling

#### 2. MCP Protocol Native Support
```python
# AI agents can directly call process management functions
{
  "tool": "start_process",
  "arguments": {"name": "webapp"}
}
```

**Token Savings**:
- No need to generate shell commands
- No output parsing required
- Bulk operations reduce interaction count

#### 3. Environment Compatibility
Works with any development environment without configuration:
- Node.js with nvm
- Python with uv/poetry/pipenv
- Any tool available in PATH

```bash
# These work automatically
circus-mcp add frontend "npm run dev"
circus-mcp add api "uv run python app.py"
```

## Core Design Principles

- **AI-First**: Every design decision optimizes for AI agent efficiency
- **Token Conservation**: Minimize AI agent token usage through direct operations
- **Simplicity**: Single-purpose modules that are easy to understand
- **Direct Integration**: No shell command overhead

## Why This Architecture Works

1. **Token Efficiency**: AI agents use fewer tokens for process management
2. **Reliability**: Structured responses instead of parsing shell output
3. **Speed**: Direct protocol communication
4. **Simplicity**: Easy for humans to understand and extend
5. **Compatibility**: Works with existing development workflows

The architecture serves its primary purpose: **making AI coding agents more efficient at development server management**.