import json
import secrets
from datetime import datetime, timezone


SUPPORTED_LANGUAGES = {"en", "hi", "te"}


def validate_json_text(value, field_name="json"):
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    if isinstance(value, str):
        try:
            json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid {field_name}: {exc}") from exc
        return value

    raise ValueError(f"{field_name} must be dict, list, JSON string, or None")


def generate_patient_uid():
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"MRP-{date_part}-{random_part}"


def generate_session_uid():
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"MRS-{date_part}-{random_part}"


def normalize_phone(phone):
    if not phone:
        return None

    digits = "".join(ch for ch in str(phone) if ch.isdigit())

    if digits.startswith("0091"):
        digits = digits[4:]

    elif digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    if len(digits) != 10:
        return None

    if digits[0] not in {"6", "7", "8", "9"}:
        return None

    return digits


def normalize_language(language):
    if language in SUPPORTED_LANGUAGES:
        return language

    return "en"