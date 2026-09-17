# ===== QUERY EXPANSION DICTIONARY =====
expansion_dict = {
    # Diabetes related
    "sugar": "blood sugar glucose diabetes insulin",
    "glucose": "blood sugar glucose diabetes fasting",
    "insulin": "insulin resistance diabetes blood sugar",
    "diabetes": "diabetes blood sugar glucose insulin type1 type2",
    "thirsty": "excessive thirst polydipsia diabetes symptom",
    "urination": "frequent urination polyuria diabetes symptom",
    "tired": "fatigue tiredness weakness diabetes symptom",
    "weight": "weight loss obesity BMI diabetes risk",
    "bmi": "BMI body mass index obesity diabetes risk",

    # Heart related
    "heart": "heart disease cardiac chest pain cardiovascular",
    "chest": "chest pain angina heart disease cardiac",
    "breath": "shortness of breath dyspnea heart disease",
    "pressure": "blood pressure hypertension heart disease risk",
    "cholesterol": "cholesterol lipids heart disease cardiovascular",
    "vessels": "blocked vessels arteries coronary heart disease",
    "exercise": "exercise pain angina heart disease exang",
    "attack": "heart attack myocardial infarction cardiac emergency",
    "palpitation": "heart palpitation irregular heartbeat arrhythmia",
    "swelling": "leg swelling edema heart failure cardiac",
    "fatigue": "fatigue tiredness heart disease cardiac symptom",
    "fainting": "fainting syncope dizziness heart disease",
    "valve": "heart valve disease murmur cardiac",
    "artery": "coronary artery disease blockage heart attack",
    "stent": "stent angioplasty coronary artery heart treatment",
    "bypass": "bypass surgery coronary artery heart treatment",
    "ecg": "ECG electrocardiogram heart rhythm abnormality",
    "angina": "angina chest pain coronary artery disease",
    "hypertension": "hypertension high blood pressure heart disease risk",
    "tachycardia": "tachycardia fast heartbeat cardiac arrhythmia",
    "bradycardia": "bradycardia slow heartbeat cardiac arrhythmia",
    "clot": "blood clot thrombosis heart attack stroke risk",
    "bpm": "heart rate beats per minute pulse cardiac",
    "pulse": "pulse heart rate beats per minute cardiac",

    # Diabetes types
    "type 1": "type 1 diabetes immune autoimmune insulin dependent",
    "type 2": "type 2 diabetes lifestyle obesity insulin resistance",
    "type 3": "type 3 diabetes pancreas organ damage pancreatogenic",
    "lada": "LADA latent autoimmune diabetes adults slow type 1",
    "mody": "MODY maturity onset diabetes young genetic",
    "gestational": "gestational diabetes pregnancy hormones",
    "prediabetic": "prediabetes borderline glucose reversible",

    # Food related
    "food": "foods diet nutrition healthy eating diabetes heart",
    "eat": "foods diet nutrition healthy eating meal plan",
    "diet": "diet plan meal nutrition healthy foods",
    "nutrition": "nutrition nutrients minerals vitamins health",
    "fruits": "fruits diabetes heart health glycemic index",
    "vegetables": "vegetables diabetes heart health fiber nutrition",
    "karela": "bitter gourd karela diabetes blood sugar",
    "methi": "fenugreek methi seeds diabetes blood sugar",
    "ragi": "ragi finger millet diabetes grain low glycemic",
    "oats": "oats fiber cholesterol diabetes heart health",
    "nuts": "nuts almonds walnuts heart diabetes healthy fat",
    "weekly": "weekly meal plan 7 day diet breakfast lunch dinner",
    "plan": "meal plan diet chart weekly breakfast lunch dinner",
    "diet chart": "diet chart meal plan breakfast lunch dinner weekly",
    "avoid": "foods to limit foods avoid unhealthy foods sugary fried processed salt diabetes heart",
    "limit": "foods to limit avoid reduce sugary fried processed salt portion control",
    "not eat": "foods to avoid foods to limit unhealthy foods diabetes heart",
    "weekly plan": "weekly meal plan 7 day plan monday tuesday wednesday breakfast lunch dinner",

    # Indian diet
    "indian": "indian diet food meal plan diabetes heart health",
    "roti": "roti wheat chapati Indian diet diabetes",
    "rice": "rice brown rice diabetes glycemic index",
    "dal": "lentils dal protein diabetes heart health",
    "idli": "idli dosa south indian diabetes breakfast",
    "upma": "upma breakfast indian diabetes healthy",
    "south indian": "south indian food diet diabetes heart health",
    "north indian": "north indian food diet diabetes heart health",

    # General
    "pain": "pain symptoms diagnosis disease risk",
    "dizzy": "dizziness lightheadedness heart diabetes symptom",
    "vision": "blurred vision diabetes eye complication",
    "heal": "slow healing wounds diabetes complication",
    "morning": "morning routine diet breakfast health",
    "breakfast": "breakfast morning meal diet health diabetes",
    "lunch": "lunch meal diet health diabetes heart",
    "dinner": "dinner meal diet health diabetes heart",
    "snack": "snack healthy eating diabetes heart",
}

