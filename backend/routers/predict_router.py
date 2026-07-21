# backend/routers/predict_router.py
"""
Combined XGBoost + Gemini prediction endpoint.
POST /predict  → returns ML career, confidence, top-3, Gemini narrative, 
                 mentors and matched universities — all in one call.
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from google import genai
from google.genai import types

from backend.models.schemas import MLPredictResponse, PredictRequest, PredictResponse
from backend.models.ml_model import run_xgboost
from backend.auth import get_current_user
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL
from backend import database as db

router = APIRouter(prefix="/predict", tags=["Prediction"])

def _get_gemini():
    if not GOOGLE_API_KEY:
        return None
    return genai.Client(api_key=GOOGLE_API_KEY)

# ── University map (mirrors Streamlit app) ────────────────────────────────────
UNIVERSITY_MAP = {
    "Medicine & Health Sciences": [
        {"name": "University of Lagos (UNILAG)", "course": "Medicine & Surgery",
         "cutoff": "280+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "University of Ibadan (UI)", "course": "Medicine & Surgery",
         "cutoff": "300+", "location": "Ibadan, Oyo", "url": "https://ui.edu.ng"},
        {"name": "Obafemi Awolowo University", "course": "Medicine & Surgery",
         "cutoff": "275+", "location": "Ile-Ife, Osun", "url": "https://oauife.edu.ng"},
        {"name": "Ahmadu Bello University (ABU)", "course": "Medicine & Surgery",
         "cutoff": "270+", "location": "Zaria, Kaduna", "url": "https://abu.edu.ng"},
    ],
    "Engineering & Technology": [
        {"name": "University of Lagos (UNILAG)", "course": "Mechanical/Electrical Engineering",
         "cutoff": "240+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "Ahmadu Bello University (ABU)", "course": "Civil/Electrical Engineering",
         "cutoff": "230+", "location": "Zaria, Kaduna", "url": "https://abu.edu.ng"},
        {"name": "University of Nigeria Nsukka", "course": "Engineering",
         "cutoff": "220+", "location": "Nsukka, Enugu", "url": "https://unn.edu.ng"},
        {"name": "Covenant University", "course": "Engineering",
         "cutoff": "220+", "location": "Ota, Ogun", "url": "https://covenantuniversity.edu.ng"},
    ],
    "Computer Science & IT": [
        {"name": "University of Lagos (UNILAG)", "course": "Computer Science",
         "cutoff": "230+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "Covenant University", "course": "Computer Science",
         "cutoff": "220+", "location": "Ota, Ogun", "url": "https://covenantuniversity.edu.ng"},
        {"name": "Obafemi Awolowo University", "course": "Computer Science & Eng.",
         "cutoff": "220+", "location": "Ile-Ife, Osun", "url": "https://oauife.edu.ng"},
        {"name": "FUTA", "course": "Computer Science",
         "cutoff": "200+", "location": "Akure, Ondo", "url": "https://futa.edu.ng"},
    ],
    "Agriculture & Environmental Sciences": [
        {"name": "FUNAAB", "course": "Agricultural Science",
         "cutoff": "180+", "location": "Abeokuta, Ogun", "url": "https://funaab.edu.ng"},
        {"name": "Ahmadu Bello University (ABU)", "course": "Agriculture",
         "cutoff": "180+", "location": "Zaria, Kaduna", "url": "https://abu.edu.ng"},
        {"name": "University of Nigeria Nsukka", "course": "Agriculture",
         "cutoff": "180+", "location": "Nsukka, Enugu", "url": "https://unn.edu.ng"},
        {"name": "Michael Okpara University", "course": "Agriculture",
         "cutoff": "170+", "location": "Umudike, Abia", "url": "https://mouau.edu.ng"},
    ],
    "Law & Social Sciences": [
        {"name": "University of Lagos (UNILAG)", "course": "Law",
         "cutoff": "250+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "University of Nigeria Nsukka", "course": "Law",
         "cutoff": "230+", "location": "Nsukka, Enugu", "url": "https://unn.edu.ng"},
        {"name": "Obafemi Awolowo University", "course": "Law",
         "cutoff": "240+", "location": "Ile-Ife, Osun", "url": "https://oauife.edu.ng"},
        {"name": "University of Ibadan (UI)", "course": "Sociology / Political Science",
         "cutoff": "200+", "location": "Ibadan, Oyo", "url": "https://ui.edu.ng"},
    ],
    "Mass Communication & Media": [
        {"name": "University of Lagos (UNILAG)", "course": "Mass Communication",
         "cutoff": "200+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "University of Nigeria Nsukka", "course": "Mass Communication",
         "cutoff": "180+", "location": "Nsukka, Enugu", "url": "https://unn.edu.ng"},
        {"name": "Bayero University Kano (BUK)", "course": "Mass Communication",
         "cutoff": "180+", "location": "Kano", "url": "https://buk.edu.ng"},
        {"name": "University of Ibadan (UI)", "course": "Communication & Language Arts",
         "cutoff": "180+", "location": "Ibadan, Oyo", "url": "https://ui.edu.ng"},
    ],
    "Education & Humanities": [
        {"name": "University of Nigeria Nsukka", "course": "Education",
         "cutoff": "160+", "location": "Nsukka, Enugu", "url": "https://unn.edu.ng"},
        {"name": "University of Ibadan (UI)", "course": "Education",
         "cutoff": "170+", "location": "Ibadan, Oyo", "url": "https://ui.edu.ng"},
        {"name": "Ahmadu Bello University (ABU)", "course": "Education",
         "cutoff": "160+", "location": "Zaria, Kaduna", "url": "https://abu.edu.ng"},
        {"name": "Lagos State University (LASU)", "course": "Education",
         "cutoff": "150+", "location": "Lagos", "url": "https://lasu.edu.ng"},
    ],
    "Business & Finance": [
        {"name": "University of Lagos (UNILAG)", "course": "Accounting / Finance",
         "cutoff": "220+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "Covenant University", "course": "Business Administration",
         "cutoff": "200+", "location": "Ota, Ogun", "url": "https://covenantuniversity.edu.ng"},
        {"name": "Obafemi Awolowo University", "course": "Accounting",
         "cutoff": "210+", "location": "Ile-Ife, Osun", "url": "https://oauife.edu.ng"},
        {"name": "Lagos Business School (PAU)", "course": "Business Studies",
         "cutoff": "220+", "location": "Lagos", "url": "https://lbs.edu.ng"},
    ],
    "Entrepreneurship & Management": [
        {"name": "Covenant University", "course": "Business Management",
         "cutoff": "200+", "location": "Ota, Ogun", "url": "https://covenantuniversity.edu.ng"},
        {"name": "Lagos Business School (PAU)", "course": "Entrepreneurship",
         "cutoff": "220+", "location": "Lagos", "url": "https://lbs.edu.ng"},
        {"name": "University of Lagos (UNILAG)", "course": "Business Administration",
         "cutoff": "210+", "location": "Lagos", "url": "https://unilag.edu.ng"},
        {"name": "Nile University of Nigeria", "course": "Management Sciences",
         "cutoff": "180+", "location": "Abuja", "url": "https://nileuniversity.edu.ng"},
    ],
    "Creative Arts & Design": [
        {"name": "Yaba College of Technology", "course": "Art & Design",
         "cutoff": "160+", "location": "Lagos", "url": "https://yabatech.edu.ng"},
        {"name": "Obafemi Awolowo University", "course": "Fine & Applied Arts",
         "cutoff": "180+", "location": "Ile-Ife, Osun", "url": "https://oauife.edu.ng"},
        {"name": "University of Nigeria Nsukka", "course": "Fine & Applied Arts",
         "cutoff": "170+", "location": "Nsukka, Enugu", "url": "https://unn.edu.ng"},
        {"name": "Lagos State University (LASU)", "course": "Fine Arts",
         "cutoff": "160+", "location": "Lagos", "url": "https://lasu.edu.ng"},
    ],
}


def _fallback_narrative(name: str, career: str, confidence: float, top3: list) -> str:
    t2 = top3[1]["career"] if len(top3) > 1 else "an alternative"
    t3 = top3[2]["career"] if len(top3) > 2 else "another option"
    return f"""## 🌟 Your Career Recommendation Summary
