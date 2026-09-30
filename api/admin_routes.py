import os
import json
from datetime import datetime, date, timedelta, time
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from backend.extensions import db
from backend.models.user import User
from backend.models.role import Role
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.doctor_availability import DoctorAvailability
from backend.models.specialization import Specialization
from backend.models.appointment import Appointment
from backend.models.symptom import Symptom
from backend.models.agent_decision import AgentDecision
from backend.services.auth_service import token_required, role_required

admin_bp = Blueprint("admin_bp", __name__)

@admin_bp.route("/analytics", methods=["GET"])
@token_required
@role_required("admin")
def get_analytics(current_user, token_payload):
    """
    Get comprehensive analytics for admin dashboard:
    - Total Patients, Total Doctors, Total Appointments
    - Appointments per day (last 14 days)
    - Most requested specializations
    - Appointment statuses breakdown
    - Agent decisions count & average confidence score
    """
    try:
        total_patients = Patient.query.count()
        total_doctors = Doctor.query.count()
        total_appointments = Appointment.query.count()
        total_symptoms_processed = Symptom.query.count()
        total_decisions = AgentDecision.query.count()

        # Appointments per day (past 14 days)
        today = date.today()
        start_14 = today - timedelta(days=13)

        appts_per_day_data = []
        for i in range(14):
            cur_d = start_14 + timedelta(days=i)
            count = Appointment.query.filter(Appointment.appointment_date == cur_d).count()
            appts_per_day_data.append({
                "date": cur_d.strftime("%b %d"),
                "count": count
            })

        # Specialization breakdown (from booked appointments through doctor)
        spec_counts = (
            db.session.query(Specialization.name, func.count(Doctor.id))
            .join(Doctor, Doctor.specialization_id == Specialization.id)
            .group_by(Specialization.name)
            .all()
        )
        specialization_distribution = [{"specialization": name, "count": count} for name, count in spec_counts]

        # Most requested specializations from AI Symptom analysis
        symptom_spec_counts = (
            db.session.query(Specialization.name, func.count(Symptom.id))
            .join(Symptom, Symptom.detected_specialization_id == Specialization.id)
            .group_by(Specialization.name)
            .order_by(func.count(Symptom.id).desc())
            .all()
        )
        symptom_distribution = [{"specialization": name, "count": count} for name, count in symptom_spec_counts]

        # Status breakdown
        statuses = ["confirmed", "completed", "cancelled", "pending"]
        status_breakdown = {}
        for st in statuses:
            status_breakdown[st] = Appointment.query.filter_by(status=st).count()

        # Average rating
        avg_rating = db.session.query(func.avg(Doctor.rating)).scalar() or 4.8
        avg_confidence = db.session.query(func.avg(Symptom.confidence_score)).scalar() or 0.88

        return jsonify({
            "success": True,
            "metrics": {
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_appointments": total_appointments,
                "total_symptoms_processed": total_symptoms_processed,
                "total_decisions": total_decisions,
                "average_doctor_rating": round(float(avg_rating), 2),
                "average_ai_confidence": round(float(avg_confidence), 2),
            },
            "appointments_per_day": appts_per_day_data,
            "specialization_distribution": specialization_distribution,
            "symptom_distribution": symptom_distribution,
            "status_breakdown": status_breakdown,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/doctors", methods=["GET"])
@token_required
@role_required("admin")
def admin_list_doctors(current_user, token_payload):
    """
    List all doctors for admin control panel with today's assigned and total patient counts.
    """
    today = date.today()
    doctors = Doctor.query.all()
    results = []
    for d in doctors:
        d_dict = d.to_dict()
        d_dict["today_patients_count"] = Appointment.query.filter(
            Appointment.doctor_id == d.id,
            Appointment.appointment_date == today,
            Appointment.status.in_(["confirmed", "completed", "pending"])
        ).count()
        d_dict["total_patients_count"] = Appointment.query.filter(
            Appointment.doctor_id == d.id
        ).count()
        results.append(d_dict)

    return jsonify({
        "success": True,
        "doctors": results,
    }), 200

@admin_bp.route("/doctors/<int:doctor_id>/history", methods=["GET"])
@token_required
@role_required("admin")
def admin_doctor_patient_history(current_user, token_payload, doctor_id):
    """
    Get complete patient history, consultations, and medical records for a specific doctor.
    """
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify({"success": False, "error": "Doctor not found."}), 404

    today = date.today()
    appts = Appointment.query.filter_by(doctor_id=doctor_id).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()

    appt_list = [a.to_dict() for a in appts]

    today_count = sum(1 for a in appts if a.appointment_date == today and a.status in ["confirmed", "completed", "pending"])
    completed_count = sum(1 for a in appts if a.status == "completed")
    upcoming_count = sum(1 for a in appts if a.appointment_date >= today and a.status in ["confirmed", "pending"])
    cancelled_count = sum(1 for a in appts if a.status == "cancelled")

    return jsonify({
        "success": True,
        "doctor": doctor.to_dict(),
        "metrics": {
            "today_patients_count": today_count,
            "total_patients_count": len(appts),
            "completed_count": completed_count,
            "upcoming_count": upcoming_count,
            "cancelled_count": cancelled_count,
        },
        "appointments": appt_list,
    }), 200

@admin_bp.route("/doctors", methods=["POST"])
@token_required
@role_required("admin")
def admin_create_doctor(current_user, token_payload):
    """
    Onboard and create a new doctor in the hospital network.
    """
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        full_name = data.get("full_name", "").strip()
        specialization_id = data.get("specialization_id")
        qualification = data.get("qualification", "MBBS, MD").strip()
        experience_years = int(data.get("experience_years", 5))
        consultation_fee = float(data.get("consultation_fee", 75.0))
        room_number = data.get("room_number", "Consultation Suite 101").strip()
        phone = data.get("phone", "").strip()
        bio = data.get("bio", "").strip()
        password = data.get("password", "Doctor@123").strip()

        if not email or not full_name or not specialization_id:
            return jsonify({"success": False, "error": "Full name, email, and specialization are required."}), 400

        # Check existing user
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "error": f"An account with email '{email}' already exists."}), 409

        spec = Specialization.query.get(specialization_id)
        if not spec:
            return jsonify({"success": False, "error": "Invalid specialization selected."}), 400

        doctor_role = Role.query.filter_by(name="doctor").first()
        if not doctor_role:
            return jsonify({"success": False, "error": "Doctor role not found in system."}), 500

        # Create user
        user = User(
            email=email,
            full_name=full_name,
            phone=phone or None,
            role_id=doctor_role.id,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Create doctor profile
        doctor = Doctor(
            user_id=user.id,
            specialization_id=spec.id,
            qualification=qualification,
            experience_years=experience_years,
            rating=5.0,
            consultation_fee=consultation_fee,
            bio=bio,
            room_number=room_number,
        )
        db.session.add(doctor)
        db.session.flush()

        # Populate standard weekly shifts (Mon-Fri 09:00 - 17:00) so slots are automatically bookable
        for day in range(5):  # 0=Monday through 4=Friday
            avail = DoctorAvailability(
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
                slot_duration_minutes=30,
                is_active=True,
            )
            db.session.add(avail)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Dr. {full_name} has been successfully onboarded to {spec.name}.",
            "doctor": doctor.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/doctors/<int:doctor_id>", methods=["PUT"])
@token_required
@role_required("admin")
def admin_update_doctor(current_user, token_payload, doctor_id):
    """
    Update an existing doctor's profile and hospital settings.
    """
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({"success": False, "error": "Doctor not found."}), 404

        data = request.get_json() or {}

        if "full_name" in data and doctor.user:
            doctor.user.full_name = data["full_name"].strip()
        if "phone" in data and doctor.user:
            doctor.user.phone = data["phone"].strip() or None
        if "email" in data and doctor.user:
            new_email = data["email"].strip().lower()
            if new_email != doctor.user.email:
                existing = User.query.filter_by(email=new_email).first()
                if existing:
                    return jsonify({"success": False, "error": "Email is already taken by another account."}), 409
                doctor.user.email = new_email

        if "specialization_id" in data:
            spec = Specialization.query.get(data["specialization_id"])
            if spec:
                doctor.specialization_id = spec.id

        if "qualification" in data:
            doctor.qualification = data["qualification"].strip()
        if "experience_years" in data:
            doctor.experience_years = int(data["experience_years"])
        if "consultation_fee" in data:
            doctor.consultation_fee = float(data["consultation_fee"])
        if "room_number" in data:
            doctor.room_number = data["room_number"].strip()
        if "bio" in data:
            doctor.bio = data["bio"].strip()
        if "rating" in data:
            doctor.rating = float(data["rating"])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Dr. {doctor.user.full_name if doctor.user else 'Doctor'} updated successfully.",
            "doctor": doctor.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/doctors/<int:doctor_id>/status", methods=["PUT"])
@token_required
@role_required("admin")
def admin_toggle_doctor_status(current_user, token_payload, doctor_id):
    """
    Toggle doctor's active/inactive status in hospital roster.
    """
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({"success": False, "error": "Doctor not found."}), 404

        if doctor.user:
            doctor.user.is_active = not doctor.user.is_active
            db.session.commit()
            status_str = "Active" if doctor.user.is_active else "Inactive"
            return jsonify({
                "success": True,
                "is_active": doctor.user.is_active,
                "message": f"Dr. {doctor.user.full_name} is now marked as {status_str}.",
            }), 200
        else:
            return jsonify({"success": False, "error": "User account not linked."}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/doctors/<int:doctor_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def admin_delete_doctor(current_user, token_payload, doctor_id):
    """
    Remove a doctor and their credentials from the system.
    """
    try:
        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            return jsonify({"success": False, "error": "Doctor not found."}), 404

        name = doctor.user.full_name if doctor.user else f"Doctor #{doctor.id}"
        # Delete user which cascades to doctor profile and availabilities
        if doctor.user:
            db.session.delete(doctor.user)
        else:
            db.session.delete(doctor)

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Dr. {name} has been removed from the hospital system.",
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/patients", methods=["GET"])
@token_required
@role_required("admin")
def admin_list_patients(current_user, token_payload):
    """
    List all patients for admin control panel with appointment counts and summary metrics.
    """
    today = date.today()
    patients = Patient.query.all()
    results = []

    total_appts_across_all = 0
    today_patients_count = 0
    active_count = 0
    inactive_count = 0

    for p in patients:
        p_dict = p.to_dict()
        appts = Appointment.query.filter_by(patient_id=p.id).all()
        total_appts = len(appts)
        total_appts_across_all += total_appts

        has_today = any(a.appointment_date == today and a.status in ["confirmed", "completed", "pending"] for a in appts)
        if has_today:
            today_patients_count += 1

        upcoming_count = sum(1 for a in appts if a.appointment_date >= today and a.status in ["confirmed", "pending"])
        completed_count = sum(1 for a in appts if a.status == "completed")
        cancelled_count = sum(1 for a in appts if a.status == "cancelled")

        latest_appt = max((a.appointment_date for a in appts), default=None)

        if p.user and p.user.is_active:
            active_count += 1
        else:
            inactive_count += 1

        p_dict["total_appointments"] = total_appts
        p_dict["upcoming_appointments"] = upcoming_count
        p_dict["completed_appointments"] = completed_count
        p_dict["cancelled_appointments"] = cancelled_count
        p_dict["has_today_appointment"] = has_today
        p_dict["latest_appointment_date"] = latest_appt.isoformat() if latest_appt else None
        results.append(p_dict)

    return jsonify({
        "success": True,
        "metrics": {
            "total_patients": len(patients),
            "active_patients": active_count,
            "inactive_patients": inactive_count,
            "today_patients": today_patients_count,
            "total_appointments": total_appts_across_all,
        },
        "patients": results,
    }), 200

@admin_bp.route("/patients", methods=["POST"])
@token_required
@role_required("admin")
def admin_create_patient(current_user, token_payload):
    """
    Onboard and create a new patient in the hospital network.
    """
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        full_name = data.get("full_name", "").strip()
        phone = data.get("phone", "").strip()
        password = data.get("password", "Patient@123").strip()
        date_of_birth_str = data.get("date_of_birth")
        gender = data.get("gender", "").strip()
        blood_group = data.get("blood_group", "").strip()
        address = data.get("address", "").strip()
        emergency_contact = data.get("emergency_contact", "").strip()
        medical_history = data.get("medical_history", "").strip()

        if not email or not full_name:
            return jsonify({"success": False, "error": "Patient full name and email are required."}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "error": f"An account with email '{email}' already exists."}), 409

        patient_role = Role.query.filter_by(name="patient").first()
        if not patient_role:
            return jsonify({"success": False, "error": "Patient role not found in system."}), 500

        dob = None
        if date_of_birth_str:
            try:
                dob = date.fromisoformat(date_of_birth_str)
            except Exception:
                pass

        user = User(
            email=email,
            full_name=full_name,
            phone=phone or None,
            role_id=patient_role.id,
            is_active=True,
        )
        user.set_password(password or "Patient@123")
        db.session.add(user)
        db.session.flush()

        patient = Patient(
            user_id=user.id,
            date_of_birth=dob,
            gender=gender or None,
            blood_group=blood_group or None,
            address=address or None,
            emergency_contact=emergency_contact or None,
            medical_history=medical_history or None,
        )
        db.session.add(patient)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Patient '{full_name}' successfully onboarded.",
            "patient": patient.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/patients/<int:patient_id>", methods=["PUT"])
@token_required
@role_required("admin")
def admin_update_patient(current_user, token_payload, patient_id):
    """
    Update patient profile and demographic records.
    """
    try:
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404

        data = request.get_json() or {}

        if "full_name" in data and patient.user:
            patient.user.full_name = data["full_name"].strip()
        if "phone" in data and patient.user:
            patient.user.phone = data["phone"].strip() or None
        if "email" in data and patient.user:
            new_email = data["email"].strip().lower()
            if new_email != patient.user.email:
                existing = User.query.filter_by(email=new_email).first()
                if existing:
                    return jsonify({"success": False, "error": "Email is already taken by another account."}), 409
                patient.user.email = new_email

        if "date_of_birth" in data:
            dob_str = data["date_of_birth"]
            if dob_str:
                try:
                    patient.date_of_birth = date.fromisoformat(dob_str)
                except Exception:
                    pass
            else:
                patient.date_of_birth = None

        if "gender" in data:
            patient.gender = data["gender"].strip() or None
        if "blood_group" in data:
            patient.blood_group = data["blood_group"].strip() or None
        if "address" in data:
            patient.address = data["address"].strip() or None
        if "emergency_contact" in data:
            patient.emergency_contact = data["emergency_contact"].strip() or None
        if "medical_history" in data:
            patient.medical_history = data["medical_history"].strip() or None

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Patient profile for '{patient.user.full_name if patient.user else 'Patient'}' updated successfully.",
            "patient": patient.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/patients/<int:patient_id>/status", methods=["PUT"])
@token_required
@role_required("admin")
def admin_toggle_patient_status(current_user, token_payload, patient_id):
    """
    Toggle patient active/inactive status.
    """
    try:
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404

        if patient.user:
            patient.user.is_active = not patient.user.is_active
            db.session.commit()
            status_str = "Active" if patient.user.is_active else "Inactive"
            return jsonify({
                "success": True,
                "is_active": patient.user.is_active,
                "message": f"Patient {patient.user.full_name} is now marked as {status_str}.",
            }), 200
        else:
            return jsonify({"success": False, "error": "User account not linked."}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/patients/<int:patient_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def admin_delete_patient(current_user, token_payload, patient_id):
    """
    Remove patient and associated account from system.
    """
    try:
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404

        name = patient.user.full_name if patient.user else f"Patient #{patient.id}"
        if patient.user:
            db.session.delete(patient.user)
        else:
            db.session.delete(patient)

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Patient '{name}' has been successfully removed.",
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/patients/<int:patient_id>/history", methods=["GET"])
@token_required
@role_required("admin")
def admin_patient_history(current_user, token_payload, patient_id):
    """
    Get full appointment history, clinical diagnoses, prescriptions, and symptoms for a patient.
    """
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"success": False, "error": "Patient not found."}), 404

    today = date.today()
    appts = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()
    symptoms = Symptom.query.filter_by(patient_id=patient_id).order_by(Symptom.created_at.desc()).all()

    appt_list = [a.to_dict() for a in appts]
    symptom_list = [s.to_dict() for s in symptoms]

    today_count = sum(1 for a in appts if a.appointment_date == today and a.status in ["confirmed", "completed", "pending"])
    completed_count = sum(1 for a in appts if a.status == "completed")
    upcoming_count = sum(1 for a in appts if a.appointment_date >= today and a.status in ["confirmed", "pending"])
    cancelled_count = sum(1 for a in appts if a.status == "cancelled")

    return jsonify({
        "success": True,
        "patient": patient.to_dict(),
        "metrics": {
            "total_appointments": len(appts),
            "today_count": today_count,
            "upcoming_count": upcoming_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "total_symptoms_reported": len(symptoms),
        },
        "appointments": appt_list,
        "symptoms": symptom_list,
    }), 200

