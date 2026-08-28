from flask import Flask
from routes import gpu_failover, cpu_recovery, device_offloading, metrics, system_health

app = Flask(__name__)

# Register API blueprints
app.register_blueprint(gpu_failover.gpu_bp)
app.register_blueprint(cpu_recovery.cpu_bp)
app.register_blueprint(device_offloading.device_bp)
app.register_blueprint(metrics.metrics_bp)
app.register_blueprint(system_health.health_bp)

if __name__ == "__main__":
    app.run(debug=True)
