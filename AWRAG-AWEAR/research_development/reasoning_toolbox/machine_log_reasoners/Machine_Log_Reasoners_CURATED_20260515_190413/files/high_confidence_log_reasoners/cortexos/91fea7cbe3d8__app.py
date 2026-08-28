from flask import Flask, render_template, jsonify
import datetime

app = Flask(__name__)

# --- Simulated Agent Data ---
SIMULATED_AGENTS_DATA = {
    "perimeter_defense": {"status": "Active", "threats_detected": 125, "rules_active": 5832},
    "endpoint_guardian": {"status": "Active", "anomalies_found": 32, "devices_monitored": 1500},
    "deception_commander": {"status": "Active", "honeypots_deployed": 75, "attackers_sandboxed": 12},
    "forensic_archiver": {"status": "Active", "logs_archived_gb": 512, "reports_generated": 45},
    "secure_communications": {"status": "Active", "encrypted_channels": 256, "auth_failures": 3},
    "threat_hunting_overseer": {"status": "Standby", "dark_web_alerts": 5, "profiles_updated": 150},
    "financial_decoy": {"status": "Active", "bait_data_accessed": 8, "decoy_ledgers_active": 20},
    "binary_symbolic_lexicon": {"status": "Active", "patterns_identified": 1280, "lexicon_size_mb": 2048}
}

SIMULATED_THREAT_FEED = [
    {"timestamp": str(datetime.datetime.now() - datetime.timedelta(minutes=2)), "source": "Perimeter Defense", "severity": "High", "description": "Multiple failed login attempts from IP 192.168.1.100"},
    {"timestamp": str(datetime.datetime.now() - datetime.timedelta(minutes=5)), "source": "Endpoint Guardian", "severity": "Medium", "description": "Unusual process activity detected on endpoint 'Workstation-05'"},
    {"timestamp": str(datetime.datetime.now() - datetime.timedelta(minutes=10)), "source": "Deception Commander", "severity": "Low", "description": "Honeypot 'SSH-Decoy-3' accessed by 10.0.0.5"},
    {"timestamp": str(datetime.datetime.now() - datetime.timedelta(minutes=15)), "source": "Threat Hunting Overseer", "severity": "Informational", "description": "New chatter detected on dark web forum regarding 'QuantumPulsar' exploit."}
]

SIMULATED_GLOBAL_THREATS = [
    {"country_code": "US", "latitude": 38.9637, "longitude": -95.7129, "threat_level": "High", "active_attacks": 5},
    {"country_code": "CN", "latitude": 35.8617, "longitude": 104.1954, "threat_level": "Medium", "active_attacks": 3},
    {"country_code": "RU", "latitude": 61.5240, "longitude": 105.3188, "threat_level": "Medium", "active_attacks": 2},
    {"country_code": "GB", "latitude": 55.3781, "longitude": -3.4360, "threat_level": "Low", "active_attacks": 1},
    {"country_code": "DE", "latitude": 51.1657, "longitude": 10.4515, "threat_level": "Low", "active_attacks": 1}
]

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', agents=SIMULATED_AGENTS_DATA, current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))

@app.route('/api/agent_status')
def agent_status():
    """API endpoint to get status of all agents."""
    return jsonify(SIMULATED_AGENTS_DATA)

@app.route('/api/threat_feed')
def threat_feed():
    """API endpoint for the live threat feed."""
    # In a real app, this would fetch new threats
    return jsonify(SIMULATED_THREAT_FEED)

@app.route('/api/global_threat_map')
def global_threat_map_data():
    """API endpoint for global threat map data."""
    return jsonify(SIMULATED_GLOBAL_THREATS)

@app.route('/api/deception_commander/deploy_honeypot', methods=['POST'])
def deploy_honeypot():
    """Simulates deploying a honeypot via Deception Commander."""
    # In a real app, this would trigger the Deception Commander Agent
    SIMULATED_AGENTS_DATA["deception_commander"]["honeypots_deployed"] += 1
    return jsonify({"status": "success", "message": "New honeypot deployment initiated.", "honeypots_active": SIMULATED_AGENTS_DATA["deception_commander"]["honeypots_deployed"]})

@app.route('/api/counter_offensive', methods=['POST'])
def trigger_counter_offensive():
    """Simulates triggering a counter-offensive."""
    # In a real app, this would initiate a complex counter-offensive strategy
    return jsonify({"status": "success", "message": "Counter-offensive 'QuantumShield Protocol Alpha' activated."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

