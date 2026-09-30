from datetime import datetime
from backend.extensions import db

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default="confirmed", nullable=False, index=True)  # pending, confirmed, completed, cancelled, rescheduled
    chief_complaint = db.Column(db.Text, nullable=True)
    booking_source = db.Column(db.String(20), default="agent_auto", nullable=False)  # agent_auto, manual
    cancellation_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    medical_notes = db.relationship("MedicalNote", back_populates="appointment", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="appointment", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.user.full_name if self.patient and self.patient.user else "Unknown Patient",
            "patient_phone": self.patient.user.phone if self.patient and self.patient.user else None,
            "patient_email": self.patient.user.email if self.patient and self.patient.user else None,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.user.full_name if self.doctor and self.doctor.user else "Unknown Doctor",
            "specialization": self.doctor.specialization.name if self.doctor and self.doctor.specialization else None,
            "appointment_date": self.appointment_date.isoformat() if self.appointment_date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "status": self.status,
            "chief_complaint": self.chief_complaint,
            "booking_source": self.booking_source,
            "cancellation_reason": self.cancellation_reason,
            "has_notes": bool(self.medical_notes),
            "medical_note": self.medical_notes[0].to_dict() if self.medical_notes else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
