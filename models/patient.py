from datetime import datetime
from backend.extensions import db

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact = db.Column(db.String(50), nullable=True)
    medical_history = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="patient_profile")
    appointments = db.relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    symptoms = db.relationship("Symptom", back_populates="patient", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.user.full_name if self.user else None,
            "email": self.user.email if self.user else None,
            "phone": self.user.phone if self.user else None,
            "is_active": self.user.is_active if self.user else True,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "blood_group": self.blood_group,
            "address": self.address,
            "emergency_contact": self.emergency_contact,
            "medical_history": self.medical_history,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
