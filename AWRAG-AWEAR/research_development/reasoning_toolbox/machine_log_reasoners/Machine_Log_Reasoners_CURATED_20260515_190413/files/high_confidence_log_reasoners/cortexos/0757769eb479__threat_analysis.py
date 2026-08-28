import os
import re
import platform
import subprocess
from transformers import pipeline

# Minimal Config Mock (replace this with your real Config if it exists)
class Config:
    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
    BLOCK_IP_ON_HIGH_THREAT = True

    @staticmethod
    def get_firewall_cmd(ip):
        system = platform.system()
        if system == "Windows":
            return f'netsh advfirewall firewall add rule name="Block IP {ip}" dir=in action=block remoteip={ip}'
        elif system == "Linux":
            return f'sudo iptables -A INPUT -s {ip} -j DROP'
        else:
            return f'echo "Unsupported OS for blocking IPs."'

# Logger
def log_event(level, message):
    print(f"[{level.upper()}] {message}")

# ThreatAnalyzer Class
class ThreatAnalyzer:
    def __init__(self):
        log_event("info", "Initializing AI-Powered Threat Analyzer...")
        self.analyzer = pipeline("text-classification", model=Config.MODEL_NAME)

    def analyze(self, log_entry):
        log_event("info", f"Analyzing log entry: {log_entry}")
        result = self.analyzer(log_entry)

        label = result[0]["label"]
        confidence = result[0]["score"]

        threat_level = self.map_label_to_threat(label)
        log_event("info", f"Threat Analysis → Level: {threat_level}, Confidence: {confidence:.2f}")

        if threat_level == "High Threat" and Config.BLOCK_IP_ON_HIGH_THREAT:
            attacker_ip = self.extract_ip(log_entry)
            if attacker_ip:
                self.block_ip(attacker_ip)

        return {"threat_level": threat_level, "confidence": confidence}

    def map_label_to_threat(self, label):
        mapping = {
            "NEGATIVE": "High Threat",
            "POSITIVE": "Low Threat"
        }
        return mapping.get(label.upper(), "Unknown Threat")

    def extract_ip(self, log_entry):
        match = re.search(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", log_entry)
        return match.group(0) if match else None

    def block_ip(self, ip_address):
        command = Config.get_firewall_cmd(ip_address)
        try:
            subprocess.run(command, shell=True, check=True)
            log_event("info", f"🔥 Blocked IP {ip_address} due to high threat level.")
        except subprocess.CalledProcessError as e:
            log_event("error", f"⚠️ Failed to block IP {ip_address}: {e}")

# Example usage:
if __name__ == "__main__":
    log = "Unauthorized access attempt from IP 192.168.1.15."
    analyzer = ThreatAnalyzer()
    result = analyzer.analyze(log)
    print("Analysis result:", result)
