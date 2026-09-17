from datetime import date, datetime, timezone

from .connection import get_connection, now_iso, row_to_dict, rows_to_dicts
from .utils import generate_patient_uid, normalize_language, normalize_phone


VALID_GENDERS = {"male", "female", "other", "unknown"}


def validate_gender(gender):
    if not gender:
        return "unknown"

    gender = gender.strip().lower()

    if gender not in VALID_GENDERS:
        raise ValueError("Invalid gender")

    return gender


def validate_date_of_birth(date_of_birth):
    if not date_of_birth:
        return None

    try:
        parsed = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("date_of_birth must be in YYYY-MM-DD format") from exc

    today = date.today()

    if parsed > today:
        raise ValueError("date_of_birth cannot be in the future")

    age = calculate_age(date_of_birth)

    if age > 125:
        raise ValueError("Patient age cannot be greater than 125 years")

    return parsed.isoformat()


def calculate_age(date_of_birth, reference_date=None):
    if not date_of_birth:
        return None

    born = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    today = reference_date or date.today()

    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def detect_possible_duplicates(full_name, phone=None, date_of_birth=None, limit=10):
    if not full_name or not full_name.strip():
        return []

    normalized_phone = normalize_phone(phone)
    normalized_dob = validate_date_of_birth(date_of_birth)
    normalized_name = full_name.strip().lower()

    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if normalized_phone:
        filters.append("phone = ?")
        params.append(normalized_phone)

    if normalized_dob:
        filters.append("(LOWER(full_name) = ? AND date_of_birth = ?)")
        params.extend([normalized_name, normalized_dob])
    else:
        filters.append("LOWER(full_name) = ?")
        params.append(normalized_name)

    params.append(limit)

    cur.execute(
        f"""
        SELECT
            id,
            patient_uid,
            full_name,
            date_of_birth,
            gender,
            phone,
            preferred_language,
            is_active,
            created_at
        FROM patients
        WHERE {" OR ".join(filters)}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        params,
    )

    duplicates = rows_to_dicts(cur.fetchall())
    conn.close()

    for patient in duplicates:
        patient["age"] = calculate_age(patient["date_of_birth"])

    return duplicates


def create_patient(
    full_name,
    date_of_birth=None,
    gender="unknown",
    phone=None,
    address=None,
    preferred_language="en",
    registered_by_user_id=None,
    allow_possible_duplicate=False,
):
    if not full_name or not full_name.strip():
        raise ValueError("Patient full name is required")

    normalized_phone = normalize_phone(phone)
    normalized_dob = validate_date_of_birth(date_of_birth)
    normalized_gender = validate_gender(gender)
    normalized_language = normalize_language(preferred_language)

    possible_duplicates = detect_possible_duplicates(
        full_name=full_name,
        phone=phone,
        date_of_birth=date_of_birth,
    )

    if possible_duplicates and not allow_possible_duplicate:
        return {
            "created": False,
            "reason": "possible_duplicate",
            "possible_duplicates": possible_duplicates,
        }

    patient_uid = generate_patient_uid()

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO patients (
                patient_uid,
                full_name,
                date_of_birth,
                gender,
                phone,
                address,
                preferred_language,
                registered_by_user_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_uid,
                full_name.strip(),
                normalized_dob,
                normalized_gender,
                normalized_phone,
                address.strip() if address else None,
                normalized_language,
                registered_by_user_id,
                now_iso(),
            ),
        )

        patient_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO audit_logs (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                registered_by_user_id,
                "create_patient",
                "patient",
                patient_id,
                f"Registered patient '{full_name.strip()}' with UID '{patient_uid}'",
                now_iso(),
            ),
        )

        conn.commit()

        return {
            "created": True,
            "id": patient_id,
            "patient_uid": patient_uid,
            "possible_duplicates": possible_duplicates,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def add_age_to_patient(patient):
    if patient:
        patient["age"] = calculate_age(patient.get("date_of_birth"))
    return patient


def get_patient(patient_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            p.id,
            p.patient_uid,
            p.full_name,
            p.date_of_birth,
            p.gender,
            p.phone,
            p.address,
            p.preferred_language,
            p.is_active,
            p.registered_by_user_id,
            p.created_at,
            p.updated_at,
            u.full_name AS registered_by_name
        FROM patients p
        LEFT JOIN users u ON u.id = p.registered_by_user_id
        WHERE p.id = ?
        """,
        (patient_id,),
    )

    patient = row_to_dict(cur.fetchone())
    conn.close()
    return add_age_to_patient(patient)


def get_patient_by_uid(patient_uid):
    if not patient_uid:
        return None

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM patients
        WHERE patient_uid = ?
        """,
        (patient_uid.strip(),),
    )

    patient = row_to_dict(cur.fetchone())
    conn.close()
    return add_age_to_patient(patient)


def find_patients_by_phone(phone):
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        return []

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            patient_uid,
            full_name,
            date_of_birth,
            gender,
            phone,
            preferred_language,
            is_active,
            created_at
        FROM patients
        WHERE phone = ?
        ORDER BY created_at DESC
        """,
        (normalized_phone,),
    )

    patients = rows_to_dicts(cur.fetchall())
    conn.close()

    for patient in patients:
        patient["age"] = calculate_age(patient["date_of_birth"])

    return patients


