import logging
import os
from config import Config

# Set up logging
LOG_FILE = os.path.join(Config.LOG_DIR, "security_logs.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

def log_event(level, message):
    """
    Logs security events at the specified level.
    """
    if level.lower() == "info":
        logging.info(message)
    elif level.lower() == "warning":
        logging.warning(message)
    elif level.lower() == "error":
        logging.error(message)
    elif level.lower() == "critical":
        logging.critical(message)
    else:
        logging.debug(message)

    print(f"[LOG] {message}")  # Also prints to console
