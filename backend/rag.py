import os
os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
import re
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer
from intent import process_query
from safety import detect_emergency, emergency_response, medical_disclaimer
from safety import detect_emergency, emergency_response, medical_disclaimer
from datetime import datetime
import requests
from dotenv import load_dotenv
from language import (
    LANGUAGE_NAMES,
    resolve_language,
    translate_to_english,
    translate_from_english,
    fixed_emergency_response,
    fixed_disclaimer,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
MAX_MEMORY_TURNS = 8
SESSION_MEMORY = {}

# ===== OPENROUTER API CONFIG =====
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found. Create a .env file.")

OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free")



TELUGU_QUERY_HINTS = {
    "ఛాతీ": "chest",
    "చాతి": "chest",
    "నొప్పి": "pain",
    "నొప్పిగా": "pain",
    "గుండె": "heart",
    "శ్వాస": "breath breathing",
    "ఊపిరి": "breath breathing",
    "చక్కెర": "sugar glucose diabetes",
    "షుగర్": "sugar glucose diabetes",
    "డయాబెటిస్": "diabetes",
    "మధుమేహం": "diabetes",
    "ఆహారం": "food diet",
    "తినాలి": "eat food diet",
    "బిపి": "blood pressure",
}

HINDI_QUERY_HINTS = {
    "सीने": "chest",
    "छाती": "chest",
    "दर्द": "pain",
    "दिल": "heart",
    "सांस": "breath breathing",
    "शुगर": "sugar glucose diabetes",
    "डायबिटीज": "diabetes",
    "मधुमेह": "diabetes",
    "खाना": "food diet",
    "आहार": "food diet",
    "बीपी": "blood pressure",
}


def detect_query_language(query):
    if any("\u0c00" <= char <= "\u0c7f" for char in query):
        return "te"
    if any("\u0900" <= char <= "\u097f" for char in query):
        return "hi"
    return "en"


def normalize_query_for_retrieval(query):
    detected_language = detect_query_language(query)
    hints = []

    if detected_language == "te":
        for keyword, expansion in TELUGU_QUERY_HINTS.items():
            if keyword in query:
                hints.append(expansion)
    elif detected_language == "hi":
        for keyword, expansion in HINDI_QUERY_HINTS.items():
            if keyword in query:
                hints.append(expansion)

    if hints:
        return query + " " + " ".join(hints)
    return query

# ===== SETUP =====
print("Loading RAG pipeline...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "vectordb"))
collection = client.get_collection("medirisk")
print("RAG pipeline ready!")


# ===== SESSION MEMORY =====
def get_memory_context(session_id, return_raw=False):
    if not session_id:
        return [] if return_raw else ""

    turns = SESSION_MEMORY.get(session_id, [])
    if not turns:
        return ""

    if return_raw:
        return turns[-MAX_MEMORY_TURNS:]

    lines = []
    for turn in turns[-MAX_MEMORY_TURNS:]:
        lines.append(f"User: {turn['user']}")
        lines.append(f"Assistant: {turn['assistant']}")

    return "\n".join(lines)


def remember_turn(session_id, user_query, assistant_answer):
    if not session_id:
        return

    answer_preview = " ".join(assistant_answer.strip().split())

    if len(answer_preview) > 220:
        answer_preview = answer_preview[:220].rsplit(" ", 1)[0] + "..."

    SESSION_MEMORY.setdefault(session_id, []).append(
        {
            "user": user_query.strip(),
            "assistant": answer_preview,
        }
    )

    SESSION_MEMORY[session_id] = SESSION_MEMORY[session_id][-MAX_MEMORY_TURNS:]

def is_memory_question(query):
    text = query.lower().strip()

    memory_patterns = [
        "what did we chat",
        "what did we talk",
        "what did we discuss",
        "what was our previous",
        "what did i ask",
        "earlier in this chat",
        "previous chat",
        "previous conversation",
        "recap",
        "summarize our chat",
        "summary of our chat",
        "what have we talked",
    ]

    return any(pattern in text for pattern in memory_patterns)


def _topic_from_query(query):
    text = query.lower()

    if any(word in text for word in ["diet", "food", "meal", "eat"]):
        if "heart" in text:
            return "heart-friendly diet"
        if any(word in text for word in ["diabetes", "sugar", "glucose"]):
            return "diabetes diet"
        return "diet guidance"

    if any(word in text for word in ["chest pain", "chest pressure"]):
        return "chest pain emergency guidance"

    if "heart rate" in text or "pulse" in text:
        return "high heart rate guidance"

    if "heart" in text or "attack" in text:
        return "heart health"

    if any(word in text for word in ["diabetes", "sugar", "glucose", "blood sugar"]):
        return "diabetes and blood sugar"

    if "yoga" in text:
        return "yoga and heart health"

    return query.strip()[:80]


def build_memory_answer(session_id):
    turns = SESSION_MEMORY.get(session_id, [])

    if not turns:
        return (
            "I do not have earlier messages in this chat yet. "
            "If you ask health questions, I can summarize this session for you."
        )

    topics = []
    for turn in turns[-8:]:
        topic = _topic_from_query(turn["user"])
        if topic not in topics:
            topics.append(topic)

    lines = ["Earlier in this chat, we talked about:"]

    for index, topic in enumerate(topics, start=1):
        lines.append(f"{index}. {topic}")

    lines.append("\nI can continue from any of these topics if you want.")
    return "\n".join(lines)

# ===== LLM API CALL =====
def call_nvidia_api(system_prompt, user_prompt, memory_turns=None):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "MediRisk AI",
    }

    messages = [{"role": "system", "content": system_prompt}]
    
    if memory_turns:
        for turn in memory_turns:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
            
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 900,
    }

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code != 200:
            print("OpenRouter API Error")
            print("Status:", response.status_code)
            print("Body:", response.text[:1000])
            return None

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"API Error: {e}")
        return None


# ===== TIME GREETING =====
def get_time_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"


