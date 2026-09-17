from datetime import datetime

from .audit_repo import log_audit
from .connection import get_connection, now_iso, row_to_dict, rows_to_dicts
from .hospital_repo import get_hospital
from .patient_repo import calculate_age, get_patient
from .auth_repo import get_user


VALID_VISIT_STATUSES = {
    "waiting",
    "in_consultation",
    "completed",
    "cancelled",
}


def validate_visit_status(status):
    if not status:
        return "waiting"

    status = status.strip().lower()

    if status not in VALID_VISIT_STATUSES:
        raise ValueError("Invalid visit status")

    return status


def validate_iso_datetime(value, field_name="datetime"):
    if not value:
        return now_iso()

    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO datetime format") from exc

    return value


def ensure_patient_exists(patient_id):
    patient = get_patient(patient_id)

    if not patient:
        raise ValueError(f"Patient not found: {patient_id}")

    if not patient["is_active"]:
        raise ValueError(f"Patient is inactive: {patient_id}")

    return patient


def ensure_hospital_exists(hospital_id):
    hospital = get_hospital(hospital_id)

    if not hospital:
        raise ValueError(f"Hospital not found: {hospital_id}")

    if not hospital["is_active"]:
        raise ValueError(f"Hospital is inactive: {hospital_id}")

    return hospital


def ensure_user_role_for_hospital(user_id, expected_role, hospital_id, field_name):
    if user_id is None:
        return None

    user = get_user(user_id)

    if not user:
        raise ValueError(f"{field_name} not found: {user_id}")

    if not user["is_active"]:
        raise ValueError(f"{field_name} is inactive: {user_id}")

    if user["role"] != expected_role:
        raise ValueError(f"{field_name} must have role '{expected_role}'")

    if user["hospital_id"] != hospital_id:
        raise ValueError(f"{field_name} must belong to the selected hospital")

    return user


