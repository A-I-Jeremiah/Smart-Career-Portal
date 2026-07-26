# backend/models/ml_model.py
"""
XGBoost model loader and prediction logic.
The saved model is a full sklearn Pipeline (ColumnTransformer + XGBClassifier),
so all preprocessing happens inside model.predict().

New model (trained on Nigerian Career Survey dataset) features:
  - Categorical: gender, school_type, department, academic_strength,
                 best_subject_category, confidence_level, career_influence,
                 + subject grades (A–F per subject column)
  - Numeric: none (cgpa, waec_credits, waec_year, jamb_score were from the
             university-student survey and are NOT expected by this model)

Test scores (aptitude, cognitive, psychometric, sentiment) collected from the
frontend are NOT model features. They are used:
  1. Post-hoc: to apply a small bounded adjustment to the ML probability
               output (±10% max, re-normalised) that reflects how well the
               student's diagnostic profile aligns with each career cluster.
  2. Gemini prompt: passed directly for personalised narrative generation.
"""
import numpy as np
import pandas as pd
import joblib
from backend.config import DEPT_TOP_K, MODEL_PATH, LABEL_ENCODER_PATH
from backend.models.department_filter import (
    apply_department_alignment,
    build_top_k,
    filter_careers_for_department,
    normalize_department,
)

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


# ── Department subject filtering ─────────────────────────────────────────────
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

# No numeric features — cgpa, waec_credits, waec_year, jamb_score came from
# the university-student survey and are not applicable to secondary school users.
NUMERICAL_COLS: list[str] = []

FEATURES = CATEGORICAL_COLS + NUMERICAL_COLS

GRADE_MAP = {"A": 8, "B": 6, "C": 5, "D": 3, "E": 2, "F": 1, "UNKNOWN": 5}

# ── Department-aware heuristic map ────────────────────────────────────────────
CAREER_SUBJECT_MAP = {
    "Computer Science & IT": [
        "computer_studies", "mathematics", "further_mathematics", "physics",
    ],
    "Engineering & Technology": [
        "physics", "mathematics", "technical_drawing", "chemistry",
    ],
    "Medicine & Health Sciences": [
        "biology", "chemistry", "english", "physics",
    ],
    "Agriculture & Environmental Sciences": [
        "agricultural_science", "biology", "geography", "chemistry",
    ],
    "Business & Finance": [
        "economics", "financial_accounting", "mathematics", "commerce",
    ],
    "Entrepreneurship & Management": [
        "economics", "financial_accounting", "commerce", "marketing",
    ],
    "Creative Arts & Design": [
        "creative_arts", "literature_in_english", "english", "marketing",
    ],
    "Law & Social Sciences": [
        "government", "literature_in_english", "english", "economics",
    ],
    "Mass Communication & Media": [
        "literature_in_english", "english", "creative_arts", "government",
    ],
    "Education & Humanities": [
        "english", "literature_in_english", "government",
        "christian_religious_studies/islamic_studies",
    ],
}

# ── Test-score → career affinity weights ─────────────────────────────────────
# Maps each career cluster to which diagnostic score most signals aptitude for
# it. Values are weights (0.0–1.0) for aptitude_10, cognitive_10, psy_5, sent_5.
# Used only in apply_test_score_adjustment() — NOT passed to the ML model.
_TEST_AFFINITY: dict[str, dict[str, float]] = {
    "Computer Science & IT":              {"aptitude": 1.0, "cognitive": 1.0, "psychometric": 0.2, "sentiment": 0.2},
    "Engineering & Technology":           {"aptitude": 1.0, "cognitive": 0.8, "psychometric": 0.2, "sentiment": 0.2},
    "Medicine & Health Sciences":         {"aptitude": 0.8, "cognitive": 1.0, "psychometric": 0.4, "sentiment": 0.3},
    "Agriculture & Environmental Sciences":{"aptitude": 0.5, "cognitive": 0.4, "psychometric": 0.5, "sentiment": 0.5},
    "Business & Finance":                 {"aptitude": 0.5, "cognitive": 0.8, "psychometric": 0.6, "sentiment": 0.4},
    "Entrepreneurship & Management":      {"aptitude": 0.4, "cognitive": 0.5, "psychometric": 1.0, "sentiment": 0.8},
    "Creative Arts & Design":             {"aptitude": 0.3, "cognitive": 0.3, "psychometric": 0.8, "sentiment": 1.0},
    "Law & Social Sciences":              {"aptitude": 0.6, "cognitive": 1.0, "psychometric": 0.7, "sentiment": 0.5},
    "Mass Communication & Media":         {"aptitude": 0.3, "cognitive": 0.4, "psychometric": 0.8, "sentiment": 1.0},
    "Education & Humanities":             {"aptitude": 0.4, "cognitive": 0.5, "psychometric": 1.0, "sentiment": 0.8},
}

