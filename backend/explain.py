def _level(value, low, high):
    if value is None:
        return None
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "normal"


def _add_factor(factors, name, value, status, explanation):
    if value is None:
        return
    factors.append(
        {
            "name": name,
            "value": value,
            "status": status,
            "explanation": explanation,
        }
    )


def explain_diabetes_prediction(data, result):
    glucose = data.get("Glucose")
    bmi = data.get("BMI")
    age = data.get("Age")
    bp = data.get("BloodPressure")
    insulin = data.get("Insulin")
    dpf = data.get("DiabetesPedigreeFunction")

    factors = []

    if glucose is not None:
        if glucose >= 126:
            _add_factor(
                factors,
                "Glucose",
                glucose,
                "high",
                "Fasting glucose at or above 126 mg/dL is in the diabetes range and strongly increases risk.",
            )
        elif glucose >= 100:
            _add_factor(
                factors,
                "Glucose",
                glucose,
                "moderate",
                "Fasting glucose between 100 and 125 mg/dL is in the prediabetes range.",
            )
        else:
            _add_factor(
                factors,
                "Glucose",
                glucose,
                "normal",
                "Fasting glucose below 100 mg/dL is generally considered normal.",
            )

    if bmi is not None:
        if bmi >= 30:
            _add_factor(
                factors,
                "BMI",
                bmi,
                "high",
                "BMI of 30 or higher is in the obesity range and can increase insulin resistance.",
            )
        elif bmi >= 25:
            _add_factor(
                factors,
                "BMI",
                bmi,
                "moderate",
                "BMI between 25 and 29.9 is overweight and may increase diabetes risk.",
            )
        else:
            _add_factor(
                factors,
                "BMI",
                bmi,
                "normal",
                "BMI below 25 is generally a healthier range for diabetes prevention.",
            )

    if age is not None:
        if age >= 45:
            _add_factor(
                factors,
                "Age",
                age,
                "moderate",
                "Diabetes risk tends to increase after age 45.",
            )
        else:
            _add_factor(
                factors,
                "Age",
                age,
                "normal",
                "Younger age is generally associated with lower type 2 diabetes risk, though risk can still exist.",
            )

    if bp is not None:
        if bp >= 90:
            _add_factor(
                factors,
                "Diastolic Blood Pressure",
                bp,
                "high",
                "Diastolic blood pressure of 90 mmHg or higher is high and may occur along with metabolic risk factors.",
            )
        elif bp >= 80:
            _add_factor(
                factors,
                "Diastolic Blood Pressure",
                bp,
                "moderate",
                "Diastolic blood pressure between 80 and 89 mmHg is elevated.",
            )
        else:
            _add_factor(
                factors,
                "Diastolic Blood Pressure",
                bp,
                "normal",
                "This diastolic blood pressure value does not strongly raise diabetes risk by itself.",
            )

    if insulin is not None:
        if insulin > 160:
            _add_factor(
                factors,
                "Insulin",
                insulin,
                "moderate",
                "Higher insulin may suggest insulin resistance, depending on the test context.",
            )

    if dpf is not None:
        if dpf >= 0.5:
            _add_factor(
                factors,
                "Family History Score",
                dpf,
                "moderate",
                "A higher diabetes pedigree score suggests stronger family-history-related risk.",
            )

    high_or_moderate = [
        f for f in factors if f["status"] in ["high", "moderate"]
    ]

    if high_or_moderate:
        top_summary = ", ".join(f["name"] for f in high_or_moderate[:3])
        plain_explanation = (
            f"The main factors influencing this result are {top_summary}. "
            "These values may increase diabetes risk when seen together."
        )
    else:
        plain_explanation = (
            "The provided values do not show strong diabetes risk signals, but regular monitoring is still useful."
        )

    if result.get("prediction") == 1:
        clinical_interpretation = (
            "The model found a diabetes-risk pattern in the provided values. "
            "This is not a diagnosis, but it should be confirmed with medical testing such as fasting glucose, HbA1c, or an oral glucose tolerance test."
        )
        next_steps = [
            "Book a doctor consultation for confirmatory testing.",
            "Monitor fasting and post-meal glucose as advised by a clinician.",
            "Reduce sugary drinks, sweets, and refined carbohydrates.",
            "Aim for regular physical activity, such as brisk walking, if medically safe.",
        ]
    else:
        clinical_interpretation = (
            "The model did not find a strong diabetes-risk pattern in the provided values. "
            "This does not rule out diabetes if symptoms or abnormal lab values are present."
        )
        next_steps = [
            "Maintain a balanced diet with vegetables, legumes, whole grains, and controlled portions.",
            "Stay physically active and monitor weight.",
            "Repeat screening periodically, especially if you have family history or symptoms.",
        ]

    clinical_risk = "Low"
    clinical_note = "The provided values do not show major diabetes screening concerns."

    if glucose is not None and glucose >= 126:
        clinical_risk = "High"
        clinical_note = (
            "Your glucose value is in the diabetes range if this was a fasting test. "
            "Please confirm with a qualified doctor and appropriate lab testing."
        )
    elif glucose is not None and glucose >= 100:
        clinical_risk = "Moderate"
        clinical_note = (
            "Your glucose value is in the prediabetes range if this was a fasting test. "
            "Lifestyle changes and follow-up testing are recommended."
        )

    if bmi is not None and bmi >= 30 and clinical_risk != "High":
        clinical_risk = "Moderate"
        clinical_note = (
            "Your BMI is in the obesity range, which can increase insulin resistance and diabetes risk."
        )
    elif bmi is not None and bmi >= 25 and clinical_risk == "Low":
        clinical_risk = "Moderate"
        clinical_note = (
            "Your BMI is in the overweight range, which may increase diabetes risk when combined with other factors."
        )

    return {
        "plain_explanation": plain_explanation,
        "clinical_interpretation": clinical_interpretation,
        "clinical_risk": clinical_risk,
        "clinical_note": clinical_note,
        "top_factors": factors,
        "next_steps": next_steps,
    }

