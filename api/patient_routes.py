from datetime import datetime, date, time, timedelta
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.specialization import Specialization
from backend.models.appointment import Appointment
from backend.models.symptom import Symptom
from backend.models.notification import Notification
from backend.agents.symptom_agent import SymptomAgent
from backend.agents.matching_agent import MatchingAgent
from backend.agents.availability_agent import AvailabilityAgent
from backend.agents.decision_agent import DecisionAgent
from backend.agents.notification_agent import NotificationAgent
from backend.schemas.symptom_schemas import SymptomInputSchema
from backend.schemas.appointment_schemas import (
    BookAppointmentSchema,
    CancelAppointmentSchema,
    RescheduleAppointmentSchema,
)
from backend.services.auth_service import token_required, role_required

patient_bp = Blueprint("patient_bp", __name__)

symptom_agent = SymptomAgent()
matching_agent = MatchingAgent()
availability_agent = AvailabilityAgent()
decision_agent = DecisionAgent()
notification_agent = NotificationAgent()

@patient_bp.route("/symptoms", methods=["POST"])
def analyze_symptoms_and_recommend():
    """
    Core Agentic AI Workflow:
    Step 1: Patient submits symptoms
    Step 2: AI Symptom Analysis Agent (identifies specialty, confidence score, urgency)
    Step 3: Doctor Matching Agent (finds doctors in DB)
    Step 4: Availability Agent (checks available slots)
    Step 5: Decision Agent (weighted scoring formula: earliest available, rating, less waiting time)
    Step 6: Optional automatic booking
    Step 7: Notification Agent (email confirmation + in-app alert)
    """
    try:
        data = request.get_json() or {}
        validated = SymptomInputSchema(**data)

        # Identify logged in patient if token is present
        auth_header = request.headers.get("Authorization")
        patient_obj = None
        if auth_header and "Bearer " in auth_header:
            try:
                from backend.services.auth_service import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                patient_obj = Patient.query.filter_by(user_id=payload["user_id"]).first()
            except Exception:
                pass

        if not patient_obj and validated.patient_id:
            patient_obj = Patient.query.get(validated.patient_id)

        workflow_trace = []

        # ==========================================
        # STEP 1: Patient submits symptoms
        # ==========================================
        workflow_trace.append({
            "step": 1,
            "agent": "Patient Intake Agent",
            "status": "completed",
            "output": f"Received symptoms: '{validated.symptoms}'",
            "timestamp": datetime.now().isoformat(),
        })

        # ==========================================
        # STEP 2: AI Symptom Analysis Agent
        # ==========================================
        symptom_result = symptom_agent.analyze(validated.symptoms)
        primary_spec_name = symptom_result["primary_specialization"]
        confidence_score = symptom_result["confidence_score"]
        urgency_level = symptom_result["urgency_level"]
        extracted_keywords = symptom_result["extracted_keywords"]

        # Persist Symptom in DB
        spec_db = Specialization.query.filter_by(name=primary_spec_name).first()
        spec_id = spec_db.id if spec_db else None

        symptom_record = Symptom(
            patient_id=patient_obj.id if patient_obj else None,
            raw_text=validated.symptoms,
            detected_specialization_id=spec_id,
            confidence_score=confidence_score,
            urgency_level=urgency_level,
            extracted_keywords=",".join(extracted_keywords),
        )
        db.session.add(symptom_record)
        db.session.commit()

        workflow_trace.append({
            "step": 2,
            "agent": "AI Symptom Analysis Agent",
            "status": "completed",
            "output": {
                "detected_specialization": primary_spec_name,
                "confidence_score": confidence_score,
                "urgency_level": urgency_level,
                "extracted_keywords": extracted_keywords,
                "rankings": symptom_result["rankings"][:3],
                "clinical_summary": symptom_result["summary"],
            },
            "timestamp": datetime.now().isoformat(),
        })

        # ==========================================
        # STEP 3: Doctor Matching Agent
        # ==========================================
        candidate_specs = [primary_spec_name]
        for r in symptom_result.get("rankings", []):
            spec_name = r.get("specialization") or r.get("name")
            if spec_name and spec_name not in candidate_specs:
                candidate_specs.append(spec_name)
        if "General Physician" not in candidate_specs:
            candidate_specs.append("General Physician")

        matched_doctors = []
        seen_doctor_ids = set()
        for s_name in candidate_specs:
            m_res = matching_agent.match_doctors(specialization_name=s_name)
            for d in m_res.get("doctors", []):
                if d["id"] not in seen_doctor_ids:
                    seen_doctor_ids.add(d["id"])
                    matched_doctors.append(d)
            if len(matched_doctors) >= 4:
                break

        workflow_trace.append({
            "step": 3,
            "agent": "Doctor Matching Agent",
            "status": "completed",
            "output": {
                "matched_count": len(matched_doctors),
                "target_specialization": primary_spec_name,
                "top_candidates": [d["full_name"] for d in matched_doctors[:3]],
            },
            "timestamp": datetime.now().isoformat(),
        })

        # ==========================================
        # STEP 4: Availability Agent
        # ==========================================
        candidate_packages = []
        for doc in matched_doctors:
            avail = availability_agent.get_available_slots(doc["id"], days_ahead=7)
            candidate_packages.append({
                "doctor": doc,
                "availability": avail,
            })

        workflow_trace.append({
            "step": 4,
            "agent": "Availability Agent",
            "status": "completed",
            "output": {
                "doctors_evaluated": len(candidate_packages),
                "total_available_slots_found": sum(len(c["availability"]["slots"]) for c in candidate_packages),
            },
            "timestamp": datetime.now().isoformat(),
        })

        # ==========================================
        # STEP 5: Smart Decision Engine Agent
        # ==========================================
        decision_result = decision_agent.evaluate(
            candidate_doctors_with_availability=candidate_packages,
            symptom_id=symptom_record.id,
            urgency_level=urgency_level
        )

        recommended_doctor = decision_result.get("recommended_doctor")
        recommended_slot = decision_result.get("recommended_slot")
        decision_score = decision_result.get("decision_score")
        score_breakdown = decision_result.get("score_breakdown")
        decision_reason = decision_result.get("decision_reason")

        workflow_trace.append({
            "step": 5,
            "agent": "Smart Decision Agent",
            "status": "completed",
            "output": {
                "recommended_doctor": recommended_doctor["full_name"] if recommended_doctor else None,
                "recommended_slot": recommended_slot,
                "composite_score": decision_score,
                "score_breakdown": score_breakdown,
                "decision_reason": decision_reason,
            },
            "timestamp": datetime.now().isoformat(),
        })

        # ==========================================
        # STEP 6: Optional Auto Booking Agent
        # ==========================================
        booked_appointment = None
        if validated.auto_book and patient_obj and recommended_doctor and recommended_slot:
            try:
                appt_date = datetime.strptime(recommended_slot["date"], "%Y-%m-%d").date()
                st_time = datetime.strptime(recommended_slot["start_time"], "%H:%M").time()
                et_time = datetime.strptime(recommended_slot["end_time"], "%H:%M").time()

                new_appt = Appointment(
                    patient_id=patient_obj.id,
                    doctor_id=recommended_doctor["id"],
                    appointment_date=appt_date,
                    start_time=st_time,
                    end_time=et_time,
                    status="confirmed",
                    chief_complaint=validated.symptoms[:250],
                    booking_source="agent_auto",
                )
                db.session.add(new_appt)
                db.session.commit()
                booked_appointment = new_appt.to_dict()

                workflow_trace.append({
                    "step": 6,
                    "agent": "Appointment Booking Agent",
                    "status": "completed",
                    "output": f"Appointment #{new_appt.id} automatically confirmed with Dr. {recommended_doctor['full_name']}",
                    "timestamp": datetime.now().isoformat(),
                })

                # ==========================================
                # STEP 7: Notification Agent
                # ==========================================
                notification_agent.send_booking_confirmation(
                    user_id=patient_obj.user_id,
                    recipient_email=patient_obj.user.email,
                    patient_name=patient_obj.user.full_name,
                    doctor_name=recommended_doctor["full_name"],
                    specialization=primary_spec_name,
                    appointment_date=recommended_slot["date"],
                    start_time=recommended_slot["start_time"],
                    room_number=recommended_doctor.get("room_number", "Room 301"),
                    appointment_id=new_appt.id,
                )

                workflow_trace.append({
                    "step": 7,
                    "agent": "Notification Agent",
                    "status": "completed",
                    "output": f"Confirmation notification & email dispatched to {patient_obj.user.email}",
                    "timestamp": datetime.now().isoformat(),
                })

            except Exception as book_err:
                db.session.rollback()
                workflow_trace.append({
                    "step": 6,
                    "agent": "Appointment Booking Agent",
                    "status": "failed",
                    "output": f"Auto-booking failed: {str(book_err)}",
                    "timestamp": datetime.now().isoformat(),
                })

        return jsonify({
            "success": True,
            "symptom_id": symptom_record.id,
            "analysis": {
                "primary_specialization": primary_spec_name,
                "confidence_score": confidence_score,
                "urgency_level": urgency_level,
                "extracted_keywords": extracted_keywords,
                "summary": symptom_result["summary"],
                "rankings": symptom_result["rankings"],
            },
            "recommendation": {
                "doctor": recommended_doctor,
                "slot": recommended_slot,
                "decision_score": decision_score,
                "score_breakdown": score_breakdown,
                "decision_reason": decision_reason,
            },
            "candidate_doctors": [c["doctor"] for c in candidate_packages],
            "workflow_trace": workflow_trace,
            "booked_appointment": booked_appointment,
        }), 200

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@patient_bp.route("/recommended-doctors", methods=["GET"])
def get_recommended_doctors():
    """
    Get doctors matching query parameters (specialization, min_rating).
    """
    specialization = request.args.get("specialization")
    min_rating = float(request.args.get("min_rating", 0.0))
    result = matching_agent.match_doctors(specialization_name=specialization, min_rating=min_rating)
    return jsonify(result), 200

