from datetime import datetime, time
from backend.extensions import db

class DoctorAvailability(db.Model):
    __tablename__ = "doctor_availability"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_duration_minutes = db.Column(db.Integer, default=30, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    doctor = db.relationship("Doctor", back_populates="availabilities")

    def to_dict(self):
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "day_of_week": self.day_of_week,
            "day_name": day_names[self.day_of_week] if 0 <= self.day_of_week <= 6 else str(self.day_of_week),
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "slot_duration_minutes": self.slot_duration_minutes,
            "is_active": self.is_active,
        }
