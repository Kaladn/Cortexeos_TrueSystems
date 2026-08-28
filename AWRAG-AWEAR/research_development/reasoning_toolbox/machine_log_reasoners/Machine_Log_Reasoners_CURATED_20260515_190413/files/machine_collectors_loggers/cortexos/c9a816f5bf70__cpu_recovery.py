from flask import Blueprint, request, jsonify
from services.cpu_service import CPUCoreRecovery

cpu_bp = Blueprint("cpu", __name__, url_prefix="/api/cpu")

@cpu_bp.route('/recover', methods=['POST'])
def recover_cpu():
    data = request.json
    core_metrics = data.get("metrics", [])
    recovery_service = CPUCoreRecovery()
    recovery_service.detect_and_recover(core_metrics)
    return jsonify({"status": "CPU core recovery initiated."}), 200