# ===== CONVERSATION RESPONSES =====
def get_greeting_response():
    greeting = get_time_greeting()
    return f"""{greeting}! Welcome to MediRisk AI - your personal health assistant!

I am here to help you with:
- Diabetes risk prediction and management
- Heart disease detection and prevention
- Healthy Indian diet plans and food advice
- Medical questions and health guidance

How are you feeling today? What can I help you with?"""


def get_thanks_response():
    return """You are very welcome!

I am always happy to help you on your health journey. Remember, small steps every day lead to big improvements in health.

Is there anything else you would like to know? Whether it is about diabetes, heart health, diet plans or general wellness - just ask!"""


def is_normal_glucose_query(query):
    text = query.lower()
    return (
        any(term in text for term in ["normal blood glucose", "normal glucose", "normal sugar", "blood sugar level"])
        and any(term in text for term in ["normal", "range", "level", "levels"])
    )


def is_heart_warning_signs_query(query):
    text = query.lower()
    return (
        "heart" in text
        and any(term in text for term in ["warning sign", "warning signs", "symptom", "symptoms", "signs"])
    )


def get_normal_glucose_response():
    return (
        "Normal blood glucose levels are usually:\n\n"
        "- Fasting glucose: below 100 mg/dL.\n"
        "- Prediabetes range: 100-125 mg/dL fasting.\n"
        "- Diabetes range: 126 mg/dL or higher fasting, confirmed on repeat testing.\n"
        "- Two hours after meals: below 140 mg/dL is generally normal.\n"
        "- HbA1c: below 5.7% is generally normal.\n\n"
        "If your readings are repeatedly high, or you have excessive thirst, frequent urination, blurred vision, fatigue, or unexplained weight loss, please consult a qualified doctor for fasting glucose, HbA1c, or other confirmatory testing."
    )


def get_heart_warning_signs_response():
    return (
        "Warning signs of possible heart disease or heart emergency can include:\n\n"
        "- Chest pain, tightness, heaviness, pressure, or burning sensation.\n"
        "- Pain spreading to the left arm, jaw, neck, back, or shoulder.\n"
        "- Shortness of breath during rest or mild activity.\n"
        "- Cold sweating, nausea, dizziness, or fainting.\n"
        "- Fast, irregular, or uncomfortable heartbeat.\n"
        "- Unusual tiredness with small effort.\n"
        "- Swelling in legs, ankles, or feet.\n\n"
        "If chest pain is happening now, especially with breathlessness, sweating, fainting, or pain spreading to arm/jaw/back, seek emergency medical care immediately."
    )


def get_direct_localized_response(intent, language):
    if language == "te":
        if intent == "food_diabetes":
            return (
                "డయాబెటిస్ ఉన్నవారికి సరళమైన భారతీయ ఆహార ప్రణాళిక:\n\n"
                "- ఉదయం: 2 రాగి ఇడ్లీలు లేదా ఓట్స్ ఉప్మా, చక్కెర లేకుండా టీ/కాఫీ.\n"
                "- మధ్యాహ్నం ముందు: ఒక చిన్న ఆపిల్ లేదా గువా, లేదా మజ్జిగ.\n"
                "- భోజనం: 1-2 గోధుమ రొట్టెలు లేదా కొద్దిగా బ్రౌన్ రైస్, ఒక కప్పు dal, ఎక్కువ కూరగాయలు, సలాడ్.\n"
                "- సాయంత్రం: roasted chana, sprouts లేదా కొద్దిగా nuts.\n"
                "- రాత్రి: తేలికైన భోజనం - roti + dal + కూరగాయలు లేదా vegetable soup.\n\n"
                "తగ్గించాలి: చక్కెర పానీయాలు, sweets, maida items, deep fried snacks, ఎక్కువ white rice.\n"
                "ముఖ్యంగా portion control పాటించండి, glucose values ని చెక్ చేస్తూ doctor/dietitian సలహా తీసుకోండి."
                + medical_disclaimer(language)
            )

        if intent in ["diabetes_question", "diabetes_prediction"]:
            return (
                "డయాబెటిస్ రిస్క్ తగ్గించడానికి ముఖ్యమైన అలవాట్లు:\n\n"
                "- చక్కెర పానీయాలు, sweets, maida, deep fried foods తగ్గించండి.\n"
                "- ప్రతి భోజనంలో కూరగాయలు, dal/protein, మరియు కొద్దిగా whole grains ఉండేలా చూసుకోండి.\n"
                "- రోజుకు కనీసం 30 నిమిషాలు నడక చేయండి, మీకు medically safe అయితే.\n"
                "- బరువు ఎక్కువైతే క్రమంగా తగ్గించుకోవడం insulin resistance తగ్గించడంలో సహాయపడుతుంది.\n"
                "- fasting glucose, post-meal glucose, HbA1c వంటి tests ను doctor సూచనల ప్రకారం చెక్ చేయండి.\n\n"
                "మీ glucose ఎక్కువగా ఉంటే లేదా thirst, frequent urination, blurry vision వంటి symptoms ఉంటే doctor ను కలవండి."
                + medical_disclaimer(language)
            )

        if intent == "food_heart":
            return (
                "గుండె ఆరోగ్యానికి సరళమైన ఆహార సూచనలు:\n\n"
                "- ఎక్కువగా కూరగాయలు, పండ్లు, dal, beans, whole grains తీసుకోండి.\n"
                "- ఉప్పు, deep fried snacks, packaged foods, sweets, sugary drinks తగ్గించండి.\n"
                "- oil తక్కువగా వాడండి; ghee/butter/vanaspati ఎక్కువగా వాడకండి.\n"
                "- nuts లేదా seeds చిన్న మోతాదులో తీసుకోవచ్చు.\n"
                "- BP, cholesterol, sugar values ను సమయానికి చెక్ చేయించుకోండి.\n\n"
                "ఛాతి నొప్పి లేదా breathlessness ఉంటే వెంటనే medical help తీసుకోండి."
                + medical_disclaimer(language)
            )

        if intent == "heart_question":
            return (
                "గుండె జబ్బుల రిస్క్ తగ్గించడానికి:\n\n"
                "- BP, cholesterol, diabetes ను control లో ఉంచండి.\n"
                "- smoking ఉంటే పూర్తిగా మానేయండి.\n"
                "- రోజూ walking లేదా light exercise చేయండి, symptoms లేకపోతే మరియు doctor అనుమతి ఉంటే.\n"
                "- ఉప్పు, fried foods, processed foods తగ్గించండి.\n"
                "- ఛాతి నొప్పి, breathlessness, fainting, లేదా నొప్పి arm/jaw/back కు వెళ్తే emergency care తీసుకోండి."
                + medical_disclaimer(language)
            )

    if language == "hi":
        if intent == "food_diabetes":
            return (
                "डायबिटीज के लिए सरल भारतीय डाइट प्लान:\n\n"
                "- सुबह: 2 रागी इडली या ओट्स उपमा, बिना चीनी की चाय/कॉफी.\n"
                "- बीच में: छोटा सेब या अमरूद, या छाछ.\n"
                "- दोपहर: 1-2 गेहूं की रोटी या थोड़ा ब्राउन राइस, एक कटोरी dal, ज्यादा सब्जियां और सलाद.\n"
                "- शाम: roasted chana, sprouts या थोड़े nuts.\n"
                "- रात: हल्का भोजन - roti + dal + सब्जी या vegetable soup.\n\n"
                "कम करें: मीठे पेय, sweets, maida items, deep fried snacks और ज्यादा white rice."
                + medical_disclaimer(language)
            )

        if intent in ["diabetes_question", "diabetes_prediction"]:
            return (
                "डायबिटीज रिस्क कम करने के लिए:\n\n"
                "- मीठे पेय, sweets, maida और deep fried foods कम करें.\n"
                "- हर meal में सब्जियां, dal/protein और थोड़े whole grains रखें.\n"
                "- अगर medically safe हो तो रोज 30 मिनट walking करें.\n"
                "- वजन ज्यादा हो तो धीरे-धीरे कम करना insulin resistance में मदद कर सकता है.\n"
                "- fasting glucose, post-meal glucose और HbA1c doctor की सलाह से चेक करें."
                + medical_disclaimer(language)
            )

        if intent == "food_heart":
            return (
                "दिल की सेहत के लिए सरल आहार सुझाव:\n\n"
                "- सब्जियां, फल, dal, beans और whole grains ज्यादा लें.\n"
                "- नमक, deep fried snacks, packaged foods, sweets और sugary drinks कम करें.\n"
                "- oil सीमित रखें; ghee/butter/vanaspati ज्यादा न लें.\n"
                "- nuts या seeds छोटी मात्रा में ले सकते हैं.\n"
                "- BP, cholesterol और sugar की जांच समय पर कराएं."
                + medical_disclaimer(language)
            )

        if intent == "heart_question":
            return (
                "दिल की बीमारी का रिस्क कम करने के लिए:\n\n"
                "- BP, cholesterol और diabetes control में रखें.\n"
                "- smoking हो तो पूरी तरह छोड़ें.\n"
                "- symptoms न हों और doctor अनुमति दें तो रोज walking करें.\n"
                "- नमक, fried foods और processed foods कम करें.\n"
                "- सीने में दर्द, सांस फूलना, बेहोशी या दर्द arm/jaw/back तक जाए तो emergency care लें."
                + medical_disclaimer(language)
            )

    return None

