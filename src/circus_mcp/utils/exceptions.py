"""
Custom exceptions for Circus MCP Manager.
"""

from typing import Optional, Any


class CircusMCPError(Exception):
    """Base exception for all Circus MCP Manager errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class CircusManagerError(CircusMCPError):
    """Exception raised by Circus Manager operations."""

    pass


class MCPServerError(CircusMCPError):
    """Exception raised by MCP Server operations."""

    pass


class LogParserError(CircusMCPError):
    """Exception raised by Log Parser operations."""

    pass


class IOControllerError(CircusMCPError):
    """Exception raised by I/O Controller operations."""

    pass


class ConfigurationError(CircusMCPError):
    """Exception raised for configuration-related errors."""

    pass


class ProcessNotFoundError(CircusManagerError):
    """Exception raised when a process is not found."""

    def __init__(self, process_name: str) -> None:
        super().__init__(f"Process '{process_name}' not found")
        self.process_name = process_name


class ProcessAlreadyRunningError(CircusManagerError):
    """Exception raised when trying to start an already running process."""

    def __init__(self, process_name: str) -> None:
        super().__init__(f"Process '{process_name}' is already running")
        self.process_name = process_name


class ProcessNotRunningError(CircusManagerError):
    """Exception raised when trying to operate on a non-running process."""

    def __init__(self, process_name: str) -> None:
        super().__init__(f"Process '{process_name}' is not running")
        self.process_name = process_name


class InvalidProcessNameError(CircusManagerError):
    """Exception raised for invalid process names."""

    def __init__(self, process_name: str, reason: str = "") -> None:
        message = f"Invalid process name '{process_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)
        self.process_name = process_name
        self.reason = reason


class MCPProtocolError(MCPServerError):
    """Exception raised for MCP protocol-related errors."""

    def __init__(self, message: str, error_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class LogPatternError(LogParserError):
    """Exception raised for log pattern-related errors."""

    pass


class StreamError(IOControllerError):
    """Exception raised for stream-related errors."""

    pass
