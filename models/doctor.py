from datetime import datetime
from backend.extensions import db

class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    specialization_id = db.Column(db.Integer, db.ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False, index=True)
    qualification = db.Column(db.String(100), nullable=False)
    experience_years = db.Column(db.Integer, default=5, nullable=False)
    rating = db.Column(db.Float, default=4.8, nullable=False)
    consultation_fee = db.Column(db.Float, default=50.0, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    room_number = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="doctor_profile")
    specialization = db.relationship("Specialization", back_populates="doctors")
    availabilities = db.relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")
    medical_notes = db.relationship("MedicalNote", back_populates="doctor", cascade="all, delete-orphan")
    decisions = db.relationship("AgentDecision", back_populates="recommended_doctor")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.user.full_name if self.user else None,
            "email": self.user.email if self.user else None,
            "phone": self.user.phone if self.user else None,
            "specialization_id": self.specialization_id,
            "specialization_name": self.specialization.name if self.specialization else None,
            "qualification": self.qualification,
            "experience_years": self.experience_years,
            "rating": self.rating,
            "consultation_fee": self.consultation_fee,
            "bio": self.bio,
            "room_number": self.room_number,
        }