# ===== SEARCH =====
def search_knowledge(query, disease_filter=None, top_k=5, memory_context=""):
    search_query = normalize_query_for_retrieval(query)

    processed = process_query(search_query)
    expanded_query = processed["expanded"]
    intent = processed["intent"]

    embedding = embedder.encode(expanded_query).tolist()

    where_filter = None
    if disease_filter:
        where_filter = {"disease": disease_filter}

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where_filter,
    )

    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        chunks.append(
            {
                "text": doc,
                "topic": results["metadatas"][0][i]["topic"],
                "source": results["metadatas"][0][i]["source"],
                "disease": results["metadatas"][0][i]["disease"],
                "intent": intent,
            }
        )

    return chunks


DIET_PLAN_TOPIC_KEYWORDS = [
    "diet_chart",
    "meal_plan",
    "weekly_plan",
    "daily_diet",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "indian_diabetic",
    "south_indian_diabetes",
    "heart_south_indian_diet_plan",
    "heart_north_indian_diet_plan",
    "heart_weekly_plan",
]


def is_diet_plan_query(query):
    text = query.lower()
    return any(
        phrase in text
        for phrase in [
            "diet plan",
            "meal plan",
            "weekly plan",
            "7 day",
            "diet chart",
            "indian diet",
            "south indian",
            "north indian",
            "breakfast",
            "lunch",
            "dinner",
            "snack",
            "what should i eat",
            "suggest me a diet",
        ]
    )


def is_weekly_plan_query(query):
    text = query.lower()
    return any(phrase in text for phrase in ["weekly", "7 day", "7-day", "monday", "sunday"])


def is_south_indian_query(query):
    return "south indian" in query.lower()


def is_dinner_query(query):
    text = query.lower()
    return "dinner" in text and not is_diet_plan_query(text.replace("dinner", ""))


def is_diabetes_cause_query(query):
    text = query.lower()
    return any(
        phrase in text
        for phrase in [
            "reason for diabetes",
            "reasons for diabetes",
            "cause of diabetes",
            "causes of diabetes",
            "why diabetes",
            "why do people get diabetes",
            "what causes diabetes",
        ]
    )


def is_fruit_diabetes_query(query):
    text = query.lower()
    return "fruit" in text and any(word in text for word in ["diabetes", "diabetic", "sugar", "glucose", "risk"])


def is_heart_test_query(query):
    text = query.lower()
    return any(
        phrase in text
        for phrase in [
            "heart test",
            "heart tests",
            "tests for heart",
            "tests are used for heart",
            "test heart disease",
            "ecg",
            "echo",
            "stress test",
            "angiography",
            "troponin",
        ]
    )


