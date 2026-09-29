import os
import sys
from datetime import time

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.role import Role
from backend.models.doctor import Doctor
from backend.models.specialization import Specialization
from backend.models.doctor_availability import DoctorAvailability

def add_doctors():
    app = create_app()
    with app.app_context():
        doctor_role = Role.query.filter_by(name="doctor").first()
        if not doctor_role:
            print("Doctor role not found!")
            return

        specs = {s.name: s for s in Specialization.query.all()}

        new_doctors_info = [
            {
                "name": "Dr. Alexander Wright",
                "email": "doctor.alexander@healthagent.ai",
                "specialization": "Dermatologist",
                "qualification": "MD, FAAD, Johns Hopkins",
                "experience_years": 12,
                "rating": 4.88,
                "consultation_fee": 95.0,
                "bio": "Clinical dermatologist specializing in allergic dermatosis, eczema, contact dermatitis, and urticaria management.",
                "room": "Derma Suite 112",
            },
            {
                "name": "Dr. Sophia Chen",
                "email": "doctor.sophia@healthagent.ai",
                "specialization": "Dermatologist",
                "qualification": "MD (Dermatology), Stanford Medicine",
                "experience_years": 8,
                "rating": 4.91,
                "consultation_fee": 90.0,
                "bio": "Dermatologist focused on acute skin rashes, hives, immunodermatology, and customized allergy therapeutic plans.",
                "room": "Derma Care 115",
            },
            {
                "name": "Dr. Marcus Brody",
                "email": "doctor.brody@healthagent.ai",
                "specialization": "General Physician",
                "qualification": "MD, Harvard Medical School",
                "experience_years": 14,
                "rating": 4.87,
                "consultation_fee": 70.0,
                "bio": "Internal medicine consultant skilled in multisystem diagnoses, acute infection assessment, and adult primary health.",
                "room": "Internal Medicine 104",
            },
            {
                "name": "Dr. Aisha Khan",
                "email": "doctor.aisha@healthagent.ai",
                "specialization": "General Physician",
                "qualification": "MBBS, MRCP, King's College London",
                "experience_years": 11,
                "rating": 4.92,
                "consultation_fee": 75.0,
                "bio": "Primary care physician dedicated to comprehensive diagnostic workups, urgent consultations, and preventative medicine.",
                "room": "Primary Care 106",
            },
            {
                "name": "Dr. Julian Sterling",
                "email": "doctor.julian@healthagent.ai",
                "specialization": "Cardiologist",
                "qualification": "MD, FACC, Cleveland Clinic",
                "experience_years": 16,
                "rating": 4.96,
                "consultation_fee": 135.0,
                "bio": "Consultant cardiologist with focus on cardiovascular risk assessment, arrhythmias, and hypertension management.",
                "room": "Cardio Wing 405",
            },
            {
                "name": "Dr. Clara Oswald",
                "email": "doctor.clara@healthagent.ai",
                "specialization": "Neurologist",
                "qualification": "MD, PhD, Oxford University",
                "experience_years": 10,
                "rating": 4.90,
                "consultation_fee": 125.0,
                "bio": "Specialist in neuro-inflammatory conditions, severe headaches, peripheral neuropathies, and vestibular medicine.",
                "room": "Neuro Clinic 308",
            },
            {
                "name": "Dr. Nathan Reed",
                "email": "doctor.nathan@healthagent.ai",
                "specialization": "Orthopedic",
                "qualification": "MS, FRCS, Mayo Clinic",
                "experience_years": 13,
                "rating": 4.89,
                "consultation_fee": 115.0,
                "bio": "Specialist in acute joint injuries, tendonitis, sports rehabilitation, and minimally invasive orthopedics.",
                "room": "Orthopedics 206",
            },
            {
                "name": "Dr. Emily Watson",
                "email": "doctor.emily@healthagent.ai",
                "specialization": "Pediatrician",
                "qualification": "MD, FAAP, University of Toronto",
                "experience_years": 9,
                "rating": 4.93,
                "consultation_fee": 80.0,
                "bio": "Pediatric specialist passionate about childhood infections, preventative immunization, and allergy relief.",
                "room": "Pediatrics 107",
            },
            {
                "name": "Dr. Oliver Hayes",
                "email": "doctor.oliver@healthagent.ai",
                "specialization": "ENT",
                "qualification": "MS, Cambridge University",
                "experience_years": 11,
                "rating": 4.84,
                "consultation_fee": 95.0,
                "bio": "Ear, nose, and throat surgeon specialized in rhinology, allergy-induced sinusitis, and throat conditions.",
                "room": "ENT Suite 208",
            },
            {
                "name": "Dr. Priya Sharma",
                "email": "doctor.priya@healthagent.ai",
                "specialization": "Gynecologist",
                "qualification": "MD, FACOG, Penn Medicine",
                "experience_years": 12,
                "rating": 4.93,
                "consultation_fee": 105.0,
                "bio": "Comprehensive women's healthcare, endocrine balance, prenatal care, and minimally invasive surgery.",
                "room": "Women's Health 315",
            },
        ]

        added_count = 0
        for info in new_doctors_info:
            existing = User.query.filter_by(email=info["email"]).first()
            if existing:
                print(f"Doctor {info['name']} already exists.")
                continue

            u = User(
                email=info["email"],
                full_name=info["name"],
                phone=f"+1-555-0{200 + added_count}",
                role_id=doctor_role.id,
            )
            u.set_password("doctor123")
            db.session.add(u)
            db.session.flush()

            spec_obj = specs.get(info["specialization"])
            if not spec_obj:
                print(f"Warning: Spec {info['specialization']} not found!")
                continue

            d = Doctor(
                user_id=u.id,
                specialization_id=spec_obj.id,
                qualification=info["qualification"],
                experience_years=info["experience_years"],
                rating=info["rating"],
                consultation_fee=info["consultation_fee"],
                bio=info["bio"],
                room_number=info["room"],
            )
            db.session.add(d)
            db.session.flush()

            # Add availability Monday - Friday morning & afternoon, and Saturday
            for dow in [0, 1, 2, 3, 4]:
                av1 = DoctorAvailability(
                    doctor_id=d.id,
                    day_of_week=dow,
                    start_time=time(9, 0),
                    end_time=time(13, 0),
                    slot_duration_minutes=30,
                    is_active=True,
                )
                av2 = DoctorAvailability(
                    doctor_id=d.id,
                    day_of_week=dow,
                    start_time=time(14, 0),
                    end_time=time(17, 0),
                    slot_duration_minutes=30,
                    is_active=True,
                )
                db.session.add_all([av1, av2])

            av_sat = DoctorAvailability(
                doctor_id=d.id,
                day_of_week=5,
                start_time=time(10, 0),
                end_time=time(14, 0),
                slot_duration_minutes=30,
                is_active=True,
            )
            db.session.add(av_sat)
            added_count += 1

        db.session.commit()
        print(f"Successfully added {added_count} new doctors with weekly schedules.")

if __name__ == "__main__":
    add_doctors()
    # Force exit to avoid apscheduler keeping script alive
    os._exit(0)
