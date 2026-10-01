from pydantic import BaseModel, Field
from typing import Optional

class BookAppointmentSchema(BaseModel):
    doctor_id: int
    appointment_date: str = Field(..., description="YYYY-MM-DD")
    start_time: str = Field(..., description="HH:MM")
    end_time: Optional[str] = Field(None, description="HH:MM")
    chief_complaint: Optional[str] = "Routine consultation"
    booking_source: Optional[str] = "agent_auto"
    patient_id: Optional[int] = None

class RescheduleAppointmentSchema(BaseModel):
    appointment_id: int
    new_date: str = Field(..., description="YYYY-MM-DD")
    new_start_time: str = Field(..., description="HH:MM")
    new_end_time: Optional[str] = None
    reason: Optional[str] = "Patient rescheduled"

class CancelAppointmentSchema(BaseModel):
    appointment_id: int
    reason: Optional[str] = "Cancelled by user"

class AvailabilitySlotSchema(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    slot_duration_minutes: Optional[int] = 30
    is_active: Optional[bool] = True

class MedicalNoteSchema(BaseModel):
    appointment_id: int
    diagnosis: str
    prescription: Optional[str] = None
    prescription_file_url: Optional[str] = None
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[str] = None
