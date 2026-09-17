import json
from datetime import date

from .audit_repo import log_audit
from .connection import get_connection, now_iso, row_to_dict, rows_to_dicts
from .patient_repo import calculate_age
from .visit_repo import get_visit


VALID_RISK_LEVELS = {"Low", "Moderate", "High", "Very High"}
VALID_HEART_MODES = {"simple_screening", "advanced_medical"}


def safe_json_text(value):
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            return json.dumps({"text": value}, ensure_ascii=False)

    return json.dumps(value, ensure_ascii=False)


def normalize_risk_level(value):
    if not value:
        return None

    value = str(value).strip()

    mapping = {
        "low": "Low",
        "moderate": "Moderate",
        "medium": "Moderate",
        "high": "High",
        "very high": "Very High",
        "very_high": "Very High",
    }

    normalized = mapping.get(value.lower(), value)

    if normalized not in VALID_RISK_LEVELS:
        raise ValueError("Invalid risk level")

    return normalized


def normalize_confidence(value):
    if value is None:
        return None

    confidence = float(value)

    if confidence < 0 or confidence > 100:
        raise ValueError("Confidence must be between 0 and 100")

    return confidence


def get_age_at_visit(visit):
    if not visit:
        return None

    visit_date = visit.get("visit_date")
    date_of_birth = visit.get("date_of_birth")

    if not date_of_birth:
        return None

    if visit_date:
        visit_day = date.fromisoformat(visit_date[:10])
        return calculate_age(date_of_birth, reference_date=visit_day)

    return calculate_age(date_of_birth)


