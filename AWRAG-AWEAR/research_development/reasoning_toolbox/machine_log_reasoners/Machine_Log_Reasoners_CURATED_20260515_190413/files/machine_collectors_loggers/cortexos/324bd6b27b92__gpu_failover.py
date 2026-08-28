from flask import Blueprint, jsonify
from services.gpu_service import GPUFailover

gpu_bp = Blueprint("gpu", __name__, url_prefix="/api/gpu")

@gpu_bp.route('/failover', methods=['POST'])
def gpu_failover():
    gpu_service = GPUFailover()
    gpu_service.monitor_and_failover()
    return jsonify({"status": "GPU failover initiated."}), 200
