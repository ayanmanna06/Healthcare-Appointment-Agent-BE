import re
import json
import logging
import requests
from typing import Dict, Any, List
from backend.config import Config

logger = logging.getLogger("SymptomAgent")
logger.setLevel(logging.INFO)

# Clinical taxonomy mapping symptom keywords to specialties
TAXONOMY: Dict[str, Dict[str, Any]] = {
    "General Physician": {
        "keywords": [
            "fever", "headache", "fatigue", "weakness", "body ache", "chills", "cold",
            "cough", "flu", "malaise", "sweating", "viral", "nausea", "loss of appetite",
            "drowsy", "exhaustion", "sore throat", "mild pain", "unwell"
        ],
        "weight": 1.0,
    },
    "Cardiologist": {
        "keywords": [
            "chest pain", "heart", "palpitations", "shortness of breath", "angina",
            "breathlessness", "hypertension", "high blood pressure", "irregular heartbeat",
            "fluttering", "dizziness", "left arm pain", "cardiac", "pulse racing"
        ],
        "weight": 1.4,
    },
    "Neurologist": {
        "keywords": [
            "migraine", "severe headache", "seizure", "numbness", "tingling",
            "memory loss", "tremor", "paralysis", "stroke", "confusion", "fainting",
            "blackout", "vertigo", "loss of balance", "nerve pain", "neuropathy"
        ],
        "weight": 1.3,
    },
    "Orthopedic": {
        "keywords": [
            "joint pain", "back pain", "knee", "fracture", "sprain", "swelling",
            "ligament", "shoulder pain", "arthritis", "stiffness", "bone pain",
            "spine", "hip pain", "ankle pain", "difficulty walking", "cartilage"
        ],
        "weight": 1.2,
    },
    "Dermatologist": {
        "keywords": [
            "skin rash", "rash", "itching", "acne", "eczema", "psoriasis", "hives",
            "hair loss", "mole", "blister", "dermatitis", "dry patch", "scalp",
            "skin allergy", "pigmentation", "redness on skin", "boil"
        ],
        "weight": 1.2,
    },
    "Pediatrician": {
        "keywords": [
            "child", "baby", "infant", "kid", "toddler", "pediatric", "teething",
            "vaccination", "crying infant", "colic", "childhood rash", "growth"
        ],
        "weight": 1.4,
    },
    "ENT": {
        "keywords": [
            "ear pain", "ear ache", "sore throat", "sinus", "congestion", "hearing loss",
            "tinnitus", "nasal", "runny nose", "tonsils", "tonsillitis", "hoarse voice",
            "swallowing pain", "ear infection", "blocked ear", "ringing in ear"
        ],
        "weight": 1.2,
    },
    "Gynecologist": {
        "keywords": [
            "period", "menstrual", "cramps", "pregnancy", "pelvic pain", "ovarian",
            "vaginal", "pcos", "irregular cycle", "hormonal", "menopause", "prenatal",
            "uterine", "breast tenderness", "bleeding between periods"
        ],
        "weight": 1.3,
    },
}

EMERGENCY_TRIGGERS = [
    "chest pain radiating", "severe difficulty breathing", "sudden paralysis",
    "unconscious", "coughing blood", "sudden loss of vision", "severe chest pressure",
    "severe head trauma", "heavy bleeding"
]

HIGH_URGENCY_TRIGGERS = [
    "chest pain", "shortness of breath", "high fever", "seizure", "blackout",
    "severe abdominal pain", "fainting", "severe migraine", "fracture"
]

