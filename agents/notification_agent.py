import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask_mail import Message
from backend.extensions import db, mail
from backend.models.notification import Notification
from backend.services.prompt_loader import load_prompt

logger = logging.getLogger("NotificationAgent")
logger.setLevel(logging.INFO)

class NotificationAgent:
    """
    Notification Agent
    Manages multichannel transactional alerts (Email & In-App notifications):
    - Booking Confirmation
    - Appointment Reminder
    - Cancellation Notice
    - Reschedule Notice
    """

    def send_booking_confirmation(
        self,
        user_id: int,
        recipient_email: str,
        patient_name: str,
        doctor_name: str,
        specialization: str,
        appointment_date: str,
        start_time: str,
        room_number: Optional[str] = "Room 302",
        appointment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send appointment confirmation email and store record.
        """
        clean_doc = doctor_name if doctor_name.startswith("Dr.") else f"Dr. {doctor_name}"
        subject = f"Appointment Confirmed: {clean_doc} ({specialization}) - {appointment_date}"
        template = load_prompt("booking_confirmation_email.txt")
        html_body = template.format(
            patient_name=patient_name,
            clean_doc=clean_doc,
            specialization=specialization,
            appointment_date=appointment_date,
            start_time=start_time,
            room_number=room_number or "Main Clinic Reception"
        )
        plain_body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with {clean_doc} ({specialization}) is confirmed for {appointment_date} at {start_time}.\n"
            f"Location: {room_number}\n\nThank you for choosing Healthcare Appointment Agent."
        )

        return self._send_and_record(
            user_id=user_id,
            recipient=recipient_email,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            notification_type="confirmation",
            appointment_id=appointment_id
        )

    def send_reminder(
        self,
        user_id: int,
        recipient_email: str,
        patient_name: str,
        doctor_name: str,
        specialization: str,
        appointment_date: str,
        start_time: str,
        appointment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send appointment reminder alert.
        """
        clean_doc = doctor_name if doctor_name.startswith("Dr.") else f"Dr. {doctor_name}"
        subject = f"Reminder: Your consultation with {clean_doc} is on {appointment_date}"
        template = load_prompt("reminder_email.txt")
        html_body = template.format(
            patient_name=patient_name,
            clean_doc=clean_doc,
            specialization=specialization,
            appointment_date=appointment_date,
            start_time=start_time
        )
        plain_body = f"Reminder: You have an appointment with {clean_doc} on {appointment_date} at {start_time}."

        return self._send_and_record(
            user_id=user_id,
            recipient=recipient_email,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            notification_type="reminder",
            appointment_id=appointment_id
        )

    def send_cancellation_notice(
        self,
        user_id: int,
        recipient_email: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        appointment_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send cancellation notification.
        """
        clean_doc = doctor_name if doctor_name.startswith("Dr.") else f"Dr. {doctor_name}"
        subject = f"Appointment Cancelled: {clean_doc} on {appointment_date}"
        template = load_prompt("cancellation_email.txt")
        html_body = template.format(
            patient_name=patient_name,
            clean_doc=clean_doc,
            appointment_date=appointment_date,
            reason=reason or "Patient cancellation"
        )
        plain_body = f"Dear {patient_name}, your appointment on {appointment_date} with {clean_doc} has been cancelled. Reason: {reason or 'Requested by user'}."
        return self._send_and_record(
            user_id=user_id,
            recipient=recipient_email,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            notification_type="cancellation",
            appointment_id=appointment_id
        )

    def send_reschedule_notice(
        self,
        user_id: int,
        recipient_email: str,
        patient_name: str,
        doctor_name: str,
        new_date: str,
        new_time: str,
        appointment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send reschedule notification.
        """
        clean_doc = doctor_name if doctor_name.startswith("Dr.") else f"Dr. {doctor_name}"
        subject = f"Appointment Rescheduled: {clean_doc} to {new_date} at {new_time}"
        template = load_prompt("reschedule_email.txt")
        html_body = template.format(
            patient_name=patient_name,
            clean_doc=clean_doc,
            new_date=new_date,
            new_time=new_time
        )
        plain_body = f"Dear {patient_name}, your appointment with {clean_doc} has been successfully rescheduled to {new_date} at {new_time}."
        return self._send_and_record(
            user_id=user_id,
            recipient=recipient_email,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            notification_type="reschedule",
            appointment_id=appointment_id
        )

    def _send_and_record(
        self,
        user_id: int,
        recipient: str,
        subject: str,
        html_body: str,
        plain_body: str,
        notification_type: str,
        appointment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        delivery_status = "sent"

        # Attempt to deliver via Flask-Mail if configured
        try:
            from flask import current_app
            if current_app and current_app.config.get("MAIL_USERNAME"):
                sender = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME")
                recipients_list = [recipient]
                organizer = current_app.config.get("ORGANIZER_EMAIL")
                if current_app.config.get("ALWAYS_NOTIFY_ORGANIZER") and organizer and organizer not in recipients_list:
                    recipients_list.append(organizer)

                msg = Message(
                    subject=subject,
                    sender=sender,
                    recipients=recipients_list,
                    body=plain_body,
                    html=html_body
                )
                mail.send(msg)
                logger.info(f"Email successfully delivered to {', '.join(recipients_list)}")
            else:
                logger.info(f"[DEV MOCK MAIL] Email to {recipient} captured: {subject}")
        except Exception as e:
            logger.warning(f"Email sending failed (will still record notification in database): {str(e)}")
            delivery_status = "pending_delivery"

        # Record in notifications table
        try:
            notif = Notification(
                user_id=user_id,
                appointment_id=appointment_id,
                type=notification_type,
                channel="email",
                recipient=recipient,
                subject=subject,
                message=plain_body,
                status=delivery_status,
                sent_at=datetime.utcnow()
            )
            db.session.add(notif)
            db.session.commit()
            return {"success": True, "notification_id": notif.id, "status": delivery_status}
        except Exception as db_err:
            db.session.rollback()
            logger.error(f"Failed to record notification: {str(db_err)}")
            return {"success": False, "error": str(db_err)}
