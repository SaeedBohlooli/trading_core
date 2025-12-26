import logging
import random
from trading_utils import date_utils
from pprint import pprint
"""
general_flask_app.py
A portfolio-aware Flask Request Broker for Trading Engine control.
"""

import argparse

from flask import Flask, request, jsonify
from threading import Lock
from flask_cors import CORS

# Import your config loader
from trading_core.config_manager import ConfigManager
from trading_core.logging_manager import LoggingManager   # <<<<<< USE YOUR LOG MANAGER

# ===================================================================
# GLOBAL STATE (protected by lock because Flask is multi-threaded)
# ===================================================================

app = Flask(__name__)

# Shared application config/state

CORS(app)  # This allows all origins

# Lock because Flask may handle multiple requests at the same time
state_lock = Lock()

user_input = {}

@app.route("/api/send-request", methods=["POST"])
def send_request():
    global user_input
    data = request.json
    request_id = date_utils.time_now_yyyy_mm_dd_hh_mm_ss_as_id()
    data['api_request_id'] = request_id

    logger.info(f"Received request data: \n{pprint(data)}")

    with state_lock:
        user_input.setdefault('requests', []).append(data)

    return jsonify({"status": "ok", "api_request_id": data['api_request_id']})


@app.route("/api/get-all-requests", methods=["GET"])
def get_application_state():
    global user_input
    with state_lock:
        for_return = user_input.copy()
        user_input = {}
        return jsonify(for_return)



@app.route("/api/requests/clear", methods=["POST"])
def api_clear_requests():
    global user_input
    """
    Optional endpoint for maintenance.

    Body example:
      { "keep_status": ["pending", "processing"] }

    Everything not in keep_status will be removed.
    Default: keeps only "pending" and "processing" and drops "done"/"error".
    """
    data = request.get_json(force=True, silent=True) or {}

    with state_lock:
       user_input = []

    return jsonify({
        "status": "ok"
    }), 200


@app.route("/api/health", methods=["GET"])
def api_health():
    logger.info("Health check OK")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":

    # ----------------------------------------------
    # Parse portfolio_id from command line
    # ----------------------------------------------
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-id", required=False)
    args = parser.parse_args()

    portfolio_id = args.portfolio_id
    if not portfolio_id:
        print("Please specify a portfolio id like --portfolio-id=p100")
        exit(1)

    # ----------------------------------------------
    # Load config YAML for this portfolio
    # ----------------------------------------------
    app_config = ConfigManager.load(portfolio_id)
    api_service_cfg = app_config["api_service"]

    logger = LoggingManager.setup(
        log_dir=f'../../portfolios/{portfolio_id}/logs/flask',
        portfolio_id=portfolio_id,
        logging_level=logging.INFO,
        # alias=f"flask"
    )

    logger.info("===========================================")
    logger.info(f"Starting api_service API for portfolio {portfolio_id}")
    logger.info(f"Config Loaded: {api_service_cfg}")
    logger.info("===========================================")


    app.run(
        host=api_service_cfg.get("host", "0.0.0.0"),
        port=api_service_cfg.get("port", 2222),
        debug=False,
        use_reloader=False
    )
