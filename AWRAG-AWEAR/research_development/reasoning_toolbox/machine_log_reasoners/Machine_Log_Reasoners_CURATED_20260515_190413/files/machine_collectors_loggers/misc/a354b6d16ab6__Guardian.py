import os
import threading
import queue
import logging
import time
from flask import Flask, render_template, jsonify
from werkzeug.utils import secure_filename

# --- Global Variables ---
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For UI messages
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Task queue and threading
priority_queue = queue.PriorityQueue()
shutdown_event = threading.Event()

# Active module tracking
modules = {
    "security": False,
    "citations": False
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Flask UI ---
@app.route('/')
def index():
    """Main control panel."""
    return '''
    <html>
        <head><title>Guardian Control Panel</title></head>
        <body>
            <h1>Guardian Control Panel</h1>
            <p>Click to start or stop specific modules.</p>

            <button onclick="toggleModule('security')">Toggle Security</button>
            <button onclick="toggleModule('citations')">Toggle Citations</button>

            <h2>Status</h2>
            <div id="status">Loading...</div>

            <script>
                function toggleModule(module) {
                    fetch('/toggle/' + module)
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status').innerHTML = data.status;
                        });
                }

                function updateStatus() {
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status').innerHTML = data.status;
                        });
                }
                
                setInterval(updateStatus, 3000);
                updateStatus();
            </script>
        </body>
    </html>
    '''

@app.route('/toggle/<module>')
def toggle_module(module):
    """Start or stop a specific module."""
    if module not in modules:
        return jsonify({"status": f"Invalid module: {module}"})

    modules[module] = not modules[module]
    return jsonify({"status": f"{module.capitalize()} is {'ON' if modules[module] else 'OFF'}"})

@app.route('/status')
def status():
    """Return the current module statuses."""
    return jsonify({"status": f"Security: {'ON' if modules['security'] else 'OFF'}, Citations: {'ON' if modules['citations'] else 'OFF'}"})

# --- Worker Threads (Idle until triggered) ---
def security_worker():
    while not shutdown_event.is_set():
        if modules["security"]:
            logging.info("Running Security Module...")
        time.sleep(5)  # Simulate processing

def citations_worker():
    while not shutdown_event.is_set():
        if modules["citations"]:
            logging.info("Running Citation Processing...")
        time.sleep(5)  # Simulate processing

# --- Start Idle Workers ---
security_thread = threading.Thread(target=security_worker, daemon=True)
citations_thread = threading.Thread(target=citations_worker, daemon=True)
security_thread.start()
citations_thread.start()

if __name__ == '__main__':
    logging.info("Starting Guardian Control Panel...")
    app.run(debug=True)
