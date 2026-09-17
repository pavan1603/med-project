from .connection import get_connection


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS hospital_networks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id INTEGER,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            city TEXT,
            state TEXT,
            address TEXT,
            phone TEXT,
            email TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (network_id)
                REFERENCES hospital_networks(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN (
                    'super_admin',
                    'hospital_admin',
                    'doctor',
                    'receptionist',
                    'patient'
                )
            ),
            phone TEXT,
            email TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_uid TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            date_of_birth TEXT,
            gender TEXT NOT NULL DEFAULT 'unknown' CHECK (
                gender IN ('male', 'female', 'other', 'unknown')
            ),
            phone TEXT,
            address TEXT,
            preferred_language TEXT NOT NULL DEFAULT 'en' CHECK (
                preferred_language IN ('en', 'hi', 'te')
            ),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            registered_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (registered_by_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS patient_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            consent_type TEXT NOT NULL,
            consent_given INTEGER NOT NULL CHECK (consent_given IN (0, 1)),
            granted_by_user_id INTEGER,
            details TEXT,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
                ON DELETE CASCADE,
            FOREIGN KEY (granted_by_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS patient_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            phone TEXT,
            email TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            hospital_id INTEGER NOT NULL,
            doctor_user_id INTEGER,
            receptionist_user_id INTEGER,
            visit_reason TEXT,
            visit_status TEXT NOT NULL DEFAULT 'waiting' CHECK (
                    visit_status IN (
                    'waiting',
                    'in_consultation',
                    'completed',
                    'cancelled'
                )
            ),
            visit_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
                ON DELETE CASCADE,
            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(id)
                ON DELETE CASCADE,
            FOREIGN KEY (doctor_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL,
            FOREIGN KEY (receptionist_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS diabetes_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL,
            pregnancies REAL,
            glucose REAL,
            blood_pressure REAL,
            skin_thickness REAL,
            insulin REAL,
            bmi REAL,
            diabetes_pedigree_function REAL,
            age_at_visit INTEGER,
            prediction_result TEXT,
            risk_level TEXT CHECK (
                risk_level IN ('Low', 'Moderate', 'High', 'Very High')
            ),
            confidence REAL,
            explanation_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (visit_id)
                REFERENCES visits(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS heart_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL,
            mode TEXT NOT NULL CHECK (
                mode IN ('simple_screening', 'advanced_medical')
            ),
            age_at_visit INTEGER,
            gender TEXT,
            chest_pain INTEGER CHECK (chest_pain IN (0, 1)),
            breathless_walking INTEGER CHECK (breathless_walking IN (0, 1)),
            high_bp INTEGER CHECK (high_bp IN (0, 1)),
            diabetes INTEGER CHECK (diabetes IN (0, 1)),
            smoking INTEGER CHECK (smoking IN (0, 1)),
            high_cholesterol INTEGER CHECK (high_cholesterol IN (0, 1)),
            tired_easily INTEGER CHECK (tired_easily IN (0, 1)),
            family_history INTEGER CHECK (family_history IN (0, 1)),
            poor_exercise_recovery INTEGER CHECK (poor_exercise_recovery IN (0, 1)),
            exercise_chest_pain INTEGER CHECK (exercise_chest_pain IN (0, 1)),

            trestbps REAL,
            chol REAL,
            fbs INTEGER CHECK (fbs IN (0, 1)),
            thalch REAL,
            exang INTEGER CHECK (exang IN (0, 1)),
            oldpeak REAL,
            ca REAL,
            ecg_result TEXT,
            thalassemia TEXT,

            prediction_result TEXT,
            risk_level TEXT CHECK (
                risk_level IN ('Low', 'Moderate', 'High', 'Very High')
            ),
            confidence REAL,
            explanation_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (visit_id)
                REFERENCES visits(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS doctor_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL,
            doctor_user_id INTEGER,
            note_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (visit_id)
                REFERENCES visits(id)
                ON DELETE CASCADE,
            FOREIGN KEY (doctor_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS patient_doctor_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_user_id INTEGER NOT NULL,
            hospital_id INTEGER,
            summary_text TEXT NOT NULL,
            medication_suggestions TEXT,
            lifestyle_suggestions TEXT,
            follow_up_advice TEXT,
            is_visible_to_patient INTEGER NOT NULL DEFAULT 1 CHECK (is_visible_to_patient IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
                ON DELETE CASCADE,
            FOREIGN KEY (doctor_user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_uid TEXT NOT NULL UNIQUE,
            patient_id INTEGER,
            hospital_id INTEGER,
            user_id INTEGER,
            language TEXT NOT NULL DEFAULT 'en' CHECK (
                language IN ('en', 'hi', 'te')
            ),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (patient_id)
                REFERENCES patients(id)
                ON DELETE CASCADE,
            FOREIGN KEY (hospital_id)
                REFERENCES hospitals(id)
                ON DELETE SET NULL,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            sender TEXT NOT NULL CHECK (sender IN ('user', 'assistant')),
            message_text TEXT NOT NULL,
            intent TEXT,
            sources_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id)
                REFERENCES chat_sessions(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (actor_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_hospitals_network_id
            ON hospitals(network_id);

        CREATE INDEX IF NOT EXISTS idx_hospitals_code
            ON hospitals(code);

        CREATE INDEX IF NOT EXISTS idx_users_hospital_id
            ON users(hospital_id);

        CREATE INDEX IF NOT EXISTS idx_users_role
            ON users(role);

        CREATE INDEX IF NOT EXISTS idx_patients_uid
            ON patients(patient_uid);

        CREATE INDEX IF NOT EXISTS idx_patients_phone
            ON patients(phone);

        CREATE INDEX IF NOT EXISTS idx_patients_full_name
            ON patients(full_name);

        CREATE INDEX IF NOT EXISTS idx_patients_dob
            ON patients(date_of_birth);

        CREATE INDEX IF NOT EXISTS idx_visits_patient_id
            ON visits(patient_id);

        CREATE INDEX IF NOT EXISTS idx_visits_hospital_id
            ON visits(hospital_id);

        CREATE INDEX IF NOT EXISTS idx_visits_visit_date
            ON visits(visit_date);

        CREATE INDEX IF NOT EXISTS idx_diabetes_reports_visit_id
            ON diabetes_reports(visit_id);

        CREATE INDEX IF NOT EXISTS idx_heart_reports_visit_id
            ON heart_reports(visit_id);

        CREATE INDEX IF NOT EXISTS idx_patient_consents_patient_type
            ON patient_consents(patient_id, consent_type, created_at);

        CREATE INDEX IF NOT EXISTS idx_patient_accounts_patient_id
            ON patient_accounts(patient_id);

        CREATE INDEX IF NOT EXISTS idx_patient_accounts_username
            ON patient_accounts(username);

        CREATE INDEX IF NOT EXISTS idx_chat_sessions_patient_id
            ON chat_sessions(patient_id);

        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
            ON chat_messages(session_id);

        CREATE INDEX IF NOT EXISTS idx_patient_doctor_summaries_patient_id
            ON patient_doctor_summaries(patient_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_patient_doctor_summaries_doctor_id
            ON patient_doctor_summaries(doctor_user_id);

        CREATE INDEX IF NOT EXISTS idx_audit_logs_actor
            ON audit_logs(actor_user_id);

        CREATE INDEX IF NOT EXISTS idx_audit_logs_entity
            ON audit_logs(entity_type, entity_id);
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")