Hi {name}! Based on your academic performance and assessments, your strongest career match is **{career}** with a confidence of **{confidence}%**.

## Recommended Career Path: {career}
This is one of the most in-demand fields in Nigeria today. Professionals work across private sector, federal agencies, and international organisations. Your assessment results show exactly the potential this field requires.

## Five Nigerian Career Roles to Explore
- **Core Specialist** — practise your craft at a federal agency or major private company
- **Consultant / Adviser** — work across multiple organisations solving problems
- **Research & Analysis** — contribute to academia, think-tanks, or government policy
- **Entrepreneurship** — start your own practice, firm, or business
- **NGO / Development Sector** — tackle national challenges with international organisations

## Your Competitive Strengths
- Strong assessment scores showing real aptitude for this career path
- Academic performance aligns well with {career} requirements
- Excellent foundation for WAEC and JAMB preparation

## Areas to Strengthen
Focus on building consistent performance across all subjects. Practice JAMB past questions daily and seek mentorship from professionals in your field of interest.

## Your Two Backup Career Options
**{t2}** is your second-best match — great if your interests evolve. **{t3}** is also a strong fit.

## Action Steps for Right Now
1. Research what professionals in **{career}** do in Nigeria — YouTube and LinkedIn are great starting points
2. Talk to your school counsellor about the right subjects for your SSS combination
3. Start practising JAMB past questions in your core subjects
4. Join a relevant school club or competition to build real experience"""


def _build_gemini_prompt(name: str, class_level: str, department: str,
                          top3: list, test_scores: dict) -> str:
    apt  = test_scores.get("aptitude_score_10", 5) * 10
    cog  = test_scores.get("cognitive_score_10", 5) * 10
    psy  = test_scores.get("psychometric_avg_5", 3.0) / 5 * 100
    sent = test_scores.get("sentiment_avg_5", 3.0) / 5 * 100
    dept_txt = f" ({department} dept.)" if department else ""

    return f"""You are a warm, expert career guidance counsellor at a top Nigerian secondary school.
