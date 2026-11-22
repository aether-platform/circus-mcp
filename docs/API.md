# API Reference

## Command Line Interface

### Daemon Management

#### `start-daemon`
Start the Circus daemon.

```bash
uv run circus-mcp start-daemon [OPTIONS]
```

**Options:**
- `-c, --config TEXT` - Configuration file path (default: circus.ini)

**Example:**
```bash
uv run circus-mcp start-daemon -c /path/to/my-circus.ini
```

#### `stop-daemon`
Stop the Circus daemon.

```bash
uv run circus-mcp stop-daemon
```

#### `daemon-status`
Check if the Circus daemon is running.

```bash
uv run circus-mcp daemon-status
```

### Process Management

#### `add`
Add a new process to Circus.

```bash
uv run circus-mcp add <name> <command> [OPTIONS]
```

**Arguments:**
- `name` - Process name
- `command` - Command to execute

**Options:**
- `-n, --numprocesses INTEGER` - Number of processes (default: 1)
- `-d, --working-dir TEXT` - Working directory

**Example:**
```bash
uv run circus-mcp add webapp "python app.py" --numprocesses 2 --working-dir /app
```

#### `start`
Start a process.

```bash
uv run circus-mcp start <name>
```

#### `stop`
Stop a process.

```bash
uv run circus-mcp stop <name>
```

#### `restart`
Restart a process.

```bash
uv run circus-mcp restart <name>
```

#### `remove`
Remove a process from Circus.

```bash
uv run circus-mcp remove <name>
```

### Intelligent Operations

#### `ensure-started`
Ensure a process is in started state (idempotent).

```bash
uv run circus-mcp ensure-started <name|all>
```

#### `ensure-stopped`
Ensure a process is in stopped state (idempotent).

```bash
uv run circus-mcp ensure-stopped <name|all>
```

### Bulk Operations

#### `start-all`
Start all processes.

```bash
uv run circus-mcp start-all [name]
```

If `name` is "all" or omitted, starts all processes.

#### `stop-all`
Stop all processes.

```bash
uv run circus-mcp stop-all [name]
```

#### `restart-all`
Restart all processes.

```bash
uv run circus-mcp restart-all [name]
```

### Status and Monitoring

#### `list`
List all processes.

```bash
uv run circus-mcp list
```

#### `status`
Get process status.

```bash
uv run circus-mcp status <name>
```

#### `status-all`
Show detailed status of all processes.

```bash
uv run circus-mcp status-all
```

#### `overview`
Show comprehensive system overview with visual status.

```bash
uv run circus-mcp overview
```

#### `stats`
Show system statistics.

```bash
uv run circus-mcp stats
```

### Log Management

#### `logs`
Show process logs.

```bash
uv run circus-mcp logs <name> [OPTIONS]
```

**Options:**
- `-n, --lines INTEGER` - Number of lines (default: 100)
- `-s, --stream CHOICE` - Stream to show: stdout, stderr, both (default: both)

**Example:**
```bash
uv run circus-mcp logs webapp --lines 50 --stream stderr
```

#### `tail`
Tail process logs.

```bash
uv run circus-mcp tail <name> [OPTIONS]
```

**Options:**
- `-s, --stream CHOICE` - Stream to tail: stdout, stderr (default: stdout)

#### `logs-all`
Show recent logs from all processes.

```bash
uv run circus-mcp logs-all
```

### MCP Integration

#### `mcp`
Start MCP server for AI agent integration. **Read-only by default.**

```bash
uv run circus-mcp mcp                          # list_processes, get_process_status only
uv run circus-mcp mcp --allow-write            # + start/stop/restart_process
uv run circus-mcp mcp --allow-write --allow-add  # + add_process (arbitrary commands)
```

