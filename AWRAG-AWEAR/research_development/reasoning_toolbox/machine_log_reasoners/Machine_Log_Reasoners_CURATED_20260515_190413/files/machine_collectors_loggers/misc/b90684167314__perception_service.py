#!/usr/bin/env python3
"""
Node 2 (i9-13900K) - Perception Service
Handles tokenization and anchor creation from any input type
"""

import sys
import json
import zmq
from pathlib import Path

# Add shared library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from wolf_engine import PerceptionLayer

print("[Node 2] Initializing Perception Service...")

# Initialize perception layer
perception = PerceptionLayer(context_window=6)

# Load config
config_path = Path(__file__).parent.parent / "configs" / "cluster_config.json"
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print(f"[Node 2] Loaded config: {config['nodes']['node2']['hostname']}")
else:
    config = {"perception": {"port": 5004}}
    print("[Node 2] Using default config")

# Setup ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.REP)
port = config.get("perception", {}).get("port", 5004)
socket.bind(f"tcp://*:{port}")

print(f"[Node 2] Perception Service running on port {port}")
print("[Node 2] Waiting for requests...")

# Main service loop
request_count = 0
total_anchors_created = 0

while True:
    try:
        # Receive request
        message = socket.recv_json()
        request_count += 1
        action = message.get("action")
        
        if action == "perceive":
            # Create anchors from input
            input_data = message.get("data")
            input_type = message.get("type", "text")
            
            anchors = perception.perceive(input_data, input_type=input_type)
            total_anchors_created += len(anchors)
            
            response = {
                "status": "ok",
                "anchors": anchors,
                "count": len(anchors)
            }
            socket.send_json(response)
            
            if request_count % 100 == 0:
                print(f"[Node 2] Processed {request_count} requests | Total anchors created: {total_anchors_created}")
        
        elif action == "health":
            # Health check
            response = {
                "status": "healthy",
                "service": "perception",
                "node": "node2",
                "uptime_requests": request_count,
                "total_anchors_created": total_anchors_created
            }
            socket.send_json(response)
        
        else:
            # Unknown action
            response = {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
            socket.send_json(response)
    
    except KeyboardInterrupt:
        print("\n[Node 2] Shutting down Perception Service...")
        break
    except Exception as e:
        print(f"[Node 2] Error: {e}")
        response = {
            "status": "error",
            "message": str(e)
        }
        socket.send_json(response)

socket.close()
context.term()
print("[Node 2] Perception Service stopped.")
