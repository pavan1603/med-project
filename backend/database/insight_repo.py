import json

from .report_repo import list_patient_diabetes_reports, list_patient_heart_reports


RISK_ORDER = {
    None: 0,
    "Low": 1,
    "Moderate": 2,
    "High": 3,
    "Very High": 4,
}


def parse_json(value):
    if not value:
        return None

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def numeric_change(current, previous):
    if current is None or previous is None:
        return None

    try:
        current = float(current)
        previous = float(previous)
    except (TypeError, ValueError):
        return None

    change = round(current - previous, 2)

    if change > 0:
        direction = "increased"
    elif change < 0:
        direction = "decreased"
    else:
        direction = "unchanged"

    return {
        "previous": previous,
        "current": current,
        "change": change,
        "direction": direction,
    }


def risk_change(current, previous):
    current_score = RISK_ORDER.get(current, 0)
    previous_score = RISK_ORDER.get(previous, 0)

    if current_score > previous_score:
        direction = "worsened"
    elif current_score < previous_score:
        direction = "improved"
    else:
        direction = "unchanged"

    return {
        "previous": previous,
        "current": current,
        "direction": direction,
    }


def interpret_metric(metric, change_data):
    if not change_data:
        return None

    direction = change_data["direction"]

    if direction == "unchanged":
        health_direction = "unchanged"
    elif metric in {"glucose", "bmi", "blood_pressure", "cholesterol", "st_depression"}:
        health_direction = "worsened" if direction == "increased" else "improved"
    elif metric == "max_heart_rate":
        health_direction = "improved" if direction == "increased" else "needs_review"
    else:
        health_direction = "changed"

    return {
        **change_data,
        "health_direction": health_direction,
    }


def build_metric_sentence(label, interpreted, unit=""):
    if not interpreted:
        return None

    previous = interpreted["previous"]
    current = interpreted["current"]
    direction = interpreted["direction"]
    health_direction = interpreted["health_direction"]

    if direction == "unchanged":
        return f"{label} stayed the same at {current}{unit}."

    if health_direction == "improved":
        return f"{label} improved from {previous}{unit} to {current}{unit}."

    if health_direction == "worsened":
        return f"{label} worsened from {previous}{unit} to {current}{unit}."

    if health_direction == "needs_review":
        return f"{label} changed from {previous}{unit} to {current}{unit}; this should be reviewed with clinical context."

    return f"{label} changed from {previous}{unit} to {current}{unit}."


def extract_top_factors(report, max_items=3):
    explanation = parse_json(report.get("explanation_json"))

    if not explanation:
        return []

    top_factors = explanation.get("top_factors")

    if not isinstance(top_factors, list):
        return []

    factors = []

    for factor in top_factors[:max_items]:
        name = factor.get("name")
        status = factor.get("status")

        if name and status:
            factors.append(f"{name} ({status})")
        elif name:
            factors.append(name)

    return factors


def compare_diabetes_reports(patient_id):
    reports = list_patient_diabetes_reports(patient_id, limit=2)

    if not reports:
        return {
            "available": False,
            "message": "No diabetes reports are available for this patient.",
        }

    current = reports[0]
    previous = reports[1] if len(reports) > 1 else None

    current_factors = extract_top_factors(current)

    if not previous:
        return {
            "available": True,
            "has_previous": False,
            "current": current,
            "current_top_factors": current_factors,
            "message": "Only one diabetes report is available. Future visits can be compared against this baseline.",
        }

    glucose_change = interpret_metric(
        "glucose",
        numeric_change(current.get("glucose"), previous.get("glucose")),
    )
    bmi_change = interpret_metric(
        "bmi",
        numeric_change(current.get("bmi"), previous.get("bmi")),
    )
    bp_change = interpret_metric(
        "blood_pressure",
        numeric_change(current.get("blood_pressure"), previous.get("blood_pressure")),
    )
    confidence_change = numeric_change(current.get("confidence"), previous.get("confidence"))
    risk_movement = risk_change(current.get("risk_level"), previous.get("risk_level"))

    summary_points = []

    for sentence in [
        build_metric_sentence("Glucose", glucose_change, " mg/dL"),
        build_metric_sentence("BMI", bmi_change),
        build_metric_sentence("Blood pressure", bp_change, " mmHg"),
    ]:
        if sentence:
            summary_points.append(sentence)

    if risk_movement["direction"] == "worsened":
        summary_points.append(
            f"Diabetes risk worsened from {risk_movement['previous']} to {risk_movement['current']}."
        )
    elif risk_movement["direction"] == "improved":
        summary_points.append(
            f"Diabetes risk improved from {risk_movement['previous']} to {risk_movement['current']}."
        )
    else:
        summary_points.append(
            f"Diabetes risk remained {risk_movement['current']}."
        )

    if current_factors:
        summary_points.append(
            "Current main diabetes factors: " + ", ".join(current_factors) + "."
        )

    return {
        "available": True,
        "has_previous": True,
        "current": current,
        "previous": previous,
        "current_visit_date": current.get("visit_date"),
        "previous_visit_date": previous.get("visit_date"),
        "current_top_factors": current_factors,
        "changes": {
            "glucose": glucose_change,
            "bmi": bmi_change,
            "blood_pressure": bp_change,
            "confidence": confidence_change,
            "risk": risk_movement,
        },
        "summary_points": summary_points,
    }


