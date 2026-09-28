from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: str = Field(default="patient")  # patient, doctor, admin
    # Optional patient profile fields
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None
    # Optional doctor profile fields
    specialization_id: Optional[int] = None
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[float] = None
    bio: Optional[str] = None
    room_number: Optional[str] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str
