from datetime import datetime
from backend.extensions import db

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    type = db.Column(db.String(50), nullable=False)  # confirmation, reminder, cancellation, reschedule
    channel = db.Column(db.String(20), default="email", nullable=False)  # email, in_app
    recipient = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="sent", nullable=False)  # sent, failed, pending
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="notifications")
    appointment = db.relationship("Appointment", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "appointment_id": self.appointment_id,
            "type": self.type,
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "message": self.message,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