def create_visit(
    patient_id,
    hospital_id,
    visit_reason=None,
    doctor_user_id=None,
    receptionist_user_id=None,
    visit_status="waiting",
    visit_date=None,
    actor_user_id=None,
):
    patient = ensure_patient_exists(patient_id)
    hospital = ensure_hospital_exists(hospital_id)

    ensure_user_role_for_hospital(
        doctor_user_id,
        "doctor",
        hospital_id,
        "doctor_user_id",
    )

    ensure_user_role_for_hospital(
        receptionist_user_id,
        "receptionist",
        hospital_id,
        "receptionist_user_id",
    )

    normalized_status = validate_visit_status(visit_status)
    normalized_visit_date = validate_iso_datetime(visit_date, "visit_date")
    age_at_visit = calculate_age(patient["date_of_birth"])

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO visits (
                patient_id,
                hospital_id,
                doctor_user_id,
                receptionist_user_id,
                visit_reason,
                visit_status,
                visit_date,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                hospital_id,
                doctor_user_id,
                receptionist_user_id,
                visit_reason.strip() if visit_reason else None,
                normalized_status,
                normalized_visit_date,
                now_iso(),
            ),
        )

        visit_id = cur.lastrowid

        log_audit(
            action="create_visit",
            entity_type="visit",
            entity_id=visit_id,
            actor_user_id=actor_user_id or receptionist_user_id or doctor_user_id,
            details=f"Created visit for patient {patient['patient_uid']} at {hospital['name']}",
            conn=conn,
        )

        conn.commit()

        return {
            "id": visit_id,
            "patient_id": patient_id,
            "hospital_id": hospital_id,
            "visit_status": normalized_status,
            "visit_date": normalized_visit_date,
            "age_at_visit": age_at_visit,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_visit(visit_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            v.id,
            v.patient_id,
            p.patient_uid,
            p.full_name AS patient_name,
            p.date_of_birth,
            p.gender AS patient_gender,
            p.phone AS patient_phone,
            v.hospital_id,
            h.name AS hospital_name,
            h.city AS hospital_city,
            v.doctor_user_id,
            doctor.full_name AS doctor_name,
            v.receptionist_user_id,
            receptionist.full_name AS receptionist_name,
            v.visit_reason,
            v.visit_status,
            v.visit_date,
            v.created_at,
            v.updated_at
        FROM visits v
        JOIN patients p ON p.id = v.patient_id
        JOIN hospitals h ON h.id = v.hospital_id
        LEFT JOIN users doctor ON doctor.id = v.doctor_user_id
        LEFT JOIN users receptionist ON receptionist.id = v.receptionist_user_id
        WHERE v.id = ?
        """,
        (visit_id,),
    )

    visit = row_to_dict(cur.fetchone())
    conn.close()

    if visit:
        visit["age_at_visit"] = calculate_age(visit["date_of_birth"])

    return visit


def list_patient_visits(
    patient_id,
    status=None,
    start_date=None,
    end_date=None,
    limit=50,
    offset=0,
):
    conn = get_connection()
    cur = conn.cursor()

    filters = ["v.patient_id = ?"]
    params = [patient_id]

    if status:
        filters.append("v.visit_status = ?")
        params.append(validate_visit_status(status))

    if start_date:
        filters.append("v.visit_date >= ?")
        params.append(validate_iso_datetime(start_date, "start_date"))

    if end_date:
        filters.append("v.visit_date <= ?")
        params.append(validate_iso_datetime(end_date, "end_date"))

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            v.id,
            v.patient_id,
            v.hospital_id,
            h.name AS hospital_name,
            h.city AS hospital_city,
            v.doctor_user_id,
            doctor.full_name AS doctor_name,
            v.receptionist_user_id,
            receptionist.full_name AS receptionist_name,
            v.visit_reason,
            v.visit_status,
            v.visit_date,
            v.created_at,
            v.updated_at
        FROM visits v
        JOIN hospitals h ON h.id = v.hospital_id
        LEFT JOIN users doctor ON doctor.id = v.doctor_user_id
        LEFT JOIN users receptionist ON receptionist.id = v.receptionist_user_id
        WHERE {" AND ".join(filters)}
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    visits = rows_to_dicts(cur.fetchall())
    conn.close()
    return visits


def list_hospital_visits(
    hospital_id,
    status=None,
    start_date=None,
    end_date=None,
    limit=100,
    offset=0,
):
    conn = get_connection()
    cur = conn.cursor()

    filters = ["v.hospital_id = ?"]
    params = [hospital_id]

    if status:
        filters.append("v.visit_status = ?")
        params.append(validate_visit_status(status))

    if start_date:
        filters.append("v.visit_date >= ?")
        params.append(validate_iso_datetime(start_date, "start_date"))

    if end_date:
        filters.append("v.visit_date <= ?")
        params.append(validate_iso_datetime(end_date, "end_date"))

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            v.id,
            v.patient_id,
            p.patient_uid,
            p.full_name AS patient_name,
            p.phone AS patient_phone,
            v.hospital_id,
            h.name AS hospital_name,
            v.doctor_user_id,
            doctor.full_name AS doctor_name,
            v.receptionist_user_id,
            receptionist.full_name AS receptionist_name,
            v.visit_reason,
            v.visit_status,
            v.visit_date,
            v.created_at
        FROM visits v
        JOIN patients p ON p.id = v.patient_id
        JOIN hospitals h ON h.id = v.hospital_id
        LEFT JOIN users doctor ON doctor.id = v.doctor_user_id
        LEFT JOIN users receptionist ON receptionist.id = v.receptionist_user_id
        WHERE {" AND ".join(filters)}
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    visits = rows_to_dicts(cur.fetchall())
    conn.close()
    return visits


def update_visit(
    visit_id,
    visit_reason=None,
    doctor_user_id=None,
    receptionist_user_id=None,
    visit_status=None,
    visit_date=None,
    actor_user_id=None,
):
    existing = get_visit(visit_id)

    if not existing:
        return False

    hospital_id = existing["hospital_id"]

    new_doctor_user_id = (
        doctor_user_id if doctor_user_id is not None else existing["doctor_user_id"]
    )

    new_receptionist_user_id = (
        receptionist_user_id
        if receptionist_user_id is not None
        else existing["receptionist_user_id"]
    )

    ensure_user_role_for_hospital(
        new_doctor_user_id,
        "doctor",
        hospital_id,
        "doctor_user_id",
    )

    ensure_user_role_for_hospital(
        new_receptionist_user_id,
        "receptionist",
        hospital_id,
        "receptionist_user_id",
    )

    new_visit_reason = (
        visit_reason.strip()
        if visit_reason is not None and visit_reason
        else existing["visit_reason"]
    )

    new_status = (
        validate_visit_status(visit_status)
        if visit_status is not None
        else existing["visit_status"]
    )

    new_visit_date = (
        validate_iso_datetime(visit_date, "visit_date")
        if visit_date is not None
        else existing["visit_date"]
    )

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE visits
            SET
                doctor_user_id = ?,
                receptionist_user_id = ?,
                visit_reason = ?,
                visit_status = ?,
                visit_date = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_doctor_user_id,
                new_receptionist_user_id,
                new_visit_reason,
                new_status,
                new_visit_date,
                now_iso(),
                visit_id,
            ),
        )

        log_audit(
            action="update_visit",
            entity_type="visit",
            entity_id=visit_id,
            actor_user_id=actor_user_id,
            details="Updated visit details",
            conn=conn,
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def cancel_visit(visit_id, actor_user_id=None, reason=None):
    existing = get_visit(visit_id)

    if not existing:
        return False

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE visits
            SET visit_status = 'cancelled',
                updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), visit_id),
        )

        log_audit(
            action="cancel_visit",
            entity_type="visit",
            entity_id=visit_id,
            actor_user_id=actor_user_id,
            details=reason or "Visit cancelled",
            conn=conn,
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_patient_timeline(patient_id, limit=50, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            v.id AS visit_id,
            v.visit_date,
            v.visit_status,
            v.visit_reason,
            h.name AS hospital_name,
            h.city AS hospital_city,

            dr.id AS diabetes_report_id,
            dr.prediction_result AS diabetes_result,
            dr.risk_level AS diabetes_risk,
            dr.confidence AS diabetes_confidence,
            dr.glucose,
            dr.bmi,

            hr.id AS heart_report_id,
            hr.mode AS heart_mode,
            hr.prediction_result AS heart_result,
            hr.risk_level AS heart_risk,
            hr.confidence AS heart_confidence
        FROM visits v
        JOIN hospitals h ON h.id = v.hospital_id
        LEFT JOIN diabetes_reports dr ON dr.visit_id = v.id
        LEFT JOIN heart_reports hr ON hr.visit_id = v.id
        WHERE v.patient_id = ?
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
        """,
        (patient_id, limit, offset),
    )

    timeline = rows_to_dicts(cur.fetchall())
    conn.close()
    return timeline


def get_latest_patient_visit(patient_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM visits
        WHERE patient_id = ?
          AND visit_status != 'cancelled'
        ORDER BY visit_date DESC
        LIMIT 1
        """,
        (patient_id,),
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return get_visit(row["id"])