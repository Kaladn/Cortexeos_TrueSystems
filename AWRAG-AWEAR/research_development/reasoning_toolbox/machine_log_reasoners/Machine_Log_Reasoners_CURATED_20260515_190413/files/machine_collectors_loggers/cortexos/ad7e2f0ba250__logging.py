import logging

logging.basicConfig(
    filename="system_logs.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def log_event(event):
    logging.info(event)
