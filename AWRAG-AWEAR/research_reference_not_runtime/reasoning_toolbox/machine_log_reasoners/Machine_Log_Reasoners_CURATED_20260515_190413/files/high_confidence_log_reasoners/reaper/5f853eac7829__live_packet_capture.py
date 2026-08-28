#!/usr/bin/env python3
"""
R.E.A.P.E.R. LIVE PACKET CAPTURE AND ANALYSIS
Real-time network monitoring with cognitive threat detection

This module captures live network traffic and processes it through
the R.E.A.P.E.R. cognitive analysis engine for real-time threat detection.

Author: R.E.A.P.E.R. Development Team
Version: 1.0
Date: June 16, 2025
"""

import subprocess
import threading
import time
import json
import csv
import os
from datetime import datetime
from reaper_network_analyzer import NetworkCognitiveAnalyzer, NetworkEvent, CognitiveEvent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveNetworkMonitor:
    """
    Real-time network monitoring with R.E.A.P.E.R. cognitive analysis
    """
    
    def __init__(self, output_file: str = "live_netstat_capture.csv"):
        self.output_file = output_file
        self.analyzer = NetworkCognitiveAnalyzer("reaper_live_network.db")
        self.monitoring = False
        self.capture_thread = None
        self.analysis_thread = None
        self.event_queue = []
        self.queue_lock = threading.Lock()
        
    def start_monitoring(self, interval: int = 5):
        """Start live network monitoring"""
        logger.info("Starting live network monitoring...")
        self.monitoring = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, args=(interval,))
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        # Start analysis thread
        self.analysis_thread = threading.Thread(target=self._analysis_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
        logger.info(f"Live monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop live network monitoring"""
        logger.info("Stopping live network monitoring...")
        self.monitoring = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=10)
        if self.analysis_thread:
            self.analysis_thread.join(timeout=10)
            
        logger.info("Live monitoring stopped")
    
    def _capture_loop(self, interval: int):
        """Continuous network capture loop"""
        while self.monitoring:
            try:
                # Capture current netstat
                connections = self._capture_netstat()
                
                # Add to queue for analysis
                with self.queue_lock:
                    self.event_queue.extend(connections)
                
                # Write to CSV file
                self._write_to_csv(connections)
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(interval)
    
    def _analysis_loop(self):
        """Continuous analysis loop"""
        while self.monitoring:
            try:
                # Process queued events
                events_to_process = []
                with self.queue_lock:
                    if self.event_queue:
                        events_to_process = self.event_queue.copy()
                        self.event_queue.clear()
                
                # Analyze events
                for event in events_to_process:
                    cognitive_event = CognitiveEvent(
                        event_type="live_network_activity",
                        timestamp=event.timestamp,
                        data=event.to_dict()
                    )
                    
                    result = self.analyzer.process_cognitive_event(cognitive_event)
                    
                    # Log significant threats
                    if result['threat_classification'] in ['THREAT', 'CRITICAL']:
                        self._log_threat_alert(result)
                
                time.sleep(1)  # Process every second
                
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                time.sleep(1)
    
    def _capture_netstat(self) -> list:
        """Capture current netstat connections"""
        connections = []
        timestamp = datetime.now().isoformat()
        
        try:
            # Run netstat command
            if os.name == 'nt':  # Windows
                cmd = ['netstat', '-ano']
            else:  # Linux/Unix
                cmd = ['netstat', '-tuln']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\\n')
                
                for line in lines[2:]:  # Skip header lines
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            # Parse netstat output
                            protocol = parts[0].upper()
                            local_addr = parts[1]
                            remote_addr = parts[2] if len(parts) > 2 else '0.0.0.0:0'
                            state = parts[3] if len(parts) > 3 else 'UNKNOWN'
                            pid = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
                            
                            # Extract addresses and ports
                            local_ip, local_port = self._parse_address(local_addr)
                            remote_ip, remote_port = self._parse_address(remote_addr)
                            
                            # Get process name (simplified)
                            process_name = self._get_process_name(pid)
                            
                            connection = NetworkEvent(
                                timestamp=timestamp,
                                protocol=protocol,
                                local_address=local_ip,
                                local_port=local_port,
                                remote_address=remote_ip,
                                remote_port=remote_port,
                                state=state,
                                pid=pid,
                                process_name=process_name
                            )
                            
                            connections.append(connection)
                            
                        except Exception as e:
                            logger.debug(f"Error parsing netstat line: {line} - {e}")
                            continue
            
        except subprocess.TimeoutExpired:
            logger.warning("Netstat command timed out")
        except Exception as e:
            logger.error(f"Error running netstat: {e}")
        
        return connections
    
    def _parse_address(self, addr_str: str) -> tuple:
        """Parse address:port string"""
        try:
            if ':' in addr_str:
                parts = addr_str.rsplit(':', 1)
                ip = parts[0]
                port = int(parts[1]) if parts[1].isdigit() else 0
                return ip, port
            else:
                return addr_str, 0
        except:
            return addr_str, 0
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID (simplified)"""
        if pid == 0:
            return "system"
        
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\\n')
                    if len(lines) > 1:
                        parts = lines[1].split(',')
                        if len(parts) > 0:
                            return parts[0].strip('"')
            else:  # Linux/Unix
                result = subprocess.run(['ps', '-p', str(pid), '-o', 'comm='], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass
        
        return f"pid_{pid}"
    
    def _write_to_csv(self, connections: list):
        """Write connections to CSV file"""
        try:
            file_exists = os.path.exists(self.output_file)
            
            with open(self.output_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header if new file
                if not file_exists:
                    writer.writerow(['timestamp', 'protocol', 'local_address', 'remote_address', 
                                   'remote_port', 'state', 'pid', 'process_name'])
                
                # Write connection data
                for conn in connections:
                    writer.writerow([
                        conn.timestamp, conn.protocol, 
                        f"{conn.local_address}:{conn.local_port}",
                        conn.remote_address, conn.remote_port,
                        conn.state, conn.pid, conn.process_name
                    ])
                    
        except Exception as e:
            logger.error(f"Error writing to CSV: {e}")
    
    def _log_threat_alert(self, result: dict):
        """Log threat alerts"""
        threat_level = result['threat_classification']
        process_name = result['process_name']
        remote_address = result['remote_address']
        remote_port = result['remote_port']
        
        alert_msg = (f"🚨 {threat_level} THREAT DETECTED: "
                    f"{process_name} → {remote_address}:{remote_port} "
                    f"(Score: {result['threat_level']:.3f})")
        
        logger.warning(alert_msg)
        print(f"\\n{alert_msg}")
        
        # Print recommendations
        for rec in result['recommendations']:
            print(f"   {rec}")
    
    def get_live_stats(self) -> dict:
        """Get live monitoring statistics"""
        summary = self.analyzer.get_anomaly_summary()
        
        # Add monitoring stats
        summary.update({
            'monitoring_active': self.monitoring,
            'queue_size': len(self.event_queue),
            'output_file': self.output_file
        })
        
        return summary

def main():
    """Main function for live network monitoring"""
    print("🔥 R.E.A.P.E.R. LIVE NETWORK MONITORING")
    print("=" * 50)
    print("Real-time cognitive threat detection")
    print("Press Ctrl+C to stop monitoring")
    print("=" * 50)
    
    monitor = LiveNetworkMonitor()
    
    try:
        # Start monitoring
        monitor.start_monitoring(interval=10)  # Capture every 10 seconds
        
        # Keep running and show periodic stats
        while True:
            time.sleep(30)  # Show stats every 30 seconds
            
            stats = monitor.get_live_stats()
            print(f"\\n📊 LIVE STATS: {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Queue Size: {stats['queue_size']}")
            print(f"   Total Anomalies: {stats['total_anomalies']}")
            print(f"   High Severity: {stats['high_severity']}")
            print(f"   Recent Anomalies: {stats['recent_anomalies']}")
            
    except KeyboardInterrupt:
        print("\\n\\n🛑 Stopping live monitoring...")
        monitor.stop_monitoring()
        print("✅ Live monitoring stopped")
        
        # Show final stats
        final_stats = monitor.get_live_stats()
        print(f"\\n📈 FINAL STATISTICS:")
        for key, value in final_stats.items():
            if key != 'monitoring_active':
                print(f"   {key.replace('_', ' ').title()}: {value}")

if __name__ == "__main__":
    main()

