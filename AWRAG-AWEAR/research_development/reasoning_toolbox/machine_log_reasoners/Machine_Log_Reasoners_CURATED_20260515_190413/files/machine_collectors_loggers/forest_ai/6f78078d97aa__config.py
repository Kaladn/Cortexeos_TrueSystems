'''
Config command group for managing system settings.
'''

import logging
import json

def show_config(args):
    logger = logging.getLogger("config_cmd")
    logger.info("Displaying current merged configuration.")
    
    # The config loader already provides the merged config
    print(json.dumps(args.config_loader.config, indent=2))

def register(subparsers, config_loader, plugin_manager):
    '''Registers the config command group.'''
    parser = subparsers.add_parser("config", help="Manage system configuration.")
    config_subparsers = parser.add_subparsers(dest="action", help="Config actions")

    # Show command
    show_parser = config_subparsers.add_parser("show", help="Display the current merged configuration.")
    show_parser.set_defaults(func=show_config, config_loader=config_loader)

