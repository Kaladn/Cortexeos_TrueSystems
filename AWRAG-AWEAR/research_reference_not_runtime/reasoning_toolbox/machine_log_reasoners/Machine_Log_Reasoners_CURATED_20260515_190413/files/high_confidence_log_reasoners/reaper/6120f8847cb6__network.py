from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class NetworkEvent(db.Model):
    """Network event model for R.E.A.P.E.R. analysis"""
    __tablename__ = 'network_events'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(50), nullable=False)
    protocol = db.Column(db.String(10))
    local_address = db.Column(db.String(50))
    local_port = db.Column(db.Integer)
    remote_address = db.Column(db.String(50))
    remote_port = db.Column(db.Integer)
    state = db.Column(db.String(20))
    pid = db.Column(db.Integer)
    process_name = db.Column(db.String(100))
    threat_level = db.Column(db.Float)
    threat_classification = db.Column(db.String(20))
    cognitive_coherence = db.Column(db.Float)
    human_likelihood = db.Column(db.Float)
    anomaly_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'protocol': self.protocol,
            'local_address': self.local_address,
            'local_port': self.local_port,
            'remote_address': self.remote_address,
            'remote_port': self.remote_port,
            'state': self.state,
            'pid': self.pid,
            'process_name': self.process_name,
            'threat_level': self.threat_level,
            'threat_classification': self.threat_classification,
            'cognitive_coherence': self.cognitive_coherence,
            'human_likelihood': self.human_likelihood,
            'anomaly_score': self.anomaly_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ProcessBaseline(db.Model):
    """Process baseline model for behavioral analysis"""
    __tablename__ = 'process_baselines'
    
    id = db.Column(db.Integer, primary_key=True)
    process_name = db.Column(db.String(100), unique=True, nullable=False)
    avg_connections = db.Column(db.Integer)
    common_ports = db.Column(db.Text)  # JSON string
    typical_protocols = db.Column(db.Text)  # JSON string
    baseline_established = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'process_name': self.process_name,
            'avg_connections': self.avg_connections,
            'common_ports': self.common_ports,
            'typical_protocols': self.typical_protocols,
            'baseline_established': self.baseline_established.isoformat() if self.baseline_established else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class AnomalyMemory(db.Model):
    """Anomaly memory model for repeat offender tracking"""
    __tablename__ = 'anomaly_memory'
    
    id = db.Column(db.Integer, primary_key=True)
    remote_address = db.Column(db.String(50))
    process_name = db.Column(db.String(100))
    anomaly_type = db.Column(db.String(50))
    first_seen = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)
    occurrence_count = db.Column(db.Integer, default=1)
    severity_score = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'remote_address': self.remote_address,
            'process_name': self.process_name,
            'anomaly_type': self.anomaly_type,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'occurrence_count': self.occurrence_count,
            'severity_score': self.severity_score
        }

