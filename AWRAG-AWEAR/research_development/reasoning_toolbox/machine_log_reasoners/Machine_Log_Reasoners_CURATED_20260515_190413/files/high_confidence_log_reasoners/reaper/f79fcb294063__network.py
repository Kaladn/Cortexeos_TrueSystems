from flask import Blueprint, request, jsonify
from src.models.network import db, NetworkEvent, ProcessBaseline, AnomalyMemory
from datetime import datetime, timedelta
import json
import os
import sys

# Add parent directory to path for importing reaper modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, parent_dir)

try:
    from reaper_network_analyzer import NetworkCognitiveAnalyzer
except ImportError:
    NetworkCognitiveAnalyzer = None

network_bp = Blueprint('network', __name__)

@network_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'operational',
        'service': 'R.E.A.P.E.R. Network API',
        'timestamp': datetime.utcnow().isoformat(),
        'analyzer_available': NetworkCognitiveAnalyzer is not None
    })

@network_bp.route('/events', methods=['GET'])
def get_network_events():
    """Get network events with optional filtering"""
    try:
        # Query parameters
        limit = request.args.get('limit', 100, type=int)
        threat_level = request.args.get('threat_level')
        process_name = request.args.get('process_name')
        hours_back = request.args.get('hours_back', 24, type=int)
        
        # Build query
        query = NetworkEvent.query
        
        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        query = query.filter(NetworkEvent.created_at >= cutoff_time)
        
        # Filter by threat level
        if threat_level:
            query = query.filter(NetworkEvent.threat_classification == threat_level.upper())
        
        # Filter by process name
        if process_name:
            query = query.filter(NetworkEvent.process_name.ilike(f'%{process_name}%'))
        
        # Order and limit
        events = query.order_by(NetworkEvent.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'events': [event.to_dict() for event in events],
            'total': len(events),
            'filters': {
                'limit': limit,
                'threat_level': threat_level,
                'process_name': process_name,
                'hours_back': hours_back
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/events/stats', methods=['GET'])
def get_event_stats():
    """Get network event statistics"""
    try:
        hours_back = request.args.get('hours_back', 24, type=int)
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Total events
        total_events = NetworkEvent.query.filter(NetworkEvent.created_at >= cutoff_time).count()
        
        # Threat level distribution
        threat_stats = db.session.query(
            NetworkEvent.threat_classification,
            db.func.count(NetworkEvent.id)
        ).filter(NetworkEvent.created_at >= cutoff_time).group_by(NetworkEvent.threat_classification).all()
        
        threat_distribution = {level: count for level, count in threat_stats}
        
        # Top processes
        process_stats = db.session.query(
            NetworkEvent.process_name,
            db.func.count(NetworkEvent.id)
        ).filter(NetworkEvent.created_at >= cutoff_time).group_by(NetworkEvent.process_name).order_by(db.func.count(NetworkEvent.id).desc()).limit(10).all()
        
        top_processes = [{'process': proc, 'count': count} for proc, count in process_stats]
        
        # Average threat level
        avg_threat = db.session.query(db.func.avg(NetworkEvent.threat_level)).filter(NetworkEvent.created_at >= cutoff_time).scalar()
        
        return jsonify({
            'total_events': total_events,
            'threat_distribution': threat_distribution,
            'top_processes': top_processes,
            'average_threat_level': float(avg_threat) if avg_threat else 0.0,
            'time_range_hours': hours_back
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/events/timeline', methods=['GET'])
def get_event_timeline():
    """Get event timeline data for charts"""
    try:
        hours_back = request.args.get('hours_back', 24, type=int)
        interval_minutes = request.args.get('interval', 60, type=int)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Generate time buckets
        timeline_data = []
        current_time = cutoff_time
        end_time = datetime.utcnow()
        
        while current_time < end_time:
            bucket_end = current_time + timedelta(minutes=interval_minutes)
            
            # Count events in this time bucket
            event_count = NetworkEvent.query.filter(
                NetworkEvent.created_at >= current_time,
                NetworkEvent.created_at < bucket_end
            ).count()
            
            # Count threats in this time bucket
            threat_count = NetworkEvent.query.filter(
                NetworkEvent.created_at >= current_time,
                NetworkEvent.created_at < bucket_end,
                NetworkEvent.threat_classification.in_(['THREAT', 'CRITICAL'])
            ).count()
            
            timeline_data.append({
                'timestamp': current_time.isoformat(),
                'events': event_count,
                'threats': threat_count
            })
            
            current_time = bucket_end
        
        return jsonify({
            'timeline': timeline_data,
            'interval_minutes': interval_minutes,
            'hours_back': hours_back
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    """Get anomaly memory data"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        anomalies = AnomalyMemory.query.order_by(AnomalyMemory.last_seen.desc()).limit(limit).all()
        
        return jsonify({
            'anomalies': [anomaly.to_dict() for anomaly in anomalies],
            'total': len(anomalies)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/process/analyze', methods=['POST'])
def analyze_data():
    """Analyze uploaded data through R.E.A.P.E.R. cognitive engine"""
    try:
        if not NetworkCognitiveAnalyzer:
            return jsonify({'error': 'R.E.A.P.E.R. analyzer not available'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Initialize analyzer
        analyzer = NetworkCognitiveAnalyzer()
        
        # Process data based on type
        data_type = data.get('type', 'network')
        events = data.get('events', [])
        
        results = []
        for event_data in events:
            # Create cognitive event
            from reaper_network_analyzer import CognitiveEvent
            cognitive_event = CognitiveEvent(
                event_type=data_type,
                timestamp=event_data.get('timestamp', datetime.utcnow().isoformat()),
                data=event_data
            )
            
            # Process through analyzer
            result = analyzer.process_cognitive_event(cognitive_event)
            results.append(result)
            
            # Store in database if it's network data
            if data_type == 'network':
                network_event = NetworkEvent(
                    timestamp=result['timestamp'],
                    protocol=event_data.get('protocol'),
                    local_address=event_data.get('local_address'),
                    local_port=event_data.get('local_port'),
                    remote_address=event_data.get('remote_address'),
                    remote_port=event_data.get('remote_port'),
                    state=event_data.get('state'),
                    pid=event_data.get('pid'),
                    process_name=event_data.get('process_name'),
                    threat_level=result['threat_level'],
                    threat_classification=result['threat_classification'],
                    cognitive_coherence=result['cognitive_coherence'],
                    human_likelihood=result['human_likelihood'],
                    anomaly_score=result['anomaly_score']
                )
                db.session.add(network_event)
        
        db.session.commit()
        
        return jsonify({
            'results': results,
            'processed_count': len(results),
            'analyzer_type': 'R.E.A.P.E.R. Cognitive Engine'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@network_bp.route('/config/yaml', methods=['GET', 'POST'])
def yaml_config():
    """Handle YAML configuration management"""
    try:
        if request.method == 'GET':
            # Return available YAML configurations
            config_dir = os.path.join(parent_dir, 'configs')
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            configs = []
            for filename in os.listdir(config_dir):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    configs.append(filename)
            
            return jsonify({
                'available_configs': configs,
                'config_directory': config_dir
            })
        
        elif request.method == 'POST':
            # Save or update YAML configuration
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            config_name = data.get('name')
            config_content = data.get('content')
            
            if not config_name or not config_content:
                return jsonify({'error': 'Name and content required'}), 400
            
            # Ensure .yaml extension
            if not config_name.endswith('.yaml'):
                config_name += '.yaml'
            
            config_dir = os.path.join(parent_dir, 'configs')
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            config_path = os.path.join(config_dir, config_name)
            
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            return jsonify({
                'message': 'Configuration saved successfully',
                'config_name': config_name,
                'config_path': config_path
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/config/yaml/<config_name>', methods=['GET', 'DELETE'])
def yaml_config_file(config_name):
    """Handle specific YAML configuration file operations"""
    try:
        config_dir = os.path.join(parent_dir, 'configs')
        config_path = os.path.join(config_dir, config_name)
        
        if request.method == 'GET':
            # Return specific YAML configuration
            if not os.path.exists(config_path):
                return jsonify({'error': 'Configuration not found'}), 404
            
            with open(config_path, 'r') as f:
                content = f.read()
            
            return jsonify({
                'name': config_name,
                'content': content,
                'path': config_path
            })
        
        elif request.method == 'DELETE':
            # Delete YAML configuration
            if not os.path.exists(config_path):
                return jsonify({'error': 'Configuration not found'}), 404
            
            os.remove(config_path)
            
            return jsonify({
                'message': 'Configuration deleted successfully',
                'config_name': config_name
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/live/start', methods=['POST'])
def start_live_monitoring():
    """Start live network monitoring"""
    try:
        data = request.get_json() or {}
        interval = data.get('interval', 10)
        
        # This would integrate with the live monitoring system
        # For now, return a success response
        return jsonify({
            'message': 'Live monitoring started',
            'interval': interval,
            'status': 'active'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/live/stop', methods=['POST'])
def stop_live_monitoring():
    """Stop live network monitoring"""
    try:
        return jsonify({
            'message': 'Live monitoring stopped',
            'status': 'inactive'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/live/status', methods=['GET'])
def live_monitoring_status():
    """Get live monitoring status"""
    try:
        return jsonify({
            'status': 'inactive',  # This would be dynamic in real implementation
            'uptime': 0,
            'events_processed': 0,
            'threats_detected': 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

