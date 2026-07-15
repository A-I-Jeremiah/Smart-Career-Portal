# backend/models/ml_model.py
"""
XGBoost model loader and prediction logic.
The saved model is a full sklearn Pipeline (ColumnTransformer + XGBClassifier),
so all preprocessing happens inside model.predict().
"""
import numpy as np
import pandas as pd
import joblib
from backend.config import MODEL_PATH, LABEL_ENCODER_PATH

# ── Lazy model loading ───────────────────────────────────────────────────────
_model = None
_label_encoder = None
_model_load_error = None


def _load_model_artifacts():
    global _model, _label_encoder, _model_load_error
    if _model is not None and _label_encoder is not None:
        return

    try:
        _model = joblib.load(MODEL_PATH)
        _label_encoder = joblib.load(LABEL_ENCODER_PATH)
        _model_load_error = None
    except FileNotFoundError:
        _model = None
        _label_encoder = None
        _model_load_error = (
            f"ML artifacts missing. Expected files at {MODEL_PATH.parent}. "
            "Ensure models/xgb_best_model.pkl and models/label_encoder.pkl are present."
        )
    except Exception as exc:
        _model = None
        _label_encoder = None
        _model_load_error = (
            f"Failed to load ML artifacts: {exc}. "
            "Check that model files are valid and readable."
        )


# ── Department subject filtering (mirrors notebook & predict.py) ──────────────
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


