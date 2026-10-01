from datetime import datetime
from backend.extensions import db

class PatientReferral(db.Model):
    __tablename__ = "patient_referrals"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    referring_doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    referred_to_doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True)

    disease_condition = db.Column(db.String(255), nullable=False) # Disease or condition diagnosed
    symptom_duration = db.Column(db.String(100), nullable=True) # Duration of symptoms
    current_medications = db.Column(db.Text, nullable=True) # Current medications and dosages
    chief_complaints = db.Column(db.Text, nullable=True) # Current symptoms and presentation
    clinical_notes = db.Column(db.Text, nullable=True) # Clinical notes and reason for referral
    urgency_level = db.Column(db.String(50), default="routine", nullable=False) # routine, urgent, emergency
    status = db.Column(db.String(50), default="pending", nullable=False) # pending, accepted, completed, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    referring_doctor = db.relationship("Doctor", foreign_keys=[referring_doctor_id])
    referred_to_doctor = db.relationship("Doctor", foreign_keys=[referred_to_doctor_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    appointment = db.relationship("Appointment", foreign_keys=[appointment_id])

    def to_dict(self):
        return {
            "id": self.id,
            "referring_doctor_id": self.referring_doctor_id,
            "referring_doctor_name": self.referring_doctor.user.full_name if self.referring_doctor and self.referring_doctor.user else "Dr. Unknown",
            "referring_doctor_specialty": self.referring_doctor.specialization.name if self.referring_doctor and self.referring_doctor.specialization else "General",
            "referring_doctor_phone": self.referring_doctor.user.phone if self.referring_doctor and self.referring_doctor.user else None,
            "referring_doctor_email": self.referring_doctor.user.email if self.referring_doctor and self.referring_doctor.user else None,
            "referred_to_doctor_id": self.referred_to_doctor_id,
            "referred_to_doctor_name": self.referred_to_doctor.user.full_name if self.referred_to_doctor and self.referred_to_doctor.user else "Dr. Unknown",
            "referred_to_doctor_specialty": self.referred_to_doctor.specialization.name if self.referred_to_doctor and self.referred_to_doctor.specialization else "Specialist",
            "patient_id": self.patient_id,
            "patient_name": self.patient.user.full_name if self.patient and self.patient.user else "Unknown Patient",
            "patient_phone": self.patient.user.phone if self.patient and self.patient.user else None,
            "patient_gender": self.patient.gender if self.patient else None,
            "patient_blood_group": self.patient.blood_group if self.patient else None,
            "patient_address": self.patient.address if self.patient else None,
            "appointment_id": self.appointment_id,
            "disease_condition": self.disease_condition,
            "symptom_duration": self.symptom_duration,
            "current_medications": self.current_medications,
            "chief_complaints": self.chief_complaints,
            "clinical_notes": self.clinical_notes,
            "urgency_level": self.urgency_level,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else None,
        }
