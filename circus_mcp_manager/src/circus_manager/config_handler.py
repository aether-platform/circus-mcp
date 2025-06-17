"""
Configuration handler for Circus Manager.
"""

import configparser
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from ..utils.exceptions import ConfigurationError
from ..utils.helpers import load_config, validate_process_name


logger = logging.getLogger(__name__)


class ConfigHandler:
    """Handles Circus configuration management."""
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize configuration handler.
        
        Args:
            config_path: Path to circus.ini file
        """
        self.config_path = config_path or Path("config/circus.ini")
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                self.config.read(self.config_path)
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Configuration file not found: {self.config_path}")
                self._create_default_config()
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def _create_default_config(self) -> None:
        """Create default configuration."""
        self.config['circus'] = {
            'check_delay': '5',
            'endpoint': 'tcp://127.0.0.1:5555',
            'pubsub_endpoint': 'tcp://127.0.0.1:5556',
            'stats_endpoint': 'tcp://127.0.0.1:5557',
        }
        logger.info("Created default configuration")
    
    def get_circus_config(self) -> Dict[str, Any]:
        """
        Get main circus configuration.
        
        Returns:
            Dictionary containing circus configuration
        """
        if 'circus' not in self.config:
            return {}
        
        return dict(self.config['circus'])
    
    def get_watcher_config(self, watcher_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific watcher.
        
        Args:
            watcher_name: Name of the watcher
            
        Returns:
            Watcher configuration or None if not found
        """
        section_name = f"watcher:{watcher_name}"
        if section_name not in self.config:
            return None
        
        return dict(self.config[section_name])
    
    def get_all_watchers(self) -> List[str]:
        """
        Get list of all configured watchers.
        
        Returns:
            List of watcher names
        """
        watchers = []
        for section_name in self.config.sections():
            if section_name.startswith("watcher:"):
                watcher_name = section_name.replace("watcher:", "")
                watchers.append(watcher_name)
        return watchers
    
    def add_watcher(self, watcher_name: str, config: Dict[str, Any]) -> None:
        """
        Add a new watcher configuration.
        
        Args:
            watcher_name: Name of the watcher
            config: Watcher configuration
            
        Raises:
            InvalidProcessNameError: If watcher name is invalid
            ConfigurationError: If configuration is invalid
        """
        validate_process_name(watcher_name)
        
        section_name = f"watcher:{watcher_name}"
        
        if section_name in self.config:
            raise ConfigurationError(f"Watcher '{watcher_name}' already exists")
        
        # Validate required fields
        required_fields = ['cmd']
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Missing required field '{field}' for watcher '{watcher_name}'")
        
        self.config[section_name] = config
        logger.info(f"Added watcher configuration: {watcher_name}")
    
    def update_watcher(self, watcher_name: str, config: Dict[str, Any]) -> None:
        """
        Update existing watcher configuration.
        
        Args:
            watcher_name: Name of the watcher
            config: Updated configuration
            
        Raises:
            ConfigurationError: If watcher doesn't exist
        """
        section_name = f"watcher:{watcher_name}"
        
        if section_name not in self.config:
            raise ConfigurationError(f"Watcher '{watcher_name}' not found")
        
        # Update configuration
        for key, value in config.items():
            self.config[section_name][key] = str(value)
        
        logger.info(f"Updated watcher configuration: {watcher_name}")
    
    def remove_watcher(self, watcher_name: str) -> None:
        """
        Remove watcher configuration.
        
        Args:
            watcher_name: Name of the watcher to remove
            
        Raises:
            ConfigurationError: If watcher doesn't exist
        """
        section_name = f"watcher:{watcher_name}"
        
        if section_name not in self.config:
            raise ConfigurationError(f"Watcher '{watcher_name}' not found")
        
        self.config.remove_section(section_name)
        logger.info(f"Removed watcher configuration: {watcher_name}")
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                self.config.write(f)
            
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {str(e)}")
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self.config.clear()
        self._load_config()
        logger.info("Reloaded configuration")
    
    def validate_config(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check circus section
        if 'circus' not in self.config:
            errors.append("Missing [circus] section")
        else:
            circus_config = self.config['circus']
            required_fields = ['endpoint', 'pubsub_endpoint']
            for field in required_fields:
                if field not in circus_config:
                    errors.append(f"Missing required field '{field}' in [circus] section")
        
        # Check watcher sections
        for section_name in self.config.sections():
            if section_name.startswith("watcher:"):
                watcher_name = section_name.replace("watcher:", "")
                watcher_config = self.config[section_name]
                
                # Validate watcher name
                try:
                    validate_process_name(watcher_name)
                except Exception as e:
                    errors.append(f"Invalid watcher name '{watcher_name}': {str(e)}")
                
                # Check required fields
                if 'cmd' not in watcher_config:
                    errors.append(f"Missing 'cmd' field in watcher '{watcher_name}'")
        
        return errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary.
        
        Returns:
            Summary of current configuration
        """
        return {
            "config_path": str(self.config_path),
            "circus_config": self.get_circus_config(),
            "watchers": self.get_all_watchers(),
            "total_watchers": len(self.get_all_watchers()),
            "validation_errors": self.validate_config(),
        }