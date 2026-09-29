from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SymptomInputSchema(BaseModel):
    symptoms: str = Field(..., min_length=1, description="Patient natural language symptoms description")
    patient_id: Optional[int] = None
    preferred_date: Optional[str] = None  # YYYY-MM-DD (optional filter)
    auto_book: Optional[bool] = False

class SpecializationScore(BaseModel):
    name: str
    confidence: float
    matched_keywords: List[str]

class DoctorRecommendation(BaseModel):
    doctor_id: int
    doctor_name: str
    specialization: str
    rating: float
    experience_years: int
    consultation_fee: float
    earliest_slot: Optional[str]
    score: float
    reason: str