def run_xgboost(input_data: dict) -> dict:
    """
    Run XGBoost prediction with a small ensemble + heuristic fallback.

    Improvements made:
    - Normalise and fill missing features robustly.
    - Ensemble the prediction by averaging probabilities with a version
      where demographic fields (gender, school_type) are set to Unknown to
      reduce potential demographic bias.
    - If the model confidence is low, apply a simple subject-based heuristic
      to pick a backup recommendation and raise confidence modestly.

    Returns: predicted_career, confidence_percent, top_3, optional warning
    """
    df = pd.DataFrame([input_data])
    df.columns = (
        df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    )

    department = str(df.get("department", pd.Series(["Unknown"]))[0]).strip()
    allowed = DEPARTMENT_SUBJECTS.get(department, ALL_SUBJECT_COLS)

    # Defaults
    defaults = {
        "gender": "Unknown", "school_type": "Unknown", "department": "Unknown",
        "academic_strength": "Unknown", "best_subject_category": "Unknown",
        "confidence_level": "Unknown", "career_influence": "Unknown",
        "waec_credits": 5.0, "cgpa": 0.0, "course_alignment": 0,
        "aptitude_score_10": 5, "cognitive_score_10": 5,
        "psychometric_avg_5": 3.0, "sentiment_avg_5": 3.0, "waec_year": 2023,
    }
    for col in ALL_SUBJECT_COLS:
        defaults[col] = "UNKNOWN"

    # Age: reasonable default if missing
    if "age" not in df.columns or pd.isna(df.at[0, "age"]):
        df["age"] = int(np.random.randint(17, 26))

    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    # Department subject filtering
    for col in ALL_SUBJECT_COLS:
        if col not in allowed:
            df[col] = "UNKNOWN"

    # Grade → numeric (robust mapping)
    for col in ALL_SUBJECT_COLS:
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.strip().str.upper()
                .map(GRADE_MAP).fillna(5)
            )

    # Ensure all features exist
    for col in FEATURES:
        if col not in df.columns:
            df[col] = (
                5.0 if col == "waec_credits"
                else "Unknown" if col in CATEGORICAL_COLS
                else 0.0
            )

    df = df[FEATURES]
    for col in NUMERICAL_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df.astype(
        {c: "float64" if c in NUMERICAL_COLS else "object" for c in FEATURES}
    )

    # Guard: F in Maths or English (immediate block)
    if df.at[0, "mathematics"] == 1 or df.at[0, "english"] == 1:
        return {
            "predicted_career": (
                "None — improve Mathematics and English to get recommendations."
            ),
            "confidence_percent": 0.0,
            "top_3": [],
            "warning": "Student has F in Mathematics or English.",
        }

    # --- Load model artifacts lazily and reduce potential demographic bias via ensemble
    _load_model_artifacts()
    if _model is None or _label_encoder is None:
        return {
            "predicted_career": "Unknown",
            "confidence_percent": 0.0,
            "top_3": [],
            "warning": _model_load_error or "ML artifacts unavailable.",
        }

    try:
        proba_full = _model.predict_proba(df)[0]
    except Exception:
        return {"predicted_career": "Unknown", "confidence_percent": 0.0, "top_3": []}

    df_no_demo = df.copy()
    for dcol in ("gender", "school_type"):
        if dcol in df_no_demo.columns:
            df_no_demo[dcol] = "Unknown"

    try:
        proba_no_demo = model.predict_proba(df_no_demo)[0]
    except Exception:
        proba_no_demo = proba_full

    # Average probabilities from both runs
    avg_proba = (proba_full + proba_no_demo) / 2.0

    # Determine predicted label from averaged probabilities
    top_idx = int(np.argmax(avg_proba))
    # label_encoder.classes_ holds class labels in index order — use it to avoid
    # assumptions about the encoder implementation (safer than inverse_transform here).
    career = label_encoder.classes_[top_idx]
    confidence = float(np.max(avg_proba))

    # Build top-3 list
    top_indices = np.argsort(avg_proba)[::-1][:3]
    top_three = [(label_encoder.classes_[i], float(avg_proba[i])) for i in top_indices]

    # Heuristic fallback: simple subject-score based matching when confidence low
    heuristic_warning = None
    if confidence < 0.40:
        # Define small mapping of career keys to subject importance
        CAREER_SUBJECT_MAP = {
            'Computer Science & IT': ['computer_studies', 'mathematics', 'further_mathematics'],
            'Engineering & Technology': ['physics', 'mathematics', 'technical_drawing'],
            'Medicine & Health Sciences': ['biology', 'chemistry', 'english'],
            'Business & Finance': ['economics', 'financial_accounting', 'mathematics'],
            'Creative Arts & Design': ['creative_arts', 'literature_in_english', 'english'],
            'Agriculture & Environmental Sciences': ['agricultural_science', 'biology', 'geography'],
            'Law & Social Sciences': ['government', 'literature_in_english', 'english'],
            'Mass Communication & Media': ['literature_in_english', 'english', 'creative_arts'],
        }

        # Score careers by average subject grades mapped from GRADE_MAP numeric values
        subject_scores = {col: float(df.at[0, col]) for col in ALL_SUBJECT_COLS}
        career_scores = []
        for c, subs in CAREER_SUBJECT_MAP.items():
            vals = [subject_scores.get(s, 5.0) for s in subs]
            career_scores.append((c, float(np.mean(vals))))
        career_scores.sort(key=lambda x: x[1], reverse=True)
        heuristic_choice, heuristic_score = career_scores[0]

        # If heuristic suggests a different career, boost it slightly as fallback
        if heuristic_choice != career and heuristic_score >= 5.5:
            career = heuristic_choice
            confidence = max(confidence, min(0.6, 0.5 + (heuristic_score - 5) / 10))
            heuristic_warning = 'Low ML confidence — using subject-based fallback.'

        # Recompute top_three to include heuristic candidates
        # Take top 3 from avg_proba but also include heuristic_choice if missing
        top_three = [(label_encoder.classes_[i], float(avg_proba[i])) for i in top_indices]
        if heuristic_choice not in [t[0] for t in top_three]:
            top_three[-1] = (heuristic_choice, confidence)

    return {
        "predicted_career": str(career),
        "confidence_percent": round(confidence * 100, 1),
        "top_3": [
            {"career": str(c), "confidence_percent": round(float(p) * 100, 1)}
            for c, p in top_three
        ],
        **({"warning": heuristic_warning} if heuristic_warning else {}),
    }
