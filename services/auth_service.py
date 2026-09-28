import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from backend.config import Config
from backend.models.user import User

def generate_token(user: User) -> str:
    """
    Generate JWT access token for authenticated user.
    """
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.name if user.role else "patient",
        "full_name": user.full_name,
        "patient_id": user.patient_profile.id if user.patient_profile else None,
        "doctor_id": user.doctor_profile.id if user.doctor_profile else None,
        "exp": datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    """
    Decode and validate JWT access token.
    """
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please login again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token.")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"success": False, "error": "Authorization token is missing."}), 401

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"success": False, "error": "Invalid Authorization header format. Expected 'Bearer <token>'."}), 401

        token = parts[1]
        try:
            payload = decode_token(token)
            current_user = User.query.get(payload["user_id"])
            if not current_user or not current_user.is_active:
                return jsonify({"success": False, "error": "User account inactive or not found."}), 401
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 401
        except Exception as e:
            return jsonify({"success": False, "error": "Token validation failed."}), 401

        return f(current_user=current_user, token_payload=payload, *args, **kwargs)

    return decorated

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Assumes token_required has already run or current_user is in kwargs
            current_user = kwargs.get("current_user")
            if not current_user:
                return jsonify({"success": False, "error": "Authentication required."}), 401

            user_role = current_user.role.name if current_user.role else ""
            if user_role not in allowed_roles and "admin" not in allowed_roles:
                return jsonify({"success": False, "error": f"Access denied. Requires one of: {', '.join(allowed_roles)}"}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
