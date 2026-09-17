import sys
import os

try:
    sys.stdout.flush()
except OSError as e:
    if e.errno == 22:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')

try:
    sys.stderr.flush()
except OSError as e:
    if e.errno == 22:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import secrets
import string
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS

from database.auth_repo import verify_user, get_user
from database.patient_account_repo import (
    create_patient_account,
    verify_patient_account,
    get_patient_account,
    get_patient_account_by_patient_id,
    reset_patient_account_password,
)
from database.hospital_repo import list_hospitals, get_hospital
from database.patient_repo import create_patient, search_patients, get_patient, list_patients
from database.visit_repo import create_visit, get_visit, list_patient_visits
from database.report_repo import (
    create_diabetes_report,
    create_heart_report,
    list_visit_reports,
    list_patient_diabetes_reports,
    list_patient_heart_reports,
)
from database.analytics_repo import (
    get_dashboard_summary,
    get_hospital_wise_summary,
    get_risk_distribution,
    get_visit_status_distribution,
    get_visit_trend,
    get_disease_risk_trend,
    get_patient_demographics,
    get_latest_high_risk_patients,
    get_recent_activity,
    get_patient_report_summary,
)
from database.insight_repo import (
    get_patient_health_insights,
    build_chatbot_context_for_patient,
)
from database.doctor_summary_repo import (
    create_patient_doctor_summary,
    list_patient_doctor_summaries,
)
from database.permissions import has_permission


app = Flask(__name__)
CORS(app)


_ai_cache = {
    "rag_get_response": None,
    "predict_diabetes": None,
    "predict_diabetes_type": None,
    "predict_heart_disease": None,
    "screen_heart_risk_simple": None,
}


def load_rag():
    if _ai_cache["rag_get_response"] is None:
        from rag import get_response

        _ai_cache["rag_get_response"] = get_response

    return _ai_cache["rag_get_response"]


def load_predict_diabetes():
    if _ai_cache["predict_diabetes"] is None:
        from predict import predict_diabetes

        _ai_cache["predict_diabetes"] = predict_diabetes

    return _ai_cache["predict_diabetes"]


def load_predict_diabetes_type():
    if _ai_cache["predict_diabetes_type"] is None:
        from predict import predict_diabetes_type

        _ai_cache["predict_diabetes_type"] = predict_diabetes_type

    return _ai_cache["predict_diabetes_type"]


def load_predict_heart_disease():
    if _ai_cache["predict_heart_disease"] is None:
        from predict import predict_heart_disease

        _ai_cache["predict_heart_disease"] = predict_heart_disease

    return _ai_cache["predict_heart_disease"]


def load_heart_screening():
    if _ai_cache["screen_heart_risk_simple"] is None:
        from heart_screening import screen_heart_risk_simple

        _ai_cache["screen_heart_risk_simple"] = screen_heart_risk_simple

    return _ai_cache["screen_heart_risk_simple"]


def get_json():
    return request.get_json(silent=True) or {}


def success(data=None, message="success"):
    return jsonify(
        {
            "success": True,
            "message": message,
            "data": data,
        }
    )


def error(message, status=400):
    return jsonify(
        {
            "success": False,
            "error": message,
        }
    ), status


def get_current_user():
    patient_account_id = request.headers.get("X-Patient-Account-Id")

    if patient_account_id:
        try:
            patient_account_id = int(patient_account_id)
        except ValueError:
            return None

        account = get_patient_account(patient_account_id)

        if not account or not account.get("is_active"):
            return None

        return {
            "id": account["id"],
            "role": "patient",
            "hospital_id": None,
            "patient_id": account["patient_id"],
            "full_name": account["full_name"],
            "username": account["username"],
            "patient_uid": account["patient_uid"],
            "preferred_language": account["preferred_language"],
            "is_active": account["is_active"],
        }

    user_id = request.headers.get("X-User-Id")

    if not user_id:
        return None

    try:
        user_id = int(user_id)
    except ValueError:
        return None

    user = get_user(user_id)

    if not user or not user.get("is_active"):
        return None

    return user


