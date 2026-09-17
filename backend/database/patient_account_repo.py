import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from .auth_repo import normalize_email, normalize_username, validate_password
from .connection import get_connection, now_iso, row_to_dict
from .patient_repo import get_patient
from .utils import normalize_phone


def create_patient_account(
    patient_id,
    username,
    password,
    phone=None,
    email=None,
):
    patient = get_patient(patient_id)

    if not patient:
        raise ValueError(f"Patient not found: {patient_id}")

    if not patient["is_active"]:
        raise ValueError(f"Patient is inactive: {patient_id}")

    validate_password(password)
    normalized_username = normalize_username(username)
    normalized_phone = normalize_phone(phone)
    normalized_email = normalize_email(email)

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO patient_accounts (
                patient_id,
                username,
                password_hash,
                phone,
                email,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                normalized_username,
                generate_password_hash(password),
                normalized_phone,
                normalized_email,
                now_iso(),
            ),
        )

        account_id = cur.lastrowid
        conn.commit()
        return account_id

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        message = str(exc).lower()

        if "patient_accounts.patient_id" in message:
            raise ValueError("This patient already has an account") from exc

        if "patient_accounts.username" in message:
            raise ValueError("Patient username already exists") from exc

        if "patient_accounts.email" in message:
            raise ValueError("Patient email already exists") from exc

        raise ValueError("Could not create patient account") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_patient_account(account_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pa.id,
            pa.patient_id,
            pa.username,
            pa.phone,
            pa.email,
            pa.is_active,
            pa.created_at,
            pa.updated_at,
            p.patient_uid,
            p.full_name,
            p.preferred_language
        FROM patient_accounts pa
        JOIN patients p ON p.id = pa.patient_id
        WHERE pa.id = ?
        """,
        (account_id,),
    )

    account = row_to_dict(cur.fetchone())
    conn.close()
    return account


def get_patient_account_by_patient_id(patient_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pa.id,
            pa.patient_id,
            pa.username,
            pa.phone,
            pa.email,
            pa.is_active,
            pa.created_at,
            pa.updated_at,
            p.patient_uid,
            p.full_name,
            p.preferred_language
        FROM patient_accounts pa
        JOIN patients p ON p.id = pa.patient_id
        WHERE pa.patient_id = ?
        """,
        (patient_id,),
    )

    account = row_to_dict(cur.fetchone())
    conn.close()
    return account


def reset_patient_account_password(patient_id, new_password):
    validate_password(new_password)

    conn = get_connection()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE patient_accounts
            SET password_hash = ?, updated_at = ?
            WHERE patient_id = ?
            """,
            (generate_password_hash(new_password), now_iso(), patient_id),
        )

        if cur.rowcount == 0:
            raise ValueError("Patient account not found")

        conn.commit()
        return get_patient_account_by_patient_id(patient_id)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def verify_patient_account(username, password):
    normalized_username = normalize_username(username)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pa.*,
            p.patient_uid,
            p.full_name,
            p.preferred_language
        FROM patient_accounts pa
        JOIN patients p ON p.id = pa.patient_id
        WHERE pa.username = ?
        """,
        (normalized_username,),
    )

    account = row_to_dict(cur.fetchone())
    conn.close()

    if not account:
        return None

    if not account["is_active"]:
        return None

    if not check_password_hash(account["password_hash"], password):
        return None

    account.pop("password_hash", None)
    account["role"] = "patient"
    return account
