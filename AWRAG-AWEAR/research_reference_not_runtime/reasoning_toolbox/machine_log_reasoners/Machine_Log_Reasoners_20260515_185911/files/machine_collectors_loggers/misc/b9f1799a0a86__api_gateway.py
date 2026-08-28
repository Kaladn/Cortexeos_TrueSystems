#!/usr/bin/env python3
"""
Node 3 (7600X) - API Gateway
REST API for Wolf Engine cluster
"""

import sys
import json
import zmq
from flask import Flask, request, jsonify
from pathlib import Path

print("[Node 3] Initializing API Gateway...")

# Load config
config_path = Path(__file__).parent.parent / "configs" / "cluster_config.json"
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print(f"[Node 3] Loaded config: {config['nodes']['node3']['hostname']}")
    
    node1_ip = config["nodes"]["node1"]["ip"]
    node2_ip = config["nodes"]["node2"]["ip"]
    forge_port = config.get("forge", {}).get("port", 5001)
    perception_port = config.get("perception", {}).get("port", 5004)
else:
    print("[Node 3] WARNING: No config found, using localhost")
    node1_ip = "127.0.0.1"
    node2_ip = "127.0.0.1"
    forge_port = 5001
    perception_port = 5004

# Setup ZeroMQ connections
context = zmq.Context()

# Connect to Forge (Node 1)
forge_socket = context.socket(zmq.REQ)
forge_socket.connect(f"tcp://{node1_ip}:{forge_port}")
print(f"[Node 3] Connected to Forge at {node1_ip}:{forge_port}")

# Connect to Perception (Node 2)
perception_socket = context.socket(zmq.REQ)
perception_socket.connect(f"tcp://{node2_ip}:{perception_port}")
print(f"[Node 3] Connected to Perception at {node2_ip}:{perception_port}")

# Flask app
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check for API Gateway"""
    try:
        # Check Forge
        forge_socket.send_json({"action": "health"})
        forge_response = forge_socket.recv_json()
        
        # Check Perception
        perception_socket.send_json({"action": "health"})
        perception_response = perception_socket.recv_json()
        
        return jsonify({
            "status": "healthy",
            "service": "api_gateway",
            "node": "node3",
            "forge": forge_response,
            "perception": perception_response
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/think', methods=['POST'])
def think():
    """Main thinking endpoint"""
    try:
        data = request.json
        input_text = data.get("input")
        input_type = data.get("type", "question")
        
        if not input_text:
            return jsonify({"error": "Missing 'input' field"}), 400
        
        # Step 1: Perceive (create anchors)
        perception_socket.send_json({
            "action": "perceive",
            "data": input_text,
            "type": "text"
        })
        perception_result = perception_socket.recv_json()
        
        if perception_result["status"] != "ok":
            return jsonify({"error": "Perception failed"}), 500
        
        anchors = perception_result["anchors"]
        
        # Step 2: Write to Forge
        forge_socket.send_json({
            "action": "write_pulse",
            "anchors": anchors,
            "importance": 1.0
        })
        write_result = forge_socket.recv_json()
        
        if write_result["status"] != "ok":
            return jsonify({"error": "Forge write failed"}), 500
        
        # Step 3: Query Forge for response
        tokens = input_text.lower().split()
        if not tokens:
            return jsonify({"response": "no input."})
        
        forge_socket.send_json({
            "action": "query",
            "token": tokens[0]
        })
        query_result = forge_socket.recv_json()
        
        # Step 4: Generate Wolf-style response
        if query_result["status"] == "ok" and query_result["result"]:
            result = query_result["result"]
            resonance = result["resonance"]
            neighbors = len(result["neighbors"])
            chains = len(result["chains"])
            response_text = f"resonance: {resonance:.1f}. {neighbors} neighbors. {chains} chains. works."
        else:
            response_text = "no data."
        
        return jsonify({
            "response": response_text,
            "anchors_created": len(anchors),
            "total_anchors": write_result.get("total_anchors", 0)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Get Forge statistics"""
    try:
        forge_socket.send_json({"action": "stats"})
        stats_result = forge_socket.recv_json()
        
        if stats_result["status"] == "ok":
            return jsonify(stats_result["stats"])
        else:
            return jsonify({"error": "Stats retrieval failed"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/query/<token>', methods=['GET'])
def query_token(token):
    """Query Forge for specific token"""
    try:
        forge_socket.send_json({
            "action": "query",
            "token": token
        })
        query_result = forge_socket.recv_json()
        
        if query_result["status"] == "ok":
            return jsonify(query_result["result"])
        else:
            return jsonify({"error": "Query failed"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def dashboard():
    """Serve monitoring dashboard"""
    from flask import send_file
    dashboard_path = Path(__file__).parent / "dashboard.html"
    return send_file(dashboard_path)

if __name__ == '__main__':
    port = config.get("api", {}).get("port", 5000) if config_path.exists() else 5000
    print(f"[Node 3] API Gateway running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
