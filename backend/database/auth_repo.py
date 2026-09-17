import re
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

from .connection import get_connection, now_iso, row_to_dict, rows_to_dicts
from .hospital_repo import get_hospital
from .permissions import validate_role
from .utils import normalize_phone


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,40}$")


def normalize_email(email):
    if not email:
        return None

    email = email.strip().lower()

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email address")

    return email


def normalize_username(username):
    if not username or not username.strip():
        raise ValueError("Username is required")

    username = username.strip().lower()

    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            "Username must be 3-40 characters and can contain letters, numbers, dot, dash, or underscore"
        )

    return username


def validate_password(password):
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if not any(ch.isupper() for ch in password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not any(ch.islower() for ch in password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not any(ch.isdigit() for ch in password):
        raise ValueError("Password must contain at least one number")

    return True


def ensure_hospital_required(role, hospital_id):
    if role == "super_admin":
        return

    if hospital_id is None:
        raise ValueError("hospital_id is required for non-super-admin users")

    hospital = get_hospital(hospital_id)

    if not hospital:
        raise ValueError(f"Hospital not found: {hospital_id}")

    if not hospital["is_active"]:
        raise ValueError(f"Hospital is inactive: {hospital_id}")


def audit_log(conn, actor_user_id, action, entity_type, entity_id=None, details=None):
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
            action,
            entity_type,
            entity_id,
            details,
            now_iso(),
        ),
    )


def create_user(
    full_name,
    username,
    password,
    role,
    hospital_id=None,
    phone=None,
    email=None,
    actor_user_id=None,
):
    validate_role(role)
    validate_password(password)
    ensure_hospital_required(role, hospital_id)

    if not full_name or not full_name.strip():
        raise ValueError("Full name is required")

    normalized_username = normalize_username(username)
    normalized_phone = normalize_phone(phone)
    normalized_email = normalize_email(email)

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO users (
                hospital_id,
                full_name,
                username,
                password_hash,
                role,
                phone,
                email,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hospital_id,
                full_name.strip(),
                normalized_username,
                generate_password_hash(password),
                role,
                normalized_phone,
                normalized_email,
                now_iso(),
            ),
        )

        user_id = cur.lastrowid

        audit_log(
            conn,
            actor_user_id,
            "create_user",
            "user",
            user_id,
            f"Created user '{normalized_username}' with role '{role}'",
        )

        conn.commit()
        return user_id

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        message = str(exc).lower()

        if "users.username" in message:
            raise ValueError("Username already exists") from exc

        if "users.email" in message:
            raise ValueError("Email already exists") from exc

        raise ValueError("Could not create user because of duplicate or invalid data") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            u.id,
            u.hospital_id,
            u.full_name,
            u.username,
            u.role,
            u.phone,
            u.email,
            u.is_active,
            u.created_at,
            u.updated_at,
            h.name AS hospital_name
        FROM users u
        LEFT JOIN hospitals h ON h.id = u.hospital_id
        WHERE u.id = ?
        """,
        (user_id,),
    )

    user = row_to_dict(cur.fetchone())
    conn.close()
    return user


def get_user_by_username(username, include_password=False):
    normalized_username = normalize_username(username)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username = ?", (normalized_username,))

    user = row_to_dict(cur.fetchone())
    conn.close()

    if user and not include_password:
        user.pop("password_hash", None)

    return user


def verify_user(username, password):
    normalized_username = normalize_username(username)

    conn = get_connection()

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (normalized_username,))
        user = row_to_dict(cur.fetchone())

        if not user:
            return None

        if not user["is_active"]:
            return None

        if not check_password_hash(user["password_hash"], password):
            return None

        user.pop("password_hash", None)
        return user

    except Exception:
        raise

    finally:
        conn.close()


def list_users(hospital_id=None, role=None, active_only=True, limit=50, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if hospital_id is not None:
        filters.append("u.hospital_id = ?")
        params.append(hospital_id)

    if role is not None:
        validate_role(role)
        filters.append("u.role = ?")
        params.append(role)

    if active_only:
        filters.append("u.is_active = 1")

    where_clause = ""

    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            u.id,
            u.hospital_id,
            u.full_name,
            u.username,
            u.role,
            u.phone,
            u.email,
            u.is_active,
            u.created_at,
            u.updated_at,
            h.name AS hospital_name
        FROM users u
        LEFT JOIN hospitals h ON h.id = u.hospital_id
        {where_clause}
        ORDER BY u.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    users = rows_to_dicts(cur.fetchall())
    conn.close()
    return users


def update_user(
    user_id,
    full_name=None,
    phone=None,
    email=None,
    role=None,
    hospital_id=None,
    actor_user_id=None,
):
    existing = get_user(user_id)

    if not existing:
        return False

    new_role = role if role is not None else existing["role"]
    new_hospital_id = hospital_id if hospital_id is not None else existing["hospital_id"]

    validate_role(new_role)
    ensure_hospital_required(new_role, new_hospital_id)

    if full_name is not None and not full_name.strip():
        raise ValueError("Full name cannot be empty")

    normalized_phone = normalize_phone(phone) if phone is not None else existing["phone"]
    normalized_email = normalize_email(email) if email is not None else existing["email"]

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET
                full_name = ?,
                phone = ?,
                email = ?,
                role = ?,
                hospital_id = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                full_name.strip() if full_name is not None else existing["full_name"],
                normalized_phone,
                normalized_email,
                new_role,
                new_hospital_id,
                now_iso(),
                user_id,
            ),
        )

        audit_log(
            conn,
            actor_user_id,
            "update_user",
            "user",
            user_id,
            "Updated user profile",
        )

        conn.commit()
        return cur.rowcount > 0

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        message = str(exc).lower()

        if "users.email" in message:
            raise ValueError("Email already exists") from exc

        raise ValueError("Could not update user because of duplicate or invalid data") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_username(user_id, new_username, actor_user_id=None):
    normalized_username = normalize_username(new_username)

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET username = ?, updated_at = ?
            WHERE id = ?
            """,
            (normalized_username, now_iso(), user_id),
        )

        audit_log(
            conn,
            actor_user_id,
            "update_username",
            "user",
            user_id,
            f"Updated username to '{normalized_username}'",
        )

        conn.commit()
        return cur.rowcount > 0

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("Username already exists") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def change_password(user_id, new_password, actor_user_id=None):
    validate_password(new_password)

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (generate_password_hash(new_password), now_iso(), user_id),
        )

        audit_log(
            conn,
            actor_user_id,
            "change_password",
            "user",
            user_id,
            "Password changed",
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def deactivate_user(user_id, actor_user_id=None):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), user_id),
        )

        audit_log(
            conn,
            actor_user_id,
            "deactivate_user",
            "user",
            user_id,
            "User deactivated",
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def activate_user(user_id, actor_user_id=None):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), user_id),
        )

        audit_log(
            conn,
            actor_user_id,
            "activate_user",
            "user",
            user_id,
            "User activated",
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def can_user_access_patient(user, patient_id):
    if not user:
        return False

    if user["role"] == "super_admin":
        return True

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1
        FROM visits
        WHERE patient_id = ?
          AND hospital_id = ?
        LIMIT 1
        """,
        (patient_id, user["hospital_id"]),
    )

    allowed = cur.fetchone() is not None
    conn.close()

    return allowed
