import re

PREVENTION_OR_EDUCATION_PATTERNS = [
    r"\breduce\b.*\brisk\b",
    r"\blower\b.*\brisk\b",
    r"\bprevent\b",
    r"\bprevention\b",
    r"\bavoid\b.*\bheart attack\b",
    r"\bheart attack risk\b",
    r"\bwarning signs\b",
    r"\bsymptoms of\b",
    r"\bwhat are\b",
    r"\bwhat is\b",
]

EMERGENCY_PATTERNS = [
    r"\bchest pain\b",
    r"\bchest pressure\b",
    r"\bpain\b.*\bchest\b",
    r"\bshortness of breath\b",
    r"\bdifficulty breathing\b",
    r"\bcan't breathe\b",
    r"\bcannot breathe\b",
    r"\bfainting\b",
    r"\bcold sweat\b",
    r"\bsudden weakness\b",
    r"\bface drooping\b",
    r"\bslurred speech\b",
    r"\bsudden numbness\b",
    r"\bsevere headache\b",
    r"ఛాతీ.*నొప్పి",
    r"చాతి.*నొప్పి",
    r"గుండె.*నొప్పి",
    r"శ్వాస.*ఇబ్బంది",
    r"ఊపిరి.*ఆడ",
    r"बेहोशी",
    r"सीने.*दर्द",
    r"छाती.*दर्द",
    r"सांस.*तकलीफ",
]

CURRENT_SYMPTOM_PATTERNS = [
    r"\bi have\b",
    r"\bi am having\b",
    r"\bi'm having\b",
    r"\bmy\b",
    r"\bfeeling\b",
    r"\bi feel\b",
    r"\bright now\b",
    r"\bnow\b",
    r"\bcurrently\b",
    r"\bsudden\b",
    r"\bsevere\b",
]

MESSAGES = {
    "en": {
        "emergency": (
            "This could be urgent. If you have chest pain, trouble breathing, fainting, "
        "cold sweating, pain spreading to the arm/jaw/back, or sudden weakness/numbness, "
        "please call 112 now, or call 108 for an ambulance where available in India. "
        "You can also go to the nearest emergency department immediately.\n\n"
        "Do not wait for an AI response or try to self-diagnose. If possible, sit down, avoid exertion, "
        "and ask someone nearby to stay with you until medical help arrives."
        ),
        "disclaimer": (
            "\n\nNote: I can provide health education and risk guidance, but I cannot diagnose or replace "
            "a qualified doctor."
        ),
    },
    "hi": {
        "emergency": (
            "यह स्थिति गंभीर हो सकती है। अगर आपको सीने में दर्द, सांस लेने में तकलीफ, बेहोशी, "
            "ठंडा पसीना, दर्द का हाथ/जबड़े/पीठ तक जाना, या अचानक कमजोरी/सुन्नपन हो रहा है, "
            "तो तुरंत नजदीकी इमरजेंसी में जाएं या स्थानीय आपातकालीन नंबर पर कॉल करें.\n\n"
            "AI के जवाब का इंतजार न करें। संभव हो तो बैठ जाएं, मेहनत वाला काम न करें, "
            "और किसी पास के व्यक्ति से मदद लें."
        ),
        "disclaimer": (
            "\n\nनोट: मैं स्वास्थ्य शिक्षा और जोखिम मार्गदर्शन दे सकता हूं, लेकिन मैं डॉक्टर की जगह नहीं ले सकता."
        ),
    },
    "te": {
        "emergency": (
            "ఇది అత్యవసర పరిస్థితి కావచ్చు. మీకు ఛాతి నొప్పి, శ్వాస తీసుకోవడంలో ఇబ్బంది, మూర్ఛ, "
            "చల్లని చెమటలు, నొప్పి చేయి/దవడ/వెనుకకు వెళ్లడం, లేదా అకస్మాత్తుగా బలహీనత/మొద్దుబారడం ఉంటే, "
            "వెంటనే దగ్గరలోని ఎమర్జెన్సీకి వెళ్లండి లేదా స్థానిక అత్యవసర నంబర్‌కు కాల్ చేయండి.\n\n"
            "AI సమాధానం కోసం వేచి ఉండకండి. సాధ్యమైతే కూర్చోండి, శ్రమ చేయకండి, "
            "మరియు దగ్గరలో ఉన్నవారి సహాయం తీసుకోండి."
        ),
        "disclaimer": (
            "\n\nగమనిక: నేను ఆరోగ్య సమాచారం మరియు ప్రమాద సూచనలు ఇవ్వగలను, కానీ నేను వైద్యుడిని భర్తీ చేయలేను."
        ),
    },
}


def _has_any(patterns, text):
    return any(re.search(pattern, text) for pattern in patterns)


def detect_emergency(query: str) -> bool:
    text = query.lower().strip()

    if _has_any(PREVENTION_OR_EDUCATION_PATTERNS, text):
        return False

    if not _has_any(EMERGENCY_PATTERNS, text):
        return False

    if _has_any(CURRENT_SYMPTOM_PATTERNS, text):
        return True

    return len(text.split()) <= 6


def emergency_response(language="en") -> str:
    return MESSAGES.get(language, MESSAGES["en"])["emergency"]


def medical_disclaimer(language="en") -> str:
    return MESSAGES.get(language, MESSAGES["en"])["disclaimer"]
