from flask import Blueprint, request, jsonify
from backend.services.chat_service import process_message

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

@chat_bp.route("/", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message")
    session_id = data.get("session_id")
    if not message or not session_id:
        return jsonify({"error": "Message and session_id are required"}), 400

    response = process_message(message, session_id)
    return jsonify(response)
