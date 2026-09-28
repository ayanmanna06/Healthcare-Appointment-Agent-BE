from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
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
    List all doctors for admin control panel.
    """
    doctors = Doctor.query.all()
    return jsonify({
        "success": True,
        "doctors": [d.to_dict() for d in doctors],
    }), 200

@admin_bp.route("/patients", methods=["GET"])
@token_required
@role_required("admin")
def admin_list_patients(current_user, token_payload):
    """
    List all patients for admin control panel.
    """
    patients = Patient.query.all()
    return jsonify({
        "success": True,
        "patients": [p.to_dict() for p in patients],
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