# ===== INTENT KEYWORDS =====
greeting_keywords = [
    'hello', 'hi', 'hey', 'good morning', 'good afternoon',
    'good evening', 'how are you', 'what are you', 'who are you',
    'namaste', 'vanakkam', 'namaskar'
]

thanks_keywords = [
    'thank you', 'thanks', 'great', 'awesome', 'helpful',
    'good job', 'well done', 'nice', 'perfect', 'wonderful'
]

diabetes_keywords = [
    'sugar', 'glucose', 'insulin', 'diabetes', 'diabetic',
    'thirsty', 'urination', 'hba1c', 'pancreas', 'prediabetes',
    'type1', 'type2', 'metformin', 'blood sugar'
]

heart_keywords = [
    'heart', 'chest', 'cardiac', 'cardiovascular', 'cholesterol',
    'blood pressure', 'hypertension', 'vessels', 'arteries',
    'ecg', 'angina', 'heartbeat', 'coronary', 'stroke',
    'attack', 'palpitation', 'swelling', 'fainting',
    'valve', 'artery', 'stent', 'bypass', 'tachycardia',
    'bradycardia', 'clot', 'fatigue', 'bpm', 'pulse',
    'heart rate'
]

prediction_keywords = [
    'predict', 'check', 'test', 'diagnose', 'assess',
    'risk', 'calculate', 'analyze', 'scan', 'evaluate'
]

diabetes_type_keywords = [
    'type 1', 'type 2', 'type 3', 'prediabetic',
    'lada', 'mody', 'gestational', 'neonatal',
    'wolfram', 'classify', 'which type', 'what type',
    'identify type', 'diabetes type'
]

food_diabetes_keywords = [
    'food for diabetes', 'eat for diabetes', 'diet for diabetes',
    'diabetic food', 'diabetic diet', 'foods to eat diabetes',
    'good food sugar', 'foods reduce sugar', 'karela', 'methi',
    'bitter gourd', 'fenugreek', 'ragi diabetes', 'fruits diabetes'
]

food_heart_keywords = [
    'food for heart', 'eat for heart', 'diet for heart',
    'heart food', 'heart diet', 'foods heart disease',
    'good food heart', 'foods reduce cholesterol',
    'omega 3', 'heart healthy food'
]

indian_diet_keywords = [
    'indian food', 'indian diet', 'south indian', 'north indian',
    'roti diabetes', 'rice diabetes', 'dal diabetes',
    'idli diabetes', 'indian meal', 'indian breakfast',
    'indian lunch', 'indian dinner', 'indian snack',
    'chapati diabetes', 'indian heart diet'
]

