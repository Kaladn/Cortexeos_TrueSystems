#!/usr/bin/env python3
"""
Node 1 (9950X3D + RTX 4080) - Forge Memory Service
Handles all memory operations, chain formation, and pattern recognition
"""

import sys
import json
import zmq
from pathlib import Path

# Add shared library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from wolf_engine import ForgeMemory, PatternRecognitionEngine

print("[Node 1] Initializing Forge Memory Service...")

# Initialize components
forge = ForgeMemory()
pattern_engine = PatternRecognitionEngine(forge)

# Load config
config_path = Path(__file__).parent.parent / "configs" / "cluster_config.json"
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print(f"[Node 1] Loaded config: {config['nodes']['node1']['hostname']}")
else:
    config = {"forge": {"port": 5001}}
    print("[Node 1] Using default config")

# Setup ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.REP)
port = config.get("forge", {}).get("port", 5001)
socket.bind(f"tcp://*:{port}")

print(f"[Node 1] Forge Memory Service running on port {port}")
print("[Node 1] Waiting for requests...")

# Main service loop
request_count = 0

while True:
    try:
        # Receive request
        message = socket.recv_json()
        request_count += 1
        action = message.get("action")
        
        if action == "write_pulse":
            # Write anchors to Forge
            anchors = message.get("anchors", [])
            importance = message.get("importance", 1.0)
            
            forge.write_pulse(anchors, importance=importance)
            forge.build_chains()
            pattern_engine.recognize_patterns()
            
            response = {
                "status": "ok",
                "anchors_written": len(anchors),
                "total_anchors": len(forge.anchors)
            }
            socket.send_json(response)
            
            if request_count % 100 == 0:
                print(f"[Node 1] Processed {request_count} requests | Total anchors: {len(forge.anchors)}")
        
        elif action == "query":
            # Query Forge for token
            token = message.get("token")
            result = forge.query(token)
            
            response = {
                "status": "ok",
                "result": result
            }
            socket.send_json(response)
        
        elif action == "stats":
            # Get Forge statistics
            stats = forge.stats()
            stats["patterns"] = len(pattern_engine.patterns)
            stats["requests_processed"] = request_count
            
            response = {
                "status": "ok",
                "stats": stats
            }
            socket.send_json(response)
        
        elif action == "health":
            # Health check
            response = {
                "status": "healthy",
                "service": "forge_memory",
                "node": "node1",
                "uptime_requests": request_count
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
        print("\n[Node 1] Shutting down Forge Memory Service...")
        break
    except Exception as e:
        print(f"[Node 1] Error: {e}")
        response = {
            "status": "error",
            "message": str(e)
        }
        socket.send_json(response)

socket.close()
context.term()
print("[Node 1] Forge Memory Service stopped.")