Write a personalised career recommendation report for a student.

STUDENT PROFILE:
- Name: {name}
- Class: {class_level}{dept_txt}

4-TEST SCORES:
- Cognitive (logic & reasoning): {cog:.0f}%
- Aptitude (natural talents): {apt:.0f}%
- Psychometric (personality): {psy:.0f}%
- Sentiment (motivation & mindset): {sent:.0f}%

ML MODEL OUTPUT:
- Primary career: {top3[0]['career']} (confidence {top3[0]['confidence_percent']}%)
- 2nd option: {top3[1]['career'] if len(top3) > 1 else 'N/A'} ({top3[1]['confidence_percent'] if len(top3) > 1 else 0}%)
- 3rd option: {top3[2]['career'] if len(top3) > 2 else 'N/A'} ({top3[2]['confidence_percent'] if len(top3) > 2 else 0}%)

Write the report using EXACTLY these section headers:

## 🌟 Your Career Recommendation Summary
2–3 sentences directly addressing {name}, referencing their strongest results.

## Recommended Career Path: {top3[0]['career']}
Two paragraphs: (1) What this career involves in Nigeria — real sectors, agencies (NNPC, CBN, NAFDAC, NTA, MTN, etc.) (2) Exactly why this matches {name}'s data — mention actual scores.

## Five Nigerian Career Roles to Explore
5 specific job roles in demand in Nigeria, one line each with a Nigerian employer or context.

## Your Competitive Strengths
Three bullet points rooted in the actual data. Reference real scores.

## Areas to Strengthen
Two specific, encouraging, actionable suggestions.

## Your Two Backup Career Options
Short paragraph each on {top3[1]['career'] if len(top3) > 1 else 'Alternative A'} and {top3[2]['career'] if len(top3) > 2 else 'Alternative B'}.

## Action Steps for Right Now
Four numbered, concrete steps {name} can take TODAY as a {class_level} student in Nigeria. Include JAMB subject choices, WAEC prep, and free resources.