def require_auth(route_fn):
    @wraps(route_fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()

        if not user:
            return error("Authentication required. Send X-User-Id header for demo testing.", 401)

        request.current_user = user
        return route_fn(*args, **kwargs)

    return wrapper


def require_permission(permission):
    def decorator(route_fn):
        @wraps(route_fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()

            if not user:
                return error("Authentication required. Send X-User-Id header for demo testing.", 401)

            if user["role"] != "super_admin" and not has_permission(user["role"], permission):
                return error(f"Permission denied: {permission}", 403)

            request.current_user = user
            return route_fn(*args, **kwargs)

        return wrapper

    return decorator


def required(data, field_name):
    value = data.get(field_name)

    if value is None or value == "":
        raise ValueError(f"{field_name} is required")

    return value


def generate_patient_username(patient_id):
    return f"patient_{patient_id}"


def generate_temporary_password(length=10):
    if length < 8:
        length = 8

    required_chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    alphabet = string.ascii_letters + string.digits
    remaining = [secrets.choice(alphabet) for _ in range(length - len(required_chars))]
    password_chars = required_chars + remaining
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def can_access_hospital(user, hospital_id):
    if user["role"] == "super_admin":
        return True

    return user["hospital_id"] == hospital_id


def can_access_visit(user, visit):
    if user["role"] == "super_admin":
        return True

    return visit and visit["hospital_id"] == user["hospital_id"]


def can_access_patient(user, patient_id):
    if user["role"] == "super_admin":
        return True

    if user["role"] == "patient":
        return user.get("patient_id") == patient_id

    hospital_id = user.get("hospital_id")
    if not hospital_id:
        return False

    return any(
        patient["id"] == patient_id
        for patient in list_patients(hospital_id=hospital_id, limit=500)
    )


@app.route("/health", methods=["GET"])
def health():
    return success({"status": "MediRisk backend is running!"})


@app.route("/api/system/warmup-ai", methods=["POST"])
@require_auth
def warmup_ai():
    try:
        user = request.current_user

        if user["role"] not in {"super_admin", "hospital_admin"}:
            return error("Only admin users can warm up AI modules", 403)

        loaded = []

        load_predict_diabetes()
        loaded.append("diabetes_model")

        load_predict_diabetes_type()
        loaded.append("diabetes_type_model")

        load_predict_heart_disease()
        loaded.append("heart_model")

        load_heart_screening()
        loaded.append("heart_screening")

        load_rag()
        loaded.append("rag_chatbot")

        return success(
            {
                "loaded": loaded,
                "note": "AI modules are warmed up and cached for this backend process.",
            },
            "AI warmup completed",
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/system/warmup-chatbot", methods=["POST"])
def warmup_chatbot():
    try:
        load_rag()
        return success(
            {
                "loaded": ["rag_chatbot"],
                "note": "RAG chatbot pipeline is loaded for this backend process.",
            },
            "Chatbot warmup completed",
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== AUTH =====

@app.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data = get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return error("Username and password are required", 400)

        user = verify_user(username, password)

        if user:
            full_user = get_user(user["id"]) or user
            return success(
                {
                    "account_type": "staff",
                    "user": full_user,
                    "demo_header": {
                        "name": "X-User-Id",
                        "value": full_user["id"],
                    },
                },
                "Login successful",
            )

        patient_account = verify_patient_account(username, password)

        if patient_account:
            return success(
                {
                    "account_type": "patient",
                    "user": patient_account,
                    "demo_header": {
                        "name": "X-Patient-Account-Id",
                        "value": patient_account["id"],
                    },
                },
                "Patient login successful",
            )

        return error("Invalid username/password or inactive account", 401)

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== CHAT =====

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = get_json()
        query = data.get("query", "")
        session_id = data.get("session_id", "default")
        language = data.get("language", "auto")
        patient_id = data.get("patient_id")

        if not query:
            return error("No query provided", 400)

        if patient_id:
            patient_context = build_chatbot_context_for_patient(patient_id)
            query = f"{query}\n\nStored patient context:\n{patient_context}"

        get_response = load_rag()
        result = get_response(query, session_id=session_id, language=language)

        return jsonify(
            {
                "answer": result.get("answer"),
                "intent": result.get("intent"),
                "sources": result.get("sources", []),
                "session_id": session_id,
                "language": result.get("language", language),
                "english_query": result.get("english_query"),
            }
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== EXISTING PREDICTION ENDPOINTS =====

@app.route("/predict/diabetes", methods=["POST"])
def diabetes_predict():
    try:
        data = get_json()
        predict_diabetes = load_predict_diabetes()
        return jsonify(predict_diabetes(data))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/predict/diabetes-type", methods=["POST"])
def diabetes_type_predict():
    try:
        data = get_json()
        predict_diabetes_type = load_predict_diabetes_type()
        return jsonify(predict_diabetes_type(data))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/predict/heart", methods=["POST"])
def heart_predict():
    try:
        data = get_json()
        predict_heart_disease = load_predict_heart_disease()
        return jsonify(predict_heart_disease(data))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/screen/heart-simple", methods=["POST"])
def heart_simple_screen():
    try:
        data = get_json()
        screen_heart_risk_simple = load_heart_screening()
        return jsonify(screen_heart_risk_simple(data))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== HOSPITALS =====

@app.route("/api/hospitals", methods=["GET"])
@require_auth
def api_list_hospitals():
    try:
        user = request.current_user

        if user["role"] == "super_admin":
            active_only = request.args.get("active_only", "true").lower() != "false"
            return success(list_hospitals(active_only=active_only))

        hospital = get_hospital(user["hospital_id"])
        return success([hospital] if hospital else [])

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/hospitals/<int:hospital_id>", methods=["GET"])
@require_auth
def api_get_hospital(hospital_id):
    try:
        user = request.current_user

        if not can_access_hospital(user, hospital_id):
            return error("You can only access your own hospital", 403)

        hospital = get_hospital(hospital_id)

        if not hospital:
            return error("Hospital not found", 404)

        return success(hospital)

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== PATIENTS =====

@app.route("/api/patients/register", methods=["POST"])
@require_permission("register_patient")
def api_register_patient():
    try:
        data = get_json()
        user = request.current_user

        result = create_patient(
            full_name=required(data, "full_name"),
            date_of_birth=data.get("date_of_birth"),
            gender=data.get("gender", "unknown"),
            phone=data.get("phone"),
            address=data.get("address"),
            preferred_language=data.get("preferred_language", "en"),
            registered_by_user_id=user["id"],
            allow_possible_duplicate=data.get("allow_possible_duplicate", False),
        )

        if result.get("created"):
            patient_id = result["id"]
            username = generate_patient_username(patient_id)
            temporary_password = generate_temporary_password()

            try:
                account_id = create_patient_account(
                    patient_id=patient_id,
                    username=username,
                    password=temporary_password,
                    phone=data.get("phone"),
                    email=data.get("email"),
                )
                result["patient_account"] = {
                    "id": account_id,
                    "username": username,
                    "temporary_password": temporary_password,
                    "note": "Show this temporary password once and ask the patient to change it later.",
                }
            except ValueError as exc:
                result["patient_account_error"] = str(exc)

        return success(result, "Patient registration processed")

    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/search", methods=["GET"])
@require_permission("search_patient")
def api_search_patients():
    try:
        query = request.args.get("q", "")

        if not query:
            return error("Search query is required", 400)

        return success(search_patients(query))

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients", methods=["GET"])
@require_auth
def api_list_patients():
    try:
        user = request.current_user
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)

        if user["role"] == "patient":
            patient = get_patient(user.get("patient_id"))
            return success([patient] if patient else [])

        hospital_id = None
        if user["role"] != "super_admin":
            hospital_id = user.get("hospital_id")

        return success(list_patients(hospital_id=hospital_id, limit=limit, offset=offset))

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>", methods=["GET"])
@require_auth
def api_get_patient(patient_id):
    try:
        patient = get_patient(patient_id)

        if not patient:
            return error("Patient not found", 404)

        return success(patient)

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/visits", methods=["GET"])
@require_auth
def api_patient_visits(patient_id):
    try:
        user = request.current_user

        if user["role"] == "patient" and user.get("patient_id") != patient_id:
            return error("You can only access your own visits", 403)

        return success(list_patient_visits(patient_id))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/reports/diabetes", methods=["GET"])
@require_auth
def api_patient_diabetes_reports(patient_id):
    try:
        user = request.current_user

        if user["role"] == "patient" and user.get("patient_id") != patient_id:
            return error("You can only access your own reports", 403)

        return success(list_patient_diabetes_reports(patient_id))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/reports/heart", methods=["GET"])
@require_auth
def api_patient_heart_reports(patient_id):
    try:
        user = request.current_user

        if user["role"] == "patient" and user.get("patient_id") != patient_id:
            return error("You can only access your own reports", 403)

        return success(list_patient_heart_reports(patient_id))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/insights", methods=["GET"])
@require_auth
def api_patient_insights(patient_id):
    try:
        user = request.current_user

        if user["role"] == "patient" and user.get("patient_id") != patient_id:
            return error("You can only access your own insights", 403)

        return success(get_patient_health_insights(patient_id))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/chat-context", methods=["GET"])
@require_auth
def api_patient_chat_context(patient_id):
    try:
        user = request.current_user

        if user["role"] == "patient" and user.get("patient_id") != patient_id:
            return error("You can only access your own chat context", 403)

        return success(
            {
                "patient_id": patient_id,
                "context": build_chatbot_context_for_patient(patient_id),
            }
        )
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/summary", methods=["GET"])
@require_auth
def api_patient_report_summary(patient_id):
    try:
        user = request.current_user

        if user["role"] == "patient" and user.get("patient_id") != patient_id:
            return error("You can only access your own summary", 403)

        return success(get_patient_report_summary(patient_id))
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/doctor-summaries", methods=["GET"])
@require_auth
def api_patient_doctor_summaries(patient_id):
    try:
        user = request.current_user

        if not can_access_patient(user, patient_id):
            return error("Permission denied: patient", 403)

        visible_only = user["role"] == "patient"
        return success(
            list_patient_doctor_summaries(
                patient_id=patient_id,
                visible_only=visible_only,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/doctor-summaries", methods=["POST"])
@require_permission("add_doctor_notes")
def api_create_patient_doctor_summary(patient_id):
    try:
        user = request.current_user

        if user["role"] not in {"doctor", "hospital_admin", "super_admin"}:
            return error("Only doctors or admins can add patient summaries", 403)

        if not can_access_patient(user, patient_id):
            return error("Permission denied: patient", 403)

        data = get_json()
        summary = create_patient_doctor_summary(
            patient_id=patient_id,
            doctor_user_id=user["id"],
            hospital_id=user.get("hospital_id"),
            summary_text=required(data, "summary_text"),
            medication_suggestions=data.get("medication_suggestions"),
            lifestyle_suggestions=data.get("lifestyle_suggestions"),
            follow_up_advice=data.get("follow_up_advice"),
            is_visible_to_patient=data.get("is_visible_to_patient", True),
        )

        return success(summary, "Patient summary saved")

    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/portal-access", methods=["GET"])
@require_auth
def api_patient_portal_access(patient_id):
    try:
        user = request.current_user

        if user["role"] not in {"super_admin", "hospital_admin"}:
            return error("Only hospital admin or super admin can view patient portal access", 403)

        if not can_access_patient(user, patient_id):
            return error("Permission denied: patient", 403)

        patient = get_patient(patient_id)
        account = get_patient_account_by_patient_id(patient_id)

        return success(
            {
                "patient": patient,
                "account": account,
                "password_visible": False,
                "password_note": "Existing passwords are hashed and cannot be viewed. Use reset to generate a new temporary password.",
            }
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/patients/<int:patient_id>/portal-access/reset-password", methods=["POST"])
@require_auth
def api_reset_patient_portal_password(patient_id):
    try:
        user = request.current_user

        if user["role"] not in {"super_admin", "hospital_admin"}:
            return error("Only hospital admin or super admin can reset patient portal passwords", 403)

        if not can_access_patient(user, patient_id):
            return error("Permission denied: patient", 403)

        temporary_password = generate_temporary_password()
        account = get_patient_account_by_patient_id(patient_id)

        if account:
            account = reset_patient_account_password(patient_id, temporary_password)
        else:
            account_id = create_patient_account(
                patient_id=patient_id,
                username=generate_patient_username(patient_id),
                password=temporary_password,
            )
            account = get_patient_account(account_id)

        return success(
            {
                "account": account,
                "temporary_password": temporary_password,
                "password_note": "Show this temporary password once. It will not be visible again.",
            },
            "Temporary password reset",
        )

    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== VISITS =====

@app.route("/api/visits/create", methods=["POST"])
@require_permission("create_visit")
def api_create_visit():
    try:
        data = get_json()
        user = request.current_user

        hospital_id = data.get("hospital_id") or user["hospital_id"]

        if not can_access_hospital(user, hospital_id):
            return error("You can only create visits for your own hospital", 403)

        receptionist_user_id = data.get("receptionist_user_id")
        doctor_user_id = data.get("doctor_user_id")

        if user["role"] == "receptionist" and receptionist_user_id is None:
            receptionist_user_id = user["id"]

        if user["role"] == "doctor" and doctor_user_id is None:
            doctor_user_id = user["id"]

        result = create_visit(
            patient_id=required(data, "patient_id"),
            hospital_id=required({"hospital_id": hospital_id}, "hospital_id"),
            visit_reason=data.get("visit_reason"),
            doctor_user_id=doctor_user_id,
            receptionist_user_id=receptionist_user_id,
            visit_status=data.get("visit_status", "waiting"),
            visit_date=data.get("visit_date"),
            actor_user_id=user["id"],
        )

        return success(result, "Visit created")

    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/visits/<int:visit_id>", methods=["GET"])
@require_auth
def api_get_visit(visit_id):
    try:
        visit = get_visit(visit_id)

        if not visit:
            return error("Visit not found", 404)

        user = request.current_user

        if not can_access_visit(user, visit):
            return error("You can only access visits from your own hospital", 403)

        return success(visit)

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/visits/<int:visit_id>/reports", methods=["GET"])
@require_auth
def api_visit_reports(visit_id):
    try:
        visit = get_visit(visit_id)

        if not visit:
            return error("Visit not found", 404)

        user = request.current_user

        if not can_access_visit(user, visit):
            return error("You can only access reports from your own hospital", 403)

        return success(list_visit_reports(visit_id))

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== REPORTS =====

@app.route("/api/reports/diabetes", methods=["POST"])
@require_permission("run_prediction")
def api_create_diabetes_report():
    try:
        data = get_json()
        user = request.current_user

        visit_id = required(data, "visit_id")
        input_values = data.get("input_values") or {}

        visit = get_visit(visit_id)

        if not visit:
            return error("Visit not found", 404)

        if not can_access_visit(user, visit):
            return error("You can only save reports for your own hospital", 403)

        prediction_result = data.get("prediction_result")

        if prediction_result is None:
            if input_values.get("Age") is None and visit.get("age_at_visit") is not None:
                input_values["Age"] = visit["age_at_visit"]

            predict_diabetes = load_predict_diabetes()
            prediction_result = predict_diabetes(input_values)

        report = create_diabetes_report(
            visit_id=visit_id,
            input_values=input_values,
            prediction_result=prediction_result,
            actor_user_id=user["id"],
        )

        return success(
            {
                "prediction": prediction_result,
                "report": report,
            },
            "Diabetes report saved",
        )

    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/reports/heart", methods=["POST"])
@require_permission("run_prediction")
def api_create_heart_report():
    try:
        data = get_json()
        user = request.current_user

        visit_id = required(data, "visit_id")
        mode = data.get("mode", "simple_screening")
        input_values = data.get("input_values") or {}

        visit = get_visit(visit_id)

        if not visit:
            return error("Visit not found", 404)

        if not can_access_visit(user, visit):
            return error("You can only save reports for your own hospital", 403)

        prediction_result = data.get("prediction_result")

        if prediction_result is None:
            if mode == "simple_screening":
                screen_heart_risk_simple = load_heart_screening()
                prediction_result = screen_heart_risk_simple(input_values)
            elif mode == "advanced_medical":
                predict_heart_disease = load_predict_heart_disease()
                prediction_result = predict_heart_disease(input_values)
            else:
                return error("Invalid heart report mode", 400)

        report = create_heart_report(
            visit_id=visit_id,
            mode=mode,
            input_values=input_values,
            prediction_result=prediction_result,
            actor_user_id=user["id"],
        )

        return success(
            {
                "prediction": prediction_result,
                "report": report,
            },
            "Heart report saved",
        )

    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


# ===== ANALYTICS =====

@app.route("/api/analytics/dashboard", methods=["GET"])
@require_auth
def api_dashboard_summary():
    try:
        user = request.current_user

        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if user["role"] != "super_admin":
            if not has_permission(user["role"], "view_own_hospital_analytics"):
                return error("Permission denied: analytics", 403)

            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_dashboard_summary(
                hospital_id=hospital_id,
                network_id=network_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/hospitals", methods=["GET"])
@require_auth
def api_hospital_wise_summary():
    try:
        user = request.current_user

        if user["role"] != "super_admin":
            if not has_permission(user["role"], "view_own_hospital_analytics"):
                return error("Permission denied: analytics", 403)

            hospital = get_hospital(user["hospital_id"])
            summary = get_dashboard_summary(hospital_id=user["hospital_id"])

            return success(
                {
                    "hospital": hospital,
                    "summary": summary,
                }
            )

        network_id = request.args.get("network_id", type=int)
        return success(get_hospital_wise_summary(network_id=network_id))

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/risk/<disease>", methods=["GET"])
@require_auth
def api_risk_distribution(disease):
    try:
        user = request.current_user
        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)

        if user["role"] != "super_admin":
            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_risk_distribution(
                disease=disease,
                hospital_id=hospital_id,
                network_id=network_id,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/visit-status", methods=["GET"])
@require_auth
def api_visit_status_distribution():
    try:
        user = request.current_user
        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)

        if user["role"] != "super_admin":
            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_visit_status_distribution(
                hospital_id=hospital_id,
                network_id=network_id,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/visit-trend", methods=["GET"])
@require_auth
def api_visit_trend():
    try:
        user = request.current_user
        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)
        group_by = request.args.get("group_by", "day")

        if user["role"] != "super_admin":
            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_visit_trend(
                hospital_id=hospital_id,
                network_id=network_id,
                group_by=group_by,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/disease-trend/<disease>", methods=["GET"])
@require_auth
def api_disease_risk_trend(disease):
    try:
        user = request.current_user
        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)
        group_by = request.args.get("group_by", "day")

        if user["role"] != "super_admin":
            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_disease_risk_trend(
                disease=disease,
                hospital_id=hospital_id,
                network_id=network_id,
                group_by=group_by,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/demographics", methods=["GET"])
@require_auth
def api_patient_demographics():
    try:
        user = request.current_user
        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)

        if user["role"] != "super_admin":
            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_patient_demographics(
                hospital_id=hospital_id,
                network_id=network_id,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/high-risk-patients", methods=["GET"])
@require_auth
def api_high_risk_patients():
    try:
        user = request.current_user
        hospital_id = request.args.get("hospital_id", type=int)
        network_id = request.args.get("network_id", type=int)

        if user["role"] != "super_admin":
            hospital_id = user["hospital_id"]
            network_id = None

        return success(
            get_latest_high_risk_patients(
                hospital_id=hospital_id,
                network_id=network_id,
            )
        )

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


@app.route("/api/analytics/recent-activity", methods=["GET"])
@require_auth
def api_recent_activity():
    try:
        user = request.current_user

        if user["role"] != "super_admin":
            return error("Only super admin can view global audit activity", 403)

        return success(get_recent_activity())

    except Exception as exc:
        import traceback
        return error(f'{str(exc)}\n{traceback.format_exc()}', 500)


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
