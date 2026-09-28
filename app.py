import os
import sys
import logging

# Ensure project root is in sys.path so 'backend.xxx' imports work when executed directly
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_CURRENT_DIR)
for _path in [_PARENT_DIR, _CURRENT_DIR]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.extensions import db, mail
from backend.api import auth_bp, patient_bp, doctor_bp, admin_bp, docs_bp
from backend.services.scheduler_service import init_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("HealthcareApp")

def create_app(config_class=Config):
    """
    Application factory for Healthcare Appointment Agent System.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(patient_bp, url_prefix="/api/patient")
    app.register_blueprint(doctor_bp, url_prefix="/api/doctor")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(docs_bp, url_prefix="/api/docs")

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Healthcare Appointment Agent API",
            "database": "connected"
        }), 200

    # Initialize APScheduler background jobs
    with app.app_context():
        # Auto-create tables if using SQLite or fresh db
        db.create_all()
        init_scheduler(app)

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"\n========================================================")
    print(f"[*] Healthcare Agent API running at http://127.0.0.1:{port}")
    print(f"[*] Swagger Docs available at http://127.0.0.1:{port}/api/docs")
    print(f"========================================================\n")
    app.run(host="0.0.0.0", port=port, debug=debug)

