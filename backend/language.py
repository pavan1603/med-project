import html
import os
import re


SUPPORTED_LANGUAGES = {"en", "hi", "te"}

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}

FIXED_TRANSLATIONS = {
    "emergency": {
        "hi": (
            "यह स्थिति गंभीर हो सकती है। अगर आपको सीने में दर्द, सांस लेने में तकलीफ, बेहोशी, "
            "ठंडा पसीना, दर्द का हाथ/जबड़े/पीठ तक जाना, या अचानक कमजोरी/सुन्नपन हो रहा है, "
            "तो तुरंत 112 पर कॉल करें या एम्बुलेंस के लिए 108 पर कॉल करें। "
            "आप नजदीकी इमरजेंसी विभाग में भी जा सकते हैं।\n\n"
            "AI के जवाब का इंतजार न करें। संभव हो तो बैठ जाएं, मेहनत वाला काम न करें, "
            "और किसी पास के व्यक्ति से मदद लें।"
        ),
        "te": (
            "ఇది అత్యవసర పరిస్థితి కావచ్చు. మీకు ఛాతి నొప్పి, శ్వాస తీసుకోవడంలో ఇబ్బంది, "
            "మూర్ఛ, చెమటలు,చేయి నొప్పి /దవడ/వెనుకకు వెళ్లడం, లేదా అకస్మాత్తుగా "
            "బలహీనత/మొద్దుబారడం ఉంటే, వెంటనే 112 కు కాల్ చేయండి లేదా అంబులెన్స్ కోసం "
            "108 కు కాల్ చేయండి. దగ్గరలోని ఎమర్జెన్సీ విభాగానికి కూడా వెళ్లవచ్చు.\n\n"
            "AI సమాధానం కోసం వేచి ఉండకండి. సాధ్యమైతే కూర్చోండి, శ్రమ చేయకండి, "
            "మరియు దగ్గరలో ఉన్నవారి సహాయం తీసుకోండి."
        ),
    },
    "disclaimer": {
        "hi": (
            "\n\nनोट: मैं स्वास्थ्य जानकारी और जोखिम मार्गदर्शन दे सकता हूं, "
            "लेकिन मैं योग्य डॉक्टर की जगह नहीं ले सकता।"
        ),
        "te": (
            "\n\nగమనిక: నేను ఆరోగ్య సమాచారం మరియు ప్రమాద సూచనలు ఇవ్వగలను, "
            "కానీ నేను అర్హత కలిగిన వైద్యుడిని భర్తీ చేయలేను."
        ),
    },
}


_translate_client = None


def detect_language(text):
    if not text:
        return "en"

    if any("\u0c00" <= char <= "\u0c7f" for char in text):
        return "te"

    if any("\u0900" <= char <= "\u097f" for char in text):
        return "hi"

    return "en"


def resolve_language(query, selected_language="en"):
    detected = detect_language(query)

    if detected != "en":
        return detected

    if selected_language in SUPPORTED_LANGUAGES:
        return selected_language

    return "en"


def get_translate_client():
    global _translate_client

    if _translate_client is not None:
        return _translate_client

    key_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "google-translate-key.json")
    )

    if os.path.exists(key_path):
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", key_path)

    try:
        from google.cloud import translate_v2 as translate
    except Exception:
        return None

    try:
        _translate_client = translate.Client()
        return _translate_client
    except Exception:
        return None


def _extract_disclaimer(text):
    markers = [
        "\n\nNote: I can provide health education and risk guidance, but I cannot diagnose or replace a qualified doctor.",
        "Note: I can provide health education and risk guidance, but I cannot diagnose or replace a qualified doctor.",
    ]

    for marker in markers:
        if marker in text:
            return text.replace(marker, "").strip(), True

    return text, False


def _restore_bullet_format(text):
    text = re.sub(r"\s+-\s+", "\n- ", text)
    text = re.sub(r"(:)\s+-\s+", r"\1\n- ", text)
    text = re.sub(r"\.\s+-\s+", ".\n- ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def translate_text(text, target_language, source_language=None):
    if not text or target_language == source_language:
        return text

    client = get_translate_client()

    if client is None:
        return text

    body, had_disclaimer = _extract_disclaimer(text)

    try:
        kwargs = {"target_language": target_language}
        if source_language:
            kwargs["source_language"] = source_language

        result = client.translate(body, **kwargs)
        translated = html.unescape(result.get("translatedText", body))
        translated = _restore_bullet_format(translated)

        if had_disclaimer:
            translated += fixed_disclaimer(target_language) or ""

        return translated
    except Exception as exc:
        print(f"Translation error: {exc}")
        return text


def translate_to_english(text, source_language):
    if source_language == "en":
        return text

    return translate_text(text, target_language="en", source_language=source_language)


def translate_from_english(text, target_language):
    if target_language == "en":
        return text

    return translate_text(text, target_language=target_language, source_language="en")


def fixed_emergency_response(language):
    if language == "en":
        return None

    return FIXED_TRANSLATIONS["emergency"].get(language)


def fixed_disclaimer(language):
    if language == "en":
        return None

    return FIXED_TRANSLATIONS["disclaimer"].get(language)