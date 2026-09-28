from datetime import datetime, date, time, timedelta
from backend.app import create_app
from backend.extensions import db
from backend.models import (
    Role,
    User,
    Specialization,
    Patient,
    Doctor,
    DoctorAvailability,
    Appointment,
    Symptom,
    AgentDecision,
    Notification,
    MedicalNote,
)

def seed_database():
    app = create_app()
    with app.app_context():
        print("[*] Seeding database for Healthcare Appointment Agent...")
        db.create_all()

        # 1. Seed Roles
        roles = {}
        for role_name, desc in [
            ("admin", "System Administrator with full analytical and operational access"),
            ("doctor", "Licensed Medical Practitioner managing appointments and notes"),
            ("patient", "Registered Patient seeking consultations and scheduling"),
        ]:
            r = Role.query.filter_by(name=role_name).first()
            if not r:
                r = Role(name=role_name, description=desc)
                db.session.add(r)
                db.session.flush()
            roles[role_name] = r

        # 2. Seed Specializations
        specs_data = [
            {
                "name": "General Physician",
                "icon": "health_and_safety",
                "description": "Primary care, fevers, general infections, chronic disease checkups, and systemic ailments.",
                "keywords": "fever, headache, fatigue, weakness, body ache, chills, cold, cough, flu, malaise, viral, nausea, infection",
            },
            {
                "name": "Cardiologist",
                "icon": "favorite",
                "description": "Heart disease, cardiovascular conditions, chest pain, hypertension, and arrhythmias.",
                "keywords": "chest pain, heart, palpitations, shortness of breath, angina, hypertension, high blood pressure, irregular heartbeat, arm pain",
            },
            {
                "name": "Neurologist",
                "icon": "psychology",
                "description": "Brain and nervous system disorders, migraines, seizures, tremors, neuropathy, and vertigo.",
                "keywords": "migraine, severe headache, seizure, numbness, tingling, memory loss, tremor, paralysis, stroke, confusion, fainting, vertigo",
            },
            {
                "name": "Orthopedic",
                "icon": "accessibility_new",
                "description": "Bones, joints, ligaments, spine, sports injuries, fractures, and arthritis care.",
                "keywords": "joint pain, back pain, knee, fracture, sprain, swelling, ligament, shoulder pain, arthritis, stiffness, bone pain, spine",
            },
            {
                "name": "Dermatologist",
                "icon": "spa",
                "description": "Skin, hair, nail conditions, rashes, eczema, acne, psoriasis, and dermatitis.",
                "keywords": "skin rash, rash, itching, acne, eczema, psoriasis, hives, hair loss, mole, blister, dermatitis, dry patch, allergy",
            },
            {
                "name": "Pediatrician",
                "icon": "child_care",
                "description": "Comprehensive healthcare for infants, children, adolescents, and immunization.",
                "keywords": "child, baby, infant, kid, toddler, pediatric, teething, vaccination, colic, childhood rash, growth",
            },
            {
                "name": "ENT",
                "icon": "hearing",
                "description": "Ear, nose, throat, sinusitis, hearing loss, allergies, and vocal disorders.",
                "keywords": "ear pain, ear ache, sore throat, sinus, congestion, hearing loss, tinnitus, nasal, runny nose, tonsils, hoarse voice",
            },
            {
                "name": "Gynecologist",
                "icon": "pregnant_woman",
                "description": "Women's reproductive health, prenatal care, menstrual disorders, and hormonal wellness.",
                "keywords": "period, menstrual, cramps, pregnancy, pelvic pain, ovarian, vaginal, pcos, irregular cycle, hormonal, prenatal",
            },
        ]

        specs_map = {}
        for s_data in specs_data:
            spec = Specialization.query.filter_by(name=s_data["name"]).first()
            if not spec:
                spec = Specialization(
                    name=s_data["name"],
                    icon=s_data["icon"],
                    description=s_data["description"],
                    keywords=s_data["keywords"],
                )
                db.session.add(spec)
                db.session.flush()
            specs_map[s_data["name"]] = spec

        # 3. Seed Admin User
        admin_user = User.query.filter_by(email="admin@healthagent.ai").first()
        if not admin_user:
            admin_user = User(
                email="admin@healthagent.ai",
                full_name="Admin Administrator",
                phone="+1-555-0100",
                role_id=roles["admin"].id,
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.flush()

        # 4. Seed Doctors
        doctors_info = [
            {
                "name": "Dr. Sarah Adams",
                "email": "doctor.sarah@healthagent.ai",
                "specialization": "Cardiologist",
                "qualification": "MD, FACC, Harvard Medical School",
                "experience_years": 14,
                "rating": 4.92,
                "consultation_fee": 120.0,
                "bio": "Senior Interventional Cardiologist specializing in preventive cardiac care and heart rhythm management.",
                "room": "Cardiology Suite 401",
            },
            {
                "name": "Dr. Marcus Vance",
                "email": "doctor.marcus@healthagent.ai",
                "specialization": "Neurologist",
                "qualification": "MD, DM (Neurology), Johns Hopkins",
                "experience_years": 12,
                "rating": 4.88,
                "consultation_fee": 130.0,
                "bio": "Board-certified neurologist dedicated to neurodegenerative treatment, complex migraines, and seizure disorders.",
                "room": "Neurology Wing 305",
            },
            {
                "name": "Dr. Elena Rostova",
                "email": "doctor.elena@healthagent.ai",
                "specialization": "General Physician",
                "qualification": "MBBS, MD (Internal Medicine), Stanford",
                "experience_years": 10,
                "rating": 4.95,
                "consultation_fee": 65.0,
                "bio": "Compassionate internal medicine specialist focusing on comprehensive diagnosis, holistic recovery, and primary health.",
                "room": "Clinic Consultation 102",
            },
            {
                "name": "Dr. James Wilson",
                "email": "doctor.james@healthagent.ai",
                "specialization": "Orthopedic",
                "qualification": "MS, M.Ch (Orthopedics), Oxford",
                "experience_years": 16,
                "rating": 4.85,
                "consultation_fee": 110.0,
                "bio": "Orthopedic surgeon renowned for sports injury rehabilitation, arthroscopy, and joint preservation.",
                "room": "Orthopedics Block 204",
            },
            {
                "name": "Dr. Maya Patel",
                "email": "doctor.maya@healthagent.ai",
                "specialization": "Dermatologist",
                "qualification": "MD (Dermatology), AIIMS",
                "experience_years": 9,
                "rating": 4.94,
                "consultation_fee": 85.0,
                "bio": "Expert clinical and cosmetic dermatologist specializing in chronic skin allergies, acne therapies, and laser surgery.",
                "room": "Derma Care 108",
            },
            {
                "name": "Dr. David Chen",
                "email": "doctor.chen@healthagent.ai",
                "specialization": "Pediatrician",
                "qualification": "MD, FAAP, Columbia University",
                "experience_years": 11,
                "rating": 4.91,
                "consultation_fee": 75.0,
                "bio": "Dedicated pediatrician committed to child developmental milestones, pediatric emergency medicine, and neonatal health.",
                "room": "Pediatrics Zone 105",
            },
            {
                "name": "Dr. Robert Miller",
                "email": "doctor.miller@healthagent.ai",
                "specialization": "ENT",
                "qualification": "MS (ENT), Edinburgh",
                "experience_years": 15,
                "rating": 4.79,
                "consultation_fee": 90.0,
                "bio": "Otolaryngologist with high success in sinus microsurgery, voice disorders, and pediatric ear infections.",
                "room": "ENT Clinic 202",
            },
            {
                "name": "Dr. Lisa Montgomery",
                "email": "doctor.lisa@healthagent.ai",
                "specialization": "Gynecologist",
                "qualification": "MD, FACOG, Yale School of Medicine",
                "experience_years": 13,
                "rating": 4.89,
                "consultation_fee": 100.0,
                "bio": "Senior obstetrician and gynecologist delivering holistic maternal health, PCOS management, and laparoscopic care.",
                "room": "Women's Health 310",
            },
        ]

        created_doctors = []
        for doc_info in doctors_info:
            u = User.query.filter_by(email=doc_info["email"]).first()
            if not u:
                u = User(
                    email=doc_info["email"],
                    full_name=doc_info["name"],
                    phone="+1-555-0" + str(120 + len(created_doctors)),
                    role_id=roles["doctor"].id,
                )
                u.set_password("doctor123")
                db.session.add(u)
                db.session.flush()

                spec_obj = specs_map.get(doc_info["specialization"])
                d = Doctor(
                    user_id=u.id,
                    specialization_id=spec_obj.id,
                    qualification=doc_info["qualification"],
                    experience_years=doc_info["experience_years"],
                    rating=doc_info["rating"],
                    consultation_fee=doc_info["consultation_fee"],
                    bio=doc_info["bio"],
                    room_number=doc_info["room"],
                )
                db.session.add(d)
                db.session.flush()

                # Add weekly schedule: Monday to Friday, 9:00 AM - 1:00 PM and 2:00 PM - 5:00 PM
                for dow in [0, 1, 2, 3, 4]:  # Mon - Fri
                    # Morning slot block
                    av1 = DoctorAvailability(
                        doctor_id=d.id,
                        day_of_week=dow,
                        start_time=time(9, 0),
                        end_time=time(13, 0),
                        slot_duration_minutes=30,
                        is_active=True,
                    )
                    # Afternoon slot block
                    av2 = DoctorAvailability(
                        doctor_id=d.id,
                        day_of_week=dow,
                        start_time=time(14, 0),
                        end_time=time(17, 0),
                        slot_duration_minutes=30,
                        is_active=True,
                    )
                    db.session.add_all([av1, av2])

                # Saturday morning availability
                av_sat = DoctorAvailability(
                    doctor_id=d.id,
                    day_of_week=5,
                    start_time=time(10, 0),
                    end_time=time(13, 0),
                    slot_duration_minutes=30,
                    is_active=True,
                )
                db.session.add(av_sat)

                created_doctors.append(d)
            else:
                if u.doctor_profile:
                    created_doctors.append(u.doctor_profile)

        # 5. Seed Patients
        patients_info = [
            {
                "name": "John Doe",
                "email": "patient@example.com",
                "phone": "+1-555-0199",
                "gender": "Male",
                "blood": "O+",
                "history": "Mild seasonal allergies, non-smoker, active lifestyle.",
            },
            {
                "name": "Emily Davis",
                "email": "emily@example.com",
                "phone": "+1-555-0211",
                "gender": "Female",
                "blood": "A+",
                "history": "History of intermittent migraine and tension headaches.",
            },
        ]

        created_patients = []
        for p_info in patients_info:
            pu = User.query.filter_by(email=p_info["email"]).first()
            if not pu:
                pu = User(
                    email=p_info["email"],
                    full_name=p_info["name"],
                    phone=p_info["phone"],
                    role_id=roles["patient"].id,
                )
                pu.set_password("password123")
                db.session.add(pu)
                db.session.flush()

                pat = Patient(
                    user_id=pu.id,
                    gender=p_info["gender"],
                    blood_group=p_info["blood"],
                    address="742 Evergreen Terrace, Springfield",
                    emergency_contact="+1-555-9988",
                    medical_history=p_info["history"],
                )
                db.session.add(pat)
                db.session.flush()
                created_patients.append(pat)
            else:
                if pu.patient_profile:
                    created_patients.append(pu.patient_profile)

        # 6. Seed Sample Appointments
        if Appointment.query.count() == 0 and created_patients and created_doctors:
            today = date.today()
            sample_appts = [
                # Past completed appointment
                Appointment(
                    patient_id=created_patients[0].id,
                    doctor_id=created_doctors[0].id,
                    appointment_date=today - timedelta(days=2),
                    start_time=time(10, 0),
                    end_time=time(10, 30),
                    status="completed",
                    chief_complaint="Chest tightness after brisk walking",
                    booking_source="agent_auto",
                ),
                # Tomorrow confirmed appointment
                Appointment(
                    patient_id=created_patients[0].id,
                    doctor_id=created_doctors[1].id,
                    appointment_date=today + timedelta(days=1),
                    start_time=time(11, 0),
                    end_time=time(11, 30),
                    status="confirmed",
                    chief_complaint="Recurrent sharp headache on right side for 4 days",
                    booking_source="agent_auto",
                ),
                # Upcoming appointment for Emily
                Appointment(
                    patient_id=created_patients[1].id,
                    doctor_id=created_doctors[2].id,
                    appointment_date=today + timedelta(days=2),
                    start_time=time(9, 30),
                    end_time=time(10, 0),
                    status="confirmed",
                    chief_complaint="Fever and persistent dry cough",
                    booking_source="manual",
                ),
                # Today pending request
                Appointment(
                    patient_id=created_patients[1].id,
                    doctor_id=created_doctors[4].id,
                    appointment_date=today,
                    start_time=time(15, 0),
                    end_time=time(15, 30),
                    status="pending",
                    chief_complaint="Skin redness and itchy rash on forearm",
                    booking_source="agent_auto",
                ),
            ]
            db.session.add_all(sample_appts)
            db.session.flush()

            # Add Medical Note for completed appointment
            note = MedicalNote(
                appointment_id=sample_appts[0].id,
                doctor_id=created_doctors[0].id,
                diagnosis="Mild exertional angina with sinus tachycardia. Normal resting ECG.",
                prescription="Aspirin 81mg daily, Metoprolol 25mg orally twice daily.",
                clinical_notes="Patient instructed on low-sodium diet and stress reduction. Schedule treadmill stress test.",
                follow_up_date=today + timedelta(days=14),
            )
            db.session.add(note)

        db.session.commit()
        print("[SUCCESS] Database seeding completed successfully!")
        print("\n=== Quick Login Credentials ===")
        print("   Patient: patient@example.com / password123")
        print("   Doctor:  doctor.sarah@healthagent.ai / doctor123")
        print("   Admin:   admin@healthagent.ai / admin123")

if __name__ == "__main__":
    seed_database()