# Diagnostic thresholds that trigger a positive signal
_APT_HIGH   = 7.0   # out of 10
_COG_HIGH   = 7.0   # out of 10
_PSY_HIGH   = 3.5   # out of 5
_SENT_HIGH  = 3.5   # out of 5
_MAX_BOOST  = 0.10  # ±10 % cap per career per dimension


def apply_test_score_adjustment(
    proba: np.ndarray,
    class_labels: list[str],
    test_scores: dict,
) -> np.ndarray:
    """
    Apply a small, bounded post-hoc adjustment to ML class probabilities using
    supplementary diagnostic test scores.

    Only applies a multiplier when a score clearly exceeds its threshold
    (≥ 70 % for aptitude/cognitive, ≥ 70 % for psychometric/sentiment).
    Maximum shift per career is ±10 %, and the array is always re-normalised
    so probabilities still sum to 1.0.

    Parameters
    ----------
    proba        : 1-D numpy array of class probabilities from the XGBoost model.
    class_labels : list of career label strings matching proba indices.
    test_scores  : dict with optional keys:
                   aptitude_score_10, cognitive_score_10,
                   psychometric_avg_5, sentiment_avg_5.

    Returns
    -------
    Adjusted (and re-normalised) 1-D numpy array.
    """
    if not test_scores:
        return proba

    apt  = float(test_scores.get("aptitude_score_10")  or 0.0)
    cog  = float(test_scores.get("cognitive_score_10") or 0.0)
    psy  = float(test_scores.get("psychometric_avg_5") or 0.0)
    sent = float(test_scores.get("sentiment_avg_5")    or 0.0)

    # Normalise scores to 0-1 relative to their scales
    apt_n  = apt  / 10.0
    cog_n  = cog  / 10.0
    psy_n  = psy  / 5.0
    sent_n = sent / 5.0

    # Only signal when score is genuinely above threshold
    apt_signal  = max(0.0, apt_n  - (_APT_HIGH  / 10.0))
    cog_signal  = max(0.0, cog_n  - (_COG_HIGH  / 10.0))
    psy_signal  = max(0.0, psy_n  - (_PSY_HIGH  / 5.0))
    sent_signal = max(0.0, sent_n - (_SENT_HIGH / 5.0))

    # If no score exceeds its threshold, skip adjustment entirely
    if not any([apt_signal, cog_signal, psy_signal, sent_signal]):
        return proba

    adjusted = proba.copy().astype(float)
    for i, career in enumerate(class_labels):
        affinity = _TEST_AFFINITY.get(career, {})
        boost = (
            apt_signal  * affinity.get("aptitude",    0.0)
            + cog_signal  * affinity.get("cognitive",   0.0)
            + psy_signal  * affinity.get("psychometric", 0.0)
            + sent_signal * affinity.get("sentiment",    0.0)
        )
        # Cap the boost at ±MAX_BOOST of original probability
        boost = min(boost, _MAX_BOOST)
        adjusted[i] = max(0.0, adjusted[i] * (1.0 + boost))

    total = adjusted.sum()
    if total > 0:
        adjusted /= total
    return adjusted


