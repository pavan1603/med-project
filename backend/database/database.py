import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "medirisk.db")


ROLES = {
    "super_admin",
    "hospital_admin",
    "doctor",
    "receptionist",
    "patient",
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT,
            area TEXT,
            phone TEXT,
            email TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        );

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_uid TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            phone TEXT,
            age INTEGER,
            gender TEXT,
            preferred_language TEXT DEFAULT 'en',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            hospital_id INTEGER NOT NULL,
            created_by_user_id INTEGER,
            doctor_user_id INTEGER,
            visit_date TEXT NOT NULL,
            reason TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
            FOREIGN KEY (created_by_user_id) REFERENCES users(id),
            FOREIGN KEY (doctor_user_id) REFERENCES users(id)
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
            age REAL,
            prediction_result TEXT,
            confidence REAL,
            risk TEXT,
            explanation_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (visit_id) REFERENCES visits(id)
        );

        CREATE TABLE IF NOT EXISTS heart_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            input_json TEXT NOT NULL,
            prediction_result TEXT,
            confidence REAL,
            score REAL,
            risk TEXT,
            explanation_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (visit_id) REFERENCES visits(id)
        );

        CREATE TABLE IF NOT EXISTS doctor_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            visit_id INTEGER,
            doctor_user_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (visit_id) REFERENCES visits(id),
            FOREIGN KEY (doctor_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            user_id INTEGER,
            session_uid TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            language TEXT DEFAULT 'en',
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_hospital ON users(hospital_id);
        CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
        CREATE INDEX IF NOT EXISTS idx_patients_uid ON patients(patient_uid);
        CREATE INDEX IF NOT EXISTS idx_visits_patient ON visits(patient_id);
        CREATE INDEX IF NOT EXISTS idx_visits_hospital ON visits(hospital_id);
        CREATE INDEX IF NOT EXISTS idx_diabetes_visit ON diabetes_reports(visit_id);
        CREATE INDEX IF NOT EXISTS idx_heart_visit ON heart_reports(visit_id);
        """
    )

    conn.commit()
    conn.close()


def create_hospital(name, city=None, area=None, phone=None, email=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO hospitals (name, city, area, phone, email, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, city, area, phone, email, now_iso()),
    )

    hospital_id = cur.lastrowid
    conn.commit()
    conn.close()
    return hospital_id


def create_user(full_name, username, password, role, hospital_id=None, phone=None, email=None):
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")

    if role != "super_admin" and hospital_id is None:
        raise ValueError("hospital_id is required for non-super-admin users")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users (
            hospital_id, full_name, username, password_hash,
            role, phone, email, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            hospital_id,
            full_name,
            username,
            generate_password_hash(password),
            role,
            phone,
            email,
            now_iso(),
        ),
    )

    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def verify_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM users
        WHERE username = ? AND is_active = 1
        """,
        (username,),
    )

    user = cur.fetchone()
    conn.close()

    if not user:
        return None

    if not check_password_hash(user["password_hash"], password):
        return None

    return dict(user)


def seed_demo_data():
    init_db()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM hospitals")
    hospital_count = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM users")
    user_count = cur.fetchone()["count"]

    conn.close()

    if hospital_count == 0:
        hospital_id = create_hospital(
            name="MediRisk Demo Hospital",
            city="Hyderabad",
            area="Kukatpally",
            phone="9999999999",
            email="demo@medirisk.local",
        )
    else:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM hospitals LIMIT 1")
        hospital_id = cur.fetchone()["id"]
        conn.close()

    if user_count == 0:
        create_user(
            full_name="Super Admin",
            username="superadmin",
            password="admin123",
            role="super_admin",
        )

        create_user(
            full_name="Hospital Admin",
            username="hospitaladmin",
            password="admin123",
            role="hospital_admin",
            hospital_id=hospital_id,
        )

        create_user(
            full_name="Demo Doctor",
            username="doctor",
            password="doctor123",
            role="doctor",
            hospital_id=hospital_id,
        )

        create_user(
            full_name="Demo Receptionist",
            username="reception",
            password="reception123",
            role="receptionist",
            hospital_id=hospital_id,
        )


if __name__ == "__main__":
    seed_demo_data()
    print(f"Database initialized at: {DB_PATH}")
    print("Demo users:")
    print("  superadmin / admin123")
    print("  hospitaladmin / admin123")
    print("  doctor / doctor123")
    print("  reception / reception123")