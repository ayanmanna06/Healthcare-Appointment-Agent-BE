from datetime import datetime, date, time
from backend.extensions import db

class DoctorDateOverride(db.Model):
    __tablename__ = "doctor_date_overrides"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    override_date = db.Column(db.Date, nullable=False, index=True)
    is_available = db.Column(db.Boolean, default=False, nullable=False)  # False = Day Off / Leave, True = Custom Working Hours
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    slot_duration_minutes = db.Column(db.Integer, default=30, nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    doctor = db.relationship("Doctor", backref=db.backref("date_overrides", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "override_date": self.override_date.isoformat() if self.override_date else None,
            "is_available": self.is_available,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "slot_duration_minutes": self.slot_duration_minutes,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