def is_avoid_food_query(query):
    text = query.lower()
    return any(
        phrase in text
        for phrase in [
            "avoid",
            "limit",
            "not eat",
            "should not eat",
            "foods to avoid",
            "foods to limit",
        ]
    )


def rerank_chunks_for_query(chunks, query, intent):
    if not chunks:
        return chunks

    query_lower = query.lower()
    diet_plan_query = is_diet_plan_query(query)
    scored_chunks = []

    for index, chunk in enumerate(chunks):
        topic = chunk.get("topic", "").lower()
        disease = chunk.get("disease", "").lower()
        text = chunk.get("text", "").lower()

        score = 100 - index

        if is_avoid_food_query(query):
            if any(keyword in topic for keyword in ["to_limit", "foods_to_limit", "foods_to_avoid", "limit", "avoid"]):
                score += 120
            if any(keyword in text for keyword in ["foods to limit", "foods to avoid", "sugary", "fried", "processed"]):
                score += 50
            if any(generic in topic for generic in ["overview", "eat_often", "vegetables"]):
                score -= 50

        if is_south_indian_query(query):
            if "south_indian" in topic:
                score += 120
            if any(keyword in text for keyword in ["idli", "dosa", "sambar", "rasam", "poriyal", "kootu"]):
                score += 35

        if is_heart_test_query(query):
            if "heart_tests" in topic:
                score += 150
            if any(keyword in text for keyword in ["ecg", "echocardiogram", "stress test", "troponin", "angiography"]):
                score += 60

        if diet_plan_query:
            if any(keyword in topic for keyword in DIET_PLAN_TOPIC_KEYWORDS):
                score += 90

            if any(keyword in text for keyword in ["breakfast", "lunch", "dinner", "snack"]):
                score += 50

            if "weekly" in query_lower or "7 day" in query_lower:
                if "weekly" in topic or "monday" in text:
                    score += 100

            if "indian" in query_lower:
                if "indian" in topic or "indian" in text:
                    score += 50

            if intent == "food_diabetes" and disease == "diabetes":
                score += 40

            if intent == "food_heart" and disease == "heart_disease":
                score += 40

            if any(generic in topic for generic in ["overview", "nutrients", "avoid", "prevention"]):
                score -= 25

        scored_chunks.append((score, index, chunk))

    scored_chunks.sort(key=lambda item: (-item[0], item[1]))
    return [chunk for _, _, chunk in scored_chunks]


# ===== COMPRESS CONTEXT =====
def compress_context(chunks, max_chunks=5):
    seen_topics = set()
    compressed = []

    for chunk in chunks:
        if chunk["topic"] in seen_topics:
            continue

        seen_topics.add(chunk["topic"])
        compressed.append(chunk)

        if len(compressed) >= max_chunks:
            break

    context = ""
    sources = []

    for chunk in compressed:
        context += chunk["text"] + "\n\n"
        sources.append(
            {
                "topic": chunk["topic"],
                "source": chunk["source"],
                "disease": chunk["disease"],
            }
        )

    return context, sources

# ===== BUILD PROMPT =====


def load_prompt_template(filename):
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
    
    
def build_prompt(query, context, intent, memory_context="", language="en"):
    greeting = get_time_greeting()
    response_language = LANGUAGE_NAMES.get(language, "English")

    system_template = load_prompt_template("system_prompt.txt")
    system_prompt = system_template.format(
        greeting=greeting,
        response_language=response_language
    )

    user_prompt = f"""Medical Knowledge:
{context}

Detected Intent: {intent}

User Question:
{query}

Provide a helpful healthcare response without mentioning internal sources or metadata."""

    return system_prompt, user_prompt

# ===== LOCAL FALLBACK =====
def _split_guidance_text(text):
    markers = [
        " Breakfast:",
        " Mid Morning:",
        " Morning Snack:",
        " Lunch:",
        " Evening Snack:",
        " Afternoon Snack:",
        " Dinner:",
        " Bedtime Snack:",
        " Key principles",
        " Key South",
        " Key Rule:",
        " Ideal Lunch Plate:",
        " Best Grains:",
        " Best Proteins:",
        " Best Vegetables:",
        " Cooking Tips:",
        " Add Garlic:",
        " Optional Weekly Add:",
        " Must Add Weekly:",
        " Avoid:",
        " South Indian Options:",
        " North Indian Options:",
        " Daily habits",
        " Monday:",
        " Tuesday:",
        " Wednesday:",
        " Thursday:",
        " Friday:",
        " Saturday:",
        " Sunday:",
        " Frequent urination",
        " Excessive thirst",
        " Unexplained weight",
        " Extreme fatigue",
        " Blurred vision",
        " Slow healing",
        " Frequent infections",
        " Tingling",
        " Dark patches",
    ]

    formatted = text.strip()
    for marker in markers:
        formatted = formatted.replace(marker, "\n  - " + marker.strip())

    return "\n".join(line.strip() for line in formatted.splitlines() if line.strip())


