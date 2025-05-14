"""
Configuration management for preserve.py.

This module handles loading, saving, and managing configuration settings
for the preserve tool. It supports both global and project-specific configs.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Set up module-level logger
logger = logging.getLogger(__name__)

class PreserveConfig:
    """
    Configuration manager for preserve settings.
    
    Handles loading and merging preferences from multiple sources:
    1. Default settings
    2. Global user configuration
    3. Project-specific configuration
    4. Command-line arguments
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        "paths": {
            "default_style": "relative",  # relative, absolute, flat
            "include_base": False,        # include base path in destination
            "preserve_dir": True,         # create .preserve directory
        },
        "verification": {
            "default_hash": "SHA256",     # default hash algorithm
            "verify_after_copy": True,    # verify files after copy operation
            "verify_after_move": True,    # verify files before deleting originals
        },
        "dazzlelink": {
            "enabled": False,             # create dazzlelinks by default
            "with_files": False,          # store alongside copied files
            "directory": ".preserve/dazzlelinks",  # default dazzlelink directory
        },
        "operations": {
            "overwrite": False,           # overwrite existing files
            "preserve_attrs": True,       # preserve file attributes
            "recursive": True,            # recurse into subdirectories
            "follow_symlinks": False,     # follow symbolic links
        },
        "platform": {
            "windows": {
                "skip_attributes": []     # file attributes to skip on Windows
            },
            "unix": {
                "skip_attributes": []     # file attributes to skip on Unix
            }
        }
    }
    
    def __init__(self, args=None):
        """
        Initialize configuration from default settings.
        
        Args:
            args: Command-line arguments (optional)
        """
        # Start with default config
        self.config = self._deep_copy(self.DEFAULT_CONFIG)
        
        # Load global configuration
        self._load_global_config()
        
        # Apply command-line arguments if provided
        if args:
            self.apply_args(args)
    
    def _deep_copy(self, obj: Any) -> Any:
        """
        Create a deep copy of a configuration object.
        
        Args:
            obj: The object to copy
            
        Returns:
            A deep copy of the object
        """
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(v) for v in obj]
        else:
            return obj
    
    def _get_global_config_path(self) -> Path:
        """
        Get the path to the global configuration file.
        
        Returns:
            Path to the global configuration file
        """
        if sys.platform == 'win32':
            # Windows: %APPDATA%\preserve\config.json
            app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
            return Path(app_data) / 'preserve' / 'config.json'
        else:
            # Unix: ~/.config/preserve/config.json
            config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
            return Path(config_dir) / 'preserve' / 'config.json'
    
    def _get_project_config_path(self, directory: Union[str, Path]) -> Path:
        """
        Get the path to a project-specific configuration file.
        
        Args:
            directory: The project directory
            
        Returns:
            Path to the project configuration file
        """
        return Path(directory) / '.preserve' / 'config.json'
    
    def _load_global_config(self) -> None:
        """
        Load the global configuration file if it exists.
        """
        config_path = self._get_global_config_path()
        self._load_config_file(config_path, "global")
    
    def load_project_config(self, directory: Union[str, Path]) -> None:
        """
        Load a project-specific configuration if available.
        
        Args:
            directory: The project directory
        """
        config_path = self._get_project_config_path(directory)
        self._load_config_file(config_path, "project")
    
    def _load_config_file(self, config_path: Path, config_type: str) -> None:
        """
        Load and merge configuration from a file.
        
        Args:
            config_path: Path to the configuration file
            config_type: Type of configuration (for error messages)
        """
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # Merge configuration
                self._merge_config(file_config)
                logger.debug(f"Loaded {config_type} configuration from {config_path}")
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in {config_type} configuration: {config_path}")
            except Exception as e:
                logger.warning(f"Error reading {config_type} configuration: {e}")
    
    def _merge_config(self, other_config: Dict[str, Any]) -> None:
        """
        Merge another configuration into this one.
        
        Args:
            other_config: Configuration to merge
        """
        def _merge_dicts(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    _merge_dicts(target[key], value)
                else:
                    target[key] = value
        
        _merge_dicts(self.config, other_config)
    
    def apply_args(self, args) -> None:
        """
        Apply command-line arguments, overriding other settings.
        
        Args:
            args: Parsed command-line arguments
        """
        # Path style
        if hasattr(args, 'rel') and args.rel:
            self.set('paths.default_style', 'relative')
        elif hasattr(args, 'abs') and args.abs:
            self.set('paths.default_style', 'absolute')
        elif hasattr(args, 'flat') and args.flat:
            self.set('paths.default_style', 'flat')
        
        # Include base path
        if hasattr(args, 'includeBase') and args.includeBase:
            self.set('paths.include_base', True)
        
        # Preserve directory
        if hasattr(args, 'preserve_dir') and args.preserve_dir:
            self.set('paths.preserve_dir', True)
        
        # Verification
        if hasattr(args, 'verify') and args.verify:
            if args.operation == 'COPY':
                self.set('verification.verify_after_copy', True)
            elif args.operation == 'MOVE':
                self.set('verification.verify_after_move', True)
        
        if hasattr(args, 'no_verify') and args.no_verify:
            if args.operation == 'COPY':
                self.set('verification.verify_after_copy', False)
            elif args.operation == 'MOVE':
                self.set('verification.verify_after_move', False)
        
        if hasattr(args, 'hash') and args.hash:
            self.set('verification.default_hash', args.hash[0])  # Use first specified hash
        
        # Dazzlelink
        if hasattr(args, 'dazzlelink') and args.dazzlelink:
            self.set('dazzlelink.enabled', True)
        
        if hasattr(args, 'dazzlelink_with_files') and args.dazzlelink_with_files:
            self.set('dazzlelink.with_files', True)
        
        if hasattr(args, 'dazzlelink_dir') and args.dazzlelink_dir:
            self.set('dazzlelink.directory', args.dazzlelink_dir)
        
        # Operations
        if hasattr(args, 'overwrite') and args.overwrite:
            self.set('operations.overwrite', True)
        
        if hasattr(args, 'no_preserve_attrs') and args.no_preserve_attrs:
            self.set('operations.preserve_attrs', False)
        
        if hasattr(args, 'recursive') and args.recursive:
            self.set('operations.recursive', True)
        
        if hasattr(args, 'follow_symlinks') and args.follow_symlinks:
            self.set('operations.follow_symlinks', True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: The configuration key (dot-separated for nested keys)
            default: Default value if key is not found
            
        Returns:
            The configuration value, or default if not found
        """
        parts = key.split('.')
        value = self.config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key (dot-separated for nested keys)
            value: The value to set
        """
        parts = key.split('.')
        target = self.config
        
        # Navigate to the nested dictionary
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        
        # Set the value
        target[parts[-1]] = value
    
    def save_global_config(self) -> bool:
        """
        Save the current configuration as global config.
        
        Returns:
            True if successful, False otherwise
        """
        config_path = self._get_global_config_path()
        return self._save_config_file(config_path)
    
    def save_project_config(self, directory: Union[str, Path]) -> bool:
        """
        Save the current configuration as project config.
        
        Args:
            directory: The project directory
            
        Returns:
            True if successful, False otherwise
        """
        config_path = self._get_project_config_path(directory)
        return self._save_config_file(config_path)
    
    def _save_config_file(self, config_path: Path) -> bool:
        """
        Save configuration to a file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
                
            logger.debug(f"Configuration saved to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """
        Reset the configuration to default values.
        """
        self.config = self._deep_copy(self.DEFAULT_CONFIG)
    
    def reset_section(self, section: str) -> bool:
        """
        Reset a section of the configuration to default values.
        
        Args:
            section: The section to reset
            
        Returns:
            True if successful, False if section not found
        """
        if section in self.DEFAULT_CONFIG:
            self.config[section] = self._deep_copy(self.DEFAULT_CONFIG[section])
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.
        
        Returns:
            The configuration dictionary
        """
        return self._deep_copy(self.config)

# Global configuration instance
_global_config = None

def get_config(args=None) -> PreserveConfig:
    """
    Get or create the global configuration instance.
    
    Args:
        args: Command-line arguments (optional)
        
    Returns:
        The global configuration instance
    """
    global _global_config
    if _global_config is None:
        _global_config = PreserveConfig(args)
    elif args is not None:
        _global_config.apply_args(args)
    return _global_config