def compare_heart_reports(patient_id):
    reports = list_patient_heart_reports(patient_id, limit=2)

    if not reports:
        return {
            "available": False,
            "message": "No heart reports are available for this patient.",
        }

    current = reports[0]
    previous = reports[1] if len(reports) > 1 else None

    current_factors = extract_top_factors(current)

    if not previous:
        return {
            "available": True,
            "has_previous": False,
            "current": current,
            "current_top_factors": current_factors,
            "message": "Only one heart report is available. Future visits can be compared against this baseline.",
        }

    bp_change = interpret_metric(
        "blood_pressure",
        numeric_change(current.get("trestbps"), previous.get("trestbps")),
    )
    cholesterol_change = interpret_metric(
        "cholesterol",
        numeric_change(current.get("chol"), previous.get("chol")),
    )
    max_hr_change = interpret_metric(
        "max_heart_rate",
        numeric_change(current.get("thalch"), previous.get("thalch")),
    )
    st_change = interpret_metric(
        "st_depression",
        numeric_change(current.get("oldpeak"), previous.get("oldpeak")),
    )
    confidence_change = numeric_change(current.get("confidence"), previous.get("confidence"))
    risk_movement = risk_change(current.get("risk_level"), previous.get("risk_level"))

    summary_points = []

    for sentence in [
        build_metric_sentence("Resting blood pressure", bp_change, " mmHg"),
        build_metric_sentence("Cholesterol", cholesterol_change, " mg/dL"),
        build_metric_sentence("Maximum heart rate", max_hr_change, " bpm"),
        build_metric_sentence("ST depression", st_change),
    ]:
        if sentence:
            summary_points.append(sentence)

    if risk_movement["direction"] == "worsened":
        summary_points.append(
            f"Heart risk worsened from {risk_movement['previous']} to {risk_movement['current']}."
        )
    elif risk_movement["direction"] == "improved":
        summary_points.append(
            f"Heart risk improved from {risk_movement['previous']} to {risk_movement['current']}."
        )
    else:
        summary_points.append(
            f"Heart risk remained {risk_movement['current']}."
        )

    if current_factors:
        summary_points.append(
            "Current main heart factors: " + ", ".join(current_factors) + "."
        )

    return {
        "available": True,
        "has_previous": True,
        "current": current,
        "previous": previous,
        "current_visit_date": current.get("visit_date"),
        "previous_visit_date": previous.get("visit_date"),
        "current_top_factors": current_factors,
        "changes": {
            "resting_bp": bp_change,
            "cholesterol": cholesterol_change,
            "max_heart_rate": max_hr_change,
            "st_depression": st_change,
            "confidence": confidence_change,
            "risk": risk_movement,
        },
        "summary_points": summary_points,
    }


def determine_severity(diabetes_comparison, heart_comparison):
    severity = "routine"

    for comparison in [diabetes_comparison, heart_comparison]:
        if not comparison.get("available"):
            continue

        current = comparison.get("current", {})
        risk = current.get("risk_level")

        if risk == "Very High":
            return "urgent"

        if risk == "High":
            severity = "priority"

    return severity


