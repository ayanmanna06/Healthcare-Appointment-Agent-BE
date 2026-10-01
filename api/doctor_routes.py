import calendar
from datetime import datetime, date, time, timedelta
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.extensions import db
from backend.models.doctor import Doctor
from backend.models.doctor_availability import DoctorAvailability
from backend.models.doctor_date_override import DoctorDateOverride
from backend.models.appointment import Appointment
from backend.models.medical_note import MedicalNote
from backend.models.patient import Patient
from backend.models.patient_referral import PatientReferral
from backend.models.notification import Notification
from backend.schemas.appointment_schemas import AvailabilitySlotSchema, MedicalNoteSchema
from backend.services.auth_service import token_required, role_required

doctor_bp = Blueprint("doctor_bp", __name__)

@doctor_bp.route("/availability", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_doctor_availability(current_user, token_payload):
    """
    Get configured recurring weekly availability and upcoming overrides for logged-in doctor.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    availabilities = DoctorAvailability.query.filter_by(doctor_id=doctor.id).order_by(DoctorAvailability.day_of_week, DoctorAvailability.start_time).all()
    
    grouped = {}
    for a in availabilities:
        if a.day_of_week not in grouped:
            grouped[a.day_of_week] = []
        grouped[a.day_of_week].append(a.to_dict())

    weekly_schedule = []
    for dow in range(7):
        shifts = grouped.get(dow, [])
        weekly_schedule.append({
            "day_of_week": dow,
            "day_name": day_names[dow],
            "is_active": len(shifts) > 0 and any(s["is_active"] for s in shifts),
            "shifts": shifts,
            "slot_duration_minutes": shifts[0]["slot_duration_minutes"] if shifts else 30,
        })

    # Upcoming date overrides
    today = date.today()
    overrides = DoctorDateOverride.query.filter(
        DoctorDateOverride.doctor_id == doctor.id,
        DoctorDateOverride.override_date >= today
    ).order_by(DoctorDateOverride.override_date.asc()).limit(30).all()

    return jsonify({
        "success": True,
        "availability": [a.to_dict() for a in availabilities],
        "weekly_schedule": weekly_schedule,
        "date_overrides": [ov.to_dict() for ov in overrides],
    }), 200

@doctor_bp.route("/availability", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def set_doctor_availability(current_user, token_payload):
    """
    Set or update recurring weekly availability slots for the doctor.
    Supports either list of slots or days array with shifts.
    """
    try:
        doctor = current_user.doctor_profile
        if not doctor:
            return jsonify({"success": False, "error": "Doctor profile not found."}), 404

        data = request.get_json() or {}

        # If overwrite is true or weekly schedule payload sent
        overwrite = request.args.get("overwrite", "true").lower() in ("true", "1")
        if "days" in data:
            # Full weekly schedule update from days array
            days_input = data.get("days", [])
            if overwrite:
                DoctorAvailability.query.filter_by(doctor_id=doctor.id).delete()

            created_slots = []
            for d in days_input:
                dow = d.get("day_of_week")
                is_active = d.get("is_active", True)
                shifts = d.get("shifts", [])
                dur = d.get("slot_duration_minutes", 30)

                if is_active and shifts:
                    for s in shifts:
                        st = datetime.strptime(s["start_time"], "%H:%M").time()
                        et = datetime.strptime(s["end_time"], "%H:%M").time()
                        avail = DoctorAvailability(
                            doctor_id=doctor.id,
                            day_of_week=dow,
                            start_time=st,
                            end_time=et,
                            slot_duration_minutes=s.get("slot_duration_minutes") or dur,
                            is_active=True,
                        )
                        db.session.add(avail)
                        created_slots.append(avail)

            db.session.commit()
            return jsonify({
                "success": True,
                "message": "Weekly availability schedule saved successfully.",
                "slots": [s.to_dict() for s in created_slots],
            }), 200

        # Legacy / single slot list input
        slots_input = data if isinstance(data, list) else data.get("slots", [data])
        if overwrite:
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

@doctor_bp.route("/month-schedule", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_month_schedule(current_user, token_payload):
    """
    Get entire month calendar schedule with day-by-day availability status, shifts, slots count, and booked appointments.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    now = datetime.now()
    year = int(request.args.get("year", now.year))
    month = int(request.args.get("month", now.month))

    num_days = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    # Weekly recurring availabilities
    weekly_availabilities = DoctorAvailability.query.filter_by(
        doctor_id=doctor.id,
        is_active=True
    ).order_by(DoctorAvailability.start_time.asc()).all()
    weekly_map = {}
    for av in weekly_availabilities:
        if av.day_of_week not in weekly_map:
            weekly_map[av.day_of_week] = []
        weekly_map[av.day_of_week].append(av)

    # Date-specific overrides for this month
    overrides = DoctorDateOverride.query.filter(
        DoctorDateOverride.doctor_id == doctor.id,
        DoctorDateOverride.override_date >= month_start,
        DoctorDateOverride.override_date <= month_end
    ).all()
    override_map = {ov.override_date: ov for ov in overrides}

    # Appointments in this month
    appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date >= month_start,
        Appointment.appointment_date <= month_end,
        Appointment.status.in_(["pending", "confirmed"])
    ).order_by(Appointment.start_time.asc()).all()
    appt_map = {}
    for appt in appointments:
        d_key = appt.appointment_date
        if d_key not in appt_map:
            appt_map[d_key] = []
        appt_map[d_key].append({
            "id": appt.id,
            "patient_name": appt.patient.user.full_name if appt.patient and appt.patient.user else "Patient",
            "start_time": appt.start_time.strftime("%H:%M"),
            "end_time": appt.end_time.strftime("%H:%M"),
            "status": appt.status,
            "chief_complaint": appt.chief_complaint,
        })

    days_data = []
    today = date.today()

    for d in range(1, num_days + 1):
        cur_date = date(year, month, d)
        dow = cur_date.weekday()  # 0=Monday..6=Sunday
        day_appts = appt_map.get(cur_date, [])

        is_override = cur_date in override_map
        if is_override:
            ov = override_map[cur_date]
            if not ov.is_available:
                status = "off"
                shifts = []
                total_slots = 0
            else:
                status = "custom"
                dur = ov.slot_duration_minutes or 30
                shifts = [{
                    "start_time": ov.start_time.strftime("%H:%M") if ov.start_time else "09:00",
                    "end_time": ov.end_time.strftime("%H:%M") if ov.end_time else "17:00",
                    "slot_duration_minutes": dur,
                }]
                if ov.start_time and ov.end_time:
                    st = datetime.combine(cur_date, ov.start_time)
                    et = datetime.combine(cur_date, ov.end_time)
                    total_slots = max(0, int((et - st).total_seconds() // (dur * 60)))
                else:
                    total_slots = 0
            override_info = ov.to_dict()
        else:
            weekly_shifts = weekly_map.get(dow, [])
            if weekly_shifts:
                status = "available"
                shifts = [{
                    "id": ws.id,
                    "start_time": ws.start_time.strftime("%H:%M"),
                    "end_time": ws.end_time.strftime("%H:%M"),
                    "slot_duration_minutes": ws.slot_duration_minutes,
                } for ws in weekly_shifts]
                total_slots = 0
                for ws in weekly_shifts:
                    dur = ws.slot_duration_minutes or 30
                    st = datetime.combine(cur_date, ws.start_time)
                    et = datetime.combine(cur_date, ws.end_time)
                    total_slots += max(0, int((et - st).total_seconds() // (dur * 60)))
            else:
                status = "off"
                shifts = []
                total_slots = 0
            override_info = None

        days_data.append({
            "date": cur_date.isoformat(),
            "day": d,
            "day_of_week": dow,
            "day_name": cur_date.strftime("%A"),
            "is_past": cur_date < today,
            "is_today": cur_date == today,
            "status": status,
            "is_override": is_override,
            "override_info": override_info,
            "shifts": shifts,
            "total_slots": total_slots,
            "booked_count": len(day_appts),
            "appointments": day_appts,
        })

    return jsonify({
        "success": True,
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "days": days_data,
        "total_days": num_days,
    }), 200

@doctor_bp.route("/date-override", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def set_date_override(current_user, token_payload):
    """
    Set date override (single date or range) for doctor (Mark as Day Off / Leave, or set Custom Hours).
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    data = request.get_json() or {}
    start_date_str = data.get("start_date") or data.get("override_date")
    end_date_str = data.get("end_date") or start_date_str
    if not start_date_str:
        return jsonify({"success": False, "error": "Date is required."}), 400

    try:
        st_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        et_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid date format: {str(e)}"}), 400

    is_available = bool(data.get("is_available", False))
    st_time = None
    et_time = None
    if is_available and data.get("start_time") and data.get("end_time"):
        try:
            st_time = datetime.strptime(data.get("start_time"), "%H:%M").time()
            et_time = datetime.strptime(data.get("end_time"), "%H:%M").time()
        except Exception as e:
            return jsonify({"success": False, "error": f"Invalid time format: {str(e)}"}), 400

    slot_duration = int(data.get("slot_duration_minutes", 30))
    reason = data.get("reason") or ("On Leave / Day Off" if not is_available else "Custom Schedule Hours")

    cur = st_date
    saved_count = 0
    while cur <= et_date:
        existing = DoctorDateOverride.query.filter_by(doctor_id=doctor.id, override_date=cur).first()
        if existing:
            existing.is_available = is_available
            existing.start_time = st_time
            existing.end_time = et_time
            existing.slot_duration_minutes = slot_duration
            existing.reason = reason
        else:
            new_ov = DoctorDateOverride(
                doctor_id=doctor.id,
                override_date=cur,
                is_available=is_available,
                start_time=st_time,
                end_time=et_time,
                slot_duration_minutes=slot_duration,
                reason=reason
            )
            db.session.add(new_ov)
        cur += timedelta(days=1)
        saved_count += 1

    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Successfully updated schedule override for {saved_count} day(s).",
    }), 200

@doctor_bp.route("/date-override", methods=["DELETE"])
@token_required
@role_required("doctor", "admin")
def delete_date_override(current_user, token_payload):
    """
    Remove date override, reverting day(s) back to standard weekly template.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    target_date = request.args.get("date")
    override_id = request.args.get("override_id")

    if override_id:
        ov = DoctorDateOverride.query.filter_by(id=override_id, doctor_id=doctor.id).first()
        if ov:
            db.session.delete(ov)
            db.session.commit()
            return jsonify({"success": True, "message": "Override removed, reverted to weekly default."}), 200
    elif target_date:
        try:
            d = datetime.strptime(target_date, "%Y-%m-%d").date()
            DoctorDateOverride.query.filter_by(doctor_id=doctor.id, override_date=d).delete()
            db.session.commit()
            return jsonify({"success": True, "message": f"Override for {target_date} removed."}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    return jsonify({"success": False, "error": "Date or override_id required."}), 400

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
            note.prescription_file_url = validated.prescription_file_url or note.prescription_file_url
            note.clinical_notes = validated.clinical_notes
            note.follow_up_date = follow_up
        else:
            note = MedicalNote(
                appointment_id=validated.appointment_id,
                doctor_id=doctor.id if doctor else appt.doctor_id,
                diagnosis=validated.diagnosis,
                prescription=validated.prescription,
                prescription_file_url=validated.prescription_file_url,
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

@doctor_bp.route("/upload-prescription", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def upload_prescription_file(current_user, token_payload):
    """
    Upload prescription document/image (PDF, PNG, JPG, JPEG, WEBP) for consultation.
    """
    import os
    import uuid

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request."}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    allowed_exts = {"pdf", "png", "jpg", "jpeg", "webp"}
    filename = file.filename
    if "." not in filename or filename.rsplit(".", 1)[1].lower() not in allowed_exts:
        return jsonify({"success": False, "error": "Invalid format. Supported: PDF, PNG, JPG, JPEG, WEBP"}), 400

    ext = filename.rsplit(".", 1)[1].lower()
    unique_name = f"rx_{uuid.uuid4().hex[:12]}.{ext}"
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "prescriptions")
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = os.path.join(upload_dir, unique_name)
    file.save(dest_path)

    file_url = f"/api/doctor/prescription-file/{unique_name}"
    return jsonify({
        "success": True,
        "file_url": file_url,
        "filename": filename,
        "message": "Prescription uploaded successfully.",
    }), 200

@doctor_bp.route("/prescription-file/<filename>", methods=["GET"])
def get_prescription_file(filename):
    """
    Serve uploaded prescription file.
    """
    from flask import send_from_directory
    import os
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "prescriptions")
    return send_from_directory(upload_dir, filename)

@doctor_bp.route("/my-patients", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_my_patients(current_user, token_payload):
    """
    List unique patients who have consulted with this doctor for referral selection.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_date.desc()).all()
    patient_map = {}
    for appt in appointments:
        if appt.patient_id and appt.patient_id not in patient_map:
            p = appt.patient
            if p:
                note = MedicalNote.query.filter_by(appointment_id=appt.id).first()
                patient_map[appt.patient_id] = {
                    "patient_id": p.id,
                    "full_name": p.user.full_name if p.user else "Patient",
                    "phone": p.user.phone if p.user else "",
                    "gender": p.gender or "N/A",
                    "blood_group": p.blood_group or "N/A",
                    "last_appointment_id": appt.id,
                    "last_appointment_date": appt.appointment_date.isoformat() if appt.appointment_date else "",
                    "chief_complaint": appt.chief_complaint or "",
                    "last_diagnosis": note.diagnosis if note else "",
                    "last_prescription": note.prescription if note else "",
                }

    return jsonify({
        "success": True,
        "patients": list(patient_map.values())
    }), 200

@doctor_bp.route("/referrals", methods=["POST"])
@token_required
@role_required("doctor", "admin")
def create_patient_referral(current_user, token_payload):
    """
    Refer a patient to another specialist with full medical condition details.
    """
    try:
        doctor = current_user.doctor_profile
        if not doctor:
            return jsonify({"success": False, "error": "Doctor profile not found."}), 404

        data = request.get_json() or {}
        referred_to_doctor_id = data.get("referred_to_doctor_id")
        patient_id = data.get("patient_id")
        disease_condition = data.get("disease_condition")

        if not referred_to_doctor_id or not patient_id or not disease_condition:
            return jsonify({
                "success": False,
                "error": "Target doctor (referred_to_doctor_id), patient (patient_id), and disease condition (disease_condition) are required."
            }), 400

        target_doctor = Doctor.query.get(referred_to_doctor_id)
        if not target_doctor:
            return jsonify({"success": False, "error": "Target specialist doctor not found."}), 404

        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404

        referral = PatientReferral(
            referring_doctor_id=doctor.id,
            referred_to_doctor_id=target_doctor.id,
            patient_id=patient.id,
            appointment_id=data.get("appointment_id"),
            disease_condition=disease_condition.strip(),
            symptom_duration=data.get("symptom_duration", "").strip() or "Not specified",
            current_medications=data.get("current_medications", "").strip() or "None",
            chief_complaints=data.get("chief_complaints", "").strip() or "Referred for advanced evaluation",
            clinical_notes=data.get("clinical_notes", "").strip() or "",
            urgency_level=data.get("urgency_level", "routine").lower(),
            status="pending",
        )
        db.session.add(referral)

        # Notify the receiving doctor
        if target_doctor.user:
            notif = Notification(
                user_id=target_doctor.user.id,
                type="referral",
                channel="in_app",
                recipient=target_doctor.user.email or "doctor",
                subject=f"New Patient Referral from {doctor.user.full_name if doctor.user else 'a Colleague'}",
                message=f"Patient {patient.user.full_name if patient.user else 'Patient'} has been referred to you for: {disease_condition}. Urgency: {referral.urgency_level.upper()}.",
                status="sent"
            )
            db.session.add(notif)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Patient referral successfully sent to {target_doctor.user.full_name if target_doctor.user else 'Specialist'}.",
            "referral": referral.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@doctor_bp.route("/referrals/sent", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_sent_referrals(current_user, token_payload):
    """
    Get all patient referrals sent by the logged-in doctor.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    referrals = PatientReferral.query.filter_by(referring_doctor_id=doctor.id).order_by(PatientReferral.created_at.desc()).all()
    return jsonify({
        "success": True,
        "count": len(referrals),
        "referrals": [r.to_dict() for r in referrals]
    }), 200

@doctor_bp.route("/referrals/received", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def get_received_referrals(current_user, token_payload):
    """
    Get all patient referrals received by the logged-in doctor from other physicians.
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    referrals = PatientReferral.query.filter_by(referred_to_doctor_id=doctor.id).order_by(PatientReferral.created_at.desc()).all()
    return jsonify({
        "success": True,
        "count": len(referrals),
        "referrals": [r.to_dict() for r in referrals]
    }), 200

@doctor_bp.route("/referrals/<int:referral_id>/status", methods=["PUT"])
@token_required
@role_required("doctor", "admin")
def update_referral_status(current_user, token_payload, referral_id):
    """
    Update referral status (accepted, declined, completed).
    """
    doctor = current_user.doctor_profile
    if not doctor:
        return jsonify({"success": False, "error": "Doctor profile not found."}), 404

    referral = PatientReferral.query.get(referral_id)
    if not referral:
        return jsonify({"success": False, "error": "Referral record not found."}), 404

    if referral.referred_to_doctor_id != doctor.id and referral.referring_doctor_id != doctor.id:
        return jsonify({"success": False, "error": "Unauthorized to update this referral."}), 403

    data = request.get_json() or {}
    new_status = data.get("status")
    if new_status not in ["pending", "accepted", "declined", "completed"]:
        return jsonify({"success": False, "error": "Invalid status. Allowed: pending, accepted, declined, completed"}), 400

    referral.status = new_status
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Referral status updated to {new_status}.",
        "referral": referral.to_dict()
    }), 200
