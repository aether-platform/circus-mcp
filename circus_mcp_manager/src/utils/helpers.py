"""
Helper utilities for Circus MCP Manager.
"""

import json
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import psutil

from .exceptions import ConfigurationError, InvalidProcessNameError


def load_config(config_path: Union[str, Path], config_type: str = "auto") -> Dict[str, Any]:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file
        config_type: Type of config file ('json', 'yaml', 'ini', 'auto')
        
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigurationError: If configuration cannot be loaded
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    try:
        if config_type == "auto":
            config_type = config_path.suffix.lower().lstrip(".")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_type in ["json"]:
                return json.load(f)
            elif config_type in ["yaml", "yml"]:
                return yaml.safe_load(f)
            elif config_type in ["ini"]:
                # For INI files, we'll return the raw content for now
                # as circus handles INI parsing internally
                return {"raw_content": f.read()}
            else:
                raise ConfigurationError(f"Unsupported config type: {config_type}")
                
    except Exception as e:
        raise ConfigurationError(f"Failed to load config from {config_path}: {str(e)}")


def validate_process_name(process_name: str) -> bool:
    """
    Validate process name according to circus naming conventions.
    
    Args:
        process_name: Name to validate
        
    Returns:
        True if valid
        
    Raises:
        InvalidProcessNameError: If name is invalid
    """
    if not process_name:
        raise InvalidProcessNameError(process_name, "Process name cannot be empty")
    
    if not isinstance(process_name, str):
        raise InvalidProcessNameError(str(process_name), "Process name must be a string")
    
    # Check for valid characters (alphanumeric, underscore, hyphen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', process_name):
        raise InvalidProcessNameError(
            process_name, 
            "Process name can only contain alphanumeric characters, underscores, and hyphens"
        )
    
    # Check length constraints
    if len(process_name) > 64:
        raise InvalidProcessNameError(process_name, "Process name too long (max 64 characters)")
    
    if len(process_name) < 1:
        raise InvalidProcessNameError(process_name, "Process name too short (min 1 character)")
    
    # Check for reserved names
    reserved_names = ["circus", "arbiter", "stats", "all"]
    if process_name.lower() in reserved_names:
        raise InvalidProcessNameError(process_name, f"'{process_name}' is a reserved name")
    
    return True


def format_log_entry(
    timestamp: datetime,
    level: str,
    process_name: str,
    message: str,
    extra_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a log entry into a standardized structure.
    
    Args:
        timestamp: Log timestamp
        level: Log level (error, warning, info, debug)
        process_name: Name of the process that generated the log
        message: Log message
        extra_data: Additional data to include
        
    Returns:
        Formatted log entry dictionary
    """
    entry = {
        "timestamp": timestamp.isoformat(),
        "level": level.lower(),
        "process_name": process_name,
        "message": message.strip(),
    }
    
    if extra_data:
        entry["extra"] = extra_data
    
    return entry


def get_system_info() -> Dict[str, Any]:
    """
    Get current system information.
    
    Returns:
        Dictionary containing system information
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            },
            "processes": len(psutil.pids()),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }
    except Exception as e:
        return {"error": f"Failed to get system info: {str(e)}"}


def sanitize_input(input_data: str, max_length: int = 1024) -> str:
    """
    Sanitize input data for security.
    
    Args:
        input_data: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized input string
    """
    if not isinstance(input_data, str):
        input_data = str(input_data)
    
    # Truncate if too long
    if len(input_data) > max_length:
        input_data = input_data[:max_length]
    
    # Remove potentially dangerous characters
    # This is a basic sanitization - adjust based on specific needs
    dangerous_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08']
    for char in dangerous_chars:
        input_data = input_data.replace(char, '')
    
    return input_data


def parse_log_level(level_str: str) -> str:
    """
    Parse and normalize log level string.
    
    Args:
        level_str: Log level string
        
    Returns:
        Normalized log level
    """
    level_mapping = {
        "critical": "error",
        "fatal": "error",
        "err": "error",
        "warn": "warning",
        "information": "info",
        "dbg": "debug",
        "trace": "debug",
    }
    
    normalized = level_str.lower().strip()
    return level_mapping.get(normalized, normalized)


def create_directory_structure(base_path: Union[str, Path]) -> None:
    """
    Create the required directory structure for the project.
    
    Args:
        base_path: Base path for the project
    """
    base_path = Path(base_path)
    
    directories = [
        "config",
        "src/circus_manager",
        "src/mcp_server", 
        "src/log_parser",
        "src/io_controller",
        "src/utils",
        "tests",
        "docs",
        "logs",
    ]
    
    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)