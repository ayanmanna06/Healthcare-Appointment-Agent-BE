import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from backend.config import Config
from backend.extensions import db
from backend.models.agent_decision import AgentDecision
from backend.services.prompt_loader import load_prompt

logger = logging.getLogger("DecisionAgent")
logger.setLevel(logging.INFO)

class DecisionAgent:
    """
    Smart Decision Engine Agent
    Selects the optimal doctor and slot using a multi-factor weighted scoring model:
    - doctor_rating (35%)
    - experience (25%)
    - availability / earliest opening (25%)
    - appointment_load / waiting time (15%)
    """

    def __init__(self):
        self.w_rating = Config.WEIGHT_RATING
        self.w_experience = Config.WEIGHT_EXPERIENCE
        self.w_earliest = Config.WEIGHT_EARLIEST_SLOT
        self.w_load = Config.WEIGHT_LOW_LOAD

    def evaluate(
        self,
        candidate_doctors_with_availability: List[Dict[str, Any]],
        symptom_id: Optional[int] = None,
        urgency_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Evaluate candidate doctors and their available slots.
        """
        try:
            if not candidate_doctors_with_availability:
                return {
                    "success": False,
                    "error": "No candidate doctors provided for decision evaluation.",
                    "recommended_doctor": None,
                    "recommended_slot": None,
                    "decision_reason": "No doctors available in the requested specialization.",
                }

            logger.info(f"Evaluating {len(candidate_doctors_with_availability)} candidate doctors for decision.")

            scored_candidates = []
            now_dt = datetime.now()

            # Dynamic weight adjustment for emergency / high urgency
            w_rating = self.w_rating
            w_experience = self.w_experience
            w_earliest = self.w_earliest
            w_load = self.w_load

            if urgency_level in ["high", "emergency"]:
                # Heavily prioritize immediate availability
                w_earliest = 0.50
                w_rating = 0.25
                w_experience = 0.15
                w_load = 0.10

            for item in candidate_doctors_with_availability:
                doctor = item["doctor"]
                avail_info = item["availability"]

                rating = float(doctor.get("rating", 4.0))
                experience = int(doctor.get("experience_years", 5))
                load = int(avail_info.get("appointment_load", 0))
                earliest_slot = avail_info.get("earliest_slot")

                # Factor 1: Normalized Doctor Rating (0.0 to 1.0)
                norm_rating = min(1.0, max(0.0, rating / 5.0))

                # Factor 2: Normalized Experience (0.0 to 1.0, capped at 25 yrs)
                norm_experience = min(1.0, max(0.0, experience / 25.0))

                # Factor 3: Availability / Earliness (0.0 to 1.0)
                if earliest_slot and earliest_slot.get("slot_datetime"):
                    slot_dt = datetime.fromisoformat(earliest_slot["slot_datetime"])
                    delta = (slot_dt - now_dt).total_seconds()
                    days_diff = max(0.0, delta / 86400.0)
                    # Slot sooner in time receives higher score
                    norm_earliness = 1.0 / (1.0 + (days_diff * 0.8))
                else:
                    norm_earliness = 0.1  # penalty if no immediate slots

                # Factor 4: Low Load / Waiting Time (0.0 to 1.0)
                norm_low_load = max(0.0, 1.0 - min(1.0, load / 15.0))

                composite_score = (
                    (w_rating * norm_rating) +
                    (w_experience * norm_experience) +
                    (w_earliest * norm_earliness) +
                    (w_load * norm_low_load)
                )

                composite_score = round(composite_score, 4)

                breakdown = {
                    "rating_score": round(norm_rating, 3),
                    "experience_score": round(norm_experience, 3),
                    "earliness_score": round(norm_earliness, 3),
                    "load_score": round(norm_low_load, 3),
                    "weights_applied": {
                        "rating": w_rating,
                        "experience": w_experience,
                        "earliest": w_earliest,
                        "low_load": w_load
                    }
                }

                scored_candidates.append({
                    "doctor": doctor,
                    "earliest_slot": earliest_slot,
                    "all_slots": avail_info.get("slots", []),
                    "composite_score": composite_score,
                    "score_breakdown": breakdown,
                    "appointment_load": load,
                })

            # Sort descending by composite score
            scored_candidates.sort(key=lambda x: x["composite_score"], reverse=True)
            best_candidate = scored_candidates[0]

            best_doctor = best_candidate["doctor"]
            best_slot = best_candidate["earliest_slot"]
            best_score = best_candidate["composite_score"]
            breakdown = best_candidate["score_breakdown"]

            slot_desc = (
                f"on {best_slot['date']} at {best_slot['start_time']}"
                if best_slot
                else "with flexible scheduling"
            )
            optimal_reason_template = load_prompt("decision_optimal_reason.txt")
            decision_reason = optimal_reason_template.format(
                doctor_name=best_doctor.get("full_name", "Doctor"),
                score_pct=int(best_score * 100),
                rating=best_doctor.get("rating", 4.8),
                experience_years=best_doctor.get("experience_years", 5),
                appointment_load=best_candidate.get("appointment_load", 0),
                slot_desc=slot_desc
            )

            # Persist decision to database if symptom_id is provided
            db_decision_id = None
            if symptom_id:
                try:
                    slot_str = f"{best_slot['date']} {best_slot['start_time']}" if best_slot else "Unscheduled"
                    decision_rec = AgentDecision(
                        symptom_id=symptom_id,
                        recommended_doctor_id=best_doctor["id"],
                        recommended_slot=slot_str,
                        decision_score=best_score,
                        score_breakdown=json.dumps(breakdown),
                        decision_reason=decision_reason
                    )
                    db.session.add(decision_rec)
                    db.session.commit()
                    db_decision_id = decision_rec.id
                    logger.info(f"Persisted AgentDecision ID {db_decision_id}")
                except Exception as db_err:
                    db.session.rollback()
                    logger.warning(f"Could not persist decision record: {str(db_err)}")

            return {
                "success": True,
                "decision_id": db_decision_id,
                "recommended_doctor": best_doctor,
                "recommended_slot": best_slot,
                "decision_score": best_score,
                "score_breakdown": breakdown,
                "decision_reason": decision_reason,
                "ranked_candidates": scored_candidates,
            }

        except Exception as e:
            logger.error(f"Error in DecisionAgent: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "recommended_doctor": None,
                "recommended_slot": None,
                "decision_reason": "Decision engine encountered an error evaluating doctors.",
            }
