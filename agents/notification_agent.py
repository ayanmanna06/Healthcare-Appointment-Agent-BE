import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask_mail import Message
from backend.extensions import db, mail
from backend.models.notification import Notification

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
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #0EA5E9, #14B8A6); color: white; padding: 30px 20px; text-align: center; }}
                .content {{ padding: 30px 25px; color: #334155; line-height: 1.6; }}
                .card {{ background: #f0fdf4; border-left: 4px solid #14B8A6; padding: 15px 20px; margin: 20px 0; border-radius: 4px; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                .details-table td {{ padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
                .label {{ font-weight: 600; color: #64748b; width: 40%; }}
                .value {{ font-weight: bold; color: #0f172a; }}
                .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin:0; font-size: 24px;">Healthcare Appointment Confirmed</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">AI Agent Automated Scheduling</p>
                </div>
                <div class="content">
                    <p>Dear <strong>{patient_name}</strong>,</p>
                    <p>Your appointment has been successfully scheduled and confirmed by our Healthcare AI Assistant.</p>
                    <div class="card">
                        <table class="details-table">
                            <tr><td class="label">Doctor</td><td class="value">{clean_doc}</td></tr>
                            <tr><td class="label">Specialization</td><td class="value">{specialization}</td></tr>
                            <tr><td class="label">Date</td><td class="value">{appointment_date}</td></tr>
                            <tr><td class="label">Time</td><td class="value">{start_time}</td></tr>
                            <tr><td class="label">Location</td><td class="value">{room_number or 'Main Clinic Reception'}</td></tr>
                        </table>
                    </div>
                    <p>Please arrive 10 minutes prior to your scheduled time with any relevant previous medical records or test reports.</p>
                </div>
                <div class="footer">
                    <p>Healthcare Appointment Agent System &bull; Automated Health Notification</p>
                </div>
            </div>
        </body>
        </html>
        """
        plain_body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with Dr. {doctor_name} ({specialization}) is confirmed for {appointment_date} at {start_time}.\n"
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
        subject = f"Reminder: Your consultation with Dr. {doctor_name} is on {appointment_date}"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; }}
                .header {{ background: #0EA5E9; color: white; padding: 25px; text-align: center; }}
                .content {{ padding: 25px; color: #334155; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin:0;">Upcoming Appointment Reminder</h2>
                </div>
                <div class="content">
                    <p>Hello <strong>{patient_name}</strong>,</p>
                    <p>This is a quick reminder for your upcoming medical appointment:</p>
                    <ul>
                        <li><strong>Doctor:</strong> Dr. {doctor_name} ({specialization})</li>
                        <li><strong>Date:</strong> {appointment_date}</li>
                        <li><strong>Time:</strong> {start_time}</li>
                    </ul>
                    <p>If you need to reschedule or cancel, please do so via the patient portal at least 2 hours in advance.</p>
                </div>
            </div>
        </body>
        </html>
        """
        plain_body = f"Reminder: You have an appointment with Dr. {doctor_name} on {appointment_date} at {start_time}."

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
        subject = f"Appointment Cancelled: Dr. {doctor_name} on {appointment_date}"
        plain_body = f"Dear {patient_name}, your appointment on {appointment_date} with Dr. {doctor_name} has been cancelled. Reason: {reason or 'Requested by user'}."
        html_body = f"""
        <div style="font-family:sans-serif; padding: 20px; max-width: 600px; margin:0 auto; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #ef4444;">Appointment Cancellation Notice</h3>
            <p>Dear {patient_name},</p>
            <p>Your appointment on <strong>{appointment_date}</strong> with <strong>Dr. {doctor_name}</strong> has been cancelled.</p>
            <p><strong>Reason:</strong> {reason or 'Patient cancellation'}</p>
            <p>You can re-book anytime using the Healthcare AI Agent.</p>
        </div>
        """
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
        subject = f"Appointment Rescheduled: Dr. {doctor_name} to {new_date} at {new_time}"
        plain_body = f"Dear {patient_name}, your appointment with Dr. {doctor_name} has been successfully rescheduled to {new_date} at {new_time}."
        html_body = f"""
        <div style="font-family:sans-serif; padding: 20px; max-width: 600px; margin:0 auto; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h3 style="color: #0EA5E9;">Appointment Rescheduled</h3>
            <p>Dear {patient_name},</p>
            <p>Your appointment with <strong>Dr. {doctor_name}</strong> has been rescheduled to:</p>
            <p><strong>New Date & Time:</strong> {new_date} at {new_time}</p>
            <p>Thank you for letting us know in advance!</p>
        </div>
        """
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