def _localized_fallback_summary(query, sources, language):
    diseases = {source.get("disease") for source in sources or []}
    topics = " ".join(source.get("topic", "") for source in sources or []).lower()

    if language == "te":
        if "heart_disease" in diseases:
            return (
                "ప్రస్తుతం AI సేవను చేరుకోలేకపోతున్నాను, కానీ మీ ప్రశ్నకు ఉపయోగపడే సాధారణ మార్గదర్శకం ఇది:\n\n"
                "- గుండె ఆరోగ్యానికి కూరగాయలు, పండ్లు, పప్పులు, సంపూర్ణ ధాన్యాలు ఎక్కువగా తీసుకోండి.\n"
                "- ఉప్పు, వేయించిన పదార్థాలు, ప్యాకెట్ ఆహారం, అధిక నూనె మరియు పొగ త్రాగడం తగ్గించండి.\n"
                "- ఛాతి నొప్పి, శ్వాస ఇబ్బంది, మూర్ఛ లేదా నొప్పి చేయి/దవడ/వెనుకకు వెళ్తే వెంటనే ఎమర్జెన్సీకి వెళ్లండి.\n"
                "- BP, చక్కెర, కొలెస్ట్రాల్ పరీక్షలు సమయానికి చేయించుకోండి."
                + medical_disclaimer(language)
            )
        if "diabetes" in diseases or "diabetes" in topics:
            return (
                "ప్రస్తుతం AI సేవను చేరుకోలేకపోతున్నాను, కానీ డయాబెటిస్ కోసం సాధారణ మార్గదర్శకం ఇది:\n\n"
                "- కూరగాయలు, పప్పులు, మిల్లెట్లు, ఓట్స్, బ్రౌన్ రైస్ లేదా గోధుమ రొట్టెను పరిమిత మోతాదులో తీసుకోండి.\n"
                "- చక్కెర పానీయాలు, స్వీట్లు, మైదా పదార్థాలు మరియు ఎక్కువగా వేయించిన ఆహారం తగ్గించండి.\n"
                "- భోజన పరిమాణాన్ని నియంత్రించండి; పెద్ద భోజనం కంటే చిన్న సమతుల్య భోజనాలు మంచివి.\n"
                "- మీ రక్త చక్కెరను పరీక్షించండి మరియు వైద్యుడి సలహా తీసుకోండి."
                + medical_disclaimer(language)
            )
        return (
            "ప్రస్తుతం AI సేవను చేరుకోలేకపోతున్నాను. దయచేసి కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి."
            + medical_disclaimer(language)
        )

    if language == "hi":
        if "heart_disease" in diseases:
            return (
                "अभी AI सेवा से संपर्क नहीं हो पा रहा है, लेकिन आपके प्रश्न के लिए सामान्य मार्गदर्शन यह है:\n\n"
                "- दिल की सेहत के लिए सब्जियां, फल, दालें और साबुत अनाज ज्यादा लें.\n"
                "- नमक, तला हुआ खाना, पैकेट वाले खाद्य पदार्थ, ज्यादा तेल और धूम्रपान कम करें.\n"
                "- सीने में दर्द, सांस फूलना, बेहोशी या दर्द का हाथ/जबड़े/पीठ तक जाना हो तो तुरंत इमरजेंसी में जाएं.\n"
                "- BP, शुगर और कोलेस्ट्रॉल की जांच समय पर कराएं."
                + medical_disclaimer(language)
            )
        if "diabetes" in diseases or "diabetes" in topics:
            return (
                "अभी AI सेवा से संपर्क नहीं हो पा रहा है, लेकिन डायबिटीज के लिए सामान्य मार्गदर्शन यह है:\n\n"
                "- सब्जियां, दालें, मिलेट्स, ओट्स, ब्राउन राइस या गेहूं की रोटी सीमित मात्रा में लें.\n"
                "- मीठे पेय, मिठाई, मैदा और ज्यादा तला हुआ खाना कम करें.\n"
                "- भोजन की मात्रा नियंत्रित रखें; बड़े भोजन के बजाय संतुलित छोटे भोजन बेहतर हैं.\n"
                "- अपनी ब्लड शुगर जांचें और डॉक्टर की सलाह लें."
                + medical_disclaimer(language)
            )
        return (
            "अभी AI सेवा से संपर्क नहीं हो पा रहा है। कृपया थोड़ी देर बाद फिर कोशिश करें."
            + medical_disclaimer(language)
        )

    return None


