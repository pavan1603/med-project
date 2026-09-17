import pickle
import pandas as pd
import numpy as np
import os
from explain import explain_diabetes_prediction, explain_heart_prediction



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')

# ===== LOAD MODELS =====
print("Loading ML models...")

with open(os.path.join(MODELS_DIR, 'diabetes_xgb_final.pkl'), 'rb') as f:
    diabetes_model = pickle.load(f)

with open(os.path.join(MODELS_DIR, 'diabetes2_xgb_model.pkl'), 'rb') as f:
    diabetes2_model = pickle.load(f)

with open(os.path.join(MODELS_DIR, 'heart_xgb_model.pkl'), 'rb') as f:
    heart_model = pickle.load(f)

print("All models loaded successfully!")


DIABETES_FEATURES = [
    'Age',
    'BMI',
    'BloodPressure',
    'DiabetesPedigreeFunction',
    'Glucose',
    'Insulin',
    'Pregnancies',
    'SkinThickness',
]


def _model_features(model, fallback):
    try:
        names = model.get_booster().feature_names
        return names or fallback
    except Exception:
        return fallback


def _ordered_frame(data, model, fallback_features):
    features = _model_features(model, fallback_features)
    row = {feature: data.get(feature, 0) for feature in features}
    return pd.DataFrame([row], columns=features)

# ===== TYPE LABELS =====
diabetes_type_labels = {
    0: 'Prediabetic',
    1: 'Type 1 Diabetes',
    2: 'Type 2 Diabetes',
    3: 'Type 3 Diabetes'
}

type_info = {
    0: {
        'name': 'Prediabetic',
        'description': 'Your blood sugar is higher than normal but not yet diabetic.',
        'risk': 'Moderate',
        'action': 'Lifestyle changes can REVERSE this condition!',
        'diet': 'Reduce sugar and carbohydrates intake.',
        'exercise': '30 minutes walking daily recommended.'
    },
    1: {
        'name': 'Type 1 Diabetes',
        'description': 'Your immune system is attacking insulin producing cells.',
        'risk': 'High',
        'action': 'Insulin injections required. See a doctor immediately!',
        'diet': 'Strict carbohydrate counting required.',
        'exercise': 'Regular exercise helps but monitor blood sugar.'
    },
    2: {
        'name': 'Type 2 Diabetes',
        'description': 'Your body is not using insulin properly due to lifestyle factors.',
        'risk': 'High',
        'action': 'Medication and lifestyle changes required immediately.',
        'diet': 'Avoid processed foods sugar and refined carbs.',
        'exercise': 'Daily exercise is critical for managing Type 2.'
    },
    3: {
        'name': 'Type 3 Diabetes',
        'description': 'Diabetes caused by organ damage to pancreas or liver.',
        'risk': 'Very High',
        'action': 'Immediate medical attention required!',
        'diet': 'Strict medical diet — consult a dietitian.',
        'exercise': 'Light exercise only — consult doctor first.'
    }
}

heart_info = {
    0: {
        'name': 'No Heart Disease',
        'risk': 'Low',
        'description': 'Your heart appears healthy based on provided data.',
        'action': 'Maintain healthy lifestyle and get regular checkups.',
        'diet': 'Continue eating balanced diet with fruits and vegetables.',
        'exercise': 'Keep up your current physical activity level.'
    },
    1: {
    'name': 'Heart Disease Risk Pattern Detected',
    'risk': 'High',
    'description': 'The provided report values show a pattern associated with higher heart disease risk.',
    'action': 'Please consult a cardiologist soon. Seek emergency care if you have chest pain, breathlessness, fainting, or pain spreading to arm, jaw, neck, or back.',
    'diet': 'Limit salt, fried foods, processed foods, trans fats and excess saturated fat. Prefer vegetables, fruits, dal, whole grains and healthy oils in small amounts.',
    'exercise': 'Avoid strenuous exercise if symptoms are present until cleared by a doctor.'
    }
}

# ===== PREDICTION FUNCTIONS =====

def predict_diabetes_type(data):
    """Predict diabetes type — new dataset model"""
    df = pd.DataFrame([data])
    prediction = diabetes2_model.predict(df)[0]
    probability = diabetes2_model.predict_proba(df)[0]
    confidence = round(float(probability[prediction]) * 100, 1)
    info = type_info[prediction]

    return {
        'prediction': int(prediction),
        'confidence': confidence,
        'type': diabetes_type_labels[prediction],
        'risk': info['risk'],
        'description': info['description'],
        'action': info['action'],
        'diet': info['diet'],
        'exercise': info['exercise']
    }