@admin_bp.route("/appointments", methods=["GET"])
@token_required
@role_required("admin")
def admin_list_appointments(current_user, token_payload):
    """
    Monitor all appointments across the system.
    """
    appts = Appointment.query.order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).limit(100).all()
    return jsonify({
        "success": True,
        "appointments": [a.to_dict() for a in appts],
    }), 200

@admin_bp.route("/decisions", methods=["GET"])
@token_required
@role_required("admin")
def admin_list_decisions(current_user, token_payload):
    """
    View AI agent decisions audit trail.
    """
    decisions = AgentDecision.query.order_by(AgentDecision.created_at.desc()).limit(50).all()
    return jsonify({
        "success": True,
        "decisions": [d.to_dict() for d in decisions],
    }), 200

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "system_settings.json")

DEFAULT_SETTINGS = {
    "practice_name": "HealthAgent Specialist Medical Network",
    "support_helpline": "+1-800-555-0199",
    "support_email": "support@healthagent.ai",
    "default_slot_duration": 30,
    "max_advance_booking_days": 14,
    "cancellation_grace_hours": 2,
    "ai_auto_booking": True,
    "ai_confidence_threshold": 75,
    "emergency_flagging": True,
    "email_notifications": True,
    "sms_notifications": False,
}

def load_system_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                merged = {**DEFAULT_SETTINGS, **saved}
                return merged
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_system_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

@admin_bp.route("/settings", methods=["GET"])
@token_required
@role_required("admin")
def admin_get_settings(current_user, token_payload):
    """
    Get clinical practice policies and AI decision engine settings.
    """
    settings = load_system_settings()
    return jsonify({"success": True, "settings": settings}), 200

@admin_bp.route("/settings", methods=["PUT"])
@token_required
@role_required("admin")
def admin_update_settings(current_user, token_payload):
    """
    Update clinical practice policies and AI decision engine settings.
    """
    try:
        data = request.get_json() or {}
        current = load_system_settings()
        for k, v in data.items():
            if k in current:
                current[k] = v
        save_system_settings(current)
        return jsonify({"success": True, "message": "System settings updated successfully.", "settings": current}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

