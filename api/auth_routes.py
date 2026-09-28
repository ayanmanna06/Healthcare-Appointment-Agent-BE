from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.extensions import db
from backend.models.user import User
from backend.models.role import Role
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.schemas.auth_schemas import RegisterSchema, LoginSchema
from backend.services.auth_service import generate_token, token_required

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user (patient, doctor, or admin).
    """
    try:
        data = request.get_json() or {}
        validated_data = RegisterSchema(**data)

        # Check existing user
        if User.query.filter_by(email=validated_data.email).first():
            return jsonify({"success": False, "error": "User with this email already exists."}), 400

        # Find or create role
        role_name = validated_data.role.lower()
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f"Default {role_name} role")
            db.session.add(role)
            db.session.flush()

        user = User(
            email=validated_data.email,
            full_name=validated_data.full_name,
            phone=validated_data.phone,
            role_id=role.id,
        )
        user.set_password(validated_data.password)
        db.session.add(user)
        db.session.flush()

        # Create role-specific profile
        if role_name == "patient":
            patient = Patient(
                user_id=user.id,
                date_of_birth=None,
                gender=validated_data.gender,
                blood_group=validated_data.blood_group,
                address=validated_data.address,
                emergency_contact=validated_data.emergency_contact,
                medical_history=validated_data.medical_history,
            )
            db.session.add(patient)

        elif role_name == "doctor":
            doctor = Doctor(
                user_id=user.id,
                specialization_id=validated_data.specialization_id or 1,
                qualification=validated_data.qualification or "MBBS, MD",
                experience_years=validated_data.experience_years or 5,
                consultation_fee=validated_data.consultation_fee or 50.0,
                bio=validated_data.bio or "Certified Healthcare Specialist",
                room_number=validated_data.room_number or "Room 201",
            )
            db.session.add(doctor)

        db.session.commit()
        token = generate_token(user)

        return jsonify({
            "success": True,
            "message": "User registered successfully.",
            "token": token,
            "user": user.to_dict(),
        }), 201

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT token.
    """
    try:
        data = request.get_json() or {}
        validated_data = LoginSchema(**data)

        user = User.query.filter_by(email=validated_data.email).first()
        if not user or not user.check_password(validated_data.password):
            return jsonify({"success": False, "error": "Invalid email or password."}), 401

        if not user.is_active:
            return jsonify({"success": False, "error": "Account is deactivated. Please contact support."}), 403

        token = generate_token(user)
        user_info = user.to_dict()

        if user.patient_profile:
            user_info["patient"] = user.patient_profile.to_dict()
        if user.doctor_profile:
            user_info["doctor"] = user.doctor_profile.to_dict()

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "token": token,
            "user": user_info,
        }), 200

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user_profile(current_user, token_payload):
    """
    Get profile of currently logged-in user.
    """
    user_info = current_user.to_dict()
    if current_user.patient_profile:
        user_info["patient"] = current_user.patient_profile.to_dict()
    if current_user.doctor_profile:
        user_info["doctor"] = current_user.doctor_profile.to_dict()

    return jsonify({"success": True, "user": user_info}), 200

@auth_bp.route("/profile", methods=["PUT"])
@token_required
def update_profile(current_user, token_payload):
    """
    Update profile details for current user.
    """
    try:
        data = request.get_json() or {}
        if "full_name" in data:
            current_user.full_name = data["full_name"]
        if "phone" in data:
            current_user.phone = data["phone"]

        if current_user.patient_profile:
            patient = current_user.patient_profile
            for field in ["gender", "blood_group", "address", "emergency_contact", "medical_history"]:
                if field in data:
                    setattr(patient, field, data[field])

        if current_user.doctor_profile:
            doctor = current_user.doctor_profile
            for field in ["qualification", "experience_years", "consultation_fee", "bio", "room_number"]:
                if field in data:
                    setattr(doctor, field, data[field])

        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully.", "user": current_user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
