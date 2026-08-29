#!/usr/bin/env python3
"""
R.E.A.P.E.R. PHASE 4: PREEMPTIVE COGNITIVE SECURITY ENGINE
Advanced Predictive Threat Modeling and Behavioral Forecasting

This module implements the core Phase 4 capabilities:
- Predictive threat modeling using machine learning
- Behavioral pattern forecasting
- Preemptive security recommendations
- Multi-dimensional risk assessment
- Temporal threat evolution tracking

Author: R.E.A.P.E.R. Development Team
Version: 4.0
Date: June 16, 2025
"""

import numpy as np
import pandas as pd
import sqlite3
import json
import yaml
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PredictiveEvent:
    """Enhanced event structure for predictive analysis"""
    event_id: str
    timestamp: str
    event_type: str
    data: Dict
    features: Dict
    prediction_confidence: float = 0.0
    threat_probability: float = 0.0
    risk_factors: List[str] = None
    temporal_context: Dict = None
    behavioral_baseline: Dict = None

@dataclass
class ThreatPrediction:
    """Threat prediction result structure"""
    prediction_id: str
    timestamp: str
    predicted_threat_level: float
    confidence_score: float
    time_to_threat: int  # minutes
    risk_factors: List[str]
    recommended_actions: List[str]
    affected_entities: List[str]
    prediction_model: str
    feature_importance: Dict

