import pytest
import json
from backend.app import create_app
from backend.extensions import db

@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        from backend.seed import seed_database
        seed_database()
        with app.test_client() as test_client:
            yield test_client

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"

def test_login_patient_success(client):
    res = client.post("/api/auth/login", json={
        "email": "patient@example.com",
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["role"] == "patient"

def test_login_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "email": "patient@example.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False

def test_symptom_consultation_pipeline(client):
    res = client.post("/api/patient/symptoms", json={
        "symptoms": "I have fever and headache for 3 days"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["analysis"]["primary_specialization"] == "General Physician"
    assert "workflow_trace" in data
    assert len(data["workflow_trace"]) >= 5
    assert data["recommendation"]["doctor"] is not None

def test_list_doctors_and_specializations(client):
    res_docs = client.get("/api/patient/doctors")
    assert res_docs.status_code == 200
    data_docs = res_docs.get_json()
    assert data_docs["count"] >= 1

    res_specs = client.get("/api/patient/specializations")
    assert res_specs.status_code == 200
    data_specs = res_specs.get_json()
    assert len(data_specs["specializations"]) >= 8

def test_admin_analytics_with_token(client):
    # Login as admin
    login_res = client.post("/api/auth/login", json={
        "email": "admin@healthagent.ai",
        "password": "admin123"
    })
    token = login_res.get_json()["token"]

    # Request analytics
    analytics_res = client.get("/api/admin/analytics", headers={
        "Authorization": f"Bearer {token}"
    })
    assert analytics_res.status_code == 200
    data = analytics_res.get_json()
    assert data["success"] is True
    assert "metrics" in data
    assert "appointments_per_day" in data
    assert "specialization_distribution" in data