@patient_bp.route("/doctors", methods=["GET"])
def list_doctors():
    """
    List all active doctors with specializations and profile information.
    """
    doctors = Doctor.query.all()
    return jsonify({
        "success": True,
        "count": len(doctors),
        "doctors": [d.to_dict() for d in doctors],
    }), 200

@patient_bp.route("/specializations", methods=["GET"])
def list_specializations():
    """
    List all medical specializations.
    """
    specs = Specialization.query.all()
    return jsonify({
        "success": True,
        "specializations": [s.to_dict() for s in specs],
    }), 200

@patient_bp.route("/doctor/<int:doctor_id>/slots", methods=["GET"])
def get_doctor_available_slots(doctor_id):
    """
    Get live available bookable slots for a doctor.
    """
    days = int(request.args.get("days", 7))
    result = availability_agent.get_available_slots(doctor_id, days_ahead=days)
    return jsonify(result), 200

@patient_bp.route("/appointments/book", methods=["POST"])
@token_required
def book_appointment(current_user, token_payload):
    """
    Manually or directly book an appointment.
    """
    try:
        data = request.get_json() or {}
        validated = BookAppointmentSchema(**data)

        patient = current_user.patient_profile
        if not patient and validated.patient_id:
            patient = Patient.query.get(validated.patient_id)

        if not patient:
            return jsonify({"success": False, "error": "Patient profile not found."}), 400

        doctor = Doctor.query.get(validated.doctor_id)
        if not doctor:
            return jsonify({"success": False, "error": "Doctor not found."}), 404

        appt_date = datetime.strptime(validated.appointment_date, "%Y-%m-%d").date()
        start_t = datetime.strptime(validated.start_time, "%H:%M").time()

        if validated.end_time:
            end_t = datetime.strptime(validated.end_time, "%H:%M").time()
        else:
            # Default 30 min duration
            start_dt = datetime.combine(appt_date, start_t)
            end_t = (start_dt + timedelta(minutes=30)).time()

        # Check for conflicts
        conflict = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == appt_date,
            Appointment.start_time == start_t,
            Appointment.status.in_(["confirmed", "pending"]),
        ).first()

        if conflict:
            return jsonify({"success": False, "error": "This slot is already booked. Please choose another slot."}), 409

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=appt_date,
            start_time=start_t,
            end_time=end_t,
            status="confirmed",
            chief_complaint=validated.chief_complaint,
            booking_source=validated.booking_source or "manual",
        )
        db.session.add(appointment)
        db.session.commit()

        # Send confirmation email
        notification_agent.send_booking_confirmation(
            user_id=current_user.id,
            recipient_email=current_user.email,
            patient_name=current_user.full_name,
            doctor_name=doctor.user.full_name,
            specialization=doctor.specialization.name if doctor.specialization else "General",
            appointment_date=validated.appointment_date,
            start_time=validated.start_time,
            room_number=doctor.room_number,
            appointment_id=appointment.id,
        )

        return jsonify({
            "success": True,
            "message": "Appointment booked successfully!",
            "appointment": appointment.to_dict(),
        }), 201

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@patient_bp.route("/appointments/cancel", methods=["POST"])
@token_required
def cancel_appointment(current_user, token_payload):
    """
    Cancel an appointment.
    """
    try:
        data = request.get_json() or {}
        validated = CancelAppointmentSchema(**data)

        appt = Appointment.query.get(validated.appointment_id)
        if not appt:
            return jsonify({"success": False, "error": "Appointment not found."}), 404

        # Verify ownership (patient or admin or doctor)
        if current_user.role.name == "patient" and appt.patient.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized to cancel this appointment."}), 403

        appt.status = "cancelled"
        appt.cancellation_reason = validated.reason
        db.session.commit()

        # Send cancellation notice
        notification_agent.send_cancellation_notice(
            user_id=appt.patient.user_id,
            recipient_email=appt.patient.user.email,
            patient_name=appt.patient.user.full_name,
            doctor_name=appt.doctor.user.full_name,
            appointment_date=appt.appointment_date.isoformat(),
            appointment_id=appt.id,
            reason=validated.reason,
        )

        return jsonify({
            "success": True,
            "message": "Appointment cancelled successfully.",
            "appointment": appt.to_dict(),
        }), 200

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@patient_bp.route("/appointments/reschedule", methods=["POST"])
@token_required
def reschedule_appointment(current_user, token_payload):
    """
    Reschedule an appointment to a new date and time.
    """
    try:
        data = request.get_json() or {}
        validated = RescheduleAppointmentSchema(**data)

        appt = Appointment.query.get(validated.appointment_id)
        if not appt:
            return jsonify({"success": False, "error": "Appointment not found."}), 404

        if current_user.role.name == "patient" and appt.patient.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized to reschedule this appointment."}), 403

        new_date = datetime.strptime(validated.new_date, "%Y-%m-%d").date()
        new_start = datetime.strptime(validated.new_start_time, "%H:%M").time()
        new_end = (datetime.combine(new_date, new_start) + timedelta(minutes=30)).time()

        # Check conflict
        conflict = Appointment.query.filter(
            Appointment.doctor_id == appt.doctor_id,
            Appointment.appointment_date == new_date,
            Appointment.start_time == new_start,
            Appointment.status.in_(["confirmed", "pending"]),
            Appointment.id != appt.id,
        ).first()

        if conflict:
            return jsonify({"success": False, "error": "The selected new slot is already booked."}), 409

        appt.appointment_date = new_date
        appt.start_time = new_start
        appt.end_time = new_end
        appt.status = "confirmed"
        db.session.commit()

        # Send reschedule notice
        notification_agent.send_reschedule_notice(
            user_id=appt.patient.user_id,
            recipient_email=appt.patient.user.email,
            patient_name=appt.patient.user.full_name,
            doctor_name=appt.doctor.user.full_name,
            new_date=validated.new_date,
            new_time=validated.new_start_time,
            appointment_id=appt.id,
        )

        return jsonify({
            "success": True,
            "message": "Appointment rescheduled successfully.",
            "appointment": appt.to_dict(),
        }), 200

    except ValidationError as ve:
        return jsonify({"success": False, "error": "Validation error", "details": ve.errors()}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@patient_bp.route("/appointments", methods=["GET"])
@token_required
def get_patient_appointments(current_user, token_payload):
    """
    Get appointment history for the logged-in patient.
    """
    patient = current_user.patient_profile
    if not patient:
        return jsonify({"success": True, "appointments": []}), 200

    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()
    return jsonify({
        "success": True,
        "count": len(appointments),
        "appointments": [a.to_dict() for a in appointments],
    }), 200

@patient_bp.route("/notifications", methods=["GET"])
@token_required
def get_user_notifications(current_user, token_payload):
    """
    Get notifications history for logged in user.
    """
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.sent_at.desc()).limit(20).all()
    return jsonify({
        "success": True,
        "notifications": [n.to_dict() for n in notifs],
    }), 200
