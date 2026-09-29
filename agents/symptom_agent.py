import re
import json
import logging
import requests
from typing import Dict, Any, List
from backend.config import Config
from backend.services.prompt_loader import load_prompt

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

GREETING_PATTERNS = [
    r"\b(hi|hello|hey|heya|howdy|hola|yo|sup|hiya|gm|gn)\b",
    r"\bgood\s*(morning|afternoon|evening|day|night)\b",
    r"\b(how\s*are\s*you|how\s*r\s*u|how\s*do\s*you\s*do|what's\s*up|whats\s*up)\b",
    r"\b(who\s*are\s*you|what\s*are\s*you|what\s*can\s*you\s*do|introduce\s*yourself|what\s*is\s*your\s*name)\b",
    r"\b(help|help\s*me|can\s*you\s*help|need\s*help|greetings|welcome|hi\s*there|hello\s*there)\b",
    r"\b(thank\s*you|thanks|thx|bye|goodbye|see\s*you|ok|okay|fine|cool|sure|yes|no)\b",
]

ADDITIONAL_PHYSICAL_SYMPTOM_KEYWORDS = [
    "pain", "ache", "aches", "aching", "hurt", "hurts", "hurting", "sore", "soreness",
    "burn", "burning", "infection", "infected", "inflammation", "inflamed",
    "feverish", "high temp", "temperature", "shivering", "shivers", "sweat", "sweating",
    "sneeze", "sneezing", "vomit", "vomiting", "throw up", "throwing up",
    "nauseous", "dizzy", "bleed", "bleeding", "blood", "wound", "injury", "injured",
    "fractured", "broken bone", "broken", "bruise", "bruised", "cut", "laceration",
    "itch", "itchy", "blisters", "allergy", "allergic", "reaction",
    "sick", "sickness", "ill", "illness", "tired", "tiredness", "exhausted",
    "weak", "cramp", "cramping", "diarrhea", "loose motion", "constipation",
    "bloating", "gas", "indigestion", "acidity", "heartburn", "acid reflux",
    "breath", "breathing", "wheezing", "asthma", "suffocating", "chest tightness",
    "pressure in chest", "spasm", "twitching", "convulsion", "faint",
    "insomnia", "sleepless", "swollen", "stiff", "stiffness",
    "head", "forehead", "throat", "neck", "shoulder", "arm", "elbow", "wrist",
    "hand", "finger", "fingers", "chest", "rib", "ribs", "abdomen", "stomach",
    "belly", "tummy", "waist", "hip", "groin", "leg", "thigh", "knee", "shin",
    "calf", "ankle", "foot", "feet", "toe", "toes", "back", "lower back",
    "spine", "muscle", "muscles", "bone", "bones", "joint", "joints",
    "skin", "eye", "eyes", "ear", "ears", "nose", "mouth", "lip", "lips",
    "tongue", "tooth", "teeth", "gum", "gums", "jaw"
]

# Precomputed aggregate of all medical and physical symptom keywords
ALL_SYMPTOM_KEYWORDS = set()
for _spec_info in TAXONOMY.values():
    for _kw in _spec_info["keywords"]:
        ALL_SYMPTOM_KEYWORDS.add(_kw.lower())
for _kw in ADDITIONAL_PHYSICAL_SYMPTOM_KEYWORDS:
    ALL_SYMPTOM_KEYWORDS.add(_kw.lower())

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

    def _classify_intent(self, text: str) -> Dict[str, Any]:
        """
        Classifies incoming input into:
        1. Clinical symptom consultation (physical health issue present)
        2. Friendly greeting (hi, hello, etc.)
        3. Off-topic query (non-health, coding, math, general chitchat)
        """
        cleaned = text.strip()
        cleaned_lower = cleaned.lower()

        # Check if any physical symptom or anatomical health keyword is present
        has_symptom = False
        matched_symptoms = []
        for kw in ALL_SYMPTOM_KEYWORDS:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, cleaned_lower):
                has_symptom = True
                matched_symptoms.append(kw)

        if has_symptom:
            return {
                "is_medical_query": True,
                "intent_type": "clinical",
                "matched_symptoms": matched_symptoms,
            }

        # Check for greeting or introductory intent
        is_greeting = False
        for g_pat in GREETING_PATTERNS:
            if re.search(g_pat, cleaned_lower):
                is_greeting = True
                break

        if is_greeting:
            return {
                "success": True,
                "is_medical_query": False,
                "intent_type": "greeting",
                "agent_message": load_prompt("greeting_response.txt"),
                "summary": "Greeting detected without clinical symptoms. Waiting for physical symptom description.",
                "primary_specialization": None,
                "confidence_score": 0.0,
                "urgency_level": "none",
                "extracted_keywords": [],
                "rankings": [],
                "source": "Clinical Intent Classifier",
            }

        # Otherwise, the query is off-topic / non-medical
        return {
            "success": True,
            "is_medical_query": False,
            "intent_type": "off_topic",
            "agent_message": load_prompt("off_topic_response.txt"),
            "summary": "Non-clinical query detected. Prompted user to describe physical health symptoms.",
            "primary_specialization": None,
            "confidence_score": 0.0,
            "urgency_level": "none",
            "extracted_keywords": [],
            "rankings": [],
            "source": "Clinical Intent Classifier",
        }

    def analyze(self, symptom_text: str) -> Dict[str, Any]:
        """
        Analyze patient's text and return matched specialties, confidence scores, and urgency.
        Attempts LLM inference first, falling back to clinical taxonomy.
        """
        if not symptom_text or not isinstance(symptom_text, str):
            raise ValueError("Symptom text must be a non-empty string.")

        cleaned_text = symptom_text.strip()
        logger.info(f"Analyzing symptom text: {cleaned_text}")

        # Intent classification: verify if the input is a greeting, off-topic, or clinical
        intent = self._classify_intent(cleaned_text)
        if not intent.get("is_medical_query", True):
            logger.info(f"Non-clinical query detected ({intent.get('intent_type')}). Skipping specialist matching.")
            return intent

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
            prompt_template = load_prompt("clinical_triage.txt")
            prompt = prompt_template.format(
                symptom_text=text,
                allowed_specializations=json.dumps(valid_specs)
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
                        "is_medical_query": True,
                        "intent_type": "clinical",
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
        summary_template = load_prompt("clinical_summary.txt")
        summary_text = summary_template.format(
            specialization=top_spec,
            confidence_percent=int(confidence * 100),
            detected_symptoms=", ".join(all_extracted_keywords) if all_extracted_keywords else "general complaint"
        )
        return {
            "success": True,
            "is_medical_query": True,
            "intent_type": "clinical",
            "raw_text": symptom_text,
            "primary_specialization": top_spec,
            "confidence_score": confidence,
            "urgency_level": urgency,
            "extracted_keywords": list(all_extracted_keywords),
            "rankings": rankings,
            "summary": summary_text,
            "source": "Clinical Taxonomy Rules",
        }
