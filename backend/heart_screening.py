def _yes(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ["yes", "true", "1", "y"]


def screen_heart_risk_simple(data):
    age = int(data.get("age", 0) or 0)
    gender = str(data.get("gender", "")).strip().lower()

    chest_pain = _yes(data.get("chest_pain"))
    breathless_walking = _yes(data.get("breathless_walking"))
    high_bp = _yes(data.get("high_bp"))
    diabetes = _yes(data.get("diabetes"))
    smoker = _yes(data.get("smoker"))
    high_cholesterol = _yes(data.get("high_cholesterol"))
    tired_easily = _yes(data.get("tired_easily"))
    family_history = _yes(data.get("family_history"))
    exercise_chest_pain = _yes(data.get("exercise_chest_pain"))

    recovery = str(data.get("exercise_recovery", "normal")).strip().lower()

    score = 0
    factors = []

    def add(points, name, explanation):
        nonlocal score
        score += points
        factors.append({
            "name": name,
            "points": points,
            "explanation": explanation
        })

    if age >= 60:
        add(2, "Age", "Age 60 or above increases cardiovascular risk.")
    elif age >= 45:
        add(1, "Age", "Heart risk tends to increase from middle age onward.")

    if gender == "male" and age >= 45:
        add(1, "Gender and age", "Men above 45 generally have higher heart-risk screening concern.")

    if chest_pain:
        add(3, "Chest pain", "Chest pain or pressure can be an important warning symptom.")

    if exercise_chest_pain:
        add(3, "Chest pain during exercise", "Chest pain during activity needs medical evaluation.")

    if breathless_walking:
        add(2, "Breathlessness while walking", "Shortness of breath with mild activity can be a heart warning sign.")

    if high_bp:
        add(2, "High blood pressure", "High blood pressure is a major risk factor for heart disease.")

    if diabetes:
        add(2, "Diabetes", "Diabetes increases the risk of heart disease and stroke.")

    if smoker:
        add(2, "Smoking", "Tobacco use increases heart disease and heart attack risk.")

    if high_cholesterol:
        add(2, "High cholesterol", "High cholesterol can contribute to plaque buildup in arteries.")

    if tired_easily:
        add(1, "Easy tiredness", "Unusual tiredness with small effort can be a warning sign.")

    if family_history:
        add(1, "Family history", "Family history can increase heart disease risk.")

    if recovery in ["poor", "slow", "bad"]:
        add(2, "Poor recovery after exercise", "Slow or poor recovery after activity may need medical review.")
    elif recovery in ["average", "moderate"]:
        add(1, "Average recovery after exercise", "Reduced recovery after activity may add some risk concern.")

    emergency_warning = chest_pain and (
        breathless_walking or exercise_chest_pain or tired_easily
    )

    if emergency_warning:
        risk = "High"
        urgency = "urgent"
    elif score >= 8:
        risk = "High"
        urgency = "doctor_soon"
    elif score >= 4:
        risk = "Moderate"
        urgency = "routine_checkup"
    else:
        risk = "Low"
        urgency = "preventive_care"

    if urgency == "urgent":
        action = (
            "If chest pain is happening now, especially with breathlessness, sweating, faintness, "
            "or pain spreading to arm/jaw/back, seek emergency medical care immediately."
        )
    elif urgency == "doctor_soon":
        action = "Please book a doctor or cardiology consultation soon for proper evaluation."
    elif urgency == "routine_checkup":
        action = "Consider a routine health checkup, including blood pressure, cholesterol, and blood sugar testing."
    else:
        action = "Keep following heart-healthy habits and repeat screening periodically."

    next_steps = [
        "Check blood pressure with a reliable device.",
        "Get cholesterol and blood sugar tested if not done recently.",
        "Avoid tobacco and limit fried, salty, and highly processed foods.",
        "Do regular walking or physical activity if you do not have symptoms and it is medically safe."
    ]

    if risk in ["Moderate", "High"]:
        next_steps.insert(0, "Discuss these symptoms and risk factors with a qualified doctor.")

    return {
        "mode": "simple_heart_screening",
        "result": f"{risk} Screening Risk",
        "risk": risk,
        "score": score,
        "urgency": urgency,
        "description": (
            "This is a simple screening result based on symptoms and risk factors. "
            "It is not a diagnosis and it does not replace ECG, blood tests, or a doctor's evaluation."
        ),
        "action": action,
        "top_factors": factors[:6],
        "next_steps": next_steps
    }