def explain_heart_prediction(data, result):
    age = data.get("age")
    bp = data.get("trestbps")
    chol = data.get("chol")
    fbs = data.get("fbs")
    thalch = data.get("thalch")
    exang = data.get("exang")
    oldpeak = data.get("oldpeak")
    ca = data.get("ca")

    factors = []

    if age is not None:
        if age >= 55:
            _add_factor(
                factors,
                "Age",
                age,
                "moderate",
                "Heart disease risk generally increases with age.",
            )

    if bp is not None:
        if bp >= 140:
            _add_factor(
                factors,
                "Resting Blood Pressure",
                bp,
                "high",
                "Resting systolic blood pressure of 140 mmHg or higher is high and can strain the heart.",
            )
        elif bp >= 130:
            _add_factor(
                factors,
                "Resting Blood Pressure",
                bp,
                "moderate",
                "Resting systolic blood pressure between 130 and 139 mmHg is elevated.",
            )

    if chol is not None:
        if chol >= 240:
            _add_factor(
                factors,
                "Cholesterol",
                chol,
                "high",
                "Total cholesterol of 240 mg/dL or higher is considered high.",
            )
        elif chol >= 200:
            _add_factor(
                factors,
                "Cholesterol",
                chol,
                "moderate",
                "Total cholesterol between 200 and 239 mg/dL is borderline high.",
            )

    if fbs == 1:
        _add_factor(
            factors,
            "Fasting Blood Sugar",
            "Above 120 mg/dL",
            "moderate",
            "High fasting blood sugar can increase cardiovascular risk.",
        )

    if thalch is not None and thalch < 120:
        _add_factor(
            factors,
            "Maximum Heart Rate",
            thalch,
            "moderate",
            "Lower maximum heart rate during exercise can be a concerning pattern depending on age and test context.",
        )

    if exang == 1:
        _add_factor(
            factors,
            "Exercise-Induced Chest Pain",
            "Yes",
            "high",
            "Chest pain during exercise can be an important warning sign and should be medically assessed.",
        )

    if oldpeak is not None and oldpeak >= 2:
        _add_factor(
            factors,
            "ST Depression",
            oldpeak,
            "high",
            "Higher ST depression can indicate heart stress during exercise testing.",
        )

    if ca is not None and ca >= 1:
        _add_factor(
            factors,
            "Blocked Vessels",
            ca,
            "high",
            "A higher number of blocked vessels is strongly associated with heart disease risk.",
        )

    if factors:
        top_summary = ", ".join(f["name"] for f in factors[:3])
        plain_explanation = (
            f"The main factors influencing this result are {top_summary}. "
            "These findings may point toward increased cardiovascular risk."
        )
    else:
        plain_explanation = (
            "The provided values do not show strong heart-risk signals, but routine monitoring is still important."
        )

    if result.get("prediction") == 1:
        clinical_interpretation = (
            "The model found a heart-disease-risk pattern in the provided values. "
            "This is not a diagnosis, but it should be reviewed by a qualified doctor or cardiologist."
        )
        next_steps = [
            "Book a cardiology consultation.",
            "Avoid strenuous exercise until cleared by a doctor if symptoms are present.",
            "Monitor blood pressure and cholesterol.",
            "Seek emergency help for chest pain, breathlessness, fainting, or pain spreading to arm, jaw, neck, or back.",
        ]
    else:
        clinical_interpretation = (
            "The model did not find a strong heart-disease-risk pattern in the provided values. "
            "This does not rule out heart disease if symptoms are present."
        )
        next_steps = [
            "Maintain regular physical activity if medically safe.",
            "Eat more vegetables, legumes, whole grains, fruits, and heart-healthy fats.",
            "Limit salt, fried foods, tobacco, and excess alcohol.",
            "Get periodic blood pressure and cholesterol checks.",
        ]

    return {
        "plain_explanation": plain_explanation,
        "clinical_interpretation": clinical_interpretation,
        "top_factors": factors,
        "next_steps": next_steps,
    }