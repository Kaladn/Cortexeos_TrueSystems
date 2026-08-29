'''
Main entry point for the Forest AI application.
'''

import sys
import logging
from pathlib import Path

def main():
    # 1. Setup paths
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from core.runtime import ConfigLoader
    from core.logger import setup_logging
    from core.cli import CommandDispatcher
    from core.plugin_manager import PluginManager
    from core.events import event_stream

    # 2. Load configuration
    try:
        config_loader = ConfigLoader(project_root)
    except FileNotFoundError as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Setup logging
    log_path = project_root / config_loader.get("log.path", "logs")
    log_level = config_loader.get("log.level", "INFO")
    setup_logging(log_path, log_level)

    event_stream.publish("system.startup", "main", details={"pid": os.getpid()})

    # 4. Initialize Plugin Manager
    plugin_manager = PluginManager(project_root)

    # 5. Setup and run CLI dispatcher
    dispatcher = CommandDispatcher(project_root, config_loader, plugin_manager)
    dispatcher.run(sys.argv[1:])

    event_stream.publish("system.shutdown", "main")

if __name__ == "__main__":
    import os
    main()