symptom_general_keywords = [
    'heart rate', 'bpm', 'pulse rate', 'beats per minute',
    'normal heart rate', 'high heart rate', 'low heart rate',
    'resting heart rate', 'exercise heart rate'
]

symptom_words = [
    'symptoms', 'what is', 'why', 'how',
    'pain', 'feeling', 'i have', 'is',
    'high', 'low', 'my blood', 'my heart',
    'my sugar', 'my pressure', 'normal'
]

def expand_query(query):
    query_lower = query.lower()
    expanded_terms = [query]
    for keyword, expansion in expansion_dict.items():
        if keyword in query_lower:
            expanded_terms.append(expansion)
    return ' '.join(expanded_terms)

import re

def detect_intent(query):
    query_lower = query.lower()
    words = set(re.findall(r'\b\w+\b', query_lower))

    # Check greeting intent
    greeting_phrases = ['good morning', 'good afternoon', 'good evening', 'how are you', 'what are you', 'who are you']
    greeting_words = ['hello', 'hi', 'hey', 'namaste', 'vanakkam', 'namaskar']
    if any(p in query_lower for p in greeting_phrases) or any(w in words for w in greeting_words):
        return 'greeting'

    # Check thanks intent
    thanks_phrases = ['thank you', 'good job', 'well done']
    thanks_words = ['thanks', 'great', 'awesome', 'helpful', 'nice', 'perfect', 'wonderful']
    if any(p in query_lower for p in thanks_phrases) or any(w in words for w in thanks_words):
        return 'thanks'

    # Strong food and diet signals
    has_food_signal = any(word in query_lower for word in [
        'food', 'foods', 'eat', 'diet', 'meal', 'meals',
        'breakfast', 'lunch', 'dinner', 'snack', 'nutrition',
        'nutrients', 'avoid', 'recommend', 'suggest'
    ])

    has_indian_signal = any(k in query_lower for k in [
        'indian', 'south indian', 'north indian', 'roti', 'chapati',
        'rice', 'dal', 'idli', 'dosa', 'upma', 'poha', 'sambar'
    ])

    has_diabetes_signal = any(k in query_lower for k in diabetes_keywords)
    has_heart_signal = any(k in query_lower for k in heart_keywords)

    # Food / diet intents should be detected before broad disease intents.
    if has_food_signal or has_indian_signal:
        if has_diabetes_signal and not has_heart_signal:
            return 'food_diabetes'
        if has_heart_signal and not has_diabetes_signal:
            return 'food_heart'
        if has_diabetes_signal and has_heart_signal:
            return 'food_general'
        if has_indian_signal:
            return 'indian_diet'
        return 'food_general'

    # Check symptom general
    if any(k in query_lower for k in symptom_general_keywords):
        return 'symptom_general'

    # Check diabetes type intent
    diabetes_type_score = sum(1 for k in diabetes_type_keywords if k in query_lower)
    if diabetes_type_score > 0:
        return 'diabetes_type_prediction'

    # Check prediction intent
    for keyword in prediction_keywords:
        if keyword in query_lower:
            if any(s in query_lower for s in symptom_words):
                break
            if has_diabetes_signal:
                return 'diabetes_prediction'
            if has_heart_signal:
                return 'heart_prediction'
            return 'prediction_unclear'

    # Check diabetes / heart medical intent
    diabetes_score = sum(1 for k in diabetes_keywords if k in query_lower)
    heart_score = sum(1 for k in heart_keywords if k in query_lower)

    if diabetes_score > heart_score and diabetes_score > 0:
        return 'diabetes_question'
    elif heart_score > diabetes_score and heart_score > 0:
        return 'heart_question'
    elif diabetes_score > 0 or heart_score > 0:
        return 'general_medical'
    else:
        return 'general_question'
    
def process_query(query):
    intent = detect_intent(query)
    expanded = expand_query(query)
    
    if intent == 'general_question':
        intent = detect_intent(expanded)
    
    return {
        'original': query,
        'expanded': expanded,
        'intent': intent
    }
