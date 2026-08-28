import os

class Config:
    """
    Configuration settings for Cortex Evolved.
    """
    # AI Model Settings
    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"  # Change this if needed
    MODEL_PATH = os.path.join(os.getcwd(), "models", MODEL_NAME)

    # Logging settings
    LOG_DIR = os.path.join(os.getcwd(), "logs")
    os.makedirs(LOG_DIR, exist_ok=True)

    # API Settings
    API_HOST = "127.0.0.1"
    API_PORT = 8000

    # Security Settings
    BLOCK_IP_ON_HIGH_THREAT = True  # Set to False if you don't want to auto-block

    # Firewall Command Paths (Windows/Linux)
    WINDOWS_FIREWALL_CMD = 'New-NetFirewallRule -DisplayName "Blocked {ip}" -Direction Inbound -RemoteAddress {ip} -Action Block'
    LINUX_IPTABLES_CMD = "sudo iptables -A INPUT -s {ip} -j DROP"

    @staticmethod
    def get_firewall_cmd(ip):
        """
        Returns the correct firewall command based on OS.
        """
        if os.name == "nt":  # Windows
            return Config.WINDOWS_FIREWALL_CMD.format(ip=ip)
        else:  # Linux
            return Config.LINUX_IPTABLES_CMD.format(ip=ip)

