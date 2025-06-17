"""
Main entry point for Circus MCP Manager.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import click

from src.circus_manager import CircusManager
from src.mcp_server import MCPServer
from src.utils.exceptions import CircusMCPError
from src.utils.helpers import create_directory_structure


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/circus_mcp_manager.log', mode='a'),
    ]
)

logger = logging.getLogger(__name__)


class CircusMCPApplication:
    """Main application class for Circus MCP Manager."""
    
    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """
        Initialize the application.
        
        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir or Path("config")
        self.circus_manager: Optional[CircusManager] = None
        self.mcp_server: Optional[MCPServer] = None
        self._shutdown_event = asyncio.Event()
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize the application components."""
        try:
            logger.info("Initializing Circus MCP Manager...")
            
            # Ensure directory structure exists
            create_directory_structure(Path.cwd())
            
            # Initialize Circus Manager
            circus_config_path = self.config_dir / "circus.ini"
            self.circus_manager = CircusManager(circus_config_path)
            await self.circus_manager.initialize()
            
            # Try to connect to Circus daemon
            connected = await self.circus_manager.connect_to_circus()
            if not connected:
                logger.warning("Could not connect to Circus daemon. Some features may not work.")
            
            # Initialize MCP Server
            mcp_config_path = self.config_dir / "mcp_config.json"
            self.mcp_server = MCPServer(self.circus_manager, mcp_config_path)
            
            logger.info("Circus MCP Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {str(e)}")
            raise CircusMCPError(f"Initialization failed: {str(e)}")
    
    async def start(self) -> None:
        """Start the application."""
        if self._running:
            logger.warning("Application is already running")
            return
        
        try:
            self._running = True
            logger.info("Starting Circus MCP Manager...")
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start MCP Server
            if self.mcp_server:
                await self.mcp_server.start()
            
            logger.info("Circus MCP Manager started successfully")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error during application startup: {str(e)}")
            raise
        finally:
            await self.cleanup()
    
    async def stop(self) -> None:
        """Stop the application."""
        if not self._running:
            return
        
        logger.info("Stopping Circus MCP Manager...")
        self._shutdown_event.set()
    
    async def cleanup(self) -> None:
        """Clean up application resources."""
        try:
            self._running = False
            
            # Stop MCP Server
            if self.mcp_server:
                await self.mcp_server.stop()
            
            # Cleanup Circus Manager
            if self.circus_manager:
                await self.circus_manager.cleanup()
            
            logger.info("Circus MCP Manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_status(self) -> dict:
        """Get application status."""
        status = {
            "running": self._running,
            "config_dir": str(self.config_dir),
        }
        
        if self.circus_manager:
            status["circus_manager"] = self.circus_manager.get_system_status()
        
        if self.mcp_server:
            status["mcp_server"] = self.mcp_server.get_server_info()
        
        return status


# CLI Commands

@click.group()
@click.option('--config-dir', type=click.Path(exists=True, path_type=Path), 
              default=Path("config"), help='Configuration directory')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), 
              default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, config_dir: Path, log_level: str):
    """Circus MCP Manager - Process management with MCP protocol support."""
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    # Store config in context
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir


@cli.command()
@click.pass_context
def start(ctx):
    """Start the Circus MCP Manager server."""
    config_dir = ctx.obj['config_dir']
    
    async def run_server():
        app = CircusMCPApplication(config_dir)
        try:
            await app.initialize()
            await app.start()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            sys.exit(1)
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


@cli.command()
@click.pass_context
def status(ctx):
    """Show status of the Circus MCP Manager."""
    config_dir = ctx.obj['config_dir']
    
    async def show_status():
        app = CircusMCPApplication(config_dir)
        try:
            await app.initialize()
            status_info = app.get_status()
            
            click.echo("Circus MCP Manager Status:")
            click.echo(f"  Running: {status_info['running']}")
            click.echo(f"  Config Directory: {status_info['config_dir']}")
            
            if 'circus_manager' in status_info:
                cm_status = status_info['circus_manager']
                click.echo("\nCircus Manager:")
                click.echo(f"  Initialized: {cm_status.get('circus_manager', {}).get('initialized', False)}")
                click.echo(f"  Connected: {cm_status.get('circus_manager', {}).get('connected', False)}")
                
                config_info = cm_status.get('configuration', {})
                click.echo(f"  Total Watchers: {config_info.get('total_watchers', 0)}")
            
            if 'mcp_server' in status_info:
                mcp_status = status_info['mcp_server']
                click.echo("\nMCP Server:")
                click.echo(f"  Name: {mcp_status.get('name', 'Unknown')}")
                click.echo(f"  Version: {mcp_status.get('version', 'Unknown')}")
                click.echo(f"  Available Tools: {mcp_status.get('available_tools', 0)}")
                click.echo(f"  Available Resources: {mcp_status.get('available_resources', 0)}")
            
        except Exception as e:
            click.echo(f"Error getting status: {str(e)}", err=True)
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(show_status())


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate configuration files."""
    config_dir = ctx.obj['config_dir']
    
    async def validate_config():
        app = CircusMCPApplication(config_dir)
        try:
            await app.initialize()
            
            if app.circus_manager:
                errors = app.circus_manager.config_handler.validate_config()
                if errors:
                    click.echo("Configuration validation errors:")
                    for error in errors:
                        click.echo(f"  - {error}")
                    sys.exit(1)
                else:
                    click.echo("Configuration validation passed")
            
        except Exception as e:
            click.echo(f"Validation error: {str(e)}", err=True)
            sys.exit(1)
        finally:
            await app.cleanup()
    
    asyncio.run(validate_config())


@cli.command()
@click.option('--create-dirs', is_flag=True, help='Create missing directories')
def init(create_dirs: bool):
    """Initialize project structure."""
    try:
        base_path = Path.cwd()
        
        if create_dirs:
            create_directory_structure(base_path)
            click.echo("Created project directory structure")
        
        # Check for required files
        required_files = [
            "config/circus.ini",
            "config/log_patterns.yaml", 
            "config/mcp_config.json",
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (base_path / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            click.echo("Missing configuration files:")
            for file_path in missing_files:
                click.echo(f"  - {file_path}")
            click.echo("\nPlease create these files before starting the server.")
        else:
            click.echo("All required configuration files are present")
        
    except Exception as e:
        click.echo(f"Initialization error: {str(e)}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()