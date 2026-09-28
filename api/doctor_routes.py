from datetime import datetime, date
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.extensions import db
from backend.models.doctor import Doctor
from backend.models.doctor_availability import DoctorAvailability
from backend.models.appointment import Appointment
from backend.models.medical_note import MedicalNote
from backend.schemas.appointment_schemas import AvailabilitySlotSchema, MedicalNoteSchema
from backend.services.auth_service import token_required, role_required

doctor_bp = Blueprint("doctor_bp", __name__)

@doctor_bp.route("/availability", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_doctor_availability(current_user, token_payload):
    """
    Get configured recurring weekly availability for logged-in doctor.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    availabilities = DoctorAvailability.query.filter_by(doctor_id=doctor.id).order_by(DoctorAvailability.day_of_week).all()
    return jsonify({
        "success": True,
        "availability": [a.to_dict() for a in availabilities],
    }), 200

@doctor_bp.route("/availability", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def set_doctor_availability(current_user, token_payload):
    """
    Set or update recurring availability slots for the doctor.
    """
    try:
        doctor = current_user.doctor_profile
        if not doctor:
            return jsonify({"success": False, "error": "Doctor profile not found."}), 404

        data = request.get_json() or {}
        # Allows single slot or list of slots
        slots_input = data if isinstance(data, list) else data.get("slots", [data])

        # Clear existing or update
        if request.args.get("overwrite", "false").lower() == "true":
            DoctorAvailability.query.filter_by(doctor_id=doctor.id).delete()

        created_slots = []
        for s in slots_input:
            validated = AvailabilitySlotSchema(**s)
            start_t = datetime.strptime(validated.start_time, "%H:%M").time()
            end_t = datetime.strptime(validated.end_time, "%H:%M").time()

            avail = DoctorAvailability(
                doctor_id=doctor.id,
                day_of_week=validated.day_of_week,
                start_time=start_t,
                end_time=end_t,
                slot_duration_minutes=validated.slot_duration_minutes or 30,
                is_active=validated.is_active,
            )
            db.session.add(avail)
            created_slots.append(avail)

        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Doctor availability updated successfully.",
            "slots": [s.to_dict() for s in created_slots],
        }), 200

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@doctor_bp.route("/appointments", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_doctor_appointments(current_user, token_payload):
    """
    List appointments for doctor: today's, upcoming, and pending requests.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    filter_status = request.args.get("status")
    query = Appointment.query.filter_by(doctor_id=doctor.id)

    if filter_status:
        query = query.filter_by(status=filter_status)

    appointments = query.order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc()).all()
    today_date = date.today()

    today_appts = [a.to_dict() for a in appointments if a.appointment_date == today_date]
    pending_appts = [a.to_dict() for a in appointments if a.status == "pending"]

    return jsonify({
        "success": True,
        "total": len(appointments),
        "today_count": len(today_appts),
        "pending_count": len(pending_appts),
        "today_appointments": today_appts,
        "pending_appointments": pending_appts,
        "all_appointments": [a.to_dict() for a in appointments],
    }), 200

@doctor_bp.route("/appointment/approve", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def approve_appointment(current_user, token_payload):
    """
    Approve an appointment request.
    """
    data = request.get_json() or {}
    appointment_id = data.get("appointment_id")
    if not appointment_id:
        return jsonify({"success": False, "error": "appointment_id is required."}), 400

    appt = Appointment.query.get(appointment_id)
    if not appt:
        return jsonify({"success": False, "error": "Appointment not found."}), 404

    appt.status = "confirmed"
    db.session.commit()
    return jsonify({"success": True, "message": "Appointment approved.", "appointment": appt.to_dict()}), 200

@doctor_bp.route("/appointment/reject", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def reject_appointment(current_user, token_payload):
    """
    Reject an appointment request.
    """
    data = request.get_json() or {}
    appointment_id = data.get("appointment_id")
    reason = data.get("reason", "Doctor unavailable")
    if not appointment_id:
        return jsonify({"success": False, "error": "appointment_id is required."}), 400

    appt = Appointment.query.get(appointment_id)
    if not appt:
        return jsonify({"success": False, "error": "Appointment not found."}), 404

    appt.status = "cancelled"
    appt.cancellation_reason = reason
    db.session.commit()
    return jsonify({"success": True, "message": "Appointment rejected/cancelled.", "appointment": appt.to_dict()}), 200

@doctor_bp.route("/appointment/notes", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def add_medical_notes(current_user, token_payload):
    """
    Add or update medical diagnosis and prescription for an appointment.
    """
    try:
        data = request.get_json() or {}
        validated = MedicalNoteSchema(**data)

        doctor = current_user.doctor_profile
        appt = Appointment.query.get(validated.appointment_id)
        if not appt:
            return jsonify({"success": False, "error": "Appointment not found."}), 404

        follow_up = None
        if validated.follow_up_date:
            follow_up = datetime.strptime(validated.follow_up_date, "%Y-%m-%d").date()

        note = MedicalNote.query.filter_by(appointment_id=validated.appointment_id).first()
        if note:
            note.diagnosis = validated.diagnosis
            note.prescription = validated.prescription
            note.clinical_notes = validated.clinical_notes
            note.follow_up_date = follow_up
        else:
            note = MedicalNote(
                appointment_id=validated.appointment_id,
                doctor_id=doctor.id if doctor else appt.doctor_id,
                diagnosis=validated.diagnosis,
                prescription=validated.prescription,
                clinical_notes=validated.clinical_notes,
                follow_up_date=follow_up,
            )
            db.session.add(note)

        # Mark appointment as completed
        appt.status = "completed"
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Medical notes and prescription recorded successfully.",
            "notes": note.to_dict(),
        }), 200

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@doctor_bp.route("/appointment/<int:appointment_id>/notes", methods=["GET"])
@token_required
def get_appointment_notes(current_user, token_payload, appointment_id):
    """
    Get medical notes for an appointment.
    """
    note = MedicalNote.query.filter_by(appointment_id=appointment_id).first()
    if not note:
        return jsonify({"success": False, "error": "No medical notes found for this appointment."}), 404

    return jsonify({"success": True, "notes": note.to_dict()}), 200
