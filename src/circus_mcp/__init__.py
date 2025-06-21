"""
Circus MCP - Simple Circus process management.

A simple tool for managing processes using Circus daemon.
"""

__version__ = "1.0.0"
__author__ = "Circus MCP Team"

from .manager import CircusManager

__all__ = ["CircusManager"]