def run_xgboost(input_data: dict, test_scores: dict | None = None) -> dict:
    """
    Run XGBoost prediction with ensemble, department alignment, and
    department-aware heuristic fallback.

    Parameters
    ----------
    input_data  : Feature dict. Must NOT contain test score keys — those are
                  stripped by the router before calling this function.
    test_scores : Optional dict with supplementary diagnostic scores
                  (aptitude_score_10, cognitive_score_10, psychometric_avg_5,
                  sentiment_avg_5). Used only for post-hoc probability
                  adjustment — never passed to model.predict_proba().

    Returns
    -------
    dict: predicted_career, confidence_percent, top_3, optional warning.
    """
    df = pd.DataFrame([input_data])
    df.columns = (
        df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
    )

    department = normalize_department(
        str(df.get("department", pd.Series(["Unknown"]))[0]).strip()
    )
    allowed = DEPARTMENT_SUBJECTS.get(department, ALL_SUBJECT_COLS)

    defaults: dict = {
        "gender": "Unknown", "school_type": "Unknown", "department": department,
        "academic_strength": "Unknown", "best_subject_category": "Unknown",
        "confidence_level": "Unknown", "career_influence": "Unknown",
    }
    for col in ALL_SUBJECT_COLS:
        defaults[col] = "UNKNOWN"

    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    # Department subject filtering — zero out irrelevant subjects
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

    # Align with training features dynamically based on the loaded model.
    # The user's trained model pipeline may expect legacy columns or newly added features.
    if hasattr(_model, "feature_names_in_"):
        expected_model_cols = list(_model.feature_names_in_)
        
        # Handle the slash vs underscore mismatch in CRS/IRS
        if "christian_religious_studies_islamic_studies" in expected_model_cols and "christian_religious_studies/islamic_studies" in df.columns:
            df.rename(columns={"christian_religious_studies/islamic_studies": "christian_religious_studies_islamic_studies"}, inplace=True)
            
        for col in expected_model_cols:
            if col not in df.columns:
                # Heuristic padding based on name
                if col in CATEGORICAL_COLS or "career" in col or "influence" in col or "strength" in col:
                    df[col] = "Unknown"
                elif col in ALL_SUBJECT_COLS or col == "french":
                    df[col] = 5.0  # Grade 'UNKNOWN' maps to 5
                else:
                    df[col] = 0.0
                    
        df = df[expected_model_cols]
    else:
        # Fallback padding if feature_names_in_ is missing
        legacy_cols = [
            "age", "cgpa", "waec_year", "waec_credits", "course_alignment",
            "aptitude_score_10", "cognitive_score_10", "psychometric_avg_5", "sentiment_avg_5",
            "current_career_satisfaction", "french", "intended_career_path", "jamb_score",
            "christian_religious_studies_islamic_studies"
        ]
        if "christian_religious_studies/islamic_studies" in df.columns:
            df.rename(columns={"christian_religious_studies/islamic_studies": "christian_religious_studies_islamic_studies"}, inplace=True)
            
        expected_cols = FEATURES + legacy_cols
        
        for col in expected_cols:
            if col not in df.columns:
                if col in CATEGORICAL_COLS or "career" in col:
                    df[col] = "Unknown"
                else:
                    df[col] = 0.0
        
        # Retain only the columns the model expects
        df = df[[c for c in expected_cols if c in df.columns]]

    # Cast dtypes dynamically based on columns that were retained
    if NUMERICAL_COLS:
        for col in NUMERICAL_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
                
    astype_dict = {c: "float64" if c in NUMERICAL_COLS else "object" for c in df.columns}
    df = df.astype(astype_dict)

    # Guard: F in Maths or English → immediate block
    if df.at[0, "mathematics"] == 1 or df.at[0, "english"] == 1:
        return {
            "predicted_career": (
                "None — improve Mathematics and English to get recommendations."
            ),
            "confidence_percent": 0.0,
            "top_3": [],
            "warning": "Student has F in Mathematics or English.",
        }

    # ── Load model artifacts lazily ───────────────────────────────────────────
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
    except Exception as e:
        return {
            "predicted_career": "Unknown",
            "confidence_percent": 0.0,
            "top_3": [],
            "warning": str(e),
        }

    # Bias-reduction ensemble: average with demographic-anonymised prediction
    df_no_demo = df.copy()
    for dcol in ("gender", "school_type"):
        if dcol in df_no_demo.columns:
            df_no_demo[dcol] = "Unknown"

    try:
        proba_no_demo = _model.predict_proba(df_no_demo)[0]
    except Exception:
        proba_no_demo = proba_full

    avg_proba = (proba_full + proba_no_demo) / 2.0
    class_labels = list(_label_encoder.classes_)

    # Department alignment post-processing
    alignment = apply_department_alignment(avg_proba, class_labels, department)
    final_proba = alignment.adjusted_proba

    # Post-hoc test score adjustment (supplementary signal — does not enter model)
    if test_scores:
        final_proba = apply_test_score_adjustment(final_proba, class_labels, test_scores)

    top_idx = int(np.argmax(final_proba))
    career = class_labels[top_idx]
    confidence = float(final_proba[top_idx])
    top_three = build_top_k(final_proba, class_labels, k=DEPT_TOP_K)

    warnings: list[str] = []
    if alignment.warning:
        warnings.append(alignment.warning)

    # Department-aware heuristic fallback when ML confidence is low
    if confidence < 0.40:
        subject_scores = {}
        for col in ALL_SUBJECT_COLS:
            check_col = "christian_religious_studies_islamic_studies" if col == "christian_religious_studies/islamic_studies" and "christian_religious_studies_islamic_studies" in df.columns else col
            subject_scores[col] = float(df.at[0, check_col]) if check_col in df.columns else 5.0
        allowed_careers = filter_careers_for_department(
            CAREER_SUBJECT_MAP.keys(), department, include_secondary=True
        )

        career_scores = []
        for c in allowed_careers:
            subs = CAREER_SUBJECT_MAP[c]
            vals = [subject_scores.get(s, 5.0) for s in subs]
            career_scores.append((c, float(np.mean(vals))))
        career_scores.sort(key=lambda x: x[1], reverse=True)

        if career_scores:
            heuristic_choice, heuristic_score = career_scores[0]
            if heuristic_choice != career and heuristic_score >= 5.5:
                career = heuristic_choice
                confidence = max(confidence, min(0.6, 0.5 + (heuristic_score - 5) / 10))
                warnings.append(
                    "Low ML confidence — using department-aware subject fallback."
                )
                top_three = build_top_k(final_proba, class_labels, k=DEPT_TOP_K)
                if heuristic_choice not in [t[0] for t in top_three]:
                    top_three[-1] = (heuristic_choice, confidence)

    return {
        "predicted_career": str(career),
        "confidence_percent": round(confidence * 100, 1),
        "top_3": [
            {"career": str(c), "confidence_percent": round(float(p) * 100, 1)}
            for c, p in top_three
        ],
        **({"warning": " ".join(warnings)} if warnings else {}),
    }
