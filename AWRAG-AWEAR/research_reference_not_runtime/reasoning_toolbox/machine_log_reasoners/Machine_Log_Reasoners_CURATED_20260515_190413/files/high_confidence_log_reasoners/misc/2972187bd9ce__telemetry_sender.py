"""
Telemetry Sender
Sends real-time telemetry to CompuCog Control Center
"""

import socket
import json
from datetime import datetime


class TelemetrySender:
    """Sends telemetry data to CompuCog Control Center"""
    
    def __init__(self, config):
        """
        Initialize telemetry sender
        
        Args:
            config: Telemetry configuration dictionary
        """
        self.config = config
        self.host = config.get('control_center_host', 'localhost')
        self.port = config.get('control_center_port', 5555)
        self.buffer_size = config.get('buffer_size', 100)
        self.enabled = True
        
        # Try to establish connection (non-blocking)
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
        except Exception as e:
            print(f"Telemetry initialization warning: {str(e)}")
            self.enabled = False
    
    def send_status(self, status, ticker):
        """
        Send status update
        
        Args:
            status: Status string (e.g., "fetching_data", "analyzing")
            ticker: Ticker being analyzed
        """
        if not self.enabled:
            return
        
        self._send({
            'worker_id': 'MARKET_ORACLE',
            'type': 'status',
            'status': status,
            'ticker': ticker,
            'timestamp': datetime.now().isoformat()
        })
    
    def send_metrics(self, metrics):
        """
        Send analysis metrics
        
        Args:
            metrics: Dictionary of metrics
        """
        if not self.enabled:
            return
        
        data = {
            'worker_id': 'MARKET_ORACLE',
            'type': 'metrics',
            'timestamp': datetime.now().isoformat()
        }
        data.update(metrics)
        
        self._send(data)
    
    def send_error(self, ticker, error_msg):
        """
        Send error notification
        
        Args:
            ticker: Ticker that failed
            error_msg: Error message
        """
        if not self.enabled:
            return
        
        self._send({
            'worker_id': 'MARKET_ORACLE',
            'type': 'error',
            'ticker': ticker,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
    
    def _send(self, data):
        """Send data via UDP"""
        try:
            message = json.dumps(data).encode('utf-8')
            self.sock.sendto(message, (self.host, self.port))
        except Exception as e:
            # Silently fail - telemetry is non-critical
            pass
    
    def close(self):
        """Close telemetry connection"""
        if hasattr(self, 'sock'):
            try:
                self.sock.close()
            except:
                pass