def cleanup_response_text(answer):
    if not answer:
        return answer

    text = answer

    replacements = {
        "Hereare": "Here are",
        "hereare": "here are",
        "Yes,a": "Yes, a",
        "Yes,A": "Yes, a",
        "whenyou": "when you",
        "Whenyou": "When you",
        "somefoods": "some foods",
        "Somefoods": "Some foods",
        "oatsupma": "oats upma",
        "Oatsupma": "Oats upma",
        "mealsevery": "meals every",
        "Mealsevery": "Meals every",
        "yourblood": "your blood",
        "Yourblood": "Your blood",
        "stressrelief": "stress relief",
        "Stressrelief": "Stress relief",
        "dryroasting": "dry roasting",
        "Dryroasting": "Dry roasting",
        "wholewheat": "whole-wheat",
        "Wholewheat": "Whole-wheat",
        "midmorning": "mid-morning",
        "Midmorning": "Mid-morning",
        "fullfat": "full-fat",
        "Fullfat": "Full-fat",
        "awarm": "a warm",
        "highwhile": "high while",
        "glucose(after": "glucose (after",
        "HbA 1 c": "HbA1c",
        "hba 1 c": "HbA1c",
        "Type 1diabetes": "Type 1 diabetes",
        "type 1diabetes": "type 1 diabetes",
        "Type 2diabetes": "Type 2 diabetes",
        "type 2diabetes": "type 2 diabetes",
        "diabetesrisk": "diabetes risk",
        "heartrisk": "heart risk",
    }

    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)
    text = text.replace("HbA 1 c", "HbA1c")
    text = text.replace("hba 1 c", "HbA1c")
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"(^|\n)-(?=\S)", r"\1- ", text)
    text = re.sub(r"\b(\d)\s+(\d)\b(?=\s+(glasses|tsp|teaspoons|hours|minutes))", r"\1-\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace(" - ", "\n- ")

    return text.strip()


def looks_incomplete(answer):
    if not answer:
        return True

    stripped = answer.strip()
    if len(stripped) < 20:
        return True

    complete_endings = (".", "!", "?", "।", "॥", ":", ")")
    return not stripped.endswith(complete_endings)

def diet_answer_needs_fallback(query, answer):
    if not answer or not is_diet_plan_query(query):
        return False

    answer_lower = answer.lower()

    if looks_incomplete(answer):
        return True

    if is_weekly_plan_query(query):
        return not ("monday" in answer_lower and "sunday" in answer_lower)

    if is_south_indian_query(query):
        south_indian_markers = ["idli", "dosa", "sambar", "rasam", "ragi", "poriyal", "kootu"]
        return not any(marker in answer_lower for marker in south_indian_markers)

    if is_dinner_query(query):
        return "dinner" not in answer_lower

    required_meal_labels = ["breakfast", "lunch", "dinner"]
    return not all(label in answer_lower for label in required_meal_labels)


def build_local_fallback_answer(query, context, sources, language="en"):
    if not context.strip():
        return (
            "I do not have enough reliable local medical knowledge to answer this safely. "
            "Please consult a qualified doctor for personal medical advice."
            + medical_disclaimer(language)
        )

    diseases = {source.get("disease") for source in sources or []}
    topics = " ".join(source.get("topic", "") for source in sources or []).lower()
    query_lower = query.lower()
    diet_plan_query = is_diet_plan_query(query)
    weekly_plan_query = is_weekly_plan_query(query)
    south_indian_query = is_south_indian_query(query)
    dinner_query = is_dinner_query(query)

    if "diabetes" in diseases or "diabetes" in topics or "glucose" in query_lower or "sugar" in query_lower:
        if is_avoid_food_query(query):
            answer = (
                "Foods to limit when you have diabetes include:\n\n"
                "- Sugary drinks, soft drinks, packaged juices, sweets, cakes, pastries, jaggery and honey in large amounts.\n"
                "- Refined foods like maida items, white bread, biscuits and large portions of white rice.\n"
                "- Deep-fried snacks such as samosa, pakora, chips and puri.\n"
                "- Large portions of starchy foods such as potato, sweet potato, tapioca and raw banana.\n"
                "- High-sugar fruits like mango, banana, grapes, chikoo, dates and jackfruit should be smaller and less frequent.\n"
                "- Cream, butter, excess cheese and mayonnaise, especially if weight or cholesterol is a concern.\n\n"
                "You do not need to starve; choose controlled portions, vegetables, dal, whole grains and protein with meals."
                + medical_disclaimer(language)
            )
        elif is_diabetes_cause_query(query):
            answer = (
                "Diabetes can happen for different reasons, and the cause depends on the type:\n\n"
                "- Type 2 diabetes is commonly linked to insulin resistance, excess body weight, low physical activity, family history, aging, and unhealthy eating patterns.\n"
                "- Type 1 diabetes happens when the immune system attacks insulin-producing cells in the pancreas. It is not caused by eating sugar.\n"
                "- Prediabetes happens when blood sugar is higher than normal but not yet in the diabetes range.\n"
                "- Pregnancy, some medicines, hormone problems, pancreatic disease, and long-term stress or poor sleep can also affect blood sugar.\n"
                "- Eating too much sugar alone does not directly cause diabetes, but sugary drinks, refined carbs, and weight gain can increase risk over time.\n\n"
                "A doctor can confirm diabetes with fasting glucose, HbA1c, or an oral glucose tolerance test."
                + medical_disclaimer(language)
            )
        elif is_fruit_diabetes_query(query):
            if any(word in query_lower for word in ["help", "reduce", "risk", "benefit"]):
                answer = (
                    "Whole fruits can help lower diabetes risk when eaten in controlled portions because they provide fiber, water, vitamins, and antioxidants:\n\n"
                    "- Fiber slows sugar absorption and may reduce sudden glucose spikes.\n"
                    "- Whole fruits are more filling, so they can replace sweets, biscuits, and sugary snacks.\n"
                    "- Better choices include guava, apple, pear, papaya, berries, citrus fruits, pomegranate, and amla.\n"
                    "- Avoid fruit juice because it raises sugar faster and removes much of the fiber benefit.\n"
                    "- Keep portions small, such as 1 small fruit or 1 cup cut fruit, and pair with nuts, curd, or sprouts if suitable.\n\n"
                    "Fruits help as part of the full diet; they do not cure diabetes by themselves."
                    + medical_disclaimer(language)
                )
            else:
                answer = (
                    "Yes, a diabetes patient can usually eat whole fruits, but portion control matters:\n\n"
                    "- Better choices: guava, apple, pear, papaya, berries, citrus fruits, pomegranate, and amla.\n"
                    "- Limit high-sugar fruits like mango, banana, grapes, chikoo, dates, and jackfruit to small portions and less often.\n"
                    "- Avoid fruit juice, canned fruit in syrup, and smoothies with added sugar.\n"
                    "- Eat fruit with a meal or pair it with nuts, curd, or sprouts to slow the glucose rise.\n"
                    "- Check your blood sugar response because tolerance differs from person to person."
                    + medical_disclaimer(language)
                )
        elif weekly_plan_query:
            answer = (
                "Here is a compact weekly Indian diabetes meal plan:\n\n"
                "- Monday: Ragi idli breakfast, brown rice with dal and palak lunch, wheat roti with bhindi dinner.\n"
                "- Tuesday: Oats upma breakfast, jowar roti with dal and methi sabzi lunch, khichdi with curd dinner.\n"
                "- Wednesday: Moong dal chilla breakfast, brown rice with rajma lunch, roti with lauki sabzi dinner.\n"
                "- Thursday: Sprouts salad with toast breakfast, bajra roti with dal lunch, vegetable soup with roti dinner.\n"
                "- Friday: Poha with sprouts breakfast, brown rice with fish curry or dal lunch, roti with dal dinner.\n"
                "- Saturday: Idli sambar breakfast, quinoa or millet vegetable curry lunch, khichdi with curd dinner.\n"
                "- Sunday: Vegetable uttapam breakfast, brown rice with chicken curry or chana lunch, light dal roti dinner.\n\n"
                "Keep portions controlled, avoid sugary drinks and fried snacks, and monitor glucose as advised by your doctor."
                + medical_disclaimer(language)
            )
        elif south_indian_query:
            answer = (
                "Here is a simple South Indian diabetes diet plan:\n\n"
                "- Breakfast: 2 small idlis with sambar, ragi dosa, cracked wheat upma, or oats upma. Avoid sugary tea/coffee.\n"
                "- Mid-morning: 1 small guava or apple, or diluted buttermilk.\n"
                "- Lunch: 1/2 cup brown rice or 2 small rotis with sambar, rasam, poriyal, salad, and curd.\n"
                "- Evening snack: Sundal, roasted chana, sprouts, or buttermilk.\n"
                "- Dinner: Ragi dosa, vegetable kootu, light dal, soup, or small millet khichdi.\n"
                "- Limit: White rice portions, sweets, fruit juice, deep-fried snacks, and coconut-heavy/oily dishes."
                + medical_disclaimer(language)
            )
        elif diet_plan_query:
            answer = (
                "Here is a simple Indian diabetes diet plan:\n\n"
                "- Breakfast: 2 ragi idlis, oats upma, moong dal chilla, or vegetable poha with no sugar tea/coffee.\n"
                "- Mid-morning: 1 small guava or apple, or 1 cup buttermilk.\n"
                "- Lunch: 2 whole-wheat rotis or 1/2 cup brown rice with dal, mixed vegetable sabzi, salad, and curd.\n"
                "- Evening snack: Roasted chana, sprouts, nuts in small quantity, or buttermilk.\n"
                "- Dinner: Light meal such as roti with dal and vegetables, vegetable soup, or khichdi with curd.\n"
                "- Limit: Sugary drinks, sweets, maida foods, deep-fried snacks, fruit juice, and large rice portions."
                + medical_disclaimer(language)
            )
        elif any(word in query_lower for word in ["food", "diet", "meal", "eat", "nutrient"]):
            answer = (
                "Here is safe diabetes-friendly food guidance:\n\n"
                "- Choose high-fiber foods such as vegetables, dal, beans, oats, millets, brown rice, and whole-wheat roti.\n"
                "- Add protein with meals, such as dal, chana, curd, eggs, fish, or lean chicken if suitable for you.\n"
                "- Limit sugary drinks, sweets, maida foods, deep-fried snacks, and very large rice portions.\n"
                "- Prefer whole fruit in controlled portions instead of fruit juice.\n"
                "- Eat balanced meals at regular times and monitor glucose as advised by your doctor."
                + medical_disclaimer(language)
            )
        else:
            answer = (
                "Here is general diabetes guidance:\n\n"
                "- Check fasting and post-meal glucose as advised by your doctor.\n"
                "- Reduce sugary drinks, sweets, refined carbohydrates, and deep-fried foods.\n"
                "- Walk or stay physically active most days if medically safe.\n"
                "- Maintain a healthy weight and sleep routine.\n"
                "- See a doctor for confirmatory tests such as fasting glucose and HbA1c."
                + medical_disclaimer(language)
            )

        return cleanup_response_text(answer)

    if "heart_disease" in diseases or "heart" in topics or "heart" in query_lower:
        if is_heart_test_query(query):
            answer = (
                "Common tests used for heart disease include:\n\n"
                "- Blood pressure check to screen for hypertension.\n"
                "- Cholesterol and triglyceride blood tests to assess heart risk.\n"
                "- Blood sugar or HbA1c because diabetes increases heart risk.\n"
                "- ECG to check heart rhythm and possible signs of heart strain or heart attack.\n"
                "- Echocardiogram to check heart pumping and valves.\n"
                "- Stress test to see how the heart responds to activity.\n"
                "- Troponin blood test when a heart attack is suspected.\n"
                "- CT coronary angiography or coronary angiography to look for narrowed or blocked arteries.\n\n"
                "A doctor chooses tests based on symptoms, risk factors and examination."
                + medical_disclaimer(language)
            )
        elif weekly_plan_query:
            answer = (
                "Here is a compact weekly Indian heart-friendly meal plan:\n\n"
                "- Monday: Oats with nuts, brown rice rasam poriyal lunch, ragi roti dal dinner.\n"
                "- Tuesday: Idli sambar, 2 rotis with dal and sabzi lunch, millet khichdi dinner.\n"
                "- Wednesday: Vegetable upma, brown rice with fish or dal and vegetables lunch, soup with rotis dinner.\n"
                "- Thursday: Moong dal chilla, rajma with brown rice and salad lunch, ragi dosa with kootu dinner.\n"
                "- Friday: Vegetable poha, rotis with palak paneer made with less cream lunch, light dal rice dinner.\n"
                "- Saturday: Fruit with seeds, grilled fish or chana with brown rice lunch, millet dosa dinner.\n"
                "- Sunday: Whole-grain toast, chicken curry or dal with brown rice lunch, khichdi with curd dinner.\n\n"
                "Use less salt and oil, avoid fried foods, and follow your doctor's advice if you have BP, cholesterol, or heart symptoms."
                + medical_disclaimer(language)
            )
        elif dinner_query:
            answer = (
                "For a heart patient, dinner should be light and low in salt:\n\n"
                "- Millet khichdi with curd and vegetable curry.\n"
                "- Ragi roti or whole-wheat roti with dal and sabzi.\n"
                "- Vegetable soup with 1-2 rotis.\n"
                "- Ragi dosa with vegetable kootu or sambar made with less oil.\n"
                "- Avoid fried snacks, salty pickles, papad, creamy gravies, red meat, and heavy late-night meals."
                + medical_disclaimer(language)
            )
        elif diet_plan_query:
            answer = (
                "Here is a simple Indian heart-friendly diet plan:\n\n"
                "- Breakfast: Oats porridge, vegetable poha, idli with sambar, or moong dal chilla.\n"
                "- Mid-morning: Apple, papaya, pomegranate, or roasted chana.\n"
                "- Lunch: 2 rotis or brown rice with dal, vegetables, salad, and low-fat curd.\n"
                "- Evening snack: Buttermilk, sprouts, roasted chana, or a small handful of nuts.\n"
                "- Dinner: Millet khichdi, ragi dosa with vegetables, soup with roti, or light dal rice.\n"
                "- Limit: Excess salt, fried foods, packaged snacks, red meat, full-fat dairy, and smoking."
                + medical_disclaimer(language)
            )
        else:
            answer = (
                "Here is safe heart-health guidance:\n\n"
                "- Keep BP, cholesterol, and blood sugar checked regularly.\n"
                "- Eat more vegetables, fruits, dal, beans, whole grains, nuts, and seeds in sensible portions.\n"
                "- Limit salt, fried foods, processed foods, sugary drinks, tobacco, and excess alcohol.\n"
                "- Do regular walking or light exercise if medically safe.\n"
                "- If you have chest pain, breathlessness, fainting, or pain spreading to arm/jaw/back, seek emergency care."
                + medical_disclaimer(language)
            )
        return cleanup_response_text(answer)

    answer = (
        "Here is general health guidance:\n\n"
        "- Keep meals balanced with vegetables, protein, and whole grains.\n"
        "- Stay hydrated and physically active if medically safe.\n"
        "- Monitor important values such as glucose, BP, and cholesterol when advised.\n"
        "- Consult a qualified doctor for personal diagnosis or treatment."
        + medical_disclaimer(language)
    )
    return cleanup_response_text(answer)


# ===== MAIN RESPONSE =====
def get_response(query, session_id=None, language="en"):
    response_language = resolve_language(query, language)
    english_query = translate_to_english(query, response_language)

    if not english_query:
        english_query = query

    processed_query = english_query
    memory_context = get_memory_context(session_id)

    processed = process_query(processed_query)
    intent = processed["intent"]

    # Emergency symptoms should not depend on the LLM.
    if detect_emergency(processed_query):
        fixed_response = fixed_emergency_response(response_language)

        if fixed_response:
            answer = fixed_response + (fixed_disclaimer(response_language) or "")
        else:
            answer = emergency_response("en") + medical_disclaimer("en")

        remember_turn(session_id, query, answer)
        return {
            "answer": answer,
            "intent": "emergency",
            "sources": [],
            "language": response_language,
            "english_query": english_query,
        }

    if is_normal_glucose_query(processed_query):
        answer = get_normal_glucose_response() + medical_disclaimer("en")
        if response_language != "en":
            translated_answer = translate_from_english(answer, response_language)
            if translated_answer:
                answer = translated_answer

        remember_turn(session_id, query, answer)
        return {
            "answer": answer,
            "intent": "diabetes_question",
            "sources": [],
            "language": response_language,
            "english_query": english_query,
        }

    if is_heart_warning_signs_query(processed_query):
        answer = get_heart_warning_signs_response() + medical_disclaimer("en")
        if response_language != "en":
            translated_answer = translate_from_english(answer, response_language)
            if translated_answer:
                answer = translated_answer

        remember_turn(session_id, query, answer)
        return {
            "answer": answer,
            "intent": "heart_question",
            "sources": [],
            "language": response_language,
            "english_query": english_query,
        }

    # Handle greetings directly.
    if intent == "greeting":
        answer = get_greeting_response()
        if response_language != "en":
            answer = translate_from_english(answer, response_language)

        remember_turn(session_id, query, answer)
        return {
            "answer": answer,
            "intent": intent,
            "sources": [],
            "language": response_language,
            "english_query": english_query,
        }

    # Handle thanks directly.
    if intent == "thanks":
        answer = get_thanks_response()
        if response_language != "en":
            answer = translate_from_english(answer, response_language)

        remember_turn(session_id, query, answer)
        return {
            "answer": answer,
            "intent": intent,
            "sources": [],
            "language": response_language,
            "english_query": english_query,
        }

    if is_memory_question(processed_query):
        answer = build_memory_answer(session_id)
        if response_language != "en":
            answer = translate_from_english(answer, response_language)

        remember_turn(session_id, query, answer)
        return {
            "answer": answer,
            "intent": "memory_recall",
            "sources": [],
            "language": response_language,
            "english_query": english_query,
        }

    # Set disease filter.
    disease_filter = None

    if intent in [
        "diabetes_question",
        "diabetes_prediction",
        "food_diabetes",
    ]:
        disease_filter = "diabetes"

    elif intent == "diabetes_type_prediction":
        disease_filter = "diabetes_types"

    elif intent in [
        "heart_question",
        "heart_prediction",
        "food_heart",
    ]:
        disease_filter = "heart_disease"

    elif intent == "symptom_general":
        disease_filter = "heart_disease"

    # Search local medical knowledge using English query.
    chunks = search_knowledge(processed_query, disease_filter, top_k=15, memory_context=memory_context)
    chunks = rerank_chunks_for_query(chunks, processed_query, intent)

    max_context_chunks = 6 if is_diet_plan_query(processed_query) else 5
    context, sources = compress_context(chunks, max_chunks=max_context_chunks)

    # Build English prompt and generate English answer.
    system_prompt, user_prompt = build_prompt(
        processed_query,
        context,
        intent,
        memory_context,
        "en",
    )

    memory_turns = get_memory_context(session_id, return_raw=True)
    answer = call_nvidia_api(system_prompt, user_prompt, memory_turns)

    if answer:
        answer = cleanup_response_text(answer)

    if answer and (is_diabetes_cause_query(processed_query) or is_fruit_diabetes_query(processed_query)):
        answer = build_local_fallback_answer(processed_query, context, sources, "en")

    elif answer and diet_answer_needs_fallback(processed_query, answer):
        answer = build_local_fallback_answer(processed_query, context, sources, "en")

    elif answer and looks_incomplete(answer):
        answer = answer.strip() + "\n\nPlease ask me to continue if you want more details."

    if not answer:
        answer = build_local_fallback_answer(processed_query, context, sources, "en")

    if response_language != "en":
        translated_answer = translate_from_english(answer, response_language)
        if translated_answer:
            answer = translated_answer

    remember_turn(session_id, query, answer)
    return {
        "answer": answer,
        "intent": intent,
        "sources": sources,
        "language": response_language,
        "english_query": english_query,
    }
    
    
    
if __name__ == "__main__":
    test_queries = [
        "hello",
        "suggest me a weekly plan for diabetes",
        "my bp is increasing what should i do",
        "give me indian diet for heart disease",
        "insulin levels are up what should i do",
        "i am having chest pain what should i do",
        "what are type 1 diabetes",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        result = get_response(query)
        print(f"Intent: {result['intent']}")
        print(f"Answer: {result['answer'][:300]}...")
