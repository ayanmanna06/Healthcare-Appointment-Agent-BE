from datetime import datetime
from backend.extensions import db

class MedicalNote(db.Model):
    __tablename__ = "medical_notes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=True)
    clinical_notes = db.Column(db.Text, nullable=True)
    follow_up_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    appointment = db.relationship("Appointment", back_populates="medical_notes")
    doctor = db.relationship("Doctor", back_populates="medical_notes")

    def to_dict(self):
        return {
            "id": self.id,
            "appointment_id": self.appointment_id,
            "doctor_id": self.doctor_id,
            "diagnosis": self.diagnosis,
            "prescription": self.prescription,
            "clinical_notes": self.clinical_notes,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
