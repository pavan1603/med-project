from .connection import get_connection, row_to_dict, rows_to_dicts


VALID_RISK_LEVELS = {"Low", "Moderate", "High", "Very High"}


def build_scope_filter(alias="v", hospital_id=None, network_id=None):
    filters = []
    params = []

    if hospital_id is not None:
        filters.append(f"{alias}.hospital_id = ?")
        params.append(hospital_id)

    if network_id is not None:
        filters.append("h.network_id = ?")
        params.append(network_id)

    return filters, params


def build_date_filter(alias="v", start_date=None, end_date=None):
    filters = []
    params = []

    if start_date:
        filters.append(f"date(substr({alias}.visit_date, 1, 10)) >= date(?)")
        params.append(start_date)

    if end_date:
        filters.append(f"date(substr({alias}.visit_date, 1, 10)) <= date(?)")
        params.append(end_date)

    return filters, params


def combine_filters(filters):
    if not filters:
        return ""

    return "WHERE " + " AND ".join(filters)


def get_dashboard_summary(
    hospital_id=None,
    network_id=None,
    start_date=None,
    end_date=None,
):
    conn = get_connection()
    cur = conn.cursor()

    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )
    date_filters, date_params = build_date_filter(
        "v",
        start_date=start_date,
        end_date=end_date,
    )

    visit_filters = ["v.visit_status != 'cancelled'"] + scope_filters + date_filters
    visit_where = combine_filters(visit_filters)
    visit_params = scope_params + date_params

    cur.execute(
        f"""
        SELECT
            COUNT(DISTINCT v.id) AS total_visits,
            COUNT(DISTINCT v.patient_id) AS total_patients,
            SUM(CASE WHEN v.visit_status = 'waiting' THEN 1 ELSE 0 END) AS waiting_visits,
            SUM(CASE WHEN v.visit_status = 'in_consultation' THEN 1 ELSE 0 END) AS in_consultation_visits,
            SUM(CASE WHEN v.visit_status = 'completed' THEN 1 ELSE 0 END) AS completed_visits
        FROM visits v
        JOIN hospitals h ON h.id = v.hospital_id
        {visit_where}
        """,
        visit_params,
    )

    visit_summary = row_to_dict(cur.fetchone())

    if hospital_id is None and network_id is None:
        cur.execute("SELECT COUNT(DISTINCT id) AS registered_patients FROM patients WHERE is_active = 1")
        registered_patients = cur.fetchone()["registered_patients"]
    else:
        patient_filters = ["p.is_active = 1"]
        patient_params = []

        if hospital_id is not None:
            patient_filters.append("u.hospital_id = ?")
            patient_params.append(hospital_id)

        if network_id is not None:
            patient_filters.append("h.network_id = ?")
            patient_params.append(network_id)

        cur.execute(
            f"""
            SELECT COUNT(DISTINCT p.id) AS registered_patients
            FROM patients p
            LEFT JOIN users u ON u.id = p.registered_by_user_id
            LEFT JOIN hospitals h ON h.id = u.hospital_id
            WHERE {" AND ".join(patient_filters)}
            """,
            patient_params,
        )
        registered_patients = cur.fetchone()["registered_patients"]

    cur.execute(
        f"""
        SELECT COUNT(DISTINCT h.id) AS total_hospitals
        FROM hospitals h
        WHERE h.is_active = 1
          AND (? IS NULL OR h.id = ?)
          AND (? IS NULL OR h.network_id = ?)
        """,
        (hospital_id, hospital_id, network_id, network_id),
    )

    hospital_summary = row_to_dict(cur.fetchone())

    cur.execute(
        f"""
        SELECT COUNT(DISTINCT dr.id) AS diabetes_reports
        FROM diabetes_reports dr
        JOIN visits v ON v.id = dr.visit_id
        JOIN hospitals h ON h.id = v.hospital_id
        {visit_where}
        """,
        visit_params,
    )

    diabetes_reports = cur.fetchone()["diabetes_reports"]

    cur.execute(
        f"""
        SELECT COUNT(DISTINCT hr.id) AS heart_reports
        FROM heart_reports hr
        JOIN visits v ON v.id = hr.visit_id
        JOIN hospitals h ON h.id = v.hospital_id
        {visit_where}
        """,
        visit_params,
    )

    heart_reports = cur.fetchone()["heart_reports"]

    conn.close()

    return {
        "total_hospitals": hospital_summary["total_hospitals"],
        "total_patients": registered_patients or visit_summary["total_patients"] or 0,
        "total_visits": visit_summary["total_visits"] or 0,
        "waiting_visits": visit_summary["waiting_visits"] or 0,
        "in_consultation_visits": visit_summary["in_consultation_visits"] or 0,
        "completed_visits": visit_summary["completed_visits"] or 0,
        "diabetes_reports": diabetes_reports or 0,
        "heart_reports": heart_reports or 0,
        "scope": {
            "hospital_id": hospital_id,
            "network_id": network_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    }


def get_hospital_wise_summary(
    network_id=None,
    start_date=None,
    end_date=None,
    limit=100,
    offset=0,
):
    conn = get_connection()
    cur = conn.cursor()

    filters = ["h.is_active = 1"]
    params = []

    if network_id is not None:
        filters.append("h.network_id = ?")
        params.append(network_id)

    if start_date:
        filters.append("(v.id IS NULL OR date(substr(v.visit_date, 1, 10)) >= date(?))")
        params.append(start_date)

    if end_date:
        filters.append("(v.id IS NULL OR date(substr(v.visit_date, 1, 10)) <= date(?))")
        params.append(end_date)

    params.extend([limit, offset])

    cur.execute(
        f"""
        SELECT
            h.id AS hospital_id,
            h.name AS hospital_name,
            h.code AS hospital_code,
            h.city,
            h.state,
            COUNT(DISTINCT v.patient_id) AS total_patients,
            COUNT(DISTINCT CASE WHEN v.visit_status != 'cancelled' THEN v.id END) AS total_visits,
            COUNT(DISTINCT dr.id) AS diabetes_reports,
            COUNT(DISTINCT hr.id) AS heart_reports,
            COUNT(DISTINCT CASE WHEN dr.risk_level IN ('High', 'Very High') THEN dr.id END) AS high_diabetes_reports,
            COUNT(DISTINCT CASE WHEN hr.risk_level IN ('High', 'Very High') THEN hr.id END) AS high_heart_reports
        FROM hospitals h
        LEFT JOIN visits v ON v.hospital_id = h.id
        LEFT JOIN diabetes_reports dr ON dr.visit_id = v.id
        LEFT JOIN heart_reports hr ON hr.visit_id = v.id
        WHERE {" AND ".join(filters)}
        GROUP BY h.id
        ORDER BY total_visits DESC, h.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_risk_distribution(
    disease,
    hospital_id=None,
    network_id=None,
    start_date=None,
    end_date=None,
):
    if disease not in {"diabetes", "heart"}:
        raise ValueError("disease must be 'diabetes' or 'heart'")

    report_table = "diabetes_reports" if disease == "diabetes" else "heart_reports"
    report_alias = "dr" if disease == "diabetes" else "hr"

    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )
    date_filters, date_params = build_date_filter(
        "v",
        start_date=start_date,
        end_date=end_date,
    )

    filters = ["v.visit_status != 'cancelled'"] + scope_filters + date_filters
    params = scope_params + date_params

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            COALESCE({report_alias}.risk_level, 'Unknown') AS risk_level,
            COUNT(*) AS count
        FROM {report_table} {report_alias}
        JOIN visits v ON v.id = {report_alias}.visit_id
        JOIN hospitals h ON h.id = v.hospital_id
        {combine_filters(filters)}
        GROUP BY COALESCE({report_alias}.risk_level, 'Unknown')
        ORDER BY count DESC
        """,
        params,
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_visit_status_distribution(
    hospital_id=None,
    network_id=None,
    start_date=None,
    end_date=None,
):
    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )
    date_filters, date_params = build_date_filter(
        "v",
        start_date=start_date,
        end_date=end_date,
    )

    filters = scope_filters + date_filters
    params = scope_params + date_params

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            v.visit_status,
            COUNT(*) AS count
        FROM visits v
        JOIN hospitals h ON h.id = v.hospital_id
        {combine_filters(filters)}
        GROUP BY v.visit_status
        ORDER BY count DESC
        """,
        params,
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_visit_trend(
    hospital_id=None,
    network_id=None,
    start_date=None,
    end_date=None,
    group_by="day",
):
    if group_by not in {"day", "month"}:
        raise ValueError("group_by must be 'day' or 'month'")

    date_expr = "substr(v.visit_date, 1, 10)" if group_by == "day" else "substr(v.visit_date, 1, 7)"

    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )
    date_filters, date_params = build_date_filter(
        "v",
        start_date=start_date,
        end_date=end_date,
    )

    filters = ["v.visit_status != 'cancelled'"] + scope_filters + date_filters
    params = scope_params + date_params

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            {date_expr} AS period,
            COUNT(*) AS visits,
            COUNT(DISTINCT v.patient_id) AS patients
        FROM visits v
        JOIN hospitals h ON h.id = v.hospital_id
        {combine_filters(filters)}
        GROUP BY {date_expr}
        ORDER BY period ASC
        """,
        params,
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_disease_risk_trend(
    disease,
    hospital_id=None,
    network_id=None,
    start_date=None,
    end_date=None,
    group_by="day",
):
    if disease not in {"diabetes", "heart"}:
        raise ValueError("disease must be 'diabetes' or 'heart'")

    if group_by not in {"day", "month"}:
        raise ValueError("group_by must be 'day' or 'month'")

    report_table = "diabetes_reports" if disease == "diabetes" else "heart_reports"
    report_alias = "dr" if disease == "diabetes" else "hr"
    date_expr = "substr(v.visit_date, 1, 10)" if group_by == "day" else "substr(v.visit_date, 1, 7)"

    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )
    date_filters, date_params = build_date_filter(
        "v",
        start_date=start_date,
        end_date=end_date,
    )

    filters = ["v.visit_status != 'cancelled'"] + scope_filters + date_filters
    params = scope_params + date_params

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            {date_expr} AS period,
            COALESCE({report_alias}.risk_level, 'Unknown') AS risk_level,
            COUNT(*) AS count
        FROM {report_table} {report_alias}
        JOIN visits v ON v.id = {report_alias}.visit_id
        JOIN hospitals h ON h.id = v.hospital_id
        {combine_filters(filters)}
        GROUP BY {date_expr}, COALESCE({report_alias}.risk_level, 'Unknown')
        ORDER BY period ASC
        """,
        params,
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_patient_demographics(
    hospital_id=None,
    network_id=None,
    start_date=None,
    end_date=None,
):
    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )
    date_filters, date_params = build_date_filter(
        "v",
        start_date=start_date,
        end_date=end_date,
    )

    filters = ["v.visit_status != 'cancelled'"] + scope_filters + date_filters
    params = scope_params + date_params

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            p.gender,
            COUNT(DISTINCT p.id) AS count
        FROM patients p
        JOIN visits v ON v.patient_id = p.id
        JOIN hospitals h ON h.id = v.hospital_id
        {combine_filters(filters)}
        GROUP BY p.gender
        ORDER BY count DESC
        """,
        params,
    )

    gender_distribution = rows_to_dicts(cur.fetchall())

    cur.execute(
        f"""
        SELECT
            CASE
                WHEN p.date_of_birth IS NULL THEN 'Unknown'
                WHEN CAST(strftime('%Y', 'now') AS INTEGER) - CAST(substr(p.date_of_birth, 1, 4) AS INTEGER) < 18 THEN '0-17'
                WHEN CAST(strftime('%Y', 'now') AS INTEGER) - CAST(substr(p.date_of_birth, 1, 4) AS INTEGER) BETWEEN 18 AND 30 THEN '18-30'
                WHEN CAST(strftime('%Y', 'now') AS INTEGER) - CAST(substr(p.date_of_birth, 1, 4) AS INTEGER) BETWEEN 31 AND 45 THEN '31-45'
                WHEN CAST(strftime('%Y', 'now') AS INTEGER) - CAST(substr(p.date_of_birth, 1, 4) AS INTEGER) BETWEEN 46 AND 60 THEN '46-60'
                ELSE '60+'
            END AS age_group,
            COUNT(DISTINCT p.id) AS count
        FROM patients p
        JOIN visits v ON v.patient_id = p.id
        JOIN hospitals h ON h.id = v.hospital_id
        {combine_filters(filters)}
        GROUP BY age_group
        ORDER BY age_group
        """,
        params,
    )

    age_distribution = rows_to_dicts(cur.fetchall())
    conn.close()

    return {
        "gender_distribution": gender_distribution,
        "age_distribution": age_distribution,
    }


