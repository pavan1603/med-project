ROLES = {
    "super_admin",
    "hospital_admin",
    "doctor",
    "receptionist",
    "patient",
}


ROLE_PERMISSIONS = {
    "super_admin": {
        "view_all_hospitals",
        "view_all_analytics",
        "manage_hospitals",
        "manage_all_users",
        "view_all_patients",
        "view_audit_logs",
    },
    "hospital_admin": {
        "manage_own_hospital_users",
        "view_own_hospital_data",
        "view_own_hospital_analytics",
        "view_own_hospital_patients",
        "register_patient",
        "search_patient",
        "create_visit",
        "run_prediction",
    },
    "doctor": {
        "view_patient_history",
        "compare_visits",
        "view_ai_explanation",
        "add_doctor_notes",
        "view_own_hospital_analytics",
        "view_assigned_patients",
        "register_patient",
        "search_patient",
        "create_visit",
        "run_prediction",
    },
    "receptionist": {
        "register_patient",
        "create_visit",
        "enter_report_values",
        "run_prediction",
        "search_patient",
    },
    "patient": {
        "view_own_reports",
        "chat_with_own_context",
        "view_own_recommendations",
    },
}


def validate_role(role):
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")


def has_permission(role, permission):
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(role, permission):
    if not has_permission(role, permission):
        raise PermissionError(f"Role '{role}' does not have permission '{permission}'")


def can_access_hospital(user, hospital_id):
    if not user:
        return False

    if user.get("role") == "super_admin":
        return True

    return user.get("hospital_id") == hospital_id
