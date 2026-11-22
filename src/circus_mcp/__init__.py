"""
Circus MCP - Simple Circus process management.

A simple tool for managing processes using Circus daemon.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("circus-mcp")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "1.1.0"
__author__ = "Circus MCP Team"

from .manager import CircusManager

__all__ = ["CircusManager"]