Tone: warm, direct, encouraging — like a trusted school counsellor talking to a Nigerian teenager.
Do NOT include university suggestions (handled separately). Total: ~650–800 words."""


@router.post("/", response_model=PredictResponse)
async def predict(
    student: PredictRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Combined endpoint: XGBoost prediction + Gemini narrative + mentors + universities.
    Saved to recommendations table for the logged-in user.
    """
    input_dict = student.model_dump()
    # Rename CRS/IRS field to match training column name
    if "christian_religious_studies_islamic_studies" in input_dict:
        input_dict["christian_religious_studies/islamic_studies"] = input_dict.pop(
            "christian_religious_studies_islamic_studies"
        )

    # ── 1. XGBoost prediction ─────────────────────────────────────────────────
    ml_result = run_xgboost(input_dict)
    top3 = ml_result["top_3"]
    career = ml_result["predicted_career"]
    confidence = ml_result["confidence_percent"]

    # ── 2. Universities ───────────────────────────────────────────────────────
    universities = UNIVERSITY_MAP.get(career, [])

    # ── 3. Gemini narrative ───────────────────────────────────────────────────
    test_scores = {
        "aptitude_score_10":  student.aptitude_score_10,
        "cognitive_score_10": student.cognitive_score_10,
        "psychometric_avg_5": student.psychometric_avg_5,
        "sentiment_avg_5":    student.sentiment_avg_5,
    }
    gemini = _get_gemini()
    try:
        if gemini is None:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        prompt = _build_gemini_prompt(
            name=current_user["full_name"],
            class_level=current_user["class_level"],
            department=student.department,
            top3=top3,
            test_scores=test_scores,
        )
        resp = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=1200, temperature=0.7),
        )
        narrative = resp.text
    except Exception:
        narrative = _fallback_narrative(
            current_user["full_name"], career, confidence, top3
        )

    # ── 4. LinkedIn mentors via Gemini ────────────────────────────────────────
    mentor_prompt = (
        f'List 4 realistic Nigerian professionals in {career}. '
        'Return a JSON array only. Each item is a string: '
        '"[Full Name] — [Job Title] at [Nigerian Organisation] — [One sentence: why they are a good mentor]" '
        'Return ONLY the JSON array. No markdown, no extra text.'
    )
    try:
        if gemini is None:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        mr = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=mentor_prompt,
            config=types.GenerateContentConfig(max_output_tokens=300, temperature=0.6),
        )
        raw = mr.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        mentors = json.loads(raw)
    except Exception:
        mentors = [
            f"Dr. Chukwuemeka Eze — Senior Professional at NNPC — 15+ years experience mentoring youth",
            f"Mrs. Ngozi Adeyemi — Director, Federal Ministry — Passionate about youth career development",
            f"Mr. Oluwaseun Bello — Lead Consultant, Lagos — Known for mentoring secondary school students",
            f"Prof. Amina Suleiman — University of Abuja — Active researcher and student career advocate",
        ]

    # ── 5. Save to DB ─────────────────────────────────────────────────────────
    db.save_recommendation(
        user_id=current_user["id"],
        career_path=career,
        confidence=confidence,
        universities=universities,
        linkedin_mentors=mentors,
        narrative=narrative,
        top3=top3,
    )
    # Clear old chat history so it resets with new recommendation
    db.clear_chat_history(current_user["id"])

    return PredictResponse(
        predicted_career=career,
        confidence_percent=confidence,
        top_3=top3,
        narrative=narrative,
        mentors=mentors,
        universities=universities,
        warning=ml_result.get("warning"),
    )


@router.post("/ml", response_model=MLPredictResponse)
def predict_ml(student: PredictRequest):
    """Public ML-only endpoint used by Streamlit and quick integrations."""
    input_dict = student.model_dump()
    if "christian_religious_studies_islamic_studies" in input_dict:
        input_dict["christian_religious_studies/islamic_studies"] = input_dict.pop(
            "christian_religious_studies_islamic_studies"
        )

    ml_result = run_xgboost(input_dict)
    career = ml_result["predicted_career"]
    return MLPredictResponse(
        predicted_career=career,
        confidence_percent=ml_result["confidence_percent"],
        top_3=ml_result["top_3"],
        universities=UNIVERSITY_MAP.get(career, []),
        warning=ml_result.get("warning"),
    )
