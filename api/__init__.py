from backend.api.auth_routes import auth_bp
from backend.api.patient_routes import patient_bp
from backend.api.doctor_routes import doctor_bp
from backend.api.admin_routes import admin_bp
from backend.api.docs_routes import docs_bp

__all__ = ["auth_bp", "patient_bp", "doctor_bp", "admin_bp", "docs_bp"]
