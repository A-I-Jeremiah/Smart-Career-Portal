# predict.py
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR.parent / "models" / "xgb_best_model.pkl"
LABEL_ENCODER_PATH = BASE_DIR.parent / "models" / "label_encoder.pkl"

model = joblib.load(MODEL_PATH)
le = joblib.load(LABEL_ENCODER_PATH)

# ── Department-specific subject combinations ──────────────────────────────────
DEPARTMENT_SUBJECTS = {
    "Science": [
        "mathematics", "english", "civic_education", "physics", "chemistry",
        "biology", "further_mathematics", "agricultural_science", "geography",
        "technical_drawing", "computer_studies",
    ],
    "Arts": [
        "mathematics", "english", "civic_education", "yoruba", "igbo_hausa",
        "literature_in_english", "christian_religious_studies/islamic_studies",
        "creative_arts", "economics", "government",
    ],
    "Commercial": [
        "mathematics", "english", "civic_education", "economics",
        "financial_accounting", "commerce", "government", "marketing",
        "data_processing",
    ],
}

# All subject grade columns (History, French, Age_Group were dropped in notebook)
ALL_SUBJECT_COLS = [
    "mathematics", "english", "civic_education", "physics", "chemistry",
    "biology", "further_mathematics", "agricultural_science", "geography",
    "technical_drawing", "computer_studies", "yoruba", "igbo_hausa",
    "data_processing", "literature_in_english",
    "christian_religious_studies/islamic_studies", "creative_arts",
    "economics", "financial_accounting", "commerce", "government", "marketing",
]

CATEGORICAL_COLS = [
    "gender", "school_type", "department", "academic_strength",
    "best_subject_category", "confidence_level", "career_influence",
] + ALL_SUBJECT_COLS

NUMERICAL_COLS = [
    "age", "waec_year", "waec_credits", "cgpa", "course_alignment",
    "aptitude_score_10", "cognitive_score_10", "psychometric_avg_5",
    "sentiment_avg_5",
]

FEATURES = CATEGORICAL_COLS + NUMERICAL_COLS

GRADE_MAP = {"A": 8, "B": 6, "C": 5, "D": 3, "E": 2, "F": 1, "UNKNOWN": 5}


def predict_career(input_data: dict):
    """
    Predict career for SS1/SS2/SS3 students (pre-WAEC).

    Only subject grades relevant to the student's department are required.
    Other subjects receive the 'UNKNOWN' default (mapped to 5).
    History, French and Age_Group are excluded (dropped during training).
    Age is auto-generated in range 17-25 if not provided.
    """
    df_input = pd.DataFrame([input_data])
    df_input.columns = (
        df_input.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    # Determine department for subject filtering
    department = str(df_input.get("department", pd.Series(["Unknown"]))[0]).strip()
    allowed_subjects = DEPARTMENT_SUBJECTS.get(department, ALL_SUBJECT_COLS)

    # Safe defaults
    defaults = {
        "gender": "Unknown",
        "school_type": "Unknown",
        "department": "Unknown",
        "academic_strength": "Unknown",
        "best_subject_category": "Unknown",
        "confidence_level": "Unknown",
        "career_influence": "Unknown",
        "waec_credits": 5.0,
        "cgpa": 0.0,
        "course_alignment": 0,
        "aptitude_score_10": 5,
        "cognitive_score_10": 5,
        "psychometric_avg_5": 3.0,
        "sentiment_avg_5": 3.0,
        "waec_year": 2023,
    }
    # All subject grades default to UNKNOWN
    for col in ALL_SUBJECT_COLS:
        defaults[col] = "UNKNOWN"

    # Generate age (17-25) if not provided — mirrors notebook training
    if "age" not in df_input.columns or pd.isna(df_input.at[0, "age"]):
        df_input["age"] = int(np.random.randint(17, 26))
    defaults.pop("age", None)

    # Apply defaults for missing columns
    for col, default_value in defaults.items():
        if col not in df_input.columns:
            df_input[col] = default_value

    # Enforce department filtering: zero-out subjects NOT in student's department
    for col in ALL_SUBJECT_COLS:
        if col not in allowed_subjects:
            df_input[col] = "UNKNOWN"

    # Map subject grades to numeric (A→8, B→6, C→5, D→3, E→2, F→1, UNKNOWN→5)
    grade_cols = [c for c in ALL_SUBJECT_COLS if c in df_input.columns]
    for col in grade_cols:
        df_input[col] = (
            df_input[col]
            .astype(str)
            .str.strip()
            .str.upper()
            .map(GRADE_MAP)
            .fillna(5)
        )

    # Ensure all feature columns exist
    for col in FEATURES:
        if col not in df_input.columns:
            df_input[col] = (
                5.0 if col == "waec_credits"
                else "Unknown" if col in CATEGORICAL_COLS
                else 0.0
            )

    df_input = df_input[FEATURES]

    # Convert numerical columns
    for col in NUMERICAL_COLS:
        if col in df_input.columns:
            df_input[col] = pd.to_numeric(df_input[col], errors="coerce").fillna(0.0)

    df_input = df_input.astype(
        {col: "float64" if col in NUMERICAL_COLS else "object" for col in FEATURES}
    )

    # Critical guard: F in Maths or English → no recommendation
    math_grade = df_input.at[0, "mathematics"]
    eng_grade = df_input.at[0, "english"]
    if math_grade == 1 or eng_grade == 1:
        return {
            "predicted_career": (
                "None — please improve your grades in Mathematics and English "
                "to get career recommendations."
            ),
            "confidence_percent": 0.0,
            "top_3": [],
        }

    # ── Predict ───────────────────────────────────────────────────────────────
    pred_encoded = model.predict(df_input)[0]
    proba = model.predict_proba(df_input)[0]

    career = le.inverse_transform([pred_encoded])[0]
    confidence = float(np.max(proba))

    top_three = sorted(
        zip(le.classes_, proba), key=lambda x: x[1], reverse=True
    )[:3]

    return {
        "predicted_career": str(career),
        "confidence_percent": float(round(confidence * 100, 1)),
        "top_3": [
            {
                "career": str(career_name),
                "confidence_percent": float(round(float(prob) * 100, 1)),
            }
            for career_name, prob in top_three
        ],
    }


# Quick test when running directly
if __name__ == "__main__":
    sample = {
        "Gender": "Male",
        "Age": 17,
        "School_Type": "Mission / Faith School",
        "Department": "Science",
        "Mathematics": "C",
        "English": "B",
        "Civic Education": "D",
        "Physics": "E",
        "Chemistry": "A",
        "Biology": "A",
        "Agricultural Science": "B",
        "Geography": "D"
    }

    result = predict_career(sample)
    print("\n=== SS Student Career Prediction ===")
    print(f"Predicted Career: {result['predicted_career']}")
    print(f"Confidence: {result['confidence_percent']:.1f}%\n")
    print("Top 3:")
    for item in result["top_3"]:
        print(f"  • {item['career']} ({item['confidence_percent']:.1f}%)")