| Option | Environment variable | Default | Effect |
|---|---|---|---|
| `--endpoint` | `CIRCUS_ENDPOINT` | `tcp://127.0.0.1:5555` | Circus control endpoint |
| `--allow-write` | `CIRCUS_MCP_ALLOW_WRITE=1` | off | Expose `start_process`, `stop_process`, `restart_process` |
| `--allow-add` | `CIRCUS_MCP_ALLOW_ADD=1` | off | Expose `add_process` |
| `--allow-remote-endpoint` | `CIRCUS_MCP_ALLOW_REMOTE_ENDPOINT=1` | off | Accept a non-loopback `tcp://` endpoint |

Results are JSON (the Circus reply). Failures — including calls to disabled tools — are returned with `isError: true`.

## MCP Protocol API

### Tools

The MCP server exposes the following tools for AI agents:

#### `add_process`
Add a new process to Circus. Requires `CIRCUS_MCP_ALLOW_ADD=1` / `--allow-add`: the command runs with the privileges of circusd, so enabling this gives the agent arbitrary command execution.

**Input Schema:**
```json
{
  "name": "string",
  "command": "string",
  "numprocesses": "integer (optional, default: 1)",
  "working_dir": "string (optional)"
}
```

#### `start_process`
Start a process. Requires `CIRCUS_MCP_ALLOW_WRITE=1` / `--allow-write` (as do `stop_process` and `restart_process`).

**Input Schema:**
```json
{
  "name": "string"
}
```

#### `stop_process`
Stop a process.

**Input Schema:**
```json
{
  "name": "string"
}
```

#### `restart_process`
Restart a process.

**Input Schema:**
```json
{
  "name": "string"
}
```

#### `list_processes`
List all processes.

**Input Schema:**
```json
{}
```

#### `get_process_status`
Get process status.

**Input Schema:**
```json
{
  "name": "string"
}
```

### Usage Examples

#### MCP Tool Call Example

```json
{
  "method": "tools/call",
  "params": {
    "name": "add_process",
    "arguments": {
      "name": "api-server",
      "command": "python -m uvicorn app:api --host 0.0.0.0 --port 8000",
      "numprocesses": 2,
      "working_dir": "/app"
    }
  }
}
```

#### Response Format

```json
{
  "content": [
    {
      "type": "text",
      "text": "{'status': 'ok', 'message': 'Process added successfully'}"
    }
  ]
}
```

## Python API

### CircusManager

Direct interface to Circus daemon.

```python
from circus_mcp.manager import CircusManager

manager = CircusManager()
await manager.connect()

# Add process
result = await manager.add_process("webapp", "python app.py", numprocesses=2)

# Start process
result = await manager.start_process("webapp")

# Get status
result = await manager.get_process_status("webapp")
```

### MCP Server

Model Context Protocol server implementation.

```python
from circus_mcp.mcp_server import CircusMCPServer

server = CircusMCPServer()
await server.run()
```

## Configuration

### Circus Configuration (circus.ini)

```ini
[circus]
endpoint = tcp://127.0.0.1:5555
pubsub_endpoint = tcp://127.0.0.1:5556
stats_endpoint = tcp://127.0.0.1:5557

[watcher:myapp]
cmd = python app.py
numprocesses = 2
working_dir = /app
stdout_stream.class = FileStream
stdout_stream.filename = /var/log/myapp.log
```

### MCP Client Configuration

**Recommended stdio transport method** (as per MCP documentation):

```json
{
  "mcpServers": {
    "circus-mcp": {
      "command": "uv",
      "args": ["run", "circus-mcp", "mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

This configuration uses MCP's stdio transport for secure, direct communication between AI agents and the process manager in local development environments.

## Error Handling

### Common Error Responses

#### Connection Error
```json
{
  "error": "Failed to connect to Circus daemon"
}
```

#### Process Not Found
```json
{
  "error": "Process 'webapp' not found"
}
```

#### Invalid Command
```json
{
  "error": "Invalid command format"
}
```

### Exit Codes

- `0` - Success
- `1` - General error
- `2` - Connection error
- `3` - Configuration error
