import pytest
from datetime import date
from backend.app import create_app
from backend.extensions import db
from backend.agents.symptom_agent import SymptomAgent
from backend.agents.matching_agent import MatchingAgent
from backend.agents.availability_agent import AvailabilityAgent
from backend.agents.decision_agent import DecisionAgent
from backend.agents.notification_agent import NotificationAgent

@pytest.fixture(scope="module")
def test_app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        # Seed minimum data for test
        from backend.seed import seed_database
        seed_database()
        yield app

def test_symptom_agent_general_fever():
    agent = SymptomAgent()
    result = agent.analyze("I have fever and headache for 3 days")
    assert result["success"] is True
    assert result["primary_specialization"] == "General Physician"
    assert result["confidence_score"] >= 0.60
    assert "fever" in result["extracted_keywords"] or "headache" in result["extracted_keywords"]

def test_symptom_agent_cardiac_emergency():
    agent = SymptomAgent()
    result = agent.analyze("Severe chest pain radiating to my left arm and breathlessness")
    assert result["success"] is True
    assert result["primary_specialization"] == "Cardiologist"
    assert result["urgency_level"] in ["high", "emergency"]
    assert result["confidence_score"] >= 0.70

def test_symptom_agent_neurology_migraine():
    agent = SymptomAgent()
    result = agent.analyze("Intense migraine, tingling sensation and severe vertigo")
    assert result["success"] is True
    assert result["primary_specialization"] == "Neurologist"

def test_matching_agent(test_app):
    with test_app.app_context():
        agent = MatchingAgent()
        result = agent.match_doctors(specialization_name="Cardiologist")
        assert result["success"] is True
        assert result["count"] >= 1
        assert any(d["specialization_name"] == "Cardiologist" for d in result["doctors"])

def test_availability_agent(test_app):
    with test_app.app_context():
        from backend.models.doctor import Doctor
        doc = Doctor.query.first()
        assert doc is not None

        agent = AvailabilityAgent()
        slots_data = agent.get_available_slots(doctor_id=doc.id, days_ahead=7)
        assert slots_data["success"] is True
        assert "slots" in slots_data
        assert isinstance(slots_data["slots"], list)

def test_decision_agent_formula():
    decision_agent = DecisionAgent()
    candidate_doctors = [
        {
            "doctor": {
                "id": 1,
                "full_name": "Dr. High Rating",
                "rating": 4.95,
                "experience_years": 15,
                "consultation_fee": 100.0,
            },
            "availability": {
                "earliest_slot": {
                    "date": "2026-10-01",
                    "start_time": "10:00",
                    "end_time": "10:30",
                    "slot_datetime": "2026-10-01T10:00:00"
                },
                "slots": [],
                "appointment_load": 2,
            }
        },
        {
            "doctor": {
                "id": 2,
                "full_name": "Dr. Busy Junior",
                "rating": 3.80,
                "experience_years": 2,
                "consultation_fee": 50.0,
            },
            "availability": {
                "earliest_slot": {
                    "date": "2026-10-05",
                    "start_time": "16:00",
                    "end_time": "16:30",
                    "slot_datetime": "2026-10-05T16:00:00"
                },
                "slots": [],
                "appointment_load": 14,
            }
        }
    ]

    eval_result = decision_agent.evaluate(candidate_doctors)
    assert eval_result["success"] is True
    # Dr. High Rating must win based on weighted score formula
    assert eval_result["recommended_doctor"]["id"] == 1
    assert eval_result["decision_score"] > 0.70
    assert "score_breakdown" in eval_result
    assert "decision_reason" in eval_result

def test_notification_agent_mock(test_app):
    with test_app.app_context():
        agent = NotificationAgent()
        res = agent.send_booking_confirmation(
            user_id=1,
            recipient_email="test.patient@example.com",
            patient_name="Test Patient",
            doctor_name="Dr. Test",
            specialization="General Physician",
            appointment_date="2026-10-01",
            start_time="09:00",
        )
        assert res["success"] is True
