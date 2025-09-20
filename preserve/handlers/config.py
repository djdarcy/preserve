"""
CONFIG operation handler for preserve tool.

This module implements the CONFIG command which manages preserve configuration
settings including viewing, setting, and resetting configuration values.

TODO: Future refactoring opportunities:
- Consider creating a ConfigManager class for more complex configuration needs
- Add configuration validation and type checking
- Support for configuration profiles
- Import/export configuration functionality
"""

import logging

from preserve.config import PreserveConfig

logger = logging.getLogger(__name__)


def handle_config_operation(args, logger):
    """Handle CONFIG operation"""
    # Load configuration
    cfg = PreserveConfig()

    if not args.config_operation:
        logger.error("No config operation specified")
        return 1

    if args.config_operation == 'VIEW':
        # View configuration
        config_dict = cfg.to_dict()

        if args.section:
            # View specific section
            if args.section in config_dict:
                print(f"Configuration section '{args.section}':")
                for key, value in config_dict[args.section].items():
                    print(f"  {key}: {value}")
            else:
                logger.error(f"Configuration section '{args.section}' not found")
                return 1
        else:
            # View all configuration
            print("Current configuration:")
            for section, section_data in config_dict.items():
                print(f"\n[{section}]")
                for key, value in section_data.items():
                    print(f"  {key}: {value}")

        return 0

    elif args.config_operation == 'SET':
        # Set configuration value
        key_parts = args.key.split('.')
        if len(key_parts) != 2:
            logger.error("Configuration key must be in the format 'section.option'")
            return 1

        section, option = key_parts
        value = args.value

        # Convert value to appropriate type
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.isdigit():
            value = int(value)

        # Set value
        cfg.set(args.key, value)

        # Save configuration
        if cfg.save_global_config():
            print(f"Set {args.key} = {value} in global configuration")
            return 0
        else:
            logger.error("Failed to save configuration")
            return 1

    elif args.config_operation == 'RESET':
        # Reset configuration
        if args.section:
            # Reset specific section
            if cfg.reset_section(args.section):
                print(f"Reset configuration section '{args.section}' to defaults")

                # Save configuration
                if cfg.save_global_config():
                    return 0
                else:
                    logger.error("Failed to save configuration")
                    return 1
            else:
                logger.error(f"Configuration section '{args.section}' not found")
                return 1
        else:
            # Reset all configuration
            cfg.reset_to_defaults()

            # Save configuration
            if cfg.save_global_config():
                print("Reset configuration to defaults")
                return 0
            else:
                logger.error("Failed to save configuration")
                return 1

    else:
        logger.error(f"Unknown config operation: {args.config_operation}")
        return 1