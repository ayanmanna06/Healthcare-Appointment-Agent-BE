from datetime import datetime
from backend.extensions import db

class Specialization(db.Model):
    __tablename__ = "specializations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True, default="medical_services")
    keywords = db.Column(db.Text, nullable=True)  # Comma-separated symptom keywords for AI matching
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    doctors = db.relationship("Doctor", back_populates="specialization")
    symptoms = db.relationship("Symptom", back_populates="detected_specialization")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "keywords": [k.strip() for k in self.keywords.split(",") if k.strip()] if self.keywords else [],
        }
