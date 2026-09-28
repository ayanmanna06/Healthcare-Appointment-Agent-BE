import logging
from datetime import datetime, date, timedelta
from backend.extensions import scheduler, db
from backend.models.appointment import Appointment
from backend.models.notification import Notification
from backend.agents.notification_agent import NotificationAgent

logger = logging.getLogger("SchedulerService")
logger.setLevel(logging.INFO)

def check_and_send_appointment_reminders(app):
    """
    Background job running on APScheduler to check upcoming appointments
    and dispatch reminders via NotificationAgent.
    """
    with app.app_context():
        try:
            now = datetime.now()
            target_date = (now + timedelta(days=1)).date()
            logger.info(f"Scheduler checking reminders for target date: {target_date}")

            # Find confirmed appointments for tomorrow
            upcoming_appointments = Appointment.query.filter(
                Appointment.appointment_date == target_date,
                Appointment.status == "confirmed"
            ).all()

            notification_agent = NotificationAgent()

            for appt in upcoming_appointments:
                # Check if reminder already sent
                existing_reminder = Notification.query.filter_by(
                    appointment_id=appt.id,
                    type="reminder"
                ).first()

                if not existing_reminder and appt.patient and appt.patient.user:
                    logger.info(f"Sending reminder for appointment #{appt.id} to {appt.patient.user.email}")
                    notification_agent.send_reminder(
                        user_id=appt.patient.user_id,
                        recipient_email=appt.patient.user.email,
                        patient_name=appt.patient.user.full_name,
                        doctor_name=appt.doctor.user.full_name if appt.doctor and appt.doctor.user else "Physician",
                        specialization=appt.doctor.specialization.name if appt.doctor and appt.doctor.specialization else "General",
                        appointment_date=appt.appointment_date.isoformat(),
                        start_time=appt.start_time.strftime("%H:%M"),
                        appointment_id=appt.id
                    )

            logger.info("Appointment reminder check finished successfully.")

        except Exception as e:
            logger.error(f"Error in scheduler job: {str(e)}", exc_info=True)

def init_scheduler(app):
    """
    Register recurring background jobs.
    """
    try:
        if not scheduler.running:
            scheduler.add_job(
                id="appointment_reminders_job",
                func=check_and_send_appointment_reminders,
                args=[app],
                trigger="interval",
                minutes=30,
                replace_existing=True
            )
            scheduler.start()
            logger.info("APScheduler initialized and running every 30 minutes.")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {str(e)}")
