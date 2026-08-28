#!/usr/bin/env python3
"""
R.E.A.P.E.R. NETWORK ANALYZER - FIXED FOR LEE'S DATA FORMAT
Real-time Cognitive Network Analysis Engine

FIXED VERSION: Properly handles Lee's netstat CSV format:
timestamp,protocol,local_address,foreign_address,state,pid,process

Author: Manus AI (Fixed for Lee)
Version: 2.1 - Lee's Data Format
Date: June 16, 2025
"""

import numpy as np
import pandas as pd
import json
import uuid
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import sqlite3
import threading
from collections import defaultdict, deque
import math
import statistics
import re
import ipaddress

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('REAPER_NETWORK')

class ThreatLevel(Enum):
    AUTHENTIC = "authentic"
    SUSPICIOUS = "suspicious" 
    THREAT = "threat"
    CRITICAL = "critical"

@dataclass
class NetworkEvent:
    """Network event for cognitive analysis"""
    timestamp: str
    protocol: str
    local_address: str
    foreign_address: str
    state: str
    pid: int
    process: str
    
    # Derived fields
    remote_ip: str = ""
    remote_port: int = 0
    local_ip: str = ""
    local_port: int = 0
    
    def __post_init__(self):
        """Parse addresses to extract IPs and ports"""
        self.local_ip, self.local_port = self._parse_address(self.local_address)
        self.remote_ip, self.remote_port = self._parse_address(self.foreign_address)
    
    def _parse_address(self, address: str) -> Tuple[str, int]:
        """Parse address:port format, handling IPv4 and IPv6"""
        if not address or address == "":
            return "", 0
            
        try:
            # Handle IPv6 addresses [::1]:port format
            if address.startswith('['):
                match = re.match(r'\[([^\]]+)\]:(\d+)', address)
                if match:
                    return match.group(1), int(match.group(2))
            
            # Handle IPv4 and simple IPv6 formats
            if ':' in address:
                # Count colons to distinguish IPv4:port from IPv6
                colon_count = address.count(':')
                if colon_count == 1:  # IPv4:port
                    ip, port = address.rsplit(':', 1)
                    return ip, int(port)
                elif colon_count > 1:  # IPv6 with port
                    # Try to find port at the end
                    parts = address.rsplit(':', 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        return parts[0], int(parts[1])
                    else:
                        # IPv6 without port
                        return address, 0
            
            return address, 0
        except (ValueError, AttributeError):
            return address, 0

@dataclass
class CognitiveAnchor:
    """Cognitive anchor for network behavior analysis"""
    name: str
    weight: float
    threshold: float
    pattern_memory: deque
    confidence: float = 0.5
    
    def __post_init__(self):
        if not hasattr(self, 'pattern_memory') or self.pattern_memory is None:
            self.pattern_memory = deque(maxlen=1000)

class NetworkCognitiveEngine:
    """
    R.E.A.P.E.R. Network Cognitive Analysis Engine
    Fixed for Lee's actual netstat data format
    """
    
    def __init__(self, db_path: str = "reaper_network.db"):
        self.db_path = db_path
        self.anchors = self._initialize_anchors()
        self.anomaly_memory = deque(maxlen=10000)
        self.baseline_patterns = defaultdict(list)
        self.threat_signatures = {}
        self.setup_database()
        
        logger.info(f"R.E.A.P.E.R. Network Engine initialized with {len(self.anchors)} anchors")
    
    def _initialize_anchors(self) -> Dict[str, CognitiveAnchor]:
        """Initialize cognitive anchors for network analysis"""
        anchors = {
            'connection_frequency': CognitiveAnchor('connection_frequency', 1.2, 0.7, deque(maxlen=1000)),
            'process_behavior': CognitiveAnchor('process_behavior', 1.4, 0.6, deque(maxlen=1000)),
            'temporal_pattern': CognitiveAnchor('temporal_pattern', 1.1, 0.8, deque(maxlen=1000)),
            'port_usage': CognitiveAnchor('port_usage', 1.3, 0.65, deque(maxlen=1000)),
            'connection_state': CognitiveAnchor('connection_state', 1.0, 0.75, deque(maxlen=1000)),
            'ip_reputation': CognitiveAnchor('ip_reputation', 1.5, 0.5, deque(maxlen=1000)),
            'protocol_anomaly': CognitiveAnchor('protocol_anomaly', 1.2, 0.7, deque(maxlen=1000)),
            'process_legitimacy': CognitiveAnchor('process_legitimacy', 1.6, 0.4, deque(maxlen=1000)),
            'connection_duration': CognitiveAnchor('connection_duration', 1.1, 0.8, deque(maxlen=1000)),
            'data_flow_pattern': CognitiveAnchor('data_flow_pattern', 1.3, 0.6, deque(maxlen=1000)),
            'geographic_anomaly': CognitiveAnchor('geographic_anomaly', 1.4, 0.55, deque(maxlen=1000)),
            'behavioral_consistency': CognitiveAnchor('behavioral_consistency', 1.2, 0.7, deque(maxlen=1000))
        }
        return anchors
    
    def setup_database(self):
        """Setup SQLite database for network analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS network_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    protocol TEXT,
                    local_address TEXT,
                    foreign_address TEXT,
                    state TEXT,
                    pid INTEGER,
                    process TEXT,
                    threat_level TEXT,
                    confidence REAL,
                    cognitive_score REAL,
                    anchor_scores TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS anomalies (
                    id TEXT PRIMARY KEY,
                    event_id TEXT,
                    anomaly_type TEXT,
                    severity REAL,
                    description TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    occurrence_count INTEGER DEFAULT 1,
                    FOREIGN KEY (event_id) REFERENCES network_events (id)
                )
            ''')
    
    def analyze_network_event(self, event: NetworkEvent) -> Dict[str, Any]:
        """Analyze a single network event through cognitive anchors"""
        
        # Generate unique event ID
        event_id = str(uuid.uuid4())
        
        # Analyze through each cognitive anchor
        anchor_scores = {}
        total_weighted_score = 0
        total_weight = 0
        
        for anchor_name, anchor in self.anchors.items():
            score = self._evaluate_anchor(anchor, event)
            anchor_scores[anchor_name] = {
                'score': score,
                'weight': anchor.weight,
                'confidence': anchor.confidence
            }
            
            weighted_score = score * anchor.weight
            total_weighted_score += weighted_score
            total_weight += anchor.weight
        
        # Calculate overall cognitive score
        cognitive_score = total_weighted_score / total_weight if total_weight > 0 else 0.5
        
        # Determine threat level
        threat_level = self._determine_threat_level(cognitive_score, anchor_scores)
        
        # Calculate confidence based on anchor consensus
        confidence = self._calculate_confidence(anchor_scores)
        
        # Store in database
        self._store_event(event_id, event, threat_level, confidence, cognitive_score, anchor_scores)
        
        # Check for anomalies
        anomalies = self._detect_anomalies(event, cognitive_score, anchor_scores)
        
        result = {
            'event_id': event_id,
            'threat_level': threat_level.value,
            'confidence': confidence,
            'cognitive_score': cognitive_score,
            'anchor_scores': anchor_scores,
            'anomalies': anomalies,
            'event_data': asdict(event)
        }
        
        logger.info(f"Network event {event_id} analyzed: {threat_level.value} (confidence: {confidence:.3f})")
        
        return result
    
    def _evaluate_anchor(self, anchor: CognitiveAnchor, event: NetworkEvent) -> float:
        """Evaluate a specific cognitive anchor against the network event"""
        
        if anchor.name == 'connection_frequency':
            return self._analyze_connection_frequency(event)
        elif anchor.name == 'process_behavior':
            return self._analyze_process_behavior(event)
        elif anchor.name == 'temporal_pattern':
            return self._analyze_temporal_pattern(event)
        elif anchor.name == 'port_usage':
            return self._analyze_port_usage(event)
        elif anchor.name == 'connection_state':
            return self._analyze_connection_state(event)
        elif anchor.name == 'ip_reputation':
            return self._analyze_ip_reputation(event)
        elif anchor.name == 'protocol_anomaly':
            return self._analyze_protocol_anomaly(event)
        elif anchor.name == 'process_legitimacy':
            return self._analyze_process_legitimacy(event)
        elif anchor.name == 'connection_duration':
            return self._analyze_connection_duration(event)
        elif anchor.name == 'data_flow_pattern':
            return self._analyze_data_flow_pattern(event)
        elif anchor.name == 'geographic_anomaly':
            return self._analyze_geographic_anomaly(event)
        elif anchor.name == 'behavioral_consistency':
            return self._analyze_behavioral_consistency(event)
        else:
            return 0.5  # Default neutral score
    
    def _analyze_connection_frequency(self, event: NetworkEvent) -> float:
        """Analyze connection frequency patterns"""
        # Check if this process is making too many connections
        recent_connections = [e for e in self.anomaly_memory 
                            if e.get('process') == event.process and 
                            self._is_recent(e.get('timestamp', ''), minutes=5)]
        
        frequency = len(recent_connections)
        
        # Normal processes: 0-10 connections per 5 min = low score
        # Suspicious: 10-50 connections = medium score  
        # Malicious: 50+ connections = high score
        if frequency <= 10:
            return 0.2
        elif frequency <= 50:
            return 0.6
        else:
            return 0.9
    
    def _analyze_process_behavior(self, event: NetworkEvent) -> float:
        """Analyze process behavior patterns"""
        process = event.process.lower()
        
        # Known system processes
        system_processes = ['system', 'svchost.exe', 'lsass.exe', 'winlogon.exe', 'csrss.exe']
        if any(sys_proc in process for sys_proc in system_processes):
            return 0.1  # Very low threat for system processes
        
        # Known browsers and applications
        known_apps = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'chatgpt.exe', 'teams.exe']
        if any(app in process for app in known_apps):
            return 0.3  # Low threat for known applications
        
        # Unknown or suspicious process names
        suspicious_patterns = ['temp', 'tmp', 'random', 'payload', 'shell', 'cmd']
        if any(pattern in process for pattern in suspicious_patterns):
            return 0.8  # High threat for suspicious names
        
        return 0.5  # Medium threat for unknown processes
    
    def _analyze_temporal_pattern(self, event: NetworkEvent) -> float:
        """Analyze temporal connection patterns"""
        try:
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            hour = event_time.hour
            
            # Normal business hours (8 AM - 6 PM) = lower score
            if 8 <= hour <= 18:
                return 0.2
            # Evening hours (6 PM - 11 PM) = medium score
            elif 18 < hour <= 23:
                return 0.4
            # Late night/early morning (11 PM - 8 AM) = higher score
            else:
                return 0.7
        except:
            return 0.5
    
    def _analyze_port_usage(self, event: NetworkEvent) -> float:
        """Analyze port usage patterns"""
        port = event.remote_port
        
        # Common legitimate ports
        common_ports = [80, 443, 53, 25, 110, 143, 993, 995, 21, 22, 23, 3389]
        if port in common_ports:
            return 0.2
        
        # High-numbered ephemeral ports (normal for outbound connections)
        if 32768 <= port <= 65535:
            return 0.3
        
        # Uncommon but potentially legitimate ports
        if 1024 <= port <= 32767:
            return 0.5
        
        # Low-numbered ports (potentially suspicious for outbound)
        if 1 <= port <= 1023:
            return 0.7
        
        return 0.5
    
    def _analyze_connection_state(self, event: NetworkEvent) -> float:
        """Analyze connection state patterns"""
        state = event.state.upper()
        
        # Normal states
        if state in ['ESTABLISHED', 'TIME_WAIT', 'CLOSE_WAIT']:
            return 0.2
        
        # Potentially suspicious states
        if state in ['SYN_SENT', 'SYN_RECV', 'FIN_WAIT1', 'FIN_WAIT2']:
            return 0.5
        
        # Unusual states
        return 0.7
    
    def _analyze_ip_reputation(self, event: NetworkEvent) -> float:
        """Analyze IP reputation (simplified)"""
        remote_ip = event.remote_ip
        
        try:
            ip_obj = ipaddress.ip_address(remote_ip)
            
            # Private/local IPs are generally safe
            if ip_obj.is_private or ip_obj.is_loopback:
                return 0.1
            
            # Check for known cloud providers (simplified)
            cloud_ranges = ['8.8.8.', '1.1.1.', '208.67.', '9.9.9.']
            if any(remote_ip.startswith(range_prefix) for range_prefix in cloud_ranges):
                return 0.3
            
            # Unknown public IPs get medium score
            return 0.5
            
        except:
            return 0.6  # Invalid IP format is suspicious
    
    def _analyze_protocol_anomaly(self, event: NetworkEvent) -> float:
        """Analyze protocol usage patterns"""
        protocol = event.protocol.upper()
        
        # TCP is most common and normal
        if protocol == 'TCP':
            return 0.2
        
        # UDP is common but can be more suspicious
        if protocol == 'UDP':
            return 0.4
        
        # Other protocols are less common
        return 0.6
    
    def _analyze_process_legitimacy(self, event: NetworkEvent) -> float:
        """Analyze process legitimacy"""
        process = event.process.lower()
        pid = event.pid
        
        # System Idle Process with PID 0 is normal
        if pid == 0 and 'system' in process:
            return 0.1
        
        # Processes with very high PIDs might be suspicious
        if pid > 50000:
            return 0.7
        
        # Check for legitimate process signatures
        legitimate_processes = [
            'svchost.exe', 'explorer.exe', 'winlogon.exe', 'lsass.exe',
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'teams.exe',
            'outlook.exe', 'word.exe', 'excel.exe', 'chatgpt.exe'
        ]
        
        if any(legit in process for legit in legitimate_processes):
            return 0.2
        
        return 0.5
    
    def _analyze_connection_duration(self, event: NetworkEvent) -> float:
        """Analyze connection duration patterns (simplified)"""
        # This would require tracking connection start/end times
        # For now, return neutral score
        return 0.5
    
    def _analyze_data_flow_pattern(self, event: NetworkEvent) -> float:
        """Analyze data flow patterns (simplified)"""
        # This would require packet size analysis
        # For now, return neutral score
        return 0.5
    
    def _analyze_geographic_anomaly(self, event: NetworkEvent) -> float:
        """Analyze geographic anomalies (simplified)"""
        # This would require GeoIP lookup
        # For now, return neutral score
        return 0.5
    
    def _analyze_behavioral_consistency(self, event: NetworkEvent) -> float:
        """Analyze behavioral consistency"""
        # Check if this process typically connects to similar destinations
        similar_connections = [e for e in self.anomaly_memory 
                             if e.get('process') == event.process]
        
        if len(similar_connections) < 5:
            return 0.6  # Not enough data, slightly suspicious
        
        # Check for consistency in destination patterns
        # This is a simplified analysis
        return 0.4
    
    def _determine_threat_level(self, cognitive_score: float, anchor_scores: Dict) -> ThreatLevel:
        """Determine threat level based on cognitive score and anchor analysis"""
        
        if cognitive_score >= 0.8:
            return ThreatLevel.CRITICAL
        elif cognitive_score >= 0.6:
            return ThreatLevel.THREAT
        elif cognitive_score >= 0.4:
            return ThreatLevel.SUSPICIOUS
        else:
            return ThreatLevel.AUTHENTIC
    
    def _calculate_confidence(self, anchor_scores: Dict) -> float:
        """Calculate confidence based on anchor consensus"""
        scores = [anchor['score'] for anchor in anchor_scores.values()]
        
        if not scores:
            return 0.5
        
        # Calculate standard deviation to measure consensus
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        mean_score = statistics.mean(scores)
        
        # Higher consensus (lower std dev) = higher confidence
        confidence = max(0.1, 1.0 - (std_dev * 2))
        
        return min(0.95, confidence)
    
    def _store_event(self, event_id: str, event: NetworkEvent, threat_level: ThreatLevel, 
                    confidence: float, cognitive_score: float, anchor_scores: Dict):
        """Store analyzed event in database"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO network_events 
                (id, timestamp, protocol, local_address, foreign_address, state, pid, process,
                 threat_level, confidence, cognitive_score, anchor_scores)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, event.timestamp, event.protocol, event.local_address,
                event.foreign_address, event.state, event.pid, event.process,
                threat_level.value, confidence, cognitive_score, json.dumps(anchor_scores)
            ))
    
    def _detect_anomalies(self, event: NetworkEvent, cognitive_score: float, 
                         anchor_scores: Dict) -> List[Dict]:
        """Detect specific anomalies in the network event"""
        anomalies = []
        
        # High cognitive score anomaly
        if cognitive_score > 0.7:
            anomalies.append({
                'type': 'high_cognitive_score',
                'severity': cognitive_score,
                'description': f'High cognitive threat score: {cognitive_score:.3f}'
            })
        
        # Process anomaly
        if anchor_scores.get('process_legitimacy', {}).get('score', 0) > 0.7:
            anomalies.append({
                'type': 'suspicious_process',
                'severity': anchor_scores['process_legitimacy']['score'],
                'description': f'Suspicious process: {event.process}'
            })
        
        # Connection frequency anomaly
        if anchor_scores.get('connection_frequency', {}).get('score', 0) > 0.8:
            anomalies.append({
                'type': 'high_connection_frequency',
                'severity': anchor_scores['connection_frequency']['score'],
                'description': f'High connection frequency from {event.process}'
            })
        
        # Store anomalies in memory for pattern analysis
        if anomalies:
            self.anomaly_memory.append({
                'timestamp': event.timestamp,
                'process': event.process,
                'anomalies': anomalies,
                'cognitive_score': cognitive_score
            })
        
        return anomalies
    
    def _is_recent(self, timestamp: str, minutes: int = 5) -> bool:
        """Check if timestamp is within recent minutes"""
        try:
            event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(event_time.tzinfo)
            return (now - event_time).total_seconds() <= (minutes * 60)
        except:
            return False

