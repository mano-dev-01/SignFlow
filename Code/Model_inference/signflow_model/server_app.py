from __future__ import annotations

import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import DEFAULT_SERVER_PORT
from .service import SignFlowModelService


def create_app(model_service: SignFlowModelService | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app)

    service = model_service or SignFlowModelService()
    if service.model is None:
        service.load()
    app.config["SIGNFLOW_MODEL_SERVICE"] = service

    @app.route("/health", methods=["GET"])
    def health():
        current_service = app.config["SIGNFLOW_MODEL_SERVICE"]
        print("[SERVER] /health endpoint called")
        status = "ok" if current_service.model is not None else "model_not_loaded"
        return jsonify({"status": status, "device": str(current_service.device)})

    @app.route("/classes", methods=["GET"])
    def get_classes():
        current_service = app.config["SIGNFLOW_MODEL_SERVICE"]
        print(
            f"[SERVER] /classes endpoint called - {len(current_service.class_names)} classes"
        )
        return jsonify(
            {
                "classes": current_service.class_names,
                "count": len(current_service.class_names),
            }
        )

    @app.route("/predict", methods=["POST"])
    def predict():
        data = request.get_json(force=True)
        if data is None:
            print("[SERVER] ERROR: No JSON body in request")
            return jsonify({"error": "No JSON body"}), 400

        frames_raw = data.get("frames")
        if frames_raw is None:
            print("[SERVER] ERROR: Missing 'frames' field")
            return jsonify({"error": "Missing 'frames' field"}), 400

        result = app.config["SIGNFLOW_MODEL_SERVICE"].predict(frames_raw)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)

    return app


app = create_app()


def main():
    port = int(os.environ.get("PORT", DEFAULT_SERVER_PORT))
    print(f"[SERVER] Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
