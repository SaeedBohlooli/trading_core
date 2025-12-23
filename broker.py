from flask import Blueprint, request, jsonify
import random
from threading import Lock
import logging
from trading_utils import date_utils
logger = logging.getLogger(__name__)
broker_bp = Blueprint("broker", __name__)
state_lock = Lock()
user_input = {}

@broker_bp.route("/api/send-request", methods=["POST"])
def send_request():
    global user_input
    data = request.json
    request_id = date_utils.time_now_yyyy_mm_dd_hh_mm_ss_as_id()
    data['api_request_id'] = request_id

    logger.info(f"Received request data: {data}")

    with state_lock:
        user_input.setdefault('requests', []).append(data)

    return jsonify({"status": "ok", "api_request_id": data['api_request_id']})


@broker_bp.route("/api/get-all-requests", methods=["GET"])
def get_all_requests():
    global user_input
    logger.info(f"Received /api/get-all-requests user_input: {user_input}")
    with state_lock:
        result = user_input.copy()
        user_input = {}
    return jsonify(result)


@broker_bp.route("/api/health", methods=["GET"])
def api_health():
    logger.info("Health check OK")
    return jsonify({"status": "ok"}), 200