
import logging

def system_info(args):
    logger = logging.getLogger("system_cmd")
    logger.info("Displaying system information.")
    print("System Information:")
    print(f"  Log Level: {args.config_loader.get('log.level')}")
    print(f"  Log Path: {args.config_loader.get('log.path')}")
    print(f"  Server Host: {args.config_loader.get('server.host')}")
    print(f"  Server Port: {args.config_loader.get('server.port')}")

def register(subparsers, config_loader, plugin_manager):
    """Registers the system command group."""
    parser = subparsers.add_parser("system", help="System diagnostics and maintenance.")
    system_subparsers = parser.add_subparsers(dest="action", help="System actions")

    # Info command
    info_parser = system_subparsers.add_parser("info", help="Display system information.")
    info_parser.set_defaults(func=system_info, config_loader=config_loader)

