"""
Simple CLI for Circus process management.
"""

import asyncio
import click
from .manager import CircusManager


@click.group()
def cli():
    """Simple Circus process manager CLI."""
    pass


@cli.command()
@click.argument('name')
@click.argument('command')
@click.option('--numprocesses', '-n', default=1, help='Number of processes')
@click.option('--working-dir', '-d', help='Working directory')
def add(name: str, command: str, numprocesses: int, working_dir: str):
    """Add a new process."""
    async def _add():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        kwargs = {"numprocesses": numprocesses}
        if working_dir:
            kwargs["working_dir"] = working_dir
        
        try:
            result = await manager.add_process(name, command, **kwargs)
            if result.get("status") == "ok":
                click.echo(f"Process '{name}' added successfully")
            else:
                click.echo(f"Failed to add process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_add())


@cli.command()
@click.argument('name')
def start(name: str):
    """Start a process."""
    async def _start():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.start_process(name)
            if result.get("status") == "ok":
                click.echo(f"Process '{name}' started")
            else:
                click.echo(f"Failed to start process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_start())


@cli.command()
@click.argument('name')
def stop(name: str):
    """Stop a process."""
    async def _stop():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.stop_process(name)
            if result.get("status") == "ok":
                click.echo(f"Process '{name}' stopped")
            else:
                click.echo(f"Failed to stop process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_stop())


@cli.command()
def list():
    """List all processes."""
    async def _list():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.list_processes()
            if result.get("status") == "ok":
                watchers = result.get("watchers", [])
                if watchers:
                    click.echo("Processes:")
                    for watcher in watchers:
                        click.echo(f"  - {watcher}")
                else:
                    click.echo("No processes found")
            else:
                click.echo(f"Failed to list processes: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_list())


@cli.command()
@click.argument('name')
def status(name: str):
    """Get process status."""
    async def _status():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.get_process_status(name)
            if result.get("status") == "ok":
                click.echo(f"Process '{name}' status: {result.get('status')}")
            else:
                click.echo(f"Failed to get status: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_status())


@cli.command()
@click.argument('name')
def restart(name: str):
    """Restart a process."""
    async def _restart():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.restart_process(name)
            if result.get("status") == "ok":
                click.echo(f"Process '{name}' restarted")
            else:
                click.echo(f"Failed to restart process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_restart())


@cli.command()
@click.argument('name')
def remove(name: str):
    """Remove a process."""
    async def _remove():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.remove_process(name)
            if result.get("status") == "ok":
                click.echo(f"Process '{name}' removed")
            else:
                click.echo(f"Failed to remove process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_remove())


@cli.command()
@click.option('--config', '-c', default='circus.ini', help='Circus configuration file')
def start_daemon(config: str):
    """Start Circus daemon."""
    manager = CircusManager(config_file=config)
    
    if manager.is_daemon_running():
        click.echo("Circus daemon is already running")
        return
    
    if manager.start_daemon(config):
        click.echo(f"Circus daemon started with config: {config}")
    else:
        click.echo("Failed to start Circus daemon")


@cli.command()
def stop_daemon():
    """Stop Circus daemon."""
    manager = CircusManager()
    
    if not manager.is_daemon_running():
        click.echo("Circus daemon is not running")
        return
    
    if manager.stop_daemon():
        click.echo("Circus daemon stopped")
    else:
        click.echo("Failed to stop Circus daemon")


@cli.command()
def daemon_status():
    """Check Circus daemon status."""
    manager = CircusManager()
    
    if manager.is_daemon_running():
        click.echo("Circus daemon is running")
    else:
        click.echo("Circus daemon is not running")


@cli.command()
@click.argument('name')
def ensure_started(name: str):
    """Ensure process is in started state (idempotent start)."""
    async def _ensure_started():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            if name.lower() == "all":
                result = await manager.start_all()
                if result.get("status") == "ok":
                    click.echo("All processes ensured started")
                else:
                    click.echo(f"Failed to start all processes: {result}")
            else:
                result = await manager.ensure_started(name)
                if result.get("status") == "ok":
                    click.echo(result.get("message", f"Process '{name}' ensured started"))
                else:
                    click.echo(f"Failed to ensure process started: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_ensure_started())


@cli.command()
@click.argument('name')
def ensure_stopped(name: str):
    """Ensure process is in stopped state (idempotent stop)."""
    async def _ensure_stopped():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            if name.lower() == "all":
                result = await manager.stop_all()
                if result.get("status") == "ok":
                    click.echo("All processes ensured stopped")
                else:
                    click.echo(f"Failed to stop all processes: {result}")
            else:
                result = await manager.ensure_stopped(name)
                if result.get("status") == "ok":
                    click.echo(result.get("message", f"Process '{name}' ensured stopped"))
                else:
                    click.echo(f"Failed to ensure process stopped: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_ensure_stopped())


@cli.command()
@click.argument('name', default='all')
def start_all(name: str):
    """Start all processes or specific process with 'all' support."""
    async def _start_all():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            if name.lower() == "all":
                result = await manager.start_all()
                if result.get("status") == "ok":
                    click.echo("All processes started")
                else:
                    click.echo(f"Failed to start all processes: {result}")
            else:
                result = await manager.start_process(name)
                if result.get("status") == "ok":
                    click.echo(f"Process '{name}' started")
                else:
                    click.echo(f"Failed to start process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_start_all())


@cli.command()
@click.argument('name', default='all')
def stop_all(name: str):
    """Stop all processes or specific process with 'all' support."""
    async def _stop_all():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            if name.lower() == "all":
                result = await manager.stop_all()
                if result.get("status") == "ok":
                    click.echo("All processes stopped")
                else:
                    click.echo(f"Failed to stop all processes: {result}")
            else:
                result = await manager.stop_process(name)
                if result.get("status") == "ok":
                    click.echo(f"Process '{name}' stopped")
                else:
                    click.echo(f"Failed to stop process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_stop_all())


@cli.command()
@click.argument('name', default='all')
def restart_all(name: str):
    """Restart all processes or specific process with 'all' support."""
    async def _restart_all():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            if name.lower() == "all":
                result = await manager.restart_all()
                if result.get("status") == "ok":
                    click.echo("All processes restarted")
                else:
                    click.echo(f"Failed to restart all processes: {result}")
            else:
                result = await manager.restart_process(name)
                if result.get("status") == "ok":
                    click.echo(f"Process '{name}' restarted")
                else:
                    click.echo(f"Failed to restart process: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_restart_all())


@cli.command()
def status_all():
    """Show status of all processes."""
    async def _status_all():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.get_all_status()
            if result.get("status") == "ok":
                processes = result.get("processes", {})
                
                click.echo("All Process Status:")
                click.echo("-" * 50)
                
                for name, status_info in processes.items():
                    status = status_info.get("status", "unknown")
                    if status == "active":
                        status_color = click.style("RUNNING", fg="green")
                    elif status == "stopped":
                        status_color = click.style("STOPPED", fg="red")
                    else:
                        status_color = click.style(status.upper(), fg="yellow")
                    
                    click.echo(f"  {name:<20} {status_color}")
                    
                    # Show additional info if available
                    if "info" in status_info:
                        info = status_info["info"]
                        if isinstance(info, dict):
                            for key, value in info.items():
                                if key not in ["status"]:
                                    click.echo(f"    {key}: {value}")
            else:
                click.echo(f"Failed to get status: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_status_all())


@cli.command()
def stats():
    """Show system statistics."""
    async def _stats():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.get_stats()
            if result.get("status") == "ok":
                click.echo("System Statistics:")
                click.echo("-" * 30)
                
                info = result.get("info", {})
                if isinstance(info, dict):
                    for key, value in info.items():
                        click.echo(f"  {key}: {value}")
                else:
                    click.echo(f"  {info}")
            else:
                click.echo(f"Failed to get stats: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_stats())


@cli.command()
def overview():
    """Show comprehensive system overview."""
    async def _overview():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            # Get all status
            status_result = await manager.get_all_status()
            
            if status_result.get("status") == "ok":
                processes = status_result.get("processes", {})
                
                # Count processes by status
                running_count = 0
                stopped_count = 0
                error_count = 0
                
                for name, status_info in processes.items():
                    status = status_info.get("status", "unknown")
                    if status == "active":
                        running_count += 1
                    elif status == "stopped":
                        stopped_count += 1
                    else:
                        error_count += 1
                
                # Display overview
                click.echo("=== Circus Process Manager Overview ===")
                click.echo(f"Total Processes: {len(processes)}")
                click.echo(f"Running: {click.style(str(running_count), fg='green')}")
                click.echo(f"Stopped: {click.style(str(stopped_count), fg='red')}")
                if error_count > 0:
                    click.echo(f"Errors: {click.style(str(error_count), fg='yellow')}")
                
                click.echo("\nProcess Details:")
                click.echo("-" * 40)
                
                for name, status_info in processes.items():
                    status = status_info.get("status", "unknown")
                    if status == "active":
                        status_display = click.style("●", fg="green") + " RUNNING"
                    elif status == "stopped":
                        status_display = click.style("●", fg="red") + " STOPPED"
                    else:
                        status_display = click.style("●", fg="yellow") + f" {status.upper()}"
                    
                    click.echo(f"  {name:<20} {status_display}")
            else:
                click.echo(f"Failed to get overview: {status_result}")
                
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_overview())


@cli.command()
@click.argument('name')
@click.option('--lines', '-n', default=100, help='Number of lines to show')
@click.option('--stream', '-s', default='both', type=click.Choice(['stdout', 'stderr', 'both']), help='Stream to show')
def logs(name: str, lines: int, stream: str):
    """Show process logs."""
    async def _logs():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            if stream == 'both':
                result = await manager.get_process_logs(name, lines)
                if result.get("status") == "ok":
                    stdout_logs = result.get("stdout", [])
                    stderr_logs = result.get("stderr", [])
                    
                    if stdout_logs:
                        click.echo(f"=== STDOUT for {name} ===")
                        for log_line in stdout_logs:
                            click.echo(log_line)
                    
                    if stderr_logs:
                        click.echo(f"\n=== STDERR for {name} ===")
                        for log_line in stderr_logs:
                            click.echo(click.style(log_line, fg="red"))
                    
                    if not stdout_logs and not stderr_logs:
                        click.echo(f"No logs found for process '{name}'")
                else:
                    click.echo(f"Failed to get logs: {result}")
            else:
                result = await manager.tail_process_logs(name, stream)
                if result.get("status") == "ok":
                    logs_data = result.get("logs", [])
                    if logs_data:
                        click.echo(f"=== {stream.upper()} for {name} ===")
                        for log_line in logs_data:
                            if stream == 'stderr':
                                click.echo(click.style(log_line, fg="red"))
                            else:
                                click.echo(log_line)
                    else:
                        click.echo(f"No {stream} logs found for process '{name}'")
                else:
                    click.echo(f"Failed to get logs: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_logs())


@cli.command()
@click.argument('name')
@click.option('--stream', '-s', default='stdout', type=click.Choice(['stdout', 'stderr']), help='Stream to tail')
def tail(name: str, stream: str):
    """Tail process logs (show recent logs)."""
    async def _tail():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            result = await manager.tail_process_logs(name, stream)
            if result.get("status") == "ok":
                logs_data = result.get("logs", [])
                if logs_data:
                    click.echo(f"=== Tail {stream.upper()} for {name} ===")
                    for log_line in logs_data:
                        if stream == 'stderr':
                            click.echo(click.style(log_line, fg="red"))
                        else:
                            click.echo(log_line)
                else:
                    click.echo(f"No recent {stream} logs found for process '{name}'")
            else:
                click.echo(f"Failed to tail logs: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_tail())


@cli.command()
def logs_all():
    """Show recent logs for all processes."""
    async def _logs_all():
        manager = CircusManager()
        if not await manager.connect():
            click.echo("Failed to connect to Circus daemon")
            return
        
        try:
            # Get list of processes first
            list_result = await manager.list_processes()
            if list_result.get("status") != "ok":
                click.echo("Failed to get process list")
                return
            
            watchers = list_result.get("watchers", [])
            
            for watcher in watchers:
                if watcher in ['circusd-stats']:  # Skip system processes
                    continue
                    
                click.echo(f"\n{'='*60}")
                click.echo(f"LOGS FOR: {watcher}")
                click.echo('='*60)
                
                result = await manager.tail_process_logs(watcher, "stdout")
                if result.get("status") == "ok":
                    logs_data = result.get("logs", [])
                    if logs_data:
                        for log_line in logs_data[-10:]:  # Show last 10 lines
                            click.echo(log_line)
                    else:
                        click.echo("No recent logs")
                else:
                    click.echo(f"Failed to get logs: {result}")
        except Exception as e:
            click.echo(f"Error: {e}")
    
    asyncio.run(_logs_all())


@cli.command()
def mcp():
    """Start MCP server."""
    async def _mcp():
        from .mcp_server import CircusMCPServer
        
        server = CircusMCPServer()
        await server.run()
    
    asyncio.run(_mcp())


if __name__ == '__main__':
    cli()