def predict_diabetes(data):
    """Predict if patient has diabetes + type"""
    df = _ordered_frame(data, diabetes_model, DIABETES_FEATURES)
    prediction = diabetes_model.predict(df)[0]
    probability = diabetes_model.predict_proba(df)[0]
    confidence = round(float(probability[prediction]) * 100, 1)

    if prediction == 1:
        diabetes_type = 'Requires clinical confirmation'
        type_confidence = None
        type_description = (
            'Diabetes type cannot be confirmed from this basic screening form alone. '
            'A doctor may use tests such as HbA1c, fasting glucose, C-peptide, ketones, '
            'and autoantibodies to classify the type.'
        )
        type_action = 'Consult a qualified doctor for confirmatory testing and diabetes type classification.'
        type_diet = 'Follow a diabetes-friendly diet while waiting for medical confirmation.'
        type_exercise = 'Do regular physical activity if medically safe and advised by your doctor.'
        type_risk = 'Needs Confirmation'
        
    else:
        diabetes_type = 'None'
        type_confidence = 0
        type_description = ''
        type_action = ''
        type_diet = ''
        type_exercise = ''
        type_risk = 'Low'

    result = {
        'prediction': int(prediction),
        'confidence': confidence,
        'result': 'Diabetic' if prediction == 1 else 'No Diabetes',
        'diabetes_type': diabetes_type,
        'type_confidence': type_confidence,
        'type_risk': type_risk,
        'risk': 'High' if prediction == 1 else 'Low',
        'description': 'Signs of diabetes detected.' if prediction == 1 else 'No signs of diabetes detected.',
        'type_description': type_description,
        'action': 'Schedule a doctor consultation for confirmatory testing.' if prediction == 1 else 'Maintain healthy lifestyle.',
        'type_action': type_action,
        'diet': 'Limit sugary drinks, sweets, and refined carbohydrates. Prefer vegetables, dal, whole grains, and controlled portions.' if prediction == 1 else 'Continue balanced diet.',
        'exercise': 'Aim for regular physical activity, such as walking, if medically safe.' if prediction == 1 else 'Keep up current activity.',
        'type_diet': type_diet,
        'type_exercise': type_exercise
    }

    result['explanation'] = explain_diabetes_prediction(data, result)

    return result

def predict_heart_disease(data):
    """Predict heart disease"""
    df = pd.DataFrame([data])
    prediction = heart_model.predict(df)[0]
    probability = heart_model.predict_proba(df)[0]
    confidence = round(float(probability[prediction]) * 100, 1)
    info = heart_info[prediction]

    result = {
        'prediction': int(prediction),
        'confidence': confidence,
        'result': info['name'],
        'risk': info['risk'],
        'description': info['description'],
        'action': info['action'],
        'diet': info['diet'],
        'exercise': info['exercise']
    }

    result['explanation'] = explain_heart_prediction(data, result)

    return result

# ===== TEST =====
if __name__ == '__main__':

    diabetes_sample = {
        'Pregnancies': 2,
        'Glucose': 150,
        'BloodPressure': 80,
        'SkinThickness': 30,
        'Insulin': 200,
        'BMI': 35.0,
        'DiabetesPedigreeFunction': 0.5,
        'Age': 45
    }

    heart_sample = {
        'age': 63, 'sex': 1, 'trestbps': 145,
        'chol': 280, 'fbs': 1, 'thalch': 100,
        'exang': 1, 'oldpeak': 2.5, 'ca': 2,
        'cp_asymptomatic': 1, 'cp_atypical angina': 0,
        'cp_non-anginal': 0, 'cp_typical angina': 0,
        'restecg_lv hypertrophy': 1, 'restecg_normal': 0,
        'restecg_st-t abnormality': 0, 'slope_downsloping': 1,
        'slope_flat': 0, 'slope_upsloping': 0,
        'thal_fixed defect': 1, 'thal_normal': 0,
        'thal_reversable defect': 0
    }

    print("\n===== DIABETES PREDICTION =====")
    result = predict_diabetes(diabetes_sample)
    print(f"Result      : {result['result']}")
    print(f"Confidence  : {result['confidence']}%")
    print(f"Risk        : {result['risk']}")
    print(f"Diabetes Type: {result['diabetes_type']}")
    print(f"Type Confidence: {result['type_confidence']}%")
    print(f"Action      : {result['action']}")
    print(f"Type Action : {result['type_action']}")

    print("\n===== HEART DISEASE PREDICTION =====")
    result = predict_heart_disease(heart_sample)
    print(f"Result      : {result['result']}")
    print(f"Confidence  : {result['confidence']}%")
    print(f"Risk        : {result['risk']}")
    print(f"Action      : {result['action']}")
