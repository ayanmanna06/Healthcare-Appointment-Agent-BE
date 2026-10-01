import logging
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List, Optional
from backend.extensions import db
from backend.models.doctor_availability import DoctorAvailability
from backend.models.doctor_date_override import DoctorDateOverride
from backend.models.appointment import Appointment
from backend.models.doctor import Doctor

logger = logging.getLogger("AvailabilityAgent")
logger.setLevel(logging.INFO)

class AvailabilityAgent:
    """
    Availability Agent
    Evaluates doctor working schedules, checks calendar conflicts against existing appointments,
    and returns available real-time time slots.
    """

    def get_available_slots(
        self,
        doctor_id: int,
        start_date: Optional[date] = None,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Generate list of available slots for a doctor starting from start_date.
        """
        try:
            if not start_date:
                start_date = date.today()

            end_date = start_date + timedelta(days=days_ahead)
            logger.info(f"Checking slots for doctor {doctor_id} from {start_date} to {end_date}")

            # Fetch doctor's recurring weekly availability
            availabilities = DoctorAvailability.query.filter_by(
                doctor_id=doctor_id,
                is_active=True
            ).all()

            if not availabilities:
                logger.warning(f"Doctor {doctor_id} has no active schedule defined.")
                return {
                    "success": True,
                    "doctor_id": doctor_id,
                    "slots": [],
                    "earliest_slot": None,
                    "total_available_slots": 0,
                    "appointment_load": 0,
                }

            # Map availabilities by day of week (0=Mon, 6=Sun)
            schedule_map = {}
            for av in availabilities:
                if av.day_of_week not in schedule_map:
                    schedule_map[av.day_of_week] = []
                schedule_map[av.day_of_week].append(av)

            # Fetch existing active appointments for this doctor in this date window
            existing_appts = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date >= start_date,
                Appointment.appointment_date <= end_date,
                Appointment.status.in_(["pending", "confirmed"])
            ).all()

            # Booked slots set: (date_str, time_str)
            booked_slots = set()
            for appt in existing_appts:
                date_str = appt.appointment_date.isoformat()
                time_str = appt.start_time.strftime("%H:%M")
                booked_slots.add((date_str, time_str))

            # Query date-specific overrides (holidays, leaves, custom single-date shifts)
            date_overrides = DoctorDateOverride.query.filter(
                DoctorDateOverride.doctor_id == doctor_id,
                DoctorDateOverride.override_date >= start_date,
                DoctorDateOverride.override_date <= end_date
            ).all()
            override_map = {ov.override_date: ov for ov in date_overrides}

            available_slots = []
            now_dt = datetime.now()

            # Iterate day by day
            for day_offset in range(days_ahead + 1):
                cur_date = start_date + timedelta(days=day_offset)
                cur_dow = cur_date.weekday()  # 0=Monday, 6=Sunday

                # Check if doctor has an override for this specific calendar date
                if cur_date in override_map:
                    ov = override_map[cur_date]
                    if not ov.is_available:
                        # Doctor is on Leave / Day Off for this specific date
                        continue
                    elif ov.start_time and ov.end_time:
                        # Custom working hours for this specific calendar date
                        duration = ov.slot_duration_minutes or 30
                        slot_start = datetime.combine(cur_date, ov.start_time)
                        slot_end_boundary = datetime.combine(cur_date, ov.end_time)

                        while slot_start + timedelta(minutes=duration) <= slot_end_boundary:
                            cur_time_str = slot_start.strftime("%H:%M")
                            cur_date_str = cur_date.isoformat()
                            end_time_str = (slot_start + timedelta(minutes=duration)).strftime("%H:%M")

                            if slot_start > now_dt:
                                if (cur_date_str, cur_time_str) not in booked_slots:
                                    available_slots.append({
                                        "date": cur_date_str,
                                        "start_time": cur_time_str,
                                        "end_time": end_time_str,
                                        "slot_datetime": slot_start.isoformat(),
                                        "day_name": cur_date.strftime("%A"),
                                    })

                            slot_start += timedelta(minutes=duration)
                        continue

                # Standard recurring weekly schedule for this day of week
                if cur_dow in schedule_map:
                    for av in schedule_map[cur_dow]:
                        duration = av.slot_duration_minutes or 30
                        slot_start = datetime.combine(cur_date, av.start_time)
                        slot_end_boundary = datetime.combine(cur_date, av.end_time)

                        while slot_start + timedelta(minutes=duration) <= slot_end_boundary:
                            cur_time_str = slot_start.strftime("%H:%M")
                            cur_date_str = cur_date.isoformat()
                            end_time_str = (slot_start + timedelta(minutes=duration)).strftime("%H:%M")

                            if slot_start > now_dt:
                                if (cur_date_str, cur_time_str) not in booked_slots:
                                    available_slots.append({
                                        "date": cur_date_str,
                                        "start_time": cur_time_str,
                                        "end_time": end_time_str,
                                        "slot_datetime": slot_start.isoformat(),
                                        "day_name": cur_date.strftime("%A"),
                                    })

                            slot_start += timedelta(minutes=duration)

            # Sort chronological
            available_slots.sort(key=lambda s: s["slot_datetime"])

            earliest_slot = available_slots[0] if available_slots else None
            appointment_load = len(existing_appts)

            return {
                "success": True,
                "doctor_id": doctor_id,
                "slots": available_slots,
                "earliest_slot": earliest_slot,
                "total_available_slots": len(available_slots),
                "appointment_load": appointment_load,
            }

        except Exception as e:
            logger.error(f"Error checking availability for doctor {doctor_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "doctor_id": doctor_id,
                "slots": [],
                "earliest_slot": None,
                "total_available_slots": 0,
                "appointment_load": 0,
                "error": str(e),
            }
