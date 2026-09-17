import re
import sqlite3

from .connection import get_connection, now_iso, row_to_dict, rows_to_dicts
from .utils import normalize_phone


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email):
    if not email:
        return None

    email = email.strip().lower()

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email address")

    return email


def normalize_code(code):
    if not code or not code.strip():
        raise ValueError("Hospital code is required")

    return code.strip().upper()


def ensure_network_exists(network_id):
    if network_id is None:
        return

    network = get_hospital_network(network_id)

    if not network:
        raise ValueError(f"Hospital network not found: {network_id}")

    if not network["is_active"]:
        raise ValueError(f"Hospital network is inactive: {network_id}")


def create_hospital_network(name, description=None):
    if not name or not name.strip():
        raise ValueError("Network name is required")

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO hospital_networks (
                name,
                description,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                name.strip(),
                description.strip() if description else None,
                now_iso(),
            ),
        )

        network_id = cur.lastrowid
        conn.commit()
        return network_id

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("Hospital network name already exists") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_hospital_network(network_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM hospital_networks
        WHERE id = ?
        """,
        (network_id,),
    )

    network = row_to_dict(cur.fetchone())
    conn.close()
    return network


def list_hospital_networks(active_only=True, limit=50, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    where_clause = "WHERE is_active = 1" if active_only else ""

    cur.execute(
        f"""
        SELECT *
        FROM hospital_networks
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )

    networks = rows_to_dicts(cur.fetchall())
    conn.close()
    return networks


def update_hospital_network(network_id, name=None, description=None):
    existing = get_hospital_network(network_id)

    if not existing:
        return False

    if name is not None and not name.strip():
        raise ValueError("Network name cannot be empty")

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE hospital_networks
            SET
                name = ?,
                description = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                name.strip() if name is not None else existing["name"],
                description.strip() if description is not None and description else existing["description"],
                now_iso(),
                network_id,
            ),
        )

        conn.commit()
        return cur.rowcount > 0

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("Hospital network name already exists") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def deactivate_hospital_network(network_id):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE hospital_networks
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), network_id),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def activate_hospital_network(network_id):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE hospital_networks
            SET is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), network_id),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def create_hospital(
    name,
    code,
    network_id=None,
    city=None,
    state=None,
    address=None,
    phone=None,
    email=None,
):
    if not name or not name.strip():
        raise ValueError("Hospital name is required")

    ensure_network_exists(network_id)

    normalized_code = normalize_code(code)
    normalized_phone = normalize_phone(phone)
    normalized_email = normalize_email(email)

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO hospitals (
                network_id,
                name,
                code,
                city,
                state,
                address,
                phone,
                email,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                network_id,
                name.strip(),
                normalized_code,
                city.strip() if city else None,
                state.strip() if state else None,
                address.strip() if address else None,
                normalized_phone,
                normalized_email,
                now_iso(),
            ),
        )

        hospital_id = cur.lastrowid
        conn.commit()
        return hospital_id

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        message = str(exc).lower()

        if "hospitals.code" in message:
            raise ValueError("Hospital code already exists") from exc

        if "hospitals.email" in message:
            raise ValueError("Hospital email already exists") from exc

        raise ValueError("Could not create hospital because of duplicate or invalid data") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_hospital(hospital_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            h.*,
            hn.name AS network_name
        FROM hospitals h
        LEFT JOIN hospital_networks hn ON hn.id = h.network_id
        WHERE h.id = ?
        """,
        (hospital_id,),
    )

    hospital = row_to_dict(cur.fetchone())
    conn.close()
    return hospital


def get_hospital_by_code(code):
    normalized_code = normalize_code(code)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            h.*,
            hn.name AS network_name
        FROM hospitals h
        LEFT JOIN hospital_networks hn ON hn.id = h.network_id
        WHERE h.code = ?
        """,
        (normalized_code,),
    )

    hospital = row_to_dict(cur.fetchone())
    conn.close()
    return hospital


def list_hospitals(active_only=True, limit=50, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    where_clause = "WHERE h.is_active = 1" if active_only else ""

    cur.execute(
        f"""
        SELECT
            h.*,
            hn.name AS network_name
        FROM hospitals h
        LEFT JOIN hospital_networks hn ON hn.id = h.network_id
        {where_clause}
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )

    hospitals = rows_to_dicts(cur.fetchall())
    conn.close()
    return hospitals


def list_hospitals_by_network(network_id, active_only=True, limit=50, offset=0):
    ensure_network_exists(network_id)

    conn = get_connection()
    cur = conn.cursor()

    filters = ["h.network_id = ?"]
    params = [network_id]

    if active_only:
        filters.append("h.is_active = 1")

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            h.*,
            hn.name AS network_name
        FROM hospitals h
        LEFT JOIN hospital_networks hn ON hn.id = h.network_id
        WHERE {" AND ".join(filters)}
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    hospitals = rows_to_dicts(cur.fetchall())
    conn.close()
    return hospitals


def search_hospitals(search_text, active_only=True, limit=50, offset=0):
    search = f"%{search_text.strip()}%" if search_text else "%"

    conn = get_connection()
    cur = conn.cursor()

    filters = [
        """
        (
            h.name LIKE ?
            OR h.code LIKE ?
            OR h.city LIKE ?
            OR h.state LIKE ?
            OR h.phone LIKE ?
            OR h.email LIKE ?
        )
        """
    ]

    params = [search, search, search, search, search, search]

    if active_only:
        filters.append("h.is_active = 1")

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            h.*,
            hn.name AS network_name
        FROM hospitals h
        LEFT JOIN hospital_networks hn ON hn.id = h.network_id
        WHERE {" AND ".join(filters)}
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    hospitals = rows_to_dicts(cur.fetchall())
    conn.close()
    return hospitals


def update_hospital(
    hospital_id,
    name=None,
    code=None,
    network_id=None,
    city=None,
    state=None,
    address=None,
    phone=None,
    email=None,
):
    existing = get_hospital(hospital_id)

    if not existing:
        return False

    if name is not None and not name.strip():
        raise ValueError("Hospital name cannot be empty")

    new_network_id = network_id if network_id is not None else existing["network_id"]
    ensure_network_exists(new_network_id)

    new_code = normalize_code(code) if code is not None else existing["code"]
    new_phone = normalize_phone(phone) if phone is not None else existing["phone"]
    new_email = normalize_email(email) if email is not None else existing["email"]

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE hospitals
            SET
                network_id = ?,
                name = ?,
                code = ?,
                city = ?,
                state = ?,
                address = ?,
                phone = ?,
                email = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_network_id,
                name.strip() if name is not None else existing["name"],
                new_code,
                city.strip() if city is not None and city else existing["city"],
                state.strip() if state is not None and state else existing["state"],
                address.strip() if address is not None and address else existing["address"],
                new_phone,
                new_email,
                now_iso(),
                hospital_id,
            ),
        )

        conn.commit()
        return cur.rowcount > 0

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        message = str(exc).lower()

        if "hospitals.code" in message:
            raise ValueError("Hospital code already exists") from exc

        if "hospitals.email" in message:
            raise ValueError("Hospital email already exists") from exc

        raise ValueError("Could not update hospital because of duplicate or invalid data") from exc

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def deactivate_hospital(hospital_id):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE hospitals
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), hospital_id),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def activate_hospital(hospital_id):
    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE hospitals
            SET is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), hospital_id),
        )

        conn.commit()
        return cur.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()