class SymptomAgent:
    """
    AI Symptom Analysis Agent
    Parses natural language symptoms using configured LLM inference (from .env),
    with automatic fallback to clinical taxonomy rules and urgency detection.
    """

    def __init__(self):
        self.taxonomy = TAXONOMY
        self.llm_url = Config.LLM_API_URL
        self.llm_model = Config.LLM_MODEL
        self.llm_timeout = Config.LLM_TIMEOUT

    def analyze(self, symptom_text: str) -> Dict[str, Any]:
        """
        Analyze patient's text and return matched specialties, confidence scores, and urgency.
        Attempts LLM inference first, falling back to clinical taxonomy.
        """
        if not symptom_text or not isinstance(symptom_text, str):
            raise ValueError("Symptom text must be a non-empty string.")

        cleaned_text = symptom_text.strip()
        logger.info(f"Analyzing symptom text: {cleaned_text}")

        # Attempt remote LLM analysis if endpoint configured in .env
        if self.llm_url and self.llm_model:
            llm_result = self._analyze_with_llm(cleaned_text)
            if llm_result:
                return llm_result

        # Fallback to rule-based NLP taxonomy engine
        return self._analyze_with_taxonomy(cleaned_text)

    def _analyze_with_llm(self, text: str) -> Dict[str, Any] | None:
        """
        Query LLM service configured via .env variables.
        """
        try:
            logger.info(f"Calling LLM service at {self.llm_url} with model {self.llm_model}...")

            valid_specs = list(self.taxonomy.keys())
            prompt = (
                f"You are an expert AI Clinical Triage Specialist in a Hospital Appointment System.\n"
                f"Patient Symptoms: \"{text}\"\n\n"
                f"Allowed Specializations (choose exactly one for primary_specialization):\n"
                f"{json.dumps(valid_specs)}\n\n"
                f"Respond ONLY with a valid JSON object strictly matching this format:\n"
                f"```json\n"
                f"{{\n"
                f"  \"primary_specialization\": \"<one of the allowed specializations>\",\n"
                f"  \"confidence_score\": <float between 0.60 and 0.99>,\n"
                f"  \"urgency_level\": \"<low | medium | high | emergency>\",\n"
                f"  \"extracted_keywords\": [\"keyword1\", \"keyword2\"],\n"
                f"  \"summary\": \"<Concise 1-2 sentence medical triage reasoning>\"\n"
                f"}}\n"
                f"```"
            )

            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }

            resp = requests.post(self.llm_url, json=payload, timeout=self.llm_timeout)
            if resp.status_code == 200:
                raw_response = resp.json().get("response", "")
                # Extract JSON block if wrapped
                json_str = raw_response
                if "```json" in raw_response:
                    json_str = raw_response.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_response:
                    json_str = raw_response.split("```")[1].split("```")[0].strip()

                parsed = json.loads(json_str)

                primary_spec = parsed.get("primary_specialization")
                if primary_spec in self.taxonomy:
                    conf = float(parsed.get("confidence_score", 0.88))
                    urgency = parsed.get("urgency_level", "medium").lower()
                    if urgency not in ["low", "medium", "high", "emergency"]:
                        urgency = "medium"

                    keywords = parsed.get("extracted_keywords", [])
                    summary = parsed.get("summary", f"LLM recommended {primary_spec}.")

                    # Generate rankings relative to the primary recommendation
                    rankings = [
                        {"specialization": primary_spec, "confidence": conf, "matched_keywords": keywords}
                    ]
                    for s in valid_specs:
                        if s != primary_spec:
                            rankings.append({"specialization": s, "confidence": round(max(0.1, (1.0 - conf) / 3.0), 2), "matched_keywords": []})

                    logger.info(f"LLM analysis succeeded: {primary_spec} ({conf})")
                    return {
                        "success": True,
                        "raw_text": text,
                        "primary_specialization": primary_spec,
                        "confidence_score": conf,
                        "urgency_level": urgency,
                        "extracted_keywords": keywords,
                        "rankings": rankings,
                        "summary": summary,
                        "source": f"LLM ({self.llm_model})",
                    }

        except Exception as e:
            logger.warning(f"LLM analysis failed or timed out ({str(e)}). Falling back to taxonomy analysis.")

        return None

    def _analyze_with_taxonomy(self, symptom_text: str) -> Dict[str, Any]:
        """
        Rule-based NLP taxonomy fallback.
        """
        cleaned_text = symptom_text.lower().strip()

        # Check urgency
        urgency = "low"
        for trigger in EMERGENCY_TRIGGERS:
            if trigger in cleaned_text:
                urgency = "emergency"
                break

        if urgency != "emergency":
            for trigger in HIGH_URGENCY_TRIGGERS:
                if trigger in cleaned_text:
                    urgency = "high"
                    break

        if urgency == "low" and any(w in cleaned_text for w in ["fever", "pain", "swelling", "vomiting", "bleeding"]):
            urgency = "medium"

        specialty_scores = {}
        matched_keywords_by_spec = {}
        all_extracted_keywords = set()

        for spec_name, spec_data in self.taxonomy.items():
            score = 0.0
            matched_kw = []
            weight = spec_data["weight"]

            for kw in spec_data["keywords"]:
                pattern = r"\b" + re.escape(kw) + r"\b"
                matches = len(re.findall(pattern, cleaned_text))
                if matches > 0:
                    kw_weight = 2.0 if " " in kw else 1.0
                    score += (matches * kw_weight * weight)
                    matched_kw.append(kw)
                    all_extracted_keywords.add(kw)

            specialty_scores[spec_name] = score
            matched_keywords_by_spec[spec_name] = matched_kw

        total_raw_score = sum(specialty_scores.values())

        if total_raw_score == 0:
            specialty_scores["General Physician"] = 1.0
            matched_keywords_by_spec["General Physician"] = ["general wellness"]
            total_raw_score = 1.0
            top_spec = "General Physician"
            confidence = 0.55
        else:
            top_spec = max(specialty_scores, key=specialty_scores.get)
            top_raw = specialty_scores[top_spec]
            confidence = min(0.98, max(0.65, round(top_raw / (total_raw_score + 1.2) * 1.35, 2)))

        rankings = []
        for spec, raw_s in sorted(specialty_scores.items(), key=lambda x: x[1], reverse=True):
            if raw_s > 0:
                spec_conf = round(raw_s / max(total_raw_score, 1.0), 2)
                rankings.append({
                    "specialization": spec,
                    "confidence": spec_conf,
                    "matched_keywords": matched_keywords_by_spec.get(spec, []),
                })

        logger.info(f"Taxonomy analysis completed: {top_spec} ({confidence})")
        return {
            "success": True,
            "raw_text": symptom_text,
            "primary_specialization": top_spec,
            "confidence_score": confidence,
            "urgency_level": urgency,
            "extracted_keywords": list(all_extracted_keywords),
            "rankings": rankings,
            "summary": f"Identified primary need for {top_spec} with {int(confidence * 100)}% confidence based on detected symptoms: {', '.join(all_extracted_keywords) if all_extracted_keywords else 'general complaint'}.",
            "source": "Clinical Taxonomy Rules",
        }
