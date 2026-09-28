import logging
from typing import Dict, Any, List, Optional
from backend.extensions import db
from backend.models.doctor import Doctor
from backend.models.specialization import Specialization

logger = logging.getLogger("MatchingAgent")
logger.setLevel(logging.INFO)

class MatchingAgent:
    """
    Doctor Matching Agent
    Finds and filters appropriate licensed doctors based on AI-detected specialization,
    patient constraints, experience, and ratings.
    """

    def match_doctors(
        self,
        specialization_name: Optional[str] = None,
        specialization_id: Optional[int] = None,
        min_rating: float = 0.0,
        max_fee: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Query database for active doctors matching specialization.
        """
        try:
            logger.info(f"Matching doctors for specialization: {specialization_name or specialization_id}")

            query = Doctor.query.join(Specialization)

            if specialization_id:
                query = query.filter(Doctor.specialization_id == specialization_id)
            elif specialization_name:
                query = query.filter(Specialization.name.ilike(f"%{specialization_name.strip()}%"))

            if min_rating > 0.0:
                query = query.filter(Doctor.rating >= min_rating)

            if max_fee is not None:
                query = query.filter(Doctor.consultation_fee <= max_fee)

            # Join User to ensure doctor user account is active
            matched_doctors = query.all()

            # If no doctors found in exact specialty, fallback to General Physician
            fallback_applied = False
            if not matched_doctors and specialization_name != "General Physician":
                logger.warning(f"No doctor found for {specialization_name}. Falling back to General Physician.")
                query_fallback = Doctor.query.join(Specialization).filter(Specialization.name == "General Physician")
                matched_doctors = query_fallback.all()
                fallback_applied = True

            doctor_list = []
            for doc in matched_doctors:
                doc_dict = doc.to_dict()
                doctor_list.append(doc_dict)

            # Sort primarily by rating descending, then experience descending
            doctor_list.sort(key=lambda d: (d["rating"], d["experience_years"]), reverse=True)

            logger.info(f"Found {len(doctor_list)} matching doctors.")
            return {
                "success": True,
                "count": len(doctor_list),
                "doctors": doctor_list,
                "fallback_applied": fallback_applied,
                "target_specialization": specialization_name or (matched_doctors[0].specialization.name if matched_doctors else None),
            }

        except Exception as e:
            logger.error(f"Error in Doctor Matching Agent: {str(e)}", exc_info=True)
            return {
                "success": False,
                "count": 0,
                "doctors": [],
                "error": str(e),
                "target_specialization": specialization_name,
            }