def search_patients(query, active_only=True, limit=25, offset=0):
    if not query or not query.strip():
        return []

    query = query.strip()
    search_value = f"%{query}%"
    normalized_phone = normalize_phone(query)

    conn = get_connection()
    cur = conn.cursor()

    filters = [
        """
        (
            patient_uid LIKE ?
            OR full_name LIKE ?
            OR phone = ?
        )
        """
    ]

    params = [search_value, search_value, normalized_phone]

    if active_only:
        filters.append("is_active = 1")

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            id,
            patient_uid,
            full_name,
            date_of_birth,
            gender,
            phone,
            preferred_language,
            is_active,
            created_at
        FROM patients
        WHERE {" AND ".join(filters)}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    patients = rows_to_dicts(cur.fetchall())
    conn.close()

    for patient in patients:
        patient["age"] = calculate_age(patient["date_of_birth"])

    return patients


def list_patients(active_only=True, hospital_id=None, limit=100, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if active_only:
        filters.append("p.is_active = 1")

    if hospital_id is not None:
        filters.append("u.hospital_id = ?")
        params.append(hospital_id)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            p.id,
            p.patient_uid,
            p.full_name,
            p.date_of_birth,
            p.gender,
            p.phone,
            p.address,
            p.preferred_language,
            p.is_active,
            p.registered_by_user_id,
            p.created_at,
            u.full_name AS registered_by_name,
            h.name AS hospital_name
        FROM patients p
        LEFT JOIN users u ON u.id = p.registered_by_user_id
        LEFT JOIN hospitals h ON h.id = u.hospital_id
        {where_clause}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    patients = rows_to_dicts(cur.fetchall())
    conn.close()

    for patient in patients:
        patient["age"] = calculate_age(patient["date_of_birth"])

    return patients


def update_patient(
    patient_id,
    full_name=None,
    date_of_birth=None,
    gender=None,
    phone=None,
    address=None,
    preferred_language=None,
    actor_user_id=None,
):
    existing = get_patient(patient_id)

    if not existing:
        return False

    new_full_name = full_name.strip() if full_name is not None else existing["full_name"]

    if not new_full_name:
        raise ValueError("Patient full name cannot be empty")

    new_dob = (
        validate_date_of_birth(date_of_birth)
        if date_of_birth is not None
        else existing["date_of_birth"]
    )

    new_gender = validate_gender(gender) if gender is not None else existing["gender"]
    new_phone = normalize_phone(phone) if phone is not None else existing["phone"]
    new_address = address.strip() if address is not None and address else existing["address"]

    new_language = (
        normalize_language(preferred_language)
        if preferred_language is not None
        else existing["preferred_language"]
    )

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE patients
            SET
                full_name = ?,
                date_of_birth = ?,
                gender = ?,
                phone = ?,
                address = ?,
                preferred_language = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_full_name,
                new_dob,
                new_gender,
                new_phone,
                new_address,
                new_language,
                now_iso(),
                patient_id,
            ),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor_user_id,
                "update_patient",
                "patient",
                patient_id,
                "Updated patient profile",
                now_iso(),
            ),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def deactivate_patient(patient_id, actor_user_id=None):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE patients
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), patient_id),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor_user_id,
                "deactivate_patient",
                "patient",
                patient_id,
                "Patient deactivated",
                now_iso(),
            ),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def activate_patient(patient_id, actor_user_id=None):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE patients
            SET is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), patient_id),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor_user_id,
                "activate_patient",
                "patient",
                patient_id,
                "Patient activated",
                now_iso(),
            ),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def grant_patient_consent(
    patient_id,
    consent_type,
    granted_by_user_id=None,
    details=None,
    expires_at=None,
):
    if not consent_type or not consent_type.strip():
        raise ValueError("Consent type is required")

    if expires_at:
        try:
            datetime.fromisoformat(expires_at)
        except ValueError as exc:
            raise ValueError("expires_at must be ISO format") from exc

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO patient_consents (
                patient_id,
                consent_type,
                consent_given,
                granted_by_user_id,
                details,
                expires_at,
                created_at
            )
            VALUES (?, ?, 1, ?, ?, ?, ?)
            """,
            (
                patient_id,
                consent_type.strip(),
                granted_by_user_id,
                details,
                expires_at,
                now_iso(),
            ),
        )

        consent_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO audit_logs (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                granted_by_user_id,
                "grant_patient_consent",
                "patient",
                patient_id,
                f"Granted consent '{consent_type.strip()}'",
                now_iso(),
            ),
        )

        conn.commit()
        return consent_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def revoke_patient_consent(
    patient_id,
    consent_type,
    revoked_by_user_id=None,
    details=None,
):
    if not consent_type or not consent_type.strip():
        raise ValueError("Consent type is required")

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO patient_consents (
                patient_id,
                consent_type,
                consent_given,
                granted_by_user_id,
                details,
                expires_at,
                created_at
            )
            VALUES (?, ?, 0, ?, ?, NULL, ?)
            """,
            (
                patient_id,
                consent_type.strip(),
                revoked_by_user_id,
                details,
                now_iso(),
            ),
        )

        consent_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO audit_logs (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                revoked_by_user_id,
                "revoke_patient_consent",
                "patient",
                patient_id,
                f"Revoked consent '{consent_type.strip()}'",
                now_iso(),
            ),
        )

        conn.commit()
        return consent_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def has_patient_consent(patient_id, consent_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT consent_given, expires_at
        FROM patient_consents
        WHERE patient_id = ?
          AND consent_type = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (patient_id, consent_type),
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return False

    if not bool(row["consent_given"]):
        return False

    if row["expires_at"]:
        expires_at = datetime.fromisoformat(row["expires_at"])

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= datetime.now(timezone.utc):
            return False

    return True
