#!/usr/bin/env python3
"""
R.E.A.P.E.R. NETWORK DATA INTEGRATION SYSTEM
Netstat CSV to Cognitive Analysis Pipeline

This module processes network connection data through the R.E.A.P.E.R. cognitive engine
to detect anomalous network behavior patterns and potential security threats.

Author: R.E.A.P.E.R. Development Team
Version: 1.0
Date: June 16, 2025
"""

import csv
import json
import sqlite3
import time
import subprocess
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging
import hashlib
import statistics
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NetworkEvent:
    """Network connection event structure"""
    timestamp: str
    protocol: str
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    state: str
    pid: int
    process_name: str
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'protocol': self.protocol,
            'local_address': self.local_address,
            'local_port': self.local_port,
            'remote_address': self.remote_address,
            'remote_port': self.remote_port,
            'state': self.state,
            'pid': self.pid,
            'process_name': self.process_name
        }

@dataclass
class CognitiveEvent:
    """Cognitive analysis event structure"""
    event_type: str
    timestamp: str
    data: Dict
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class NetworkCognitiveAnalyzer:
    """
    R.E.A.P.E.R. Network Cognitive Analysis Engine
    
    Processes network connection data through cognitive resonance analysis
    to detect anomalous patterns and potential security threats.
    """
    
    def __init__(self, db_path: str = "reaper_network.db"):
        self.db_path = db_path
        self.cognitive_anchors = self._initialize_cognitive_anchors()
        self.baseline_patterns = {}
        self.anomaly_memory = {}
        self.threat_thresholds = {
            'AUTHENTIC': 0.3,
            'SUSPICIOUS': 0.5,
            'THREAT': 0.7,
            'CRITICAL': 0.9
        }
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize SQLite database for network analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Network events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                protocol TEXT,
                local_address TEXT,
                local_port INTEGER,
                remote_address TEXT,
                remote_port INTEGER,
                state TEXT,
                pid INTEGER,
                process_name TEXT,
                threat_level REAL,
                cognitive_coherence REAL,
                human_likelihood REAL,
                anomaly_score REAL
            )
        ''')
        
        # Process baselines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_baselines (
                process_name TEXT PRIMARY KEY,
                avg_connections INTEGER,
                common_ports TEXT,
                typical_protocols TEXT,
                baseline_established TIMESTAMP,
                last_updated TIMESTAMP
            )
        ''')
        
        # Anomaly memory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remote_address TEXT,
                process_name TEXT,
                anomaly_type TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                occurrence_count INTEGER,
                severity_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    def _initialize_cognitive_anchors(self) -> Dict:
        """Initialize cognitive anchors for network analysis"""
        return {
            'connection_timing': {
                'weight': 1.2,
                'description': 'Analysis of connection establishment timing patterns'
            },
            'port_behavior': {
                'weight': 1.1,
                'description': 'Port usage patterns and anomalies'
            },
            'process_consistency': {
                'weight': 1.3,
                'description': 'Process behavior consistency analysis'
            },
            'protocol_adherence': {
                'weight': 1.0,
                'description': 'Protocol usage pattern analysis'
            },
            'connection_frequency': {
                'weight': 1.1,
                'description': 'Connection frequency and rhythm analysis'
            },
            'remote_reputation': {
                'weight': 1.4,
                'description': 'Remote address reputation and behavior'
            },
            'state_transitions': {
                'weight': 1.0,
                'description': 'Connection state transition patterns'
            },
            'temporal_clustering': {
                'weight': 0.9,
                'description': 'Temporal clustering of network events'
            },
            'bandwidth_patterns': {
                'weight': 1.1,
                'description': 'Bandwidth usage pattern analysis'
            },
            'session_persistence': {
                'weight': 1.0,
                'description': 'Session persistence and duration analysis'
            },
            'geographic_anomalies': {
                'weight': 1.2,
                'description': 'Geographic location anomaly detection'
            },
            'encryption_patterns': {
                'weight': 1.1,
                'description': 'Encryption usage pattern analysis'
            }
        }
    
    def process_netstat_csv(self, csv_path: str) -> List[Dict]:
        """Process netstat CSV file through cognitive analysis"""
        logger.info(f"Processing netstat CSV: {csv_path}")
        results = []
        
        try:
            with open(csv_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader, None)  # Skip header if present
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        # Parse CSV row into NetworkEvent
                        if len(row) >= 8:
                            network_event = NetworkEvent(
                                timestamp=row[0] if row[0] else datetime.now().isoformat(),
                                protocol=row[1],
                                local_address=row[2].split(':')[0] if ':' in row[2] else row[2],
                                local_port=int(row[2].split(':')[1]) if ':' in row[2] and row[2].split(':')[1].isdigit() else 0,
                                remote_address=row[3].split(':')[0] if ':' in row[3] else row[3],
                                remote_port=int(row[4]) if row[4].isdigit() else 0,
                                state=row[5],
                                pid=int(row[6]) if row[6].isdigit() else 0,
                                process_name=row[7]
                            )
                            
                            # Convert to CognitiveEvent
                            cognitive_event = CognitiveEvent(
                                event_type="network_activity",
                                timestamp=network_event.timestamp,
                                data=network_event.to_dict()
                            )
                            
                            # Process through cognitive analysis
                            result = self.process_cognitive_event(cognitive_event)
                            results.append(result)
                            
                            # Store in database
                            self._store_network_event(network_event, result)
                            
                        else:
                            logger.warning(f"Skipping malformed row {row_num}: {row}")
                            
                    except Exception as e:
                        logger.error(f"Error processing row {row_num}: {e}")
                        continue
                        
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_path}")
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            
        logger.info(f"Processed {len(results)} network events")
        return results
    
    def process_cognitive_event(self, event: CognitiveEvent) -> Dict:
        """Process a single cognitive event through the analysis engine"""
        data = event.data
        
        # Calculate cognitive anchor scores
        anchor_scores = {}
        for anchor_name, anchor_config in self.cognitive_anchors.items():
            score = self._calculate_anchor_score(anchor_name, data)
            anchor_scores[anchor_name] = score * anchor_config['weight']
        
        # Calculate overall metrics
        cognitive_coherence = self._calculate_cognitive_coherence(anchor_scores)
        human_likelihood = self._calculate_human_likelihood(anchor_scores, data)
        threat_level = self._calculate_threat_level(anchor_scores, cognitive_coherence)
        anomaly_score = self._calculate_anomaly_score(data, anchor_scores)
        
        # Determine threat classification
        threat_classification = self._classify_threat_level(threat_level)
        
        # Update anomaly memory
        self._update_anomaly_memory(data, anomaly_score, threat_classification)
        
        result = {
            'timestamp': event.timestamp,
            'event_type': event.event_type,
            'threat_level': threat_level,
            'threat_classification': threat_classification,
            'cognitive_coherence': cognitive_coherence,
            'human_likelihood': human_likelihood,
            'anomaly_score': anomaly_score,
            'anchor_scores': anchor_scores,
            'process_name': data.get('process_name', 'unknown'),
            'remote_address': data.get('remote_address', 'unknown'),
            'remote_port': data.get('remote_port', 0),
            'recommendations': self._generate_recommendations(threat_classification, anomaly_score, data)
        }
        
        return result
    
    def _calculate_anchor_score(self, anchor_name: str, data: Dict) -> float:
        """Calculate score for a specific cognitive anchor"""
        if anchor_name == 'connection_timing':
            return self._analyze_connection_timing(data)
        elif anchor_name == 'port_behavior':
            return self._analyze_port_behavior(data)
        elif anchor_name == 'process_consistency':
            return self._analyze_process_consistency(data)
        elif anchor_name == 'protocol_adherence':
            return self._analyze_protocol_adherence(data)
        elif anchor_name == 'connection_frequency':
            return self._analyze_connection_frequency(data)
        elif anchor_name == 'remote_reputation':
            return self._analyze_remote_reputation(data)
        elif anchor_name == 'state_transitions':
            return self._analyze_state_transitions(data)
        elif anchor_name == 'temporal_clustering':
            return self._analyze_temporal_clustering(data)
        elif anchor_name == 'bandwidth_patterns':
            return self._analyze_bandwidth_patterns(data)
        elif anchor_name == 'session_persistence':
            return self._analyze_session_persistence(data)
        elif anchor_name == 'geographic_anomalies':
            return self._analyze_geographic_anomalies(data)
        elif anchor_name == 'encryption_patterns':
            return self._analyze_encryption_patterns(data)
        else:
            return 0.5  # Default neutral score
    
    def _analyze_connection_timing(self, data: Dict) -> float:
        """Analyze connection timing patterns"""
        # Simulate timing analysis based on timestamp patterns
        timestamp = data.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = dt.hour
            
            # Suspicious hours (late night/early morning)
            if 2 <= hour <= 5:
                return 0.8  # Higher suspicion
            elif 22 <= hour or hour <= 1:
                return 0.6  # Moderate suspicion
            else:
                return 0.3  # Normal hours
        except:
            return 0.5  # Unknown timing
    
    def _analyze_port_behavior(self, data: Dict) -> float:
        """Analyze port usage patterns"""
        remote_port = data.get('remote_port', 0)
        local_port = data.get('local_port', 0)
        
        # Common legitimate ports
        common_ports = {80, 443, 53, 22, 21, 25, 110, 143, 993, 995}
        suspicious_ports = {1337, 31337, 4444, 5555, 6666, 7777, 8888, 9999}
        
        if remote_port in suspicious_ports:
            return 0.9  # Highly suspicious
        elif remote_port in common_ports:
            return 0.2  # Legitimate
        elif remote_port > 49152:  # Ephemeral port range
            return 0.4  # Potentially normal
        else:
            return 0.5  # Unknown
    
    def _analyze_process_consistency(self, data: Dict) -> float:
        """Analyze process behavior consistency"""
        process_name = data.get('process_name', '').lower()
        remote_port = data.get('remote_port', 0)
        protocol = data.get('protocol', '').lower()
        
        # Known process patterns
        if 'chrome' in process_name or 'firefox' in process_name:
            if remote_port in {80, 443}:
                return 0.2  # Normal browser behavior
            else:
                return 0.6  # Unusual for browser
        elif 'ssh' in process_name:
            if remote_port == 22:
                return 0.2  # Normal SSH
            else:
                return 0.7  # SSH on unusual port
        elif 'system' in process_name or process_name == '':
            return 0.8  # System processes can be suspicious
        else:
            return 0.5  # Unknown process
    
    def _analyze_protocol_adherence(self, data: Dict) -> float:
        """Analyze protocol usage patterns"""
        protocol = data.get('protocol', '').lower()
        remote_port = data.get('remote_port', 0)
        
        # Protocol-port consistency
        if protocol == 'tcp':
            if remote_port in {80, 443, 22, 21, 25}:
                return 0.2  # Normal TCP usage
            else:
                return 0.4  # TCP on other ports
        elif protocol == 'udp':
            if remote_port in {53, 123, 161}:
                return 0.2  # Normal UDP usage
            else:
                return 0.5  # UDP on other ports
        else:
            return 0.6  # Unknown protocol
    
    def _analyze_connection_frequency(self, data: Dict) -> float:
        """Analyze connection frequency patterns"""
        # This would require historical data analysis
        # For now, return a baseline score
        return 0.4
    
    def _analyze_remote_reputation(self, data: Dict) -> float:
        """Analyze remote address reputation"""
        remote_address = data.get('remote_address', '')
        
        # Private IP ranges (generally safe)
        if (remote_address.startswith('192.168.') or 
            remote_address.startswith('10.') or 
            remote_address.startswith('172.16.') or
            remote_address.startswith('127.')):
            return 0.2  # Local/private network
        
        # Known suspicious patterns
        if (remote_address.startswith('0.') or 
            remote_address == '0.0.0.0' or
            remote_address == '255.255.255.255'):
            return 0.9  # Highly suspicious
        
        return 0.5  # Unknown external address
    
    def _analyze_state_transitions(self, data: Dict) -> float:
        """Analyze connection state patterns"""
        state = data.get('state', '').upper()
        
        if state in ['ESTABLISHED', 'LISTEN']:
            return 0.3  # Normal states
        elif state in ['SYN_SENT', 'SYN_RECV']:
            return 0.4  # Connection establishment
        elif state in ['FIN_WAIT', 'CLOSE_WAIT', 'CLOSING']:
            return 0.3  # Normal termination
        elif state in ['TIME_WAIT']:
            return 0.2  # Normal cleanup
        else:
            return 0.6  # Unknown state
    
    def _analyze_temporal_clustering(self, data: Dict) -> float:
        """Analyze temporal clustering of events"""
        # This would require analysis of multiple events
        # For now, return baseline
        return 0.4
    
    def _analyze_bandwidth_patterns(self, data: Dict) -> float:
        """Analyze bandwidth usage patterns"""
        # This would require actual bandwidth data
        # For now, return baseline
        return 0.4
    
    def _analyze_session_persistence(self, data: Dict) -> float:
        """Analyze session persistence patterns"""
        state = data.get('state', '').upper()
        
        if state == 'ESTABLISHED':
            return 0.3  # Normal persistent connection
        elif state == 'LISTEN':
            return 0.2  # Server listening
        else:
            return 0.5  # Transient connection
    
    def _analyze_geographic_anomalies(self, data: Dict) -> float:
        """Analyze geographic location anomalies"""
        # This would require GeoIP lookup
        # For now, return baseline
        return 0.4
    
    def _analyze_encryption_patterns(self, data: Dict) -> float:
        """Analyze encryption usage patterns"""
        remote_port = data.get('remote_port', 0)
        
        # Encrypted ports
        if remote_port in {443, 993, 995, 22}:
            return 0.2  # Encrypted connection
        elif remote_port in {80, 21, 23, 25}:
            return 0.6  # Unencrypted connection
        else:
            return 0.5  # Unknown
    
    def _calculate_cognitive_coherence(self, anchor_scores: Dict) -> float:
        """Calculate overall cognitive coherence"""
        if not anchor_scores:
            return 0.5
        
        scores = list(anchor_scores.values())
        mean_score = statistics.mean(scores)
        variance = statistics.variance(scores) if len(scores) > 1 else 0
        
        # Lower variance indicates higher coherence
        coherence = max(0.0, min(1.0, 1.0 - variance))
        return coherence
    
    def _calculate_human_likelihood(self, anchor_scores: Dict, data: Dict) -> float:
        """Calculate likelihood of human vs automated behavior"""
        process_name = data.get('process_name', '').lower()
        
        # Automated processes
        if any(term in process_name for term in ['bot', 'crawler', 'spider', 'automated']):
            return 0.1
        
        # Human-operated applications
        if any(term in process_name for term in ['chrome', 'firefox', 'safari', 'edge']):
            return 0.8
        
        # System processes
        if 'system' in process_name or process_name == '':
            return 0.3
        
        # Calculate based on anchor patterns
        timing_score = anchor_scores.get('connection_timing', 0.5)
        frequency_score = anchor_scores.get('connection_frequency', 0.5)
        
        # Human behavior tends to be more irregular
        irregularity = abs(timing_score - 0.5) + abs(frequency_score - 0.5)
        human_likelihood = 0.5 + (irregularity * 0.3)
        
        return max(0.0, min(1.0, human_likelihood))
    
    def _calculate_threat_level(self, anchor_scores: Dict, cognitive_coherence: float) -> float:
        """Calculate overall threat level"""
        if not anchor_scores:
            return 0.5
        
        # Weighted average of anchor scores
        total_weight = sum(self.cognitive_anchors[anchor]['weight'] 
                          for anchor in anchor_scores.keys())
        weighted_sum = sum(score * self.cognitive_anchors[anchor]['weight'] 
                          for anchor, score in anchor_scores.items())
        
        base_threat = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # Adjust based on cognitive coherence
        # Low coherence might indicate evasion attempts
        coherence_adjustment = (1.0 - cognitive_coherence) * 0.2
        
        threat_level = min(1.0, base_threat + coherence_adjustment)
        return threat_level
    
    def _calculate_anomaly_score(self, data: Dict, anchor_scores: Dict) -> float:
        """Calculate anomaly score based on deviation from baseline"""
        # For now, use a simple calculation
        # In production, this would compare against established baselines
        
        high_risk_anchors = ['remote_reputation', 'process_consistency', 'port_behavior']
        high_risk_scores = [anchor_scores.get(anchor, 0.5) for anchor in high_risk_anchors]
        
        anomaly_score = statistics.mean(high_risk_scores)
        return anomaly_score
    
    def _classify_threat_level(self, threat_level: float) -> str:
        """Classify threat level into categories"""
        if threat_level >= self.threat_thresholds['CRITICAL']:
            return 'CRITICAL'
        elif threat_level >= self.threat_thresholds['THREAT']:
            return 'THREAT'
        elif threat_level >= self.threat_thresholds['SUSPICIOUS']:
            return 'SUSPICIOUS'
        else:
            return 'AUTHENTIC'
    
    def _update_anomaly_memory(self, data: Dict, anomaly_score: float, threat_classification: str):
        """Update anomaly memory for repeat offender tracking"""
        remote_address = data.get('remote_address', '')
        process_name = data.get('process_name', '')
        
        if threat_classification in ['SUSPICIOUS', 'THREAT', 'CRITICAL']:
            key = f"{remote_address}:{process_name}"
            
            if key in self.anomaly_memory:
                self.anomaly_memory[key]['count'] += 1
                self.anomaly_memory[key]['last_seen'] = datetime.now().isoformat()
                self.anomaly_memory[key]['severity_score'] = max(
                    self.anomaly_memory[key]['severity_score'], 
                    anomaly_score
                )
            else:
                self.anomaly_memory[key] = {
                    'remote_address': remote_address,
                    'process_name': process_name,
                    'first_seen': datetime.now().isoformat(),
                    'last_seen': datetime.now().isoformat(),
                    'count': 1,
                    'severity_score': anomaly_score
                }
    
    def _generate_recommendations(self, threat_classification: str, anomaly_score: float, data: Dict) -> List[str]:
        """Generate security recommendations based on analysis"""
        recommendations = []
        
        if threat_classification == 'CRITICAL':
            recommendations.extend([
                "🚨 IMMEDIATE ACTION REQUIRED",
                "Block connection immediately",
                "Investigate process and system compromise",
                "Check for lateral movement",
                "Preserve forensic evidence"
            ])
        elif threat_classification == 'THREAT':
            recommendations.extend([
                "⚠️ HIGH PRIORITY INVESTIGATION",
                "Monitor connection closely",
                "Verify process legitimacy",
                "Check system integrity",
                "Consider temporary restrictions"
            ])
        elif threat_classification == 'SUSPICIOUS':
            recommendations.extend([
                "🔍 ENHANCED MONITORING",
                "Log detailed connection data",
                "Verify normal business purpose",
                "Monitor for pattern changes"
            ])
        else:
            recommendations.append("✅ Continue normal monitoring")
        
        # Specific recommendations based on data
        remote_port = data.get('remote_port', 0)
        if remote_port in {1337, 31337, 4444}:
            recommendations.append("🚩 Connection to known malicious port")
        
        process_name = data.get('process_name', '')
        if 'system' in process_name.lower() and threat_classification != 'AUTHENTIC':
            recommendations.append("🔍 Investigate system process behavior")
        
        return recommendations
    
    def _store_network_event(self, event: NetworkEvent, analysis: Dict):
        """Store network event and analysis in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO network_events 
            (timestamp, protocol, local_address, local_port, remote_address, 
             remote_port, state, pid, process_name, threat_level, 
             cognitive_coherence, human_likelihood, anomaly_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.timestamp, event.protocol, event.local_address, event.local_port,
            event.remote_address, event.remote_port, event.state, event.pid,
            event.process_name, analysis['threat_level'], analysis['cognitive_coherence'],
            analysis['human_likelihood'], analysis['anomaly_score']
        ))
        
        conn.commit()
        conn.close()
    
    def get_anomaly_summary(self) -> Dict:
        """Get summary of detected anomalies"""
        return {
            'total_anomalies': len(self.anomaly_memory),
            'repeat_offenders': len([k for k, v in self.anomaly_memory.items() if v['count'] > 1]),
            'high_severity': len([k for k, v in self.anomaly_memory.items() if v['severity_score'] > 0.7]),
            'recent_anomalies': len([k for k, v in self.anomaly_memory.items() 
                                   if datetime.fromisoformat(v['last_seen']) > datetime.now() - timedelta(hours=1)])
        }

def create_sample_netstat_csv():
    """Create a sample netstat CSV for testing"""
    sample_data = [
        ['timestamp', 'protocol', 'local_address', 'remote_address', 'remote_port', 'state', 'pid', 'process_name'],
        ['2025-06-16T10:30:00', 'TCP', '192.168.1.100:54321', '142.250.191.14', '443', 'ESTABLISHED', '1234', 'chrome.exe'],
        ['2025-06-16T10:30:01', 'TCP', '192.168.1.100:54322', '52.97.144.85', '443', 'ESTABLISHED', '1234', 'chrome.exe'],
        ['2025-06-16T10:30:02', 'TCP', '192.168.1.100:22', '0.0.0.0', '0', 'LISTEN', '567', 'sshd'],
        ['2025-06-16T02:15:00', 'TCP', '192.168.1.100:54323', '185.220.101.32', '1337', 'ESTABLISHED', '9999', 'system'],
        ['2025-06-16T10:30:04', 'UDP', '192.168.1.100:53', '8.8.8.8', '53', 'ESTABLISHED', '890', 'dns.exe'],
        ['2025-06-16T03:45:00', 'TCP', '192.168.1.100:54324', '192.168.1.1', '4444', 'ESTABLISHED', '0', ''],
    ]
    
    with open('sample_netstat.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)
    
    print("✅ Created sample_netstat.csv for testing")

def main():
    """Main function to demonstrate R.E.A.P.E.R. network analysis"""
    print("🔥 R.E.A.P.E.R. NETWORK COGNITIVE ANALYSIS ENGINE")
    print("=" * 60)
    
    # Create sample data if it doesn't exist
    import os
    if not os.path.exists('sample_netstat.csv'):
        create_sample_netstat_csv()
    
    # Initialize analyzer
    analyzer = NetworkCognitiveAnalyzer()
    
    # Process sample CSV
    print("\n🧵 PROCESSING NETWORK DATA THROUGH COGNITIVE ANALYSIS...")
    results = analyzer.process_netstat_csv('sample_netstat.csv')
    
    print(f"\n📊 ANALYSIS COMPLETE - {len(results)} EVENTS PROCESSED")
    print("=" * 60)
    
    # Display results
    for i, result in enumerate(results, 1):
        print(f"\n🔍 EVENT {i}: {result['process_name']} → {result['remote_address']}:{result['remote_port']}")
        print(f"   Threat Level: {result['threat_classification']} ({result['threat_level']:.3f})")
        print(f"   Cognitive Coherence: {result['cognitive_coherence']:.3f}")
        print(f"   Human Likelihood: {result['human_likelihood']:.3f}")
        print(f"   Anomaly Score: {result['anomaly_score']:.3f}")
        
        if result['threat_classification'] != 'AUTHENTIC':
            print("   🚨 RECOMMENDATIONS:")
            for rec in result['recommendations']:
                print(f"      {rec}")
    
    # Display anomaly summary
    print(f"\n📈 ANOMALY SUMMARY:")
    summary = analyzer.get_anomaly_summary()
    for key, value in summary.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print("\n🎯 R.E.A.P.E.R. NETWORK ANALYSIS COMPLETE")
    print("💀 'Cognitive resonance applied to network forensics' 💀")

if __name__ == "__main__":
    main()

