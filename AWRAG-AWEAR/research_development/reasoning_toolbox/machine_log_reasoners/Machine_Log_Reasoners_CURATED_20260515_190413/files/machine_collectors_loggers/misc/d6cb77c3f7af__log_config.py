import logging
import logging.handlers
import os
import sys
from datetime import datetime

class LogConfig:
    """Configure logging for the RBAC system with rotation and proper formatting."""
    
    def __init__(self, log_dir="/app/logs", log_level=None):
        """
        Initialize logging configuration.
        
        Args:
            log_dir: Directory to store log files
            log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_dir = log_dir
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set log level from environment variable or default to INFO
        if log_level is None:
            log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        
        # Map string log level to logging constants
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        numeric_level = level_map.get(log_level, logging.INFO)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(numeric_level)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # Add file handler with rotation
        log_file = os.path.join(self.log_dir, 'rbac.log')
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        # Add security audit log handler
        audit_log_file = os.path.join(self.log_dir, 'rbac_audit.log')
        audit_handler = logging.handlers.RotatingFileHandler(
            filename=audit_log_file,
            maxBytes=10485760,  # 10MB
            backupCount=20  # Keep more audit logs
        )
        audit_format = logging.Formatter('%(asctime)s - AUDIT - %(message)s')
        audit_handler.setFormatter(audit_format)
        audit_handler.setLevel(logging.INFO)  # Always log audits at INFO level or above
        
        # Create audit logger
        self.audit_logger = logging.getLogger('rbac.audit')
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.addHandler(audit_handler)
        
        # Log startup
        logging.info(f"RBAC logging initialized at {log_level} level")
        self.audit_logger.info(f"RBAC system started")
    
    def log_security_event(self, event_type, username, details):
        """
        Log a security event to the audit log.
        
        Args:
            event_type: Type of security event
            username: Username associated with the event
            details: Dictionary of event details
        """
        timestamp = datetime.utcnow().isoformat()
        message = f"[{event_type}] User: {username} - {details}"
        self.audit_logger.info(message)

# Example usage
if __name__ == "__main__":
    # Initialize logging
    log_config = LogConfig()
    
    # Example log messages
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    
    # Example audit log
    log_config.log_security_event(
        "LOGIN_ATTEMPT", 
        "alice", 
        {"status": "success", "ip": "192.168.1.1"}
    )
