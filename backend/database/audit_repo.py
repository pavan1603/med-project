from .connection import get_connection, now_iso, row_to_dict, rows_to_dicts


def log_audit(
    action,
    entity_type,
    entity_id=None,
    actor_user_id=None,
    details=None,
    conn=None,
):
    own_connection = conn is None

    if own_connection:
        conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
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

        audit_id = cur.lastrowid

        if own_connection:
            conn.commit()

        return audit_id

    except Exception:
        if own_connection:
            conn.rollback()
        raise

    finally:
        if own_connection:
            conn.close()


def get_audit_log(audit_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.id,
            a.actor_user_id,
            u.full_name AS actor_name,
            u.role AS actor_role,
            a.action,
            a.entity_type,
            a.entity_id,
            a.details,
            a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.actor_user_id
        WHERE a.id = ?
        """,
        (audit_id,),
    )

    audit = row_to_dict(cur.fetchone())
    conn.close()
    return audit


def list_audit_logs(
    actor_user_id=None,
    entity_type=None,
    entity_id=None,
    action=None,
    limit=100,
    offset=0,
):
    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if actor_user_id is not None:
        filters.append("a.actor_user_id = ?")
        params.append(actor_user_id)

    if entity_type is not None:
        filters.append("a.entity_type = ?")
        params.append(entity_type)

    if entity_id is not None:
        filters.append("a.entity_id = ?")
        params.append(entity_id)

    if action is not None:
        filters.append("a.action = ?")
        params.append(action)

    where_clause = ""

    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            a.id,
            a.actor_user_id,
            u.full_name AS actor_name,
            u.role AS actor_role,
            a.action,
            a.entity_type,
            a.entity_id,
            a.details,
            a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.actor_user_id
        {where_clause}
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    logs = rows_to_dicts(cur.fetchall())
    conn.close()
    return logs


def list_entity_audit_history(entity_type, entity_id, limit=100, offset=0):
    return list_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )