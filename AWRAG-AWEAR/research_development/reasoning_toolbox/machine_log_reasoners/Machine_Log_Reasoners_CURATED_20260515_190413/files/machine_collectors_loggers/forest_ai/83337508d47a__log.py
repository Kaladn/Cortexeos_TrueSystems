'''
Log command group for monitoring system events.
'''

import logging
import json

def view_log(args):
    logger = logging.getLogger("log_cmd")
    log_file = args.config_loader.base_path / "logs" / "events.jsonl"

    if not log_file.exists():
        print("Event log file not found.")
        return

    with open(log_file, "r") as f:
        lines = f.readlines()

    print(f"Displaying last {args.lines} events:")
    for line in lines[-args.lines:]:
        print(line.strip())

def register(subparsers, config_loader, plugin_manager):
    '''Registers the log command group.'''
    parser = subparsers.add_parser("log", help="Monitor system events.")
    log_subparsers = parser.add_subparsers(dest="action", help="Log actions")

    # View command
    view_parser = log_subparsers.add_parser("view", help="View recent system events.")
    view_parser.add_argument("-n", "--lines", type=int, default=20, help="Number of recent lines to display.")
    view_parser.set_defaults(func=view_log, config_loader=config_loader)

