from datetime import datetime
from backend.extensions import db

class Symptom(db.Model):
    __tablename__ = "symptoms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_text = db.Column(db.Text, nullable=False)
    detected_specialization_id = db.Column(db.Integer, db.ForeignKey("specializations.id", ondelete="SET NULL"), nullable=True)
    confidence_score = db.Column(db.Float, nullable=False, default=0.0)
    urgency_level = db.Column(db.String(20), default="medium", nullable=False)  # low, medium, high, emergency
    extracted_keywords = db.Column(db.Text, nullable=True)  # JSON or comma-separated
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="symptoms")
    detected_specialization = db.relationship("Specialization", back_populates="symptoms")
    decisions = db.relationship("AgentDecision", back_populates="symptom", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "raw_text": self.raw_text,
            "detected_specialization_id": self.detected_specialization_id,
            "detected_specialization_name": self.detected_specialization.name if self.detected_specialization else None,
            "confidence_score": self.confidence_score,
            "urgency_level": self.urgency_level,
            "extracted_keywords": self.extracted_keywords.split(",") if self.extracted_keywords else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