def load_network_data(csv_path: str) -> List[NetworkEvent]:
    """Load network data from Lee's CSV format"""
    logger.info(f"Loading network data from: {csv_path}")
    
    try:
        # Read CSV with Lee's column format
        df = pd.read_csv(csv_path)
        
        # Filter out header rows and empty rows
        df = df.dropna(subset=['timestamp'])
        df = df[~df['timestamp'].str.contains('New Run:', na=False)]
        df = df[df['timestamp'] != 'timestamp']  # Remove header duplicates
        
        logger.info(f"Loaded {len(df)} network events from CSV")
        
        # Convert to NetworkEvent objects
        events = []
        for _, row in df.iterrows():
            try:
                event = NetworkEvent(
                    timestamp=str(row['timestamp']),
                    protocol=str(row['protocol']),
                    local_address=str(row['local_address']),
                    foreign_address=str(row['foreign_address']),
                    state=str(row['state']),
                    pid=int(row['pid']) if pd.notna(row['pid']) else 0,
                    process=str(row['process'])
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(events)} network events")
        return events
        
    except Exception as e:
        logger.error(f"Error loading network data: {e}")
        return []

def analyze_network_data(csv_path: str = "sample_netstat.csv"):
    """Main function to analyze Lee's network data"""
    
    print("🔥 R.E.A.P.E.R. NETWORK ANALYZER - FIXED FOR LEE'S DATA")
    print("=" * 60)
    print("Real-time Cognitive Network Analysis Engine")
    print("=" * 60)
    
    # Initialize cognitive engine
    engine = NetworkCognitiveEngine()
    
    # Load network data
    events = load_network_data(csv_path)
    
    if not events:
        print("❌ NO NETWORK EVENTS LOADED!")
        print("Check your CSV file format and path.")
        return
    
    print(f"\n🔍 ANALYZING {len(events)} NETWORK EVENTS...")
    print("=" * 50)
    
    # Analyze events
    results = []
    threat_counts = defaultdict(int)
    anomaly_counts = defaultdict(int)
    
    for i, event in enumerate(events):
        if i % 1000 == 0:  # Progress indicator
            print(f"Processing event {i+1}/{len(events)}...")
        
        result = engine.analyze_network_event(event)
        results.append(result)
        
        # Count threat levels
        threat_counts[result['threat_level']] += 1
        
        # Count anomalies
        for anomaly in result['anomalies']:
            anomaly_counts[anomaly['type']] += 1
    
    # Display results
    print(f"\n📊 ANALYSIS COMPLETE - {len(events)} EVENTS PROCESSED")
    print("=" * 60)
    
    print("\n🎯 THREAT LEVEL DISTRIBUTION:")
    for threat_level, count in threat_counts.items():
        percentage = (count / len(events)) * 100
        print(f"   {threat_level.upper()}: {count} events ({percentage:.1f}%)")
    
    print("\n📈 ANOMALY SUMMARY:")
    total_anomalies = sum(anomaly_counts.values())
    print(f"   Total Anomalies: {total_anomalies}")
    
    if anomaly_counts:
        print("   Anomaly Types:")
        for anomaly_type, count in sorted(anomaly_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"     • {anomaly_type}: {count}")
    
    # Show high-threat events
    high_threat_events = [r for r in results if r['threat_level'] in ['threat', 'critical']]
    if high_threat_events:
        print(f"\n🚨 HIGH-THREAT EVENTS ({len(high_threat_events)}):")
        for event in high_threat_events[:10]:  # Show top 10
            event_data = event['event_data']
            print(f"   • {event_data['process']} -> {event_data['foreign_address']} "
                  f"[{event['threat_level'].upper()}] (Score: {event['cognitive_score']:.3f})")
    
    # Show suspicious processes
    suspicious_processes = defaultdict(int)
    for result in results:
        if result['threat_level'] in ['suspicious', 'threat', 'critical']:
            suspicious_processes[result['event_data']['process']] += 1
    
    if suspicious_processes:
        print(f"\n🔍 SUSPICIOUS PROCESSES:")
        for process, count in sorted(suspicious_processes.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   • {process}: {count} suspicious connections")
    
    print("\n🎯 R.E.A.P.E.R. NETWORK ANALYSIS COMPLETE")
    print("💀 'Cognitive resonance applied to network forensics' 💀")
    
    return results

if __name__ == "__main__":
    # Run analysis on Lee's data
    analyze_network_data("sample_netstat.csv")

