# backend/models/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str
    dob: str                     # ISO date string e.g. "2005-03-15"
    class_level: str             # "SSS 1" | "SSS 2" | "SSS 3" | "JSS 2" etc.
    department: Optional[str] = None   # "Science" | "Arts" | "Commercial"
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


# ── Prediction ────────────────────────────────────────────────────────────────

class CareerMatch(BaseModel):
    career: str
    confidence_percent: float


class PredictRequest(BaseModel):
    gender: Optional[str] = "Unknown"
    age: Optional[int] = None
    school_type: Optional[str] = "Unknown"
    department: str
    academic_strength: Optional[str] = "Unknown"
    best_subject_category: Optional[str] = "Unknown"
    confidence_level: Optional[str] = "Unknown"
    career_influence: Optional[str] = "Unknown"
    # Subject grades (A-F or UNKNOWN)
    mathematics: Optional[str] = "UNKNOWN"
    english: Optional[str] = "UNKNOWN"
    civic_education: Optional[str] = "UNKNOWN"
    physics: Optional[str] = "UNKNOWN"
    chemistry: Optional[str] = "UNKNOWN"
    biology: Optional[str] = "UNKNOWN"
    further_mathematics: Optional[str] = "UNKNOWN"
    agricultural_science: Optional[str] = "UNKNOWN"
    geography: Optional[str] = "UNKNOWN"
    technical_drawing: Optional[str] = "UNKNOWN"
    computer_studies: Optional[str] = "UNKNOWN"
    yoruba: Optional[str] = "UNKNOWN"
    igbo_hausa: Optional[str] = "UNKNOWN"
    data_processing: Optional[str] = "UNKNOWN"
    literature_in_english: Optional[str] = "UNKNOWN"
    christian_religious_studies_islamic_studies: Optional[str] = "UNKNOWN"
    creative_arts: Optional[str] = "UNKNOWN"
    economics: Optional[str] = "UNKNOWN"
    financial_accounting: Optional[str] = "UNKNOWN"
    commerce: Optional[str] = "UNKNOWN"
    government: Optional[str] = "UNKNOWN"
    marketing: Optional[str] = "UNKNOWN"
    # Test scores (0–10 scale from frontend)
    aptitude_score_10: Optional[float] = 5.0
    cognitive_score_10: Optional[float] = 5.0
    psychometric_avg_5: Optional[float] = 3.0
    sentiment_avg_5: Optional[float] = 3.0
    # WAEC / academic metadata
    waec_credits: Optional[float] = 5.0
    cgpa: Optional[float] = 0.0
    course_alignment: Optional[int] = 0
    waec_year: Optional[int] = 2023


class PredictResponse(BaseModel):
    predicted_career: str
    confidence_percent: float
    top_3: List[CareerMatch]
    narrative: str
    mentors: List[str]
    universities: List[Dict[str, Any]]
    warning: Optional[str] = None


class MLPredictResponse(BaseModel):
    predicted_career: str
    confidence_percent: float
    top_3: List[CareerMatch]
    universities: List[Dict[str, Any]]
    warning: Optional[str] = None


# ── Academic Results ──────────────────────────────────────────────────────────

class AcademicResultIn(BaseModel):
    result_type: str      # "First Term" | "Second Term" | "Third Term"
    subject: str
    score: float = Field(ge=0, le=100)
    exam_date: Optional[str] = None


class AcademicResultOut(BaseModel):
    id: int
    result_type: str
    subject: str
    score: float
    exam_date: str
    uploaded_at: str


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSubmitRequest(BaseModel):
    test_type: str                  # "cognitive" | "aptitude" | "psychometric" | "sentiment"
    answers: Dict[str, Any]         # {question_id: selected answer text or answer_index}
    department: Optional[str] = "Science"


class TestScoreResponse(BaseModel):
    test_type: str
    score: float
    message: str


class CompletedTestsResponse(BaseModel):
    completed: List[str]
    scores: Dict[str, float]


# ── Recommendation ────────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    career_path: str
    confidence: float
    top3: List[Any]
    universities: List[Dict[str, Any]]
    mentors: List[str]
    narrative: str
    generated_at: str


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    role: str
    message: str