def get_latest_high_risk_patients(
    hospital_id=None,
    network_id=None,
    limit=50,
    offset=0,
):
    scope_filters, scope_params = build_scope_filter(
        "v",
        hospital_id=hospital_id,
        network_id=network_id,
    )

    filters = ["v.visit_status != 'cancelled'"] + scope_filters
    params = scope_params + [limit, offset]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        WITH latest_visits AS (
            SELECT
                v.patient_id,
                MAX(v.visit_date) AS latest_visit_date
            FROM visits v
            JOIN hospitals h ON h.id = v.hospital_id
            {combine_filters(filters)}
            GROUP BY v.patient_id
        )
        SELECT
            p.id AS patient_id,
            p.patient_uid,
            p.full_name,
            p.phone,
            p.preferred_language,
            v.id AS visit_id,
            v.visit_date,
            h.name AS hospital_name,
            dr.risk_level AS diabetes_risk,
            hr.risk_level AS heart_risk
        FROM latest_visits lv
        JOIN visits v
            ON v.patient_id = lv.patient_id
           AND v.visit_date = lv.latest_visit_date
        JOIN patients p ON p.id = v.patient_id
        JOIN hospitals h ON h.id = v.hospital_id
        LEFT JOIN diabetes_reports dr ON dr.visit_id = v.id
        LEFT JOIN heart_reports hr ON hr.visit_id = v.id
        WHERE (
            dr.risk_level IN ('High', 'Very High')
            OR hr.risk_level IN ('High', 'Very High')
        )
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_recent_activity(limit=50, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.id,
            a.action,
            a.entity_type,
            a.entity_id,
            a.details,
            a.created_at,
            u.full_name AS actor_name,
            u.role AS actor_role
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.actor_user_id
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )

    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return rows


def get_patient_report_summary(patient_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            p.id AS patient_id,
            p.patient_uid,
            p.full_name,
            p.preferred_language,
            COUNT(DISTINCT v.id) AS total_visits,
            COUNT(DISTINCT dr.id) AS diabetes_reports,
            COUNT(DISTINCT hr.id) AS heart_reports,
            MAX(v.visit_date) AS latest_visit_date
        FROM patients p
        LEFT JOIN visits v
            ON v.patient_id = p.id
           AND v.visit_status != 'cancelled'
        LEFT JOIN diabetes_reports dr ON dr.visit_id = v.id
        LEFT JOIN heart_reports hr ON hr.visit_id = v.id
        WHERE p.id = ?
        GROUP BY p.id
        """,
        (patient_id,),
    )

    summary = row_to_dict(cur.fetchone())
    conn.close()
    return summary
