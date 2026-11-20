"""
AquaSure Backend - Main Flask Application
Tamil Nadu Groundwater Quality Analytics REST API

Endpoints:
    GET  /api/overview
    GET  /api/districts
    GET  /api/district/<name>
    GET  /api/trends
    POST /api/calculate-wqi
    GET  /api/sensitivity
    GET  /api/parameters
    GET  /api/correlation
    GET  /api/health
"""

import sys
import os

# ---------------------------------------------------------------------------
# Ensure the project root (d:\collegeprojects\Aqua_sure) is on sys.path so
# that  `from backend.xxx import ...`  works regardless of CWD.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import Flask, jsonify
from flask_cors import CORS

from backend.analytics.data_loader import get_dataframe
from backend.routes.overview import overview_bp
from backend.routes.districts import districts_bp
from backend.routes.trends import trends_bp
from backend.routes.calculator import calculator_bp
from backend.routes.correlation import correlation_bp
from backend.routes.assessment import assessment_bp
from backend.routes.report import report_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes (React / frontend dev server)

    # Register blueprints
    app.register_blueprint(overview_bp)
    app.register_blueprint(districts_bp)
    app.register_blueprint(trends_bp)
    app.register_blueprint(calculator_bp)
    app.register_blueprint(correlation_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(report_bp)

    # Health-check endpoint
    @app.route("/api/health", methods=["GET"])
    def health():
        try:
            df = get_dataframe()
            return jsonify(
                {
                    "status": "ok",
                    "rows_loaded": int(len(df)),
                    "columns": list(df.columns),
                }
            )
        except Exception as exc:
            return jsonify({"status": "error", "message": str(exc)}), 500

    # Generic 404 handler
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found.", "message": str(e)}), 404

    # Generic 405 handler
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed.", "message": str(e)}), 405

    return app


# Pre-load data and warm caches at startup so every API call is instant
def _preload_data():
    try:
        import requests, threading

        df = get_dataframe()
        print(f"[AquaSure] Data loaded: {len(df):,} rows, {df.shape[1]} columns.")

        # Warm caches by calling route functions directly (no HTTP round-trip)
        def _warm():
            import time
            time.sleep(0.5)  # wait for Flask to fully start
            for endpoint in ["/api/overview", "/api/districts", "/api/trends"]:
                try:
                    r = requests.get(f"http://127.0.0.1:5000{endpoint}", timeout=60)
                    print(f"[AquaSure] Cache warmed: {endpoint} ({r.status_code})")
                except Exception as e:
                    print(f"[AquaSure] Cache warm failed for {endpoint}: {e}")

        threading.Thread(target=_warm, daemon=True).start()

    except FileNotFoundError as exc:
        print(f"[AquaSure] WARNING: {exc}")
        print("[AquaSure] API will return errors until the data pipeline is run.")


if __name__ == "__main__":
    _preload_data()
    app = create_app()
    print("[AquaSure] Starting Flask development server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