def build_patient_recommendations(diabetes_comparison, heart_comparison):
    recommendations = []

    if diabetes_comparison.get("available"):
        current = diabetes_comparison.get("current", {})
        glucose = current.get("glucose")
        bmi = current.get("bmi")
        risk = current.get("risk_level")

        if risk in {"High", "Very High"}:
            recommendations.append(
                "Schedule a doctor consultation for diabetes confirmation and treatment planning."
            )

        if glucose is not None and glucose >= 126:
            recommendations.append(
                "Monitor fasting and post-meal glucose as advised by a clinician."
            )

        if bmi is not None and bmi >= 25:
            recommendations.append(
                "Focus on weight management through portion control and regular walking if medically safe."
            )

        recommendations.append(
            "Prefer vegetables, dal, whole grains, controlled rice portions, and avoid sugary drinks."
        )

    if heart_comparison.get("available"):
        current = heart_comparison.get("current", {})
        risk = current.get("risk_level")
        bp = current.get("trestbps")
        chol = current.get("chol")

        if risk in {"High", "Very High"}:
            recommendations.append(
                "Consult a cardiologist and seek emergency care for chest pain, breathlessness, fainting, or pain spreading to arm or jaw."
            )

        if bp is not None and bp >= 140:
            recommendations.append(
                "Monitor blood pressure regularly and reduce excess salt intake."
            )

        if chol is not None and chol >= 200:
            recommendations.append(
                "Limit fried foods, packaged snacks, excess ghee, butter, and high-fat foods."
            )

        recommendations.append(
            "Stay physically active only as medically safe, especially if heart symptoms are present."
        )

    if not recommendations:
        recommendations.append(
            "Continue routine checkups, balanced diet, regular activity, and follow your doctor's advice."
        )

    seen = set()
    unique_recommendations = []

    for item in recommendations:
        if item not in seen:
            unique_recommendations.append(item)
            seen.add(item)

    return unique_recommendations


def get_patient_health_insights(patient_id):
    diabetes_comparison = compare_diabetes_reports(patient_id)
    heart_comparison = compare_heart_reports(patient_id)

    doctor_summary = []
    patient_summary = []

    if diabetes_comparison.get("available"):
        if diabetes_comparison.get("has_previous"):
            doctor_summary.extend(diabetes_comparison.get("summary_points", []))
            patient_summary.extend(diabetes_comparison.get("summary_points", [])[:3])
        else:
            doctor_summary.append(diabetes_comparison.get("message"))
            patient_summary.append(diabetes_comparison.get("message"))

    if heart_comparison.get("available"):
        if heart_comparison.get("has_previous"):
            doctor_summary.extend(heart_comparison.get("summary_points", []))
            patient_summary.extend(heart_comparison.get("summary_points", [])[:3])
        else:
            doctor_summary.append(heart_comparison.get("message"))
            patient_summary.append(heart_comparison.get("message"))

    if not doctor_summary:
        doctor_summary.append(
            "No previous diabetes or heart reports are available for comparison."
        )

    if not patient_summary:
        patient_summary.append(
            "Your report history is not available yet. Future visits can be compared once reports are saved."
        )

    recommendations = build_patient_recommendations(
        diabetes_comparison,
        heart_comparison,
    )

    severity = determine_severity(diabetes_comparison, heart_comparison)

    return {
        "patient_id": patient_id,
        "severity": severity,
        "diabetes": diabetes_comparison,
        "heart": heart_comparison,
        "doctor_summary": doctor_summary,
        "patient_summary": patient_summary,
        "recommendations": recommendations,
    }


def build_chatbot_context_for_patient(patient_id, max_lines=10):
    insights = get_patient_health_insights(patient_id)

    lines = [
        "Patient health context from stored hospital reports:",
        f"Overall follow-up priority: {insights['severity']}.",
    ]

    for item in insights["patient_summary"]:
        if item and len(lines) < max_lines:
            lines.append(f"- {item}")

    if insights["recommendations"] and len(lines) < max_lines:
        lines.append("Recommended guidance:")

    for item in insights["recommendations"]:
        if len(lines) >= max_lines:
            break
        lines.append(f"- {item}")

    lines.append(
        "Use this context carefully. Do not diagnose. Encourage doctor consultation for medical decisions."
    )

    return "\n".join(lines)