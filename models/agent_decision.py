from datetime import datetime
from backend.extensions import db

class AgentDecision(db.Model):
    __tablename__ = "agent_decisions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symptom_id = db.Column(db.Integer, db.ForeignKey("symptoms.id", ondelete="CASCADE"), nullable=False, index=True)
    recommended_doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    recommended_slot = db.Column(db.String(100), nullable=False)  # ISO string or formatted date+time
    decision_score = db.Column(db.Float, nullable=False, default=0.0)
    score_breakdown = db.Column(db.Text, nullable=True)  # JSON string
    decision_reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    symptom = db.relationship("Symptom", back_populates="decisions")
    recommended_doctor = db.relationship("Doctor", back_populates="decisions")

    def to_dict(self):
        import json
        breakdown = {}
        if self.score_breakdown:
            try:
                breakdown = json.loads(self.score_breakdown)
            except Exception:
                breakdown = {"raw": self.score_breakdown}

        return {
            "id": self.id,
            "symptom_id": self.symptom_id,
            "recommended_doctor_id": self.recommended_doctor_id,
            "recommended_doctor_name": self.recommended_doctor.user.full_name if self.recommended_doctor and self.recommended_doctor.user else None,
            "recommended_slot": self.recommended_slot,
            "decision_score": self.decision_score,
            "score_breakdown": breakdown,
            "decision_reason": self.decision_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