def create_diabetes_report(
    visit_id,
    input_values,
    prediction_result,
    actor_user_id=None,
):
    visit = get_visit(visit_id)

    if not visit:
        raise ValueError(f"Visit not found: {visit_id}")

    age_at_visit = get_age_at_visit(visit)

    explanation_json = safe_json_text(prediction_result.get("explanation"))

    risk_level = normalize_risk_level(
        prediction_result.get("risk")
        or prediction_result.get("clinical_risk")
        or prediction_result.get("risk_level")
    )

    confidence = normalize_confidence(prediction_result.get("confidence"))

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO diabetes_reports (
                visit_id,
                pregnancies,
                glucose,
                blood_pressure,
                skin_thickness,
                insulin,
                bmi,
                diabetes_pedigree_function,
                age_at_visit,
                prediction_result,
                risk_level,
                confidence,
                explanation_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visit_id,
                input_values.get("Pregnancies"),
                input_values.get("Glucose"),
                input_values.get("BloodPressure"),
                input_values.get("SkinThickness"),
                input_values.get("Insulin"),
                input_values.get("BMI"),
                input_values.get("DiabetesPedigreeFunction"),
                age_at_visit,
                prediction_result.get("result"),
                risk_level,
                confidence,
                explanation_json,
                now_iso(),
            ),
        )

        report_id = cur.lastrowid

        log_audit(
            action="create_diabetes_report",
            entity_type="diabetes_report",
            entity_id=report_id,
            actor_user_id=actor_user_id,
            details=f"Created diabetes report for visit {visit_id}",
            conn=conn,
        )

        conn.commit()

        return {
            "id": report_id,
            "visit_id": visit_id,
            "risk_level": risk_level,
            "confidence": confidence,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def create_heart_report(
    visit_id,
    mode,
    input_values,
    prediction_result,
    actor_user_id=None,
):
    visit = get_visit(visit_id)

    if not visit:
        raise ValueError(f"Visit not found: {visit_id}")

    if mode not in VALID_HEART_MODES:
        raise ValueError("Invalid heart report mode")

    age_at_visit = get_age_at_visit(visit)

    explanation_json = safe_json_text(
        prediction_result.get("explanation")
        or prediction_result.get("top_factors")
        or prediction_result
    )

    risk_level = normalize_risk_level(
        prediction_result.get("risk")
        or prediction_result.get("risk_level")
    )

    confidence = normalize_confidence(prediction_result.get("confidence"))

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO heart_reports (
                visit_id,
                mode,
                age_at_visit,
                gender,
                chest_pain,
                breathless_walking,
                high_bp,
                diabetes,
                smoking,
                high_cholesterol,
                tired_easily,
                family_history,
                poor_exercise_recovery,
                exercise_chest_pain,

                trestbps,
                chol,
                fbs,
                thalch,
                exang,
                oldpeak,
                ca,
                ecg_result,
                thalassemia,

                prediction_result,
                risk_level,
                confidence,
                explanation_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visit_id,
                mode,
                age_at_visit,
                input_values.get("gender") or input_values.get("Gender"),
                input_values.get("chest_pain"),
                input_values.get("breathless_walking"),
                input_values.get("high_bp"),
                input_values.get("diabetes"),
                input_values.get("smoking"),
                input_values.get("high_cholesterol"),
                input_values.get("tired_easily"),
                input_values.get("family_history"),
                input_values.get("poor_exercise_recovery"),
                input_values.get("exercise_chest_pain"),

                input_values.get("trestbps"),
                input_values.get("chol"),
                input_values.get("fbs"),
                input_values.get("thalch"),
                input_values.get("exang"),
                input_values.get("oldpeak"),
                input_values.get("ca"),
                input_values.get("ecg_result"),
                input_values.get("thalassemia"),

                prediction_result.get("result"),
                risk_level,
                confidence,
                explanation_json,
                now_iso(),
            ),
        )

        report_id = cur.lastrowid

        log_audit(
            action="create_heart_report",
            entity_type="heart_report",
            entity_id=report_id,
            actor_user_id=actor_user_id,
            details=f"Created heart report for visit {visit_id}",
            conn=conn,
        )

        conn.commit()

        return {
            "id": report_id,
            "visit_id": visit_id,
            "mode": mode,
            "risk_level": risk_level,
            "confidence": confidence,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_diabetes_report(report_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM diabetes_reports
        WHERE id = ?
        """,
        (report_id,),
    )

    report = row_to_dict(cur.fetchone())
    conn.close()
    return report


def get_heart_report(report_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM heart_reports
        WHERE id = ?
        """,
        (report_id,),
    )

    report = row_to_dict(cur.fetchone())
    conn.close()
    return report


def list_visit_reports(visit_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            'diabetes' AS report_type,
            id,
            visit_id,
            prediction_result,
            risk_level,
            confidence,
            created_at
        FROM diabetes_reports
        WHERE visit_id = ?

        UNION ALL

        SELECT
            'heart' AS report_type,
            id,
            visit_id,
            prediction_result,
            risk_level,
            confidence,
            created_at
        FROM heart_reports
        WHERE visit_id = ?

        ORDER BY created_at DESC
        """,
        (visit_id, visit_id),
    )

    reports = rows_to_dicts(cur.fetchall())
    conn.close()
    return reports


def get_latest_diabetes_report(patient_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT dr.*
        FROM diabetes_reports dr
        JOIN visits v ON v.id = dr.visit_id
        WHERE v.patient_id = ?
          AND v.visit_status != 'cancelled'
        ORDER BY dr.created_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )

    report = row_to_dict(cur.fetchone())
    conn.close()
    return report


def get_latest_heart_report(patient_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT hr.*
        FROM heart_reports hr
        JOIN visits v ON v.id = hr.visit_id
        WHERE v.patient_id = ?
          AND v.visit_status != 'cancelled'
        ORDER BY hr.created_at DESC
        LIMIT 1
        """,
        (patient_id,),
    )

    report = row_to_dict(cur.fetchone())
    conn.close()
    return report


def list_patient_diabetes_reports(patient_id, limit=20, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            dr.*,
            v.visit_date,
            h.name AS hospital_name
        FROM diabetes_reports dr
        JOIN visits v ON v.id = dr.visit_id
        JOIN hospitals h ON h.id = v.hospital_id
        WHERE v.patient_id = ?
          AND v.visit_status != 'cancelled'
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
        """,
        (patient_id, limit, offset),
    )

    reports = rows_to_dicts(cur.fetchall())
    conn.close()
    return reports


def list_patient_heart_reports(patient_id, limit=20, offset=0):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            hr.*,
            v.visit_date,
            h.name AS hospital_name
        FROM heart_reports hr
        JOIN visits v ON v.id = hr.visit_id
        JOIN hospitals h ON h.id = v.hospital_id
        WHERE v.patient_id = ?
          AND v.visit_status != 'cancelled'
        ORDER BY v.visit_date DESC
        LIMIT ? OFFSET ?
        """,
        (patient_id, limit, offset),
    )

    reports = rows_to_dicts(cur.fetchall())
    conn.close()
    return reports