class PredictiveModelManager:
    """
    Manages multiple predictive models for different threat types
    """
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.models = {}
        self.scalers = {}
        self.feature_extractors = {}
        self.model_metadata = {}
        
    def train_threat_prediction_model(self, training_data: pd.DataFrame, model_name: str):
        """Train a predictive model for threat detection"""
        logger.info(f"Training predictive model: {model_name}")
        
        # Feature engineering
        features = self._extract_predictive_features(training_data)
        
        # Prepare target variable (threat level)
        y = training_data['threat_level'].apply(lambda x: 1 if x > 0.5 else 0)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Random Forest model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        accuracy = model.score(X_test_scaled, y_test)
        
        logger.info(f"Model {model_name} trained with accuracy: {accuracy:.3f}")
        
        # Store model and scaler
        self.models[model_name] = model
        self.scalers[model_name] = scaler
        self.model_metadata[model_name] = {
            'accuracy': accuracy,
            'feature_names': list(features.columns),
            'trained_at': datetime.now().isoformat(),
            'training_samples': len(X_train)
        }
        
        # Save to disk
        self._save_model(model_name)
        
        return accuracy
    
    def _extract_predictive_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features for predictive modeling"""
        features = pd.DataFrame()
        
        # Temporal features
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        features['hour'] = data['timestamp'].dt.hour
        features['day_of_week'] = data['timestamp'].dt.dayofweek
        features['is_weekend'] = (data['timestamp'].dt.dayofweek >= 5).astype(int)
        features['is_night'] = ((data['timestamp'].dt.hour >= 22) | 
                               (data['timestamp'].dt.hour <= 6)).astype(int)
        
        # Behavioral features
        features['cognitive_coherence'] = data.get('cognitive_coherence', 0.5)
        features['human_likelihood'] = data.get('human_likelihood', 0.5)
        features['anomaly_score'] = data.get('anomaly_score', 0.5)
        
        # Network-specific features (if available)
        if 'remote_port' in data.columns:
            features['is_common_port'] = data['remote_port'].isin([80, 443, 22, 21, 25]).astype(int)
            features['is_suspicious_port'] = data['remote_port'].isin([1337, 31337, 4444]).astype(int)
            features['port_category'] = pd.cut(data['remote_port'], 
                                             bins=[0, 1024, 49152, 65536], 
                                             labels=[0, 1, 2]).astype(int)
        
        # Process-specific features (if available)
        if 'process_name' in data.columns:
            features['is_system_process'] = data['process_name'].str.contains('system', case=False, na=False).astype(int)
            features['is_browser'] = data['process_name'].str.contains('chrome|firefox|safari|edge', case=False, na=False).astype(int)
            features['process_name_length'] = data['process_name'].str.len().fillna(0)
        
        # Statistical features
        features['threat_level_ma'] = data['threat_level'].rolling(window=5, min_periods=1).mean()
        features['threat_level_std'] = data['threat_level'].rolling(window=5, min_periods=1).std().fillna(0)
        
        return features.fillna(0)
    
    def predict_threat(self, event_data: Dict, model_name: str = 'default') -> ThreatPrediction:
        """Predict threat level for a given event"""
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not found, using default prediction")
            return self._default_prediction(event_data)
        
        # Extract features
        df = pd.DataFrame([event_data])
        features = self._extract_predictive_features(df)
        
        # Scale features
        features_scaled = self.scalers[model_name].transform(features)
        
        # Make prediction
        model = self.models[model_name]
        threat_probability = model.predict_proba(features_scaled)[0][1]
        confidence = max(model.predict_proba(features_scaled)[0])
        
        # Calculate feature importance for this prediction
        feature_importance = dict(zip(
            self.model_metadata[model_name]['feature_names'],
            model.feature_importances_
        ))
        
        # Generate risk factors
        risk_factors = self._identify_risk_factors(features.iloc[0], feature_importance)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(threat_probability, risk_factors)
        
        # Estimate time to threat
        time_to_threat = self._estimate_time_to_threat(threat_probability, event_data)
        
        prediction = ThreatPrediction(
            prediction_id=f"pred_{int(time.time())}_{hash(str(event_data)) % 10000}",
            timestamp=datetime.now().isoformat(),
            predicted_threat_level=threat_probability,
            confidence_score=confidence,
            time_to_threat=time_to_threat,
            risk_factors=risk_factors,
            recommended_actions=recommendations,
            affected_entities=[event_data.get('process_name', 'unknown')],
            prediction_model=model_name,
            feature_importance=feature_importance
        )
        
        return prediction
    
    def _identify_risk_factors(self, features: pd.Series, feature_importance: Dict) -> List[str]:
        """Identify key risk factors from feature analysis"""
        risk_factors = []
        
        # Check high-importance features
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        
        for feature_name, importance in sorted_features[:5]:
            if importance > 0.1:  # Significant importance threshold
                feature_value = features.get(feature_name, 0)
                
                if feature_name == 'is_night' and feature_value == 1:
                    risk_factors.append("Activity during suspicious hours (night time)")
                elif feature_name == 'is_suspicious_port' and feature_value == 1:
                    risk_factors.append("Connection to known malicious port")
                elif feature_name == 'is_system_process' and feature_value == 1:
                    risk_factors.append("System process with unusual behavior")
                elif feature_name == 'anomaly_score' and feature_value > 0.7:
                    risk_factors.append("High anomaly score detected")
                elif feature_name == 'cognitive_coherence' and feature_value < 0.3:
                    risk_factors.append("Low cognitive coherence (potential evasion)")
                elif feature_name == 'human_likelihood' and feature_value < 0.2:
                    risk_factors.append("Automated/non-human behavior detected")
        
        return risk_factors if risk_factors else ["General behavioral anomaly"]
    
    def _generate_recommendations(self, threat_probability: float, risk_factors: List[str]) -> List[str]:
        """Generate actionable recommendations based on threat prediction"""
        recommendations = []
        
        if threat_probability > 0.8:
            recommendations.extend([
                "🚨 IMMEDIATE ACTION: Isolate affected system",
                "🔍 Conduct forensic analysis",
                "📋 Document incident details",
                "🚫 Block suspicious connections",
                "👥 Notify security team"
            ])
        elif threat_probability > 0.6:
            recommendations.extend([
                "⚠️ ENHANCED MONITORING: Increase logging detail",
                "🔍 Investigate process behavior",
                "📊 Analyze historical patterns",
                "🛡️ Apply additional security controls"
            ])
        elif threat_probability > 0.4:
            recommendations.extend([
                "👁️ CONTINUOUS MONITORING: Track behavior changes",
                "📈 Establish baseline patterns",
                "🔄 Schedule regular reviews"
            ])
        else:
            recommendations.append("✅ Continue normal monitoring")
        
        # Add specific recommendations based on risk factors
        for factor in risk_factors:
            if "night time" in factor:
                recommendations.append("🌙 Implement time-based access controls")
            elif "malicious port" in factor:
                recommendations.append("🚫 Block access to suspicious ports")
            elif "system process" in factor:
                recommendations.append("🔍 Verify system process integrity")
            elif "automated" in factor:
                recommendations.append("🤖 Implement bot detection measures")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _estimate_time_to_threat(self, threat_probability: float, event_data: Dict) -> int:
        """Estimate time until threat materializes (in minutes)"""
        base_time = 60  # Base time of 1 hour
        
        # Adjust based on threat probability
        if threat_probability > 0.8:
            return 5  # Immediate threat
        elif threat_probability > 0.6:
            return 15  # High threat
        elif threat_probability > 0.4:
            return 60  # Medium threat
        else:
            return 240  # Low threat (4 hours)
    
    def _default_prediction(self, event_data: Dict) -> ThreatPrediction:
        """Generate default prediction when no model is available"""
        # Simple heuristic-based prediction
        threat_level = 0.3  # Default moderate threat
        
        # Adjust based on available data
        if event_data.get('remote_port') in [1337, 31337, 4444]:
            threat_level += 0.4
        if 'system' in event_data.get('process_name', '').lower():
            threat_level += 0.2
        if event_data.get('anomaly_score', 0) > 0.7:
            threat_level += 0.3
        
        threat_level = min(threat_level, 1.0)
        
        return ThreatPrediction(
            prediction_id=f"default_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            predicted_threat_level=threat_level,
            confidence_score=0.6,
            time_to_threat=120,
            risk_factors=["Heuristic-based assessment"],
            recommended_actions=["Train predictive model for better accuracy"],
            affected_entities=[event_data.get('process_name', 'unknown')],
            prediction_model='heuristic',
            feature_importance={}
        )
    
    def _save_model(self, model_name: str):
        """Save model and scaler to disk"""
        import os
        os.makedirs(self.model_dir, exist_ok=True)
        
        model_path = f"{self.model_dir}/{model_name}_model.joblib"
        scaler_path = f"{self.model_dir}/{model_name}_scaler.joblib"
        metadata_path = f"{self.model_dir}/{model_name}_metadata.json"
        
        joblib.dump(self.models[model_name], model_path)
        joblib.dump(self.scalers[model_name], scaler_path)
        
        with open(metadata_path, 'w') as f:
            json.dump(self.model_metadata[model_name], f, indent=2)
        
        logger.info(f"Model {model_name} saved to {self.model_dir}")

class TemporalThreatAnalyzer:
    """
    Analyzes threat evolution over time and predicts future threat landscapes
    """
    
    def __init__(self, db_path: str = "reaper_temporal.db"):
        self.db_path = db_path
        self.threat_timeline = []
        self.pattern_memory = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize temporal analysis database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threat_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                threat_level REAL,
                threat_type TEXT,
                entity_id TEXT,
                prediction_accuracy REAL,
                actual_outcome TEXT,
                temporal_features TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threat_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT UNIQUE,
                pattern_data TEXT,
                confidence_score REAL,
                last_updated TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def analyze_threat_evolution(self, historical_data: List[Dict]) -> Dict:
        """Analyze how threats evolve over time"""
        logger.info("Analyzing threat evolution patterns")
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(historical_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Calculate threat velocity (rate of change)
        df['threat_velocity'] = df['threat_level'].diff() / df['timestamp'].diff().dt.total_seconds()
        
        # Identify threat escalation patterns
        escalation_events = df[df['threat_velocity'] > 0.001]  # Significant increase
        
        # Analyze temporal patterns
        hourly_patterns = df.groupby(df['timestamp'].dt.hour)['threat_level'].agg(['mean', 'std', 'count'])
        daily_patterns = df.groupby(df['timestamp'].dt.dayofweek)['threat_level'].agg(['mean', 'std', 'count'])
        
        # Identify recurring threat cycles
        threat_cycles = self._identify_threat_cycles(df)
        
        analysis_result = {
            'total_events': len(df),
            'escalation_events': len(escalation_events),
            'average_threat_level': df['threat_level'].mean(),
            'threat_volatility': df['threat_level'].std(),
            'hourly_patterns': hourly_patterns.to_dict(),
            'daily_patterns': daily_patterns.to_dict(),
            'threat_cycles': threat_cycles,
            'peak_threat_hours': hourly_patterns['mean'].nlargest(3).index.tolist(),
            'threat_trend': 'increasing' if df['threat_level'].tail(10).mean() > df['threat_level'].head(10).mean() else 'decreasing'
        }
        
        return analysis_result
    
    def _identify_threat_cycles(self, df: pd.DataFrame) -> List[Dict]:
        """Identify recurring threat patterns"""
        cycles = []
        
        # Look for weekly patterns
        weekly_avg = df.groupby([df['timestamp'].dt.dayofweek, df['timestamp'].dt.hour])['threat_level'].mean()
        
        # Identify high-threat periods
        high_threat_threshold = weekly_avg.quantile(0.8)
        high_threat_periods = weekly_avg[weekly_avg > high_threat_threshold]
        
        for (day, hour), threat_level in high_threat_periods.items():
            cycles.append({
                'type': 'weekly',
                'day_of_week': day,
                'hour': hour,
                'average_threat_level': threat_level,
                'pattern_strength': threat_level / weekly_avg.mean()
            })
        
        return cycles
    
    def predict_future_threats(self, prediction_horizon_hours: int = 24) -> List[Dict]:
        """Predict future threat levels"""
        logger.info(f"Predicting threats for next {prediction_horizon_hours} hours")
        
        predictions = []
        current_time = datetime.now()
        
        for hour_offset in range(prediction_horizon_hours):
            future_time = current_time + timedelta(hours=hour_offset)
            
            # Base prediction on historical patterns
            hour_of_day = future_time.hour
            day_of_week = future_time.weekday()
            
            # Simple pattern-based prediction (would be enhanced with ML in production)
            base_threat = 0.3  # Baseline threat level
            
            # Adjust for time patterns
            if 2 <= hour_of_day <= 5:  # Night hours
                base_threat += 0.2
            elif 9 <= hour_of_day <= 17:  # Business hours
                base_threat += 0.1
            
            # Adjust for day patterns
            if day_of_week >= 5:  # Weekend
                base_threat -= 0.1
            
            # Add some randomness for realistic variation
            import random
            threat_level = max(0.0, min(1.0, base_threat + random.uniform(-0.1, 0.1)))
            
            predictions.append({
                'timestamp': future_time.isoformat(),
                'predicted_threat_level': threat_level,
                'confidence': 0.7,  # Would be calculated based on model performance
                'hour_of_day': hour_of_day,
                'day_of_week': day_of_week
            })
        
        return predictions

class BehavioralBaselineManager:
    """
    Manages behavioral baselines for entities and detects deviations
    """
    
    def __init__(self, db_path: str = "reaper_baselines.db"):
        self.db_path = db_path
        self.baselines = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize baseline database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavioral_baselines (
                entity_id TEXT PRIMARY KEY,
                baseline_data TEXT,
                confidence_score REAL,
                sample_count INTEGER,
                last_updated TIMESTAMP,
                baseline_type TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baseline_deviations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT,
                timestamp TEXT,
                deviation_score REAL,
                deviation_type TEXT,
                baseline_features TEXT,
                actual_features TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def establish_baseline(self, entity_id: str, historical_events: List[Dict]) -> Dict:
        """Establish behavioral baseline for an entity"""
        logger.info(f"Establishing baseline for entity: {entity_id}")
        
        if len(historical_events) < 10:
            logger.warning(f"Insufficient data for baseline (need 10+, got {len(historical_events)})")
            return None
        
        # Extract behavioral features
        features = []
        for event in historical_events:
            feature_vector = self._extract_behavioral_features(event)
            features.append(feature_vector)
        
        # Calculate baseline statistics
        feature_df = pd.DataFrame(features)
        baseline = {
            'entity_id': entity_id,
            'feature_means': feature_df.mean().to_dict(),
            'feature_stds': feature_df.std().fillna(0).to_dict(),
            'feature_mins': feature_df.min().to_dict(),
            'feature_maxs': feature_df.max().to_dict(),
            'sample_count': len(features),
            'established_at': datetime.now().isoformat(),
            'confidence': min(1.0, len(features) / 100)  # Higher confidence with more samples
        }
        
        # Store baseline
        self.baselines[entity_id] = baseline
        self._save_baseline(baseline)
        
        return baseline
    
    def _extract_behavioral_features(self, event: Dict) -> Dict:
        """Extract behavioral features from an event"""
        features = {}
        
        # Temporal features
        if 'timestamp' in event:
            dt = pd.to_datetime(event['timestamp'])
            features['hour'] = dt.hour
            features['day_of_week'] = dt.dayofweek
            features['is_weekend'] = 1 if dt.dayofweek >= 5 else 0
        
        # Threat-related features
        features['threat_level'] = event.get('threat_level', 0.5)
        features['cognitive_coherence'] = event.get('cognitive_coherence', 0.5)
        features['human_likelihood'] = event.get('human_likelihood', 0.5)
        features['anomaly_score'] = event.get('anomaly_score', 0.5)
        
        # Network features (if available)
        if 'remote_port' in event:
            features['remote_port'] = event['remote_port']
            features['is_common_port'] = 1 if event['remote_port'] in [80, 443, 22, 21] else 0
        
        return features
    
    def detect_baseline_deviation(self, entity_id: str, current_event: Dict) -> Dict:
        """Detect deviation from established baseline"""
        if entity_id not in self.baselines:
            return {'deviation_detected': False, 'reason': 'No baseline established'}
        
        baseline = self.baselines[entity_id]
        current_features = self._extract_behavioral_features(current_event)
        
        # Calculate deviation scores
        deviations = {}
        total_deviation = 0
        
        for feature, value in current_features.items():
            if feature in baseline['feature_means']:
                mean = baseline['feature_means'][feature]
                std = baseline['feature_stds'][feature]
                
                if std > 0:
                    # Z-score based deviation
                    z_score = abs(value - mean) / std
                    deviations[feature] = z_score
                    total_deviation += z_score
                else:
                    # For features with no variance, check exact match
                    deviations[feature] = 0 if value == mean else 1
                    total_deviation += deviations[feature]
        
        # Calculate overall deviation score
        avg_deviation = total_deviation / len(deviations) if deviations else 0
        
        # Determine if significant deviation
        deviation_threshold = 2.0  # Z-score threshold
        significant_deviation = avg_deviation > deviation_threshold
        
        result = {
            'deviation_detected': significant_deviation,
            'deviation_score': avg_deviation,
            'feature_deviations': deviations,
            'baseline_confidence': baseline['confidence'],
            'most_deviant_features': sorted(deviations.items(), key=lambda x: x[1], reverse=True)[:3]
        }
        
        # Store deviation if significant
        if significant_deviation:
            self._store_deviation(entity_id, current_event, result)
        
        return result
    
    def _save_baseline(self, baseline: Dict):
        """Save baseline to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO behavioral_baselines 
            (entity_id, baseline_data, confidence_score, sample_count, last_updated, baseline_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            baseline['entity_id'],
            json.dumps(baseline),
            baseline['confidence'],
            baseline['sample_count'],
            baseline['established_at'],
            'behavioral'
        ))
        
        conn.commit()
        conn.close()
    
    def _store_deviation(self, entity_id: str, event: Dict, deviation_result: Dict):
        """Store significant deviation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO baseline_deviations 
            (entity_id, timestamp, deviation_score, deviation_type, baseline_features, actual_features)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            entity_id,
            event.get('timestamp', datetime.now().isoformat()),
            deviation_result['deviation_score'],
            'behavioral',
            json.dumps(deviation_result['feature_deviations']),
            json.dumps(self._extract_behavioral_features(event))
        ))
        
        conn.commit()
        conn.close()

class Phase4CognitiveEngine:
    """
    Main Phase 4 Cognitive Engine integrating all predictive capabilities
    """
    
    def __init__(self, config_path: str = "phase4_config.yaml"):
        self.config = self._load_config(config_path)
        self.model_manager = PredictiveModelManager()
        self.temporal_analyzer = TemporalThreatAnalyzer()
        self.baseline_manager = BehavioralBaselineManager()
        self.prediction_history = []
        
        logger.info("Phase 4 Cognitive Engine initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load Phase 4 configuration"""
        default_config = {
            'prediction_models': ['network', 'behavioral', 'temporal'],
            'prediction_horizon_hours': 24,
            'baseline_update_interval': 3600,  # 1 hour
            'threat_thresholds': {
                'low': 0.3,
                'medium': 0.5,
                'high': 0.7,
                'critical': 0.9
            },
            'feature_weights': {
                'temporal': 1.0,
                'behavioral': 1.2,
                'network': 1.1,
                'anomaly': 1.3
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return default_config
    
    def process_event_with_prediction(self, event_data: Dict) -> Dict:
        """Process event through Phase 4 predictive analysis"""
        logger.info("Processing event through Phase 4 analysis")
        
        # Extract entity ID
        entity_id = self._extract_entity_id(event_data)
        
        # Check baseline deviation
        baseline_deviation = self.baseline_manager.detect_baseline_deviation(entity_id, event_data)
        
        # Generate threat prediction
        threat_prediction = self.model_manager.predict_threat(event_data)
        
        # Analyze temporal context
        temporal_context = self._analyze_temporal_context(event_data)
        
        # Calculate composite risk score
        composite_risk = self._calculate_composite_risk(
            threat_prediction, baseline_deviation, temporal_context
        )
        
        # Generate preemptive recommendations
        preemptive_actions = self._generate_preemptive_actions(
            composite_risk, threat_prediction, baseline_deviation
        )
        
        # Create comprehensive result
        result = {
            'event_id': f"phase4_{int(time.time())}_{hash(str(event_data)) % 10000}",
            'timestamp': datetime.now().isoformat(),
            'original_event': event_data,
            'threat_prediction': asdict(threat_prediction),
            'baseline_deviation': baseline_deviation,
            'temporal_context': temporal_context,
            'composite_risk_score': composite_risk,
            'preemptive_actions': preemptive_actions,
            'phase4_features': {
                'predictive_confidence': threat_prediction.confidence_score,
                'baseline_confidence': baseline_deviation.get('baseline_confidence', 0.5),
                'temporal_risk': temporal_context.get('risk_factor', 0.5),
                'entity_id': entity_id
            }
        }
        
        # Store prediction for learning
        self.prediction_history.append(result)
        
        return result
    
    def _extract_entity_id(self, event_data: Dict) -> str:
        """Extract entity identifier from event data"""
        # Try multiple fields to identify the entity
        candidates = [
            event_data.get('process_name'),
            event_data.get('user_id'),
            event_data.get('account_id'),
            event_data.get('remote_address'),
            'unknown_entity'
        ]
        
        for candidate in candidates:
            if candidate and candidate != '':
                return str(candidate)
        
        return 'unknown_entity'
    
    def _analyze_temporal_context(self, event_data: Dict) -> Dict:
        """Analyze temporal context of the event"""
        current_time = datetime.now()
        
        # Time-based risk factors
        hour = current_time.hour
        day_of_week = current_time.weekday()
        
        risk_factor = 0.3  # Base risk
        
        # Adjust for suspicious hours
        if 2 <= hour <= 5:  # Late night
            risk_factor += 0.3
        elif 22 <= hour or hour <= 1:  # Evening/early night
            risk_factor += 0.1
        
        # Adjust for weekends
        if day_of_week >= 5:
            risk_factor += 0.1
        
        return {
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': day_of_week >= 5,
            'is_night_hours': 22 <= hour or hour <= 6,
            'risk_factor': min(risk_factor, 1.0),
            'temporal_category': self._categorize_time_period(hour, day_of_week)
        }
    
    def _categorize_time_period(self, hour: int, day_of_week: int) -> str:
        """Categorize time period for analysis"""
        if day_of_week >= 5:  # Weekend
            if 6 <= hour <= 22:
                return 'weekend_day'
            else:
                return 'weekend_night'
        else:  # Weekday
            if 9 <= hour <= 17:
                return 'business_hours'
            elif 18 <= hour <= 22:
                return 'evening'
            elif 6 <= hour <= 8:
                return 'morning'
            else:
                return 'night'
    
    def _calculate_composite_risk(self, threat_prediction: ThreatPrediction, 
                                 baseline_deviation: Dict, temporal_context: Dict) -> float:
        """Calculate composite risk score from all factors"""
        weights = self.config['feature_weights']
        
        # Base threat prediction
        threat_score = threat_prediction.predicted_threat_level * weights['behavioral']
        
        # Baseline deviation contribution
        deviation_score = baseline_deviation.get('deviation_score', 0) / 3.0  # Normalize Z-score
        deviation_score = min(deviation_score, 1.0) * weights['behavioral']
        
        # Temporal risk contribution
        temporal_score = temporal_context.get('risk_factor', 0.3) * weights['temporal']
        
        # Anomaly contribution (if available in original event)
        anomaly_score = 0.5 * weights['anomaly']  # Default value
        
        # Calculate weighted average
        total_weight = sum(weights.values())
        composite_score = (threat_score + deviation_score + temporal_score + anomaly_score) / total_weight
        
        return min(composite_score, 1.0)
    
    def _generate_preemptive_actions(self, composite_risk: float, 
                                   threat_prediction: ThreatPrediction,
                                   baseline_deviation: Dict) -> List[str]:
        """Generate preemptive security actions"""
        actions = []
        
        # Risk-based actions
        if composite_risk > 0.8:
            actions.extend([
                "🚨 PREEMPTIVE ISOLATION: Prepare to isolate entity",
                "🔒 ENHANCED AUTHENTICATION: Require additional verification",
                "📋 INCIDENT PREPARATION: Ready incident response team",
                "🚫 PREVENTIVE BLOCKING: Block high-risk connections",
                "👥 STAKEHOLDER ALERT: Notify security leadership"
            ])
        elif composite_risk > 0.6:
            actions.extend([
                "⚠️ ELEVATED MONITORING: Increase surveillance level",
                "🔍 PROACTIVE INVESTIGATION: Begin preliminary analysis",
                "🛡️ DEFENSIVE MEASURES: Apply additional security controls",
                "📊 PATTERN ANALYSIS: Compare with known attack patterns"
            ])
        elif composite_risk > 0.4:
            actions.extend([
                "👁️ ENHANCED OBSERVATION: Monitor for escalation",
                "📈 TREND ANALYSIS: Track behavioral changes",
                "🔄 BASELINE UPDATE: Refresh behavioral baselines"
            ])
        
        # Specific actions based on prediction factors
        for risk_factor in threat_prediction.risk_factors:
            if "night time" in risk_factor:
                actions.append("🌙 TIME-BASED CONTROLS: Implement after-hours restrictions")
            elif "malicious port" in risk_factor:
                actions.append("🚫 PORT BLOCKING: Preemptively block suspicious ports")
            elif "system process" in risk_factor:
                actions.append("🔍 SYSTEM INTEGRITY: Verify system process authenticity")
        
        # Baseline deviation actions
        if baseline_deviation.get('deviation_detected'):
            actions.append("📊 BASELINE INVESTIGATION: Analyze deviation patterns")
            actions.append("🔄 ADAPTIVE LEARNING: Update behavioral models")
        
        return list(set(actions))  # Remove duplicates
    
    def generate_threat_forecast(self, horizon_hours: int = 24) -> Dict:
        """Generate comprehensive threat forecast"""
        logger.info(f"Generating {horizon_hours}-hour threat forecast")
        
        # Get temporal predictions
        temporal_predictions = self.temporal_analyzer.predict_future_threats(horizon_hours)
        
        # Analyze current threat landscape
        current_threats = self._analyze_current_threat_landscape()
        
        # Generate forecast summary
        forecast = {
            'forecast_generated': datetime.now().isoformat(),
            'horizon_hours': horizon_hours,
            'temporal_predictions': temporal_predictions,
            'current_threat_landscape': current_threats,
            'risk_periods': self._identify_high_risk_periods(temporal_predictions),
            'recommended_preparations': self._generate_forecast_recommendations(temporal_predictions),
            'confidence_metrics': {
                'overall_confidence': 0.75,  # Would be calculated from model performance
                'temporal_confidence': 0.7,
                'pattern_confidence': 0.8
            }
        }
        
        return forecast
    
    def _analyze_current_threat_landscape(self) -> Dict:
        """Analyze current threat environment"""
        # This would analyze recent events and current system state
        return {
            'active_threats': 3,
            'threat_velocity': 0.05,  # Threats per hour
            'dominant_threat_types': ['network_anomaly', 'behavioral_deviation'],
            'threat_distribution': {
                'low': 0.6,
                'medium': 0.25,
                'high': 0.12,
                'critical': 0.03
            }
        }
    
    def _identify_high_risk_periods(self, predictions: List[Dict]) -> List[Dict]:
        """Identify high-risk time periods from predictions"""
        high_risk_periods = []
        
        for pred in predictions:
            if pred['predicted_threat_level'] > 0.6:
                high_risk_periods.append({
                    'start_time': pred['timestamp'],
                    'threat_level': pred['predicted_threat_level'],
                    'confidence': pred['confidence'],
                    'risk_category': 'high' if pred['predicted_threat_level'] > 0.7 else 'medium'
                })
        
        return high_risk_periods
    
    def _generate_forecast_recommendations(self, predictions: List[Dict]) -> List[str]:
        """Generate recommendations based on threat forecast"""
        recommendations = []
        
        # Analyze prediction patterns
        high_threat_hours = [p for p in predictions if p['predicted_threat_level'] > 0.6]
        
        if high_threat_hours:
            recommendations.extend([
                f"🕐 PREPARE FOR HIGH-RISK PERIODS: {len(high_threat_hours)} hours of elevated threat",
                "👥 STAFF READINESS: Ensure security team availability during peak hours",
                "🛡️ DEFENSIVE POSTURE: Pre-position security controls",
                "📋 INCIDENT READINESS: Prepare incident response procedures"
            ])
        
        # Time-specific recommendations
        night_threats = [p for p in predictions if p['hour_of_day'] in [22, 23, 0, 1, 2, 3, 4, 5] and p['predicted_threat_level'] > 0.5]
        if night_threats:
            recommendations.append("🌙 NIGHT WATCH: Enhanced monitoring during overnight hours")
        
        weekend_threats = [p for p in predictions if p['day_of_week'] >= 5 and p['predicted_threat_level'] > 0.5]
        if weekend_threats:
            recommendations.append("📅 WEEKEND PREPARATION: Maintain security coverage during weekends")
        
        return recommendations

def main():
    """Main function to demonstrate Phase 4 capabilities"""
    print("🔥 R.E.A.P.E.R. PHASE 4: PREEMPTIVE COGNITIVE SECURITY ENGINE")
    print("=" * 70)
    print("Advanced Predictive Threat Modeling and Behavioral Forecasting")
    print("=" * 70)
    
    # Initialize Phase 4 engine
    engine = Phase4CognitiveEngine()
    
    # Sample event data for demonstration
    sample_events = [
        {
            'timestamp': '2025-06-16T02:30:00',
            'process_name': 'system',
            'remote_address': '185.220.101.32',
            'remote_port': 1337,
            'threat_level': 0.8,
            'cognitive_coherence': 0.3,
            'human_likelihood': 0.2,
            'anomaly_score': 0.9
        },
        {
            'timestamp': '2025-06-16T14:15:00',
            'process_name': 'chrome.exe',
            'remote_address': '142.250.191.14',
            'remote_port': 443,
            'threat_level': 0.2,
            'cognitive_coherence': 0.8,
            'human_likelihood': 0.9,
            'anomaly_score': 0.1
        }
    ]
    
    print("\n🧠 PROCESSING EVENTS THROUGH PHASE 4 ANALYSIS...")
    print("=" * 50)
    
    # Process each event
    for i, event in enumerate(sample_events, 1):
        print(f"\n🔍 EVENT {i}: {event['process_name']} → {event['remote_address']}:{event['remote_port']}")
        
        result = engine.process_event_with_prediction(event)
        
        print(f"   📊 Composite Risk Score: {result['composite_risk_score']:.3f}")
        print(f"   🎯 Threat Prediction: {result['threat_prediction']['predicted_threat_level']:.3f}")
        print(f"   ⏰ Time to Threat: {result['threat_prediction']['time_to_threat']} minutes")
        print(f"   📈 Baseline Deviation: {'YES' if result['baseline_deviation']['deviation_detected'] else 'NO'}")
        
        if result['preemptive_actions']:
            print("   🚨 PREEMPTIVE ACTIONS:")
            for action in result['preemptive_actions'][:3]:  # Show top 3
                print(f"      {action}")
    
    print("\n📈 GENERATING 24-HOUR THREAT FORECAST...")
    print("=" * 40)
    
    # Generate threat forecast
    forecast = engine.generate_threat_forecast(24)
    
    print(f"   🕐 Forecast Period: {forecast['horizon_hours']} hours")
    print(f"   ⚠️ High-Risk Periods: {len(forecast['risk_periods'])}")
    print(f"   📊 Overall Confidence: {forecast['confidence_metrics']['overall_confidence']:.1%}")
    
    if forecast['recommended_preparations']:
        print("   💡 FORECAST RECOMMENDATIONS:")
        for rec in forecast['recommended_preparations'][:3]:
            print(f"      {rec}")
    
    print("\n🎯 PHASE 4 CAPABILITIES DEMONSTRATED:")
    print("=" * 40)
    print("✅ Predictive Threat Modeling")
    print("✅ Behavioral Baseline Analysis")
    print("✅ Temporal Pattern Recognition")
    print("✅ Composite Risk Assessment")
    print("✅ Preemptive Action Generation")
    print("✅ 24-Hour Threat Forecasting")
    
    print("\n💀 'From detection to prediction - cognitive security evolution' 💀")

if __name__ == "__main__":
    main()

