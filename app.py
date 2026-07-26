import pandas as pd
import datetime
import os
import json
import sqlite3
from pathlib import Path
from random import Random

from collections import defaultdict
import bcrypt
import numpy as np
import requests
import streamlit as st
try:
    from streamlit_option_menu import option_menu
except ImportError:
    option_menu = None
from google import genai
from google.genai import types
from dotenv import load_dotenv
import re


# Load environment variables from .env file
load_dotenv()
    
@st.fragment(run_every=30)  # Runs every 30 seconds to keep WebSocket alive
def keep_alive():
    """Prevents sudden logout by maintaining active connection"""
    st.empty()  # Invisible element that keeps the session alive

# ====================== GEMINI CONFIG ======================
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
gemini_client  = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL   = "gemini-3.1-flash-lite"
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "https://smart-career-app-4702.onrender.com").rstrip("/")
QUESTIONS_PATH = Path(__file__).resolve().parent / "backend" / "questions_engine" / "assessment_questions.json"

# ====================== ML CONFIG ======================
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml", "models")
ML_READY  = False
ml_models = {}

try:
    import joblib
    _req = ["xgb_model.pkl","scaler.pkl","le_career.pkl","feature_names.pkl",
            "le_class_level.pkl","le_department.pkl","le_strength_level.pkl",
            "le_performance_trend.pkl","le_best_subject.pkl","le_weak_subject.pkl"]
    if all(os.path.exists(os.path.join(MODEL_DIR, f)) for f in _req):
        ml_models = {
            "xgb":          joblib.load(os.path.join(MODEL_DIR, "xgb_model.pkl")),
            "scaler":       joblib.load(os.path.join(MODEL_DIR, "scaler.pkl")),
            "le_career":    joblib.load(os.path.join(MODEL_DIR, "le_career.pkl")),
            "le_class":     joblib.load(os.path.join(MODEL_DIR, "le_class_level.pkl")),
            "le_dept":      joblib.load(os.path.join(MODEL_DIR, "le_department.pkl")),
            "le_strength":  joblib.load(os.path.join(MODEL_DIR, "le_strength_level.pkl")),
            "le_trend":     joblib.load(os.path.join(MODEL_DIR, "le_performance_trend.pkl")),
            "le_best":      joblib.load(os.path.join(MODEL_DIR, "le_best_subject.pkl")),
            "le_weak":      joblib.load(os.path.join(MODEL_DIR, "le_weak_subject.pkl")),
            "feature_names":joblib.load(os.path.join(MODEL_DIR, "feature_names.pkl")),
        }
        ML_READY = True
except Exception:
    pass

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Smart Career Portal", page_icon="🎓", layout="wide")

# ====================== CUSTOM CSS ======================
st.markdown("""
<style>
    body { background-color: #f5f6fa; }
    .title   { font-size: 30px; font-weight: 800; text-align: center; margin-bottom: 8px; }
    .subtitle{ font-size: 14px; color: gray; text-align: center; margin-bottom: 20px; }
    .caption { font-size: 12px; text-align: center; color: gray; margin-bottom: 30px; }

    /* Remove standard Streamlit form borders and background */
    div[data-testid="stForm"] {
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
    }

    /* Beautiful custom container for our login form */
    .auth-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 10px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        margin-top: 5px;
    }

    /* Centered heading styles */
    .auth-title {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        text-align: center;
        margin-bottom: 24px !important;
    }

    /* Style all standard inputs inside the auth area */
    .stTextInput input {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
        border-radius: 8px !important;  
        transition: all 0.2s ease !important;
    }

    /* Give the login button a broad, premium aesthetic */
    div[data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        background: linear-gradient(135deg, #1e3a8a 0%, #2d6cdf 100%) !important;
        color: white !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(45, 108, 223, 0.2) !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(45, 108, 223, 0.3) !important;
    }
    .footer { text-align: center; font-size: 13px; margin-top: 15px; }
    
    /* Remove default Streamlit top padding */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem !important; }
    
    /* ENsure the sidebar trigger button remains visible and interactive */
    div[data-testid="StHeader"] {
        background-color: transparent;
        background: transparent;
    }
    button[data-testid="stSidebarCollapseButton"] {
        visibility: visible;
        z-index: 999999;
    }
    
    /* Modernized Hero Header Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        padding: 24px 20px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.2);
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .hero-title {
        color: #ffffff !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        margin-bottom: 6px !important;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: #93c5fd !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        margin: 0 !important;
        opacity: 0.9;
    }
    /* Polished Title Area */
    .dash-header {
        text-align: center;
        margin-bottom: 25px;
    }
    .dash-welcome {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        margin-bottom: 4px !important;
    }
    .dash-meta {
        font-size: 0.95rem !important;
        color: #64748b !important;
    }
    /* Main metric cards */
    .dashboard-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 15px;
    }
    .dashboard-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    .card-icon {
        font-size: 2rem;
        margin-bottom: 8px;
    }
    .card-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e293b;
        line-height: 1.2;
        margin: 8px 0;
    }
    .card-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* How it works step cards */
    .step-card {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 15px 20px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
    .step-header {
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 4px;
    }
    .step-desc {
        font-size: 0.9rem;
        color: #64748b;
    }
            
    /* ====================== SEGMENTED CONTROL STYLING ====================== */
        div[data-testid="stSegmentedControl"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 4px;
        border: 1px solid #e0e0e0;
    }

    /* Individual segments */
    div[data-testid="stSegmentedControl"] button {
        border-radius: 8px !important;
        padding: 6px 14px;
        font-weight: 500;
        color: #555;
        transition: all 0.2s ease-in-out;
    }

    /* Hover effect */
    div[data-testid="stSegmentedControl"] button:hover {
        background-color: #f0f0f0;
        color: #222;
    }

    /* Active segment */
    div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
            
    /* ====================== UPLOAD TAB SPECIFIC STYLES ====================== */

    /* Container for the left input panel */
    .input-panel-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }

    .panel-title {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        margin-bottom: 16px !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Make custom action buttons pop */
    div.stButton > button:first-child {
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        transition: all 0.2s ease !important;
    }

    /* Accent primary button color (Add Score) */
    .add-btn button {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%) !important;
        color: white !important;
        border: none !important;
    }
    .add-btn button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
    }

    /* Secondary danger button color (Clear All) */
    .clear-btn button {
        background-color: #fff5f5 !important;
        color: #e53e3e !important;
        border: 1px solid #fed7d7 !important;
    }
    .clear-btn button:hover {
        background-color: #fff5f5 !important;
        border-color: #e53e3e !important;
        box-shadow: 0 2px 8px rgba(229, 62, 62, 0.1) !important;
    }

    /* Micro metric chip styles for the uploaded data summary */
    .summary-chip {
        background-color: #f1f5f9;
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .summary-chip:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    .chip-val {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0f172a;
    }
    .chip-lbl {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 600;
    }

    .upload-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 30px;
        padding: 5px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
        margin-bottom: 10px;
        margin-top: 10px;
    }
    .upload-section-title {
        font-size: 2.2rem;
        font-weight: 800;
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 16px;
        margin-bottom: 18px;
    }
    .upload-section-title h3 {
        margin: 0;
        font-size: 1.1rem;
        color: #0f172a;
        font-weight: 800;
    }
    .upload-section-title subtitle {
        font-size: 0.5rem;}
    .upload-section-title span {
        color: #475569;
        font-size: 2.0rem;
    }
    .file-hint {
        background: #f8fafc;
        border: 2px solid #dbeafe;
        border-radius: 14px;
        padding: 10px 10px;
        color: #475569;
        margin-top: 5px;
        line-height: 1.7;
    }
    .ledger-header {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e293b;
        margin: 20px 0 10px;
    }
    div[data-testid="stFileUploader"] {
        background: rgba(59, 130, 246, 0.05);
        border: 1px dashed #93c5fd;
        border-radius: 18px;
        padding: 8px 10px;
    }
    div[data-testid="stFileUploader"] > div {
        color: #0f172a;
    }

    /* ── Test tab ─────────────────────────────────────── */
    .test-progress-bar {
        background:#e0e7ff; border-radius:10px; height:12px;
        margin-bottom:8px; overflow:hidden;
    }
    .test-progress-fill {
        background:linear-gradient(90deg,#2d6cdf,#5b8dee);
        height:100%; border-radius:10px; transition:width 0.4s ease;
    }
    .test-header {
        background:linear-gradient(135deg,#2d6cdf 0%,#1a3c8f 100%);
        color:white; padding:18px 24px; border-radius:14px; margin-bottom:20px;
    }
    .test-header h2 { margin:0; font-size:20px; }
    .test-header p  { margin:4px 0 0; font-size:13px; opacity:0.85; }
    .q-card {
        background:white; border-radius:12px; border-left:5px solid #2d6cdf;
        padding:16px 20px; margin-bottom:14px;
        box-shadow:0 2px 10px rgba(0,0,0,0.06);
    }
    .q-num  { font-size:11px; font-weight:700; color:#2d6cdf;
              text-transform:uppercase; letter-spacing:0.05em; }
    .q-text { font-size:15px; font-weight:600; color:#1a1a2e; margin-top:4px; }
    .completed-badge {
        display:inline-block; background:#d1fae5; color:#065f46;
        border-radius:20px; padding:4px 14px; font-size:13px; font-weight:600; margin:4px;
    }
    .locked-badge {
        display:inline-block; background:#fef3c7; color:#92400e;
        border-radius:20px; padding:4px 14px; font-size:13px; font-weight:600; margin:4px;
    }
    .active-badge {
        display:inline-block; background:#dbeafe; color:#1e40af;
        border-radius:20px; padding:4px 14px; font-size:13px; font-weight:600; margin:4px;
    }

    /* ── Recommendations ─────────────────────────────── */
    .rec-hero {
        background:linear-gradient(135deg,#1a3c8f 0%,#2d6cdf 60%,#5b8dee 100%);
        color:white; padding:28px 32px; border-radius:18px; margin-bottom:24px; text-align:center;
    }
    .rec-hero h1 { margin:0; font-size:26px; }
    .rec-hero p  { margin:8px 0 0; font-size:14px; opacity:0.9; }
    .uni-card {
        background:#f0f7ff; border-radius:12px; padding:14px 18px;
        margin-bottom:10px; border-left:4px solid #10b981;
    }
    .score-bar-bg {
        background:#e0e7ff; border-radius:8px; height:10px;
        overflow:hidden; margin-top:4px;
    }
    .score-bar-fill {
        background:linear-gradient(90deg,#2d6cdf,#5b8dee);
        height:100%; border-radius:8px;
    }

    /* ── Chatbot ─────────────────────────────────────── */
    .chat-user {
        background:#2d6cdf; color:white; border-radius:14px 14px 4px 14px;
        padding:10px 16px; margin:8px 0 8px auto; max-width:72%;
        font-size:14px; width:fit-content; margin-left:auto;
    }
    .chat-ai {
        background:white; color:#1a1a2e; border-radius:14px 14px 14px 4px;
        padding:10px 16px; margin:8px 0; max-width:82%;
        box-shadow:0 2px 8px rgba(0,0,0,0.08); font-size:14px; width:fit-content;
    }
</style>
""", unsafe_allow_html=True)


# ====================== CONSTANTS ======================
DEPARTMENT_SUBJECTS = {
    "Science":    ["English","Mathematics", "Civic Education","Physics","Chemistry","Biology",
                   "Further Mathematics","Agricultural Science","Computer Science","Geography"],
    "Arts":       ["English","Mathematics","Literature in English","Government",
                   "CRS/IRK","History","Economics","Yoruba/Hausa/Igbo","Civic Education"],
    "Commercial": ["English","Mathematics","Civic Education","Economics","Accounting","Commerce",
                   "Business Studies","Government","Office Practice","Insurance"],
}

UNIVERSITY_MAP = {
    "Medicine & Health Sciences": [
        {"name":"University of Lagos (UNILAG)","course":"Medicine & Surgery","cutoff":"280+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"University of Ibadan (UI)",   "course":"Medicine & Surgery","cutoff":"300+","location":"Ibadan, Oyo","url":"https://ui.edu.ng"},
        {"name":"Obafemi Awolowo University",  "course":"Medicine & Surgery","cutoff":"275+","location":"Ile-Ife, Osun","url":"https://oauife.edu.ng"},
        {"name":"Ahmadu Bello University (ABU)","course":"Medicine & Surgery","cutoff":"270+","location":"Zaria, Kaduna","url":"https://abu.edu.ng"},
    ],
    "Engineering & Technology": [
        {"name":"University of Lagos (UNILAG)", "course":"Mechanical/Electrical Engineering","cutoff":"240+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"Ahmadu Bello University (ABU)","course":"Civil/Electrical Engineering","cutoff":"230+","location":"Zaria, Kaduna","url":"https://abu.edu.ng"},
        {"name":"University of Nigeria Nsukka", "course":"Engineering","cutoff":"220+","location":"Nsukka, Enugu","url":"https://unn.edu.ng"},
        {"name":"Covenant University",          "course":"Engineering","cutoff":"220+","location":"Ota, Ogun","url":"https://covenantuniversity.edu.ng"},
    ],
    "Computer Science & IT": [
        {"name":"University of Lagos (UNILAG)","course":"Computer Science","cutoff":"230+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"Covenant University",         "course":"Computer Science","cutoff":"220+","location":"Ota, Ogun","url":"https://covenantuniversity.edu.ng"},
        {"name":"Obafemi Awolowo University",  "course":"Computer Science & Eng.","cutoff":"220+","location":"Ile-Ife, Osun","url":"https://oauife.edu.ng"},
        {"name":"Federal University of Technology Akure (FUTA)","course":"Computer Science","cutoff":"200+","location":"Akure, Ondo","url":"https://futa.edu.ng"},
    ],
    "Agriculture & Environmental Sciences": [
        {"name":"FUNAAB","course":"Agricultural Science","cutoff":"180+","location":"Abeokuta, Ogun","url":"https://funaab.edu.ng"},
        {"name":"Ahmadu Bello University (ABU)","course":"Agriculture","cutoff":"180+","location":"Zaria, Kaduna","url":"https://abu.edu.ng"},
        {"name":"University of Nigeria Nsukka","course":"Agriculture","cutoff":"180+","location":"Nsukka, Enugu","url":"https://unn.edu.ng"},
        {"name":"Michael Okpara University","course":"Agriculture","cutoff":"170+","location":"Umudike, Abia","url":"https://mouau.edu.ng"},
    ],
    "Law & Social Sciences": [
        {"name":"University of Lagos (UNILAG)","course":"Law","cutoff":"250+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"University of Nigeria Nsukka","course":"Law","cutoff":"230+","location":"Nsukka, Enugu","url":"https://unn.edu.ng"},
        {"name":"Obafemi Awolowo University",  "course":"Law","cutoff":"240+","location":"Ile-Ife, Osun","url":"https://oauife.edu.ng"},
        {"name":"University of Ibadan (UI)",   "course":"Sociology / Political Science","cutoff":"200+","location":"Ibadan, Oyo","url":"https://ui.edu.ng"},
    ],
    "Mass Communication & Media": [
        {"name":"University of Lagos (UNILAG)","course":"Mass Communication","cutoff":"200+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"University of Nigeria Nsukka","course":"Mass Communication","cutoff":"180+","location":"Nsukka, Enugu","url":"https://unn.edu.ng"},
        {"name":"Bayero University Kano (BUK)","course":"Mass Communication","cutoff":"180+","location":"Kano","url":"https://buk.edu.ng"},
        {"name":"University of Ibadan (UI)",   "course":"Communication & Language Arts","cutoff":"180+","location":"Ibadan, Oyo","url":"https://ui.edu.ng"},
    ],
    "Education & Humanities": [
        {"name":"University of Nigeria Nsukka","course":"Education","cutoff":"160+","location":"Nsukka, Enugu","url":"https://unn.edu.ng"},
        {"name":"University of Ibadan (UI)",   "course":"Education","cutoff":"170+","location":"Ibadan, Oyo","url":"https://ui.edu.ng"},
        {"name":"Ahmadu Bello University (ABU)","course":"Education","cutoff":"160+","location":"Zaria, Kaduna","url":"https://abu.edu.ng"},
        {"name":"Lagos State University (LASU)","course":"Education","cutoff":"150+","location":"Lagos","url":"https://lasu.edu.ng"},
    ],
    "Business & Finance": [
        {"name":"University of Lagos (UNILAG)","course":"Accounting / Finance","cutoff":"220+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"Covenant University",         "course":"Business Administration","cutoff":"200+","location":"Ota, Ogun","url":"https://covenantuniversity.edu.ng"},
        {"name":"Obafemi Awolowo University",  "course":"Accounting","cutoff":"210+","location":"Ile-Ife, Osun","url":"https://oauife.edu.ng"},
        {"name":"Lagos Business School (PAU)", "course":"Business Studies","cutoff":"220+","location":"Lagos","url":"https://lbs.edu.ng"},
    ],
    "Entrepreneurship & Management": [
        {"name":"Covenant University",         "course":"Business Management","cutoff":"200+","location":"Ota, Ogun","url":"https://covenantuniversity.edu.ng"},
        {"name":"Lagos Business School (PAU)", "course":"Entrepreneurship","cutoff":"220+","location":"Lagos","url":"https://lbs.edu.ng"},
        {"name":"University of Lagos (UNILAG)","course":"Business Administration","cutoff":"210+","location":"Lagos","url":"https://unilag.edu.ng"},
        {"name":"Nile University of Nigeria",  "course":"Management Sciences","cutoff":"180+","location":"Abuja","url":"https://nileuniversity.edu.ng"},
    ],
    "Creative Arts & Design": [
        {"name":"Yaba College of Technology",   "course":"Art & Design","cutoff":"160+","location":"Lagos","url":"https://yabatech.edu.ng"},
        {"name":"Obafemi Awolowo University",   "course":"Fine & Applied Arts","cutoff":"180+","location":"Ile-Ife, Osun","url":"https://oauife.edu.ng"},
        {"name":"University of Nigeria Nsukka", "course":"Fine & Applied Arts","cutoff":"170+","location":"Nsukka, Enugu","url":"https://unn.edu.ng"},
        {"name":"Lagos State University (LASU)","course":"Fine Arts","cutoff":"160+","location":"Lagos","url":"https://lasu.edu.ng"},
    ],
}

# ====================== TEST QUESTIONS ======================
COGNITIVE_QUESTIONS = [
    {"id":"cog_1","text":"If 3 pencils cost ₦45, how much do 7 pencils cost?",
     "options":["₦95","₦105","₦100","₦115"],"correct":1},
    {"id":"cog_2","text":"Which number comes next in the sequence: 2, 6, 18, 54, ___?",
     "options":["108","162","72","216"],"correct":1},
    {"id":"cog_3","text":"A rectangle has length 12 cm and width 5 cm. What is its area?",
     "options":["34 cm²","60 cm²","17 cm²","70 cm²"],"correct":1},
    {"id":"cog_4","text":"If today is Wednesday and a test is in 10 days, what day is the test?",
     "options":["Monday","Friday","Saturday","Sunday"],"correct":3},
    {"id":"cog_5","text":"BOOK is to LIBRARY as PAINTING is to:",
     "options":["Canvas","Museum","Artist","Brush"],"correct":1},
    {"id":"cog_6","text":"Which word does NOT belong: Cat, Dog, Eagle, Rabbit?",
     "options":["Cat","Dog","Eagle","Rabbit"],"correct":2},
    {"id":"cog_7","text":"A train travels 240 km in 3 hours. How far does it travel in 5 hours?",
     "options":["360 km","480 km","400 km","300 km"],"correct":2},
    {"id":"cog_8","text":"If ALL doctors are graduates, and Emeka is a doctor, then:",
     "options":["Emeka may not be a graduate","Emeka is definitely a graduate",
                "Emeka is not a graduate","We cannot tell"],"correct":1},
    {"id":"cog_9","text":"What is 15% of 200?",
     "options":["25","30","35","20"],"correct":1},
    {"id":"cog_10","text":"Choose the word with the opposite meaning of ANCIENT:",
     "options":["Old","Historic","Modern","Antique"],"correct":2},
]

APTITUDE_QUESTIONS = [
    {"id":"apt_1","text":"You are given a broken device. Your first instinct is to:",
     "options":["Take it apart to understand how it works","Look up a repair video online",
                "Ask someone with technical knowledge","Buy a new one"],
     "correct":None,"weights":{"Science":[3,2,1,0],"Arts":[1,2,3,0],"Commercial":[1,2,2,1]}},
    {"id":"apt_2","text":"Which activity would you enjoy MOST on a free Saturday?",
     "options":["Conducting a science experiment at home","Writing a short story or poem",
                "Organising a small business selling snacks","Playing a musical instrument"],
     "correct":None,"weights":{"Science":[3,1,1,1],"Arts":[1,3,0,2],"Commercial":[1,0,3,1]}},
    {"id":"apt_3","text":"Your school wants to raise funds. You suggest:",
     "options":["Build a website to accept donations","Write persuasive letters to sponsors",
                "Create a business plan and sell products","Organise a school debate competition"],
     "correct":None,"weights":{"Science":[3,1,2,1],"Arts":[1,3,1,2],"Commercial":[2,1,3,1]}},
    {"id":"apt_4","text":"Which subject do you find most interesting?",
     "options":["Physics / Biology / Chemistry","Literature / History / Government",
                "Economics / Accounting / Commerce","Music / Fine Art / Drama"],
     "correct":None,"weights":{"Science":[3,0,1,0],"Arts":[0,3,1,2],"Commercial":[1,0,3,1]}},
    {"id":"apt_5","text":"When reading a long text, you prefer to:",
     "options":["Draw diagrams and charts to summarise it","Write bullet points and key arguments",
                "Create a table or spreadsheet of key data","Discuss it with classmates"],
     "correct":None,"weights":{"Science":[3,1,2,1],"Arts":[1,3,1,2],"Commercial":[1,1,3,2]}},
    {"id":"apt_6","text":"Which of these jobs sounds most exciting to you?",
     "options":["Engineer or Doctor","Lawyer or Journalist","Banker or Entrepreneur","Teacher or Counsellor"],
     "correct":None,"weights":{"Science":[3,1,1,1],"Arts":[1,3,0,2],"Commercial":[0,1,3,2]}},
    {"id":"apt_7","text":"A classmate is struggling with a problem. You:",
     "options":["Help them figure out the logic step-by-step","Listen and offer emotional support",
                "Help them plan a practical solution","Encourage them with motivational words"],
     "correct":None,"weights":{"Science":[3,1,2,1],"Arts":[1,3,1,2],"Commercial":[1,1,3,2]}},
    {"id":"apt_8","text":"You are strongest at:",
     "options":["Solving maths and science problems quickly","Expressing ideas through words and debate",
                "Managing money and identifying business opportunities","Creating art, music or stories"],
     "correct":None,"weights":{"Science":[3,1,1,1],"Arts":[0,3,0,2],"Commercial":[1,1,3,0]}},
]

PSYCHOMETRIC_QUESTIONS = [
    {"id":"psy_1","text":"I enjoy working in groups and collaborating with others.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Extraversion"},
    {"id":"psy_2","text":"I like to plan and organise things well in advance.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Conscientiousness"},
    {"id":"psy_3","text":"I stay calm and focused even when things get difficult.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Emotional Stability"},
    {"id":"psy_4","text":"I enjoy trying out new ideas and thinking creatively.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Openness"},
    {"id":"psy_5","text":"I consider how my decisions will affect other people.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Agreeableness"},
    {"id":"psy_6","text":"I prefer working on one task at a time until it is completed.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Conscientiousness"},
    {"id":"psy_7","text":"I feel energised when I am around people.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Extraversion"},
    {"id":"psy_8","text":"I am comfortable leading a group or project.",
     "options":["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"],"trait":"Leadership"},
]

SENTIMENT_QUESTIONS = [
    {"id":"sen_1","text":"How excited are you about your future career?",
     "options":["Not at all","A little","Moderately","Very excited","Extremely excited"]},
    {"id":"sen_2","text":"How confident are you that you will succeed in your chosen career?",
     "options":["Not confident","Slightly confident","Moderately confident","Confident","Very confident"]},
    {"id":"sen_3","text":"How much does your family support your career aspirations?",
     "options":["No support","Little support","Some support","Good support","Full support"]},
    {"id":"sen_4","text":"How would you describe your current academic motivation?",
     "options":["Very low","Low","Average","High","Very high"]},
    {"id":"sen_5","text":"How do you feel when you face a very difficult academic challenge?",
     "options":["Give up easily","Feel discouraged","Push through with difficulty",
                "Stay motivated","Thrive on the challenge"]},
    {"id":"sen_6","text":"How clear is your vision of what career you want?",
     "options":["Completely unclear","Very unclear","Somewhat clear","Mostly clear","Completely clear"]},
]

TEST_META = [
    {"key":"cognitive",    "label":"Cognitive Test",    "icon":"🧩",
     "desc":"Logic, reasoning & problem-solving",  "questions":COGNITIVE_QUESTIONS},
    {"key":"aptitude",     "label":"Aptitude Test",     "icon":"🎯",
     "desc":"Natural talents & subject strengths", "questions":APTITUDE_QUESTIONS},
    {"key":"psychometric", "label":"Psychometric Test", "icon":"🧠",
     "desc":"Personality traits & working style",  "questions":PSYCHOMETRIC_QUESTIONS},
    {"key":"sentiment",    "label":"Sentiment Test",    "icon":"💬",
     "desc":"Attitudes, motivation & mindset",     "questions":SENTIMENT_QUESTIONS},
]

QUESTION_CATEGORY_MAP = {
    "cognitive": "cognitive",
    "aptitude": "aptitude",
    "psychometric": "psychometric",
    "sentiment": "personality",
}


def load_question_bank():
    if not QUESTIONS_PATH.exists():
        return []
    with QUESTIONS_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def get_question_session(test_key, user_id, department):
    if "question_sessions" not in st.session_state:
        st.session_state.question_sessions = {}
    if "question_attempts" not in st.session_state:
        st.session_state.question_attempts = {}

    cache_key = f"{user_id}:{department}:{test_key}:{st.session_state.question_attempts.get(test_key, 0)}"
    if cache_key in st.session_state.question_sessions:
        return st.session_state.question_sessions[cache_key]

    category = QUESTION_CATEGORY_MAP.get(test_key, test_key)
    subject_category = "Arts" if department == "Arts" else "Commercial" if department == "Commercial" else "Science"
    bank = load_question_bank()
    questions = [
        q for q in bank
        if q.get("category") == category
        and q.get("options")
        and (q.get("subject_category") in (subject_category, "General", None))
    ]
    if len(questions) < 10:
        questions = [q for q in bank if q.get("category") == category and q.get("options")]

    rng = Random(f"{user_id}-{department}-{test_key}-{st.session_state.question_attempts.get(test_key, 0)}")
    questions = list(questions)
    rng.shuffle(questions)
    selected = []
    for q in questions[:10]:
        options = list(q.get("options", []))
        rng.shuffle(options)
        prompt = q.get("prompt", q.get("text", ""))
        clean_prompt = re.sub(r'\s*Q\d+:\s*', ': ', prompt)
        selected.append({
            "id": q.get("id"),
            "text": clean_prompt,
            "options": options,
            "answer": q.get("answer"),
            "category": q.get("category"),
        })

    st.session_state.question_sessions[cache_key] = selected
    return selected


def get_dynamic_test_meta():
    base = [
        {"key":"cognitive", "label":"Cognitive Test", "icon":"🧩", "desc":"Logic, reasoning & problem-solving"},
        {"key":"aptitude", "label":"Aptitude Test", "icon":"🎯", "desc":"Natural talents & subject strengths"},
        {"key":"psychometric", "label":"Psychometric Test", "icon":"🧠", "desc":"Personality traits & working style"},
        {"key":"sentiment", "label":"Sentiment Test", "icon":"💬", "desc":"Attitudes, motivation & mindset"},
    ]
    if not st.session_state.get("user_id"):
        return TEST_META
    return [
        {
            **meta,
            "questions": get_question_session(
                meta["key"],
                st.session_state.user_id,
                st.session_state.department or "Science",
            ),
        }
        for meta in base
    ]

# ====================== DATABASE ======================
def init_db():
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT, dob TEXT, class_level TEXT,
        department TEXT, email TEXT UNIQUE, password TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS academic_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, result_type TEXT, subject TEXT,
        score REAL, exam_date TEXT, uploaded_at TEXT, UNIQUE(user_id, result_type, subject, score, exam_date))""")
    c.execute("""CREATE TABLE IF NOT EXISTS test_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, test_type TEXT, question_id TEXT,
        answer TEXT, score REAL, submitted_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, career_path TEXT, confidence REAL,
        universities TEXT, linkedin_mentors TEXT,
        narrative TEXT, top3 TEXT, generated_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, role TEXT, message TEXT, created_at TEXT)""")
    for col, typ in [("narrative","TEXT"),("top3","TEXT")]:
        try:
            c.execute(f"ALTER TABLE recommendations ADD COLUMN {col} {typ}")
        except Exception:
            pass
    conn.commit()
    conn.close()
    create_admin_user()

def remove_duplicate_results():

    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()

    c.execute("""
    DELETE FROM academic_results
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM academic_results
        GROUP BY
            user_id,
            result_type,
            subject,
            score,
            exam_date
    )
    """)

    conn.commit()
    conn.close()

def parse_results(text):
    results = []
    lines = text.split("\n")

    for line in lines:
        match = re.search(r"([A-Za-z ]+)\s+(\d{1,3})", line)
        if match:
            subject = match.group(1).strip()
            score = float(match.group(2))

            if 0 <= score <= 100:
                results.append((subject, score))

    return results

def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode("utf-8")

def check_password(p, h):
    if isinstance(h, str):
        h = h.encode("utf-8")
    return bcrypt.checkpw(p.encode(), h)

def create_admin_user():
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE email='Admin'")
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (full_name,dob,class_level,department,email,password) VALUES (?,?,?,?,?,?)",
                  ("Administrator","2000-01-01","Admin",None,"Admin",hash_password("Admin")))
        conn.commit()
        st.toast("✅ Admin account created  (email: Admin / password: Admin)", icon="🔑")
    else:
        # Migrate old bytes-stored hash or incorrect admin password if needed.
        stored_pw = row[1]
        needs_reset = isinstance(stored_pw, bytes) or (isinstance(stored_pw, str) and stored_pw.startswith("b'"))
        try:
            needs_reset = needs_reset or not check_password("Admin", stored_pw)
        except Exception:
            needs_reset = True
        if needs_reset:
            c.execute("UPDATE users SET password=? WHERE email='Admin'", (hash_password("Admin"),))
            conn.commit()
    conn.close()

def create_user(full_name, dob, class_level, department, email, password):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (full_name,dob,class_level,department,email,password) VALUES (?,?,?,?,?,?)",
                  (full_name, str(dob), class_level, department, email, hash_password(password)))
        conn.commit(); return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("SELECT id,full_name,class_level,department,password FROM users WHERE email=?", (email,))
    user = c.fetchone(); conn.close()
    return user if (user and check_password(password, user[4])) else None


def save_academic_result(
    user_id,
    result_type,
    subject,
    score,
    exam_date
):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    # Check for duplicate first
    c.execute(
        """
        SELECT id
        FROM academic_results
        WHERE user_id = ?
        AND result_type = ?
        AND subject = ?
        AND score = ?
        AND exam_date = ?
        """,
        (
            user_id,
            result_type,
            subject,
            score,
            str(exam_date)
        )
    )
    existing = c.fetchone()
    if existing:
        conn.close()
        return False
    c.execute(
        """
        INSERT INTO academic_results
        (
            user_id,
            result_type,
            subject,
            score,
            exam_date,
            uploaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            result_type,
            subject,
            score,
            str(exam_date),
            datetime.datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()
    return True

def get_user_results(user_id):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("SELECT id,result_type,subject,score,exam_date,uploaded_at FROM academic_results WHERE user_id=? ORDER BY uploaded_at DESC", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def delete_academic_result(result_id):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("DELETE FROM academic_results WHERE id=?", (result_id,))
    conn.commit(); conn.close()

def save_test_responses(user_id, test_type, answers_dict, score):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("DELETE FROM test_responses WHERE user_id=? AND test_type=?", (user_id, test_type))
    now = datetime.datetime.now().isoformat()
    for q_id, ans in answers_dict.items():
        c.execute("INSERT INTO test_responses (user_id,test_type,question_id,answer,score,submitted_at) VALUES (?,?,?,?,?,?)",
                  (user_id, test_type, q_id, str(ans), score, now))
    conn.commit(); conn.close()

def get_completed_tests(user_id):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT test_type FROM test_responses WHERE user_id=?", (user_id,))
    rows = c.fetchall(); conn.close()
    return {r[0] for r in rows}

def save_recommendation(user_id, career_path, confidence, universities, mentors, narrative, top3):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("DELETE FROM recommendations WHERE user_id=?", (user_id,))
    c.execute("""INSERT INTO recommendations
        (user_id,career_path,confidence,universities,linkedin_mentors,narrative,top3,generated_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, career_path, confidence,
         json.dumps(universities), json.dumps(mentors),
         narrative, json.dumps(top3),
         datetime.datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_recommendation(user_id):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("""SELECT career_path,confidence,universities,linkedin_mentors,
                        narrative,top3,generated_at
                 FROM recommendations WHERE user_id=? ORDER BY generated_at DESC LIMIT 1""", (user_id,))
    row = c.fetchone(); conn.close()
    if not row: return None
    return {"career_path":row[0],"confidence":row[1],
            "universities":json.loads(row[2] or "[]"),
            "mentors":     json.loads(row[3] or "[]"),
            "narrative":   row[4] or "",
            "top3":        json.loads(row[5] or "[]"),
            "generated_at":row[6]}

def save_chat_message(user_id, role, message):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id,role,message,created_at) VALUES (?,?,?,?)",
              (user_id, role, message, datetime.datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_chat_history(user_id, limit=40):
    conn = sqlite3.connect("career_portal.db")
    c = conn.cursor()
    c.execute("SELECT role,message FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
              (user_id, limit))
    rows = c.fetchall(); conn.close()
    return list(reversed(rows))

# ====================== HELPERS ======================
def get_result_types(class_level):  return ["Current Grade"]

def get_subjects(class_level, department=None):
    return DEPARTMENT_SUBJECTS.get(department, ["English","Mathematics"])

def score_cognitive(answers, questions):
    total = 0
    correct = 0
    for q in questions:
        ans_idx = answers.get(q["id"])
        if ans_idx is None:
            continue
        total += 1
        selected = q["options"][ans_idx] if ans_idx < len(q["options"]) else ""
        if str(selected).strip().lower() == str(q.get("answer", "")).strip().lower():
            correct += 1
    return round(correct / max(total, 1) * 100, 1)

def score_aptitude(answers, questions, department):
    total = 0
    correct = 0
    for q in questions:
        ans_idx = answers.get(q["id"])
        if ans_idx is None:
            continue
        total += 1
        selected = q["options"][ans_idx] if ans_idx < len(q["options"]) else ""
        if str(selected).strip().lower() == str(q.get("answer", "")).strip().lower():
            correct += 1
    return round(correct / max(total, 1) * 100, 1)

def score_likert(answers, questions):
    scores = [answers[q["id"]]+1 for q in questions if answers.get(q["id"]) is not None]
    return round(sum(scores)/(len(scores)*5)*100, 1) if scores else 0.0


# ====================== ML INFERENCE ======================
def build_feature_vector(results, profile):
    TERM_MAP = {"First Term":"t1","Second Term":"t2","Third Term":"t3"}
    bucket = defaultdict(list)
    for r in results:
        pfx = TERM_MAP.get(r[1],"t3")
        key = r[2].replace(" ","_").replace("/","_").replace("&","and")
        bucket[(pfx,key)].append(float(r[3]))

    subj_avg = {f"{p}_{k}": round(sum(v)/len(v),2) for (p,k),v in bucket.items()}

    def tavg(pfx):
        vs=[v for k,v in subj_avg.items() if k.startswith(pfx+"_")]
        return round(sum(vs)/len(vs),2) if vs else 0.0

    t3a=tavg("t3"); t2a=tavg("t2") or t3a; t1a=tavg("t1") or t2a
    sess=round((t1a+t2a+t3a)/3,2)
    cons=round(max(0,100-np.std([t1a,t2a,t3a])*2),2)
    trend="Improving" if t3a>t1a+4 else ("Declining" if t3a<t1a-4 else "Stable")
    strength="high" if sess>=65 else ("average" if sess>=50 else "low")

    SCI  = ["t3_Mathematics","t3_Basic_Science","t3_Physics","t3_Chemistry",
            "t3_Biology","t3_Computer_Studies","t3_Computer_Science","t3_Further_Mathematics"]
    ARTS = ["t3_English_Language","t3_Literature_in_English","t3_Government",
            "t3_History","t3_Social_Studies","t3_Cultural_and_Creative_Arts","t3_CRS_IRK"]
    COM  = ["t3_Economics","t3_Accounting","t3_Commerce","t3_Business_Studies","t3_Office_Practice"]

    def davg(ks):
        vs=[subj_avg[k] for k in ks if k in subj_avg]; return round(sum(vs)/len(vs),2) if vs else 0.0

    t3s={k:v for k,v in subj_avg.items() if k.startswith("t3_")}
    best_k=max(t3s,key=t3s.get) if t3s else "t3_Mathematics"
    weak_k=min(t3s,key=t3s.get) if t3s else "t3_Mathematics"

    def grade(s):
        return "A" if s>=75 else "B" if s>=65 else "C" if s>=50 else "D" if s>=45 else "E" if s>=40 else "F"
    gc={"A":0,"B":0,"C":0,"D":0,"E":0,"F":0}
    for v in t3s.values(): gc[grade(v)]+=1

    CLASS_MAP={"JSS 2":"JSS2","JSS 3":"JSS3","SSS 1":"SSS1","SSS 2":"SSS2","Admin":"JSS2"}
    DEPT_MAP ={"Science":"Science","Arts":"Arts","Commercial":"Commercial",
               None:"N_A","":"N_A","Select Department":"N_A"}

    def se(le_key, val):
        le=ml_models[le_key]; cls=list(le.classes_)
        return int(le.transform([val])[0]) if val in cls else 0

    row = {
        "term1_avg":t1a,"term2_avg":t2a,"term3_avg":t3a,
        "session_avg":sess,"consistency_score":cons,
        "science_aptitude_score":davg(SCI),"arts_aptitude_score":davg(ARTS),
        "commercial_aptitude_score":davg(COM),
        "best_subject_score":t3s.get(best_k,0),"weak_subject_score":t3s.get(weak_k,0),
        "grade_A_count":gc["A"],"grade_B_count":gc["B"],"grade_C_count":gc["C"],
        "grade_D_count":gc["D"],"grade_E_count":gc["E"],"grade_F_count":gc["F"],
        "class_level_enc":    se("le_class",   CLASS_MAP.get(profile.get("class_level","JSS2"),"JSS2")),
        "department_enc":     se("le_dept",    DEPT_MAP.get(profile.get("department",""),"N_A")),
        "strength_level_enc": se("le_strength",strength),
        "performance_trend_enc":se("le_trend", trend),
        "best_subject_enc":   se("le_best", best_k.replace("t3_","").replace("_"," ")),
        "weak_subject_enc":   se("le_weak", weak_k.replace("t3_","").replace("_"," ")),
    }
    row.update(subj_avg)
    vec = np.array([row.get(f,0.0) for f in ml_models["feature_names"]], dtype=np.float32)
    meta = {"session_avg":sess,"trend":trend,"strength":strength,
            "best_subject":best_k.replace("t3_","").replace("_"," "),"best_score":t3s.get(best_k,0),
            "weak_subject":weak_k.replace("t3_","").replace("_"," "),"weak_score":t3s.get(weak_k,0),
            "t1_avg":t1a,"t2_avg":t2a,"t3_avg":t3a,"consistency":cons,
            "sci_apt":davg(SCI),"arts_apt":davg(ARTS),"com_apt":davg(COM),"grade_counts":gc}
    return vec, meta

def ml_predict(results, profile):
    vec, meta = build_feature_vector(results, profile)
    vs  = ml_models["scaler"].transform(vec.reshape(1,-1))
    idx = ml_models["xgb"].predict(vs)[0]
    proba = ml_models["xgb"].predict_proba(vs)[0]
    career = ml_models["le_career"].inverse_transform([idx])[0]
    conf   = round(float(proba[idx])*100,1)
    t3i    = np.argsort(proba)[::-1][:3]
    top3   = [(ml_models["le_career"].inverse_transform([i])[0], round(float(proba[i])*100,1))
              for i in t3i]
    return {"career_path":career,"confidence":conf,"top3":top3,"meta":meta}

SUBJECT_TO_API_KEY = {
    "mathematics": "mathematics",
    "english": "english",
    "english language": "english",
    "civic education": "civic_education",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "further mathematics": "further_mathematics",
    "agricultural science": "agricultural_science",
    "agriculture": "agricultural_science",
    "geography": "geography",
    "technical drawing": "technical_drawing",
    "computer studies": "computer_studies",
    "computer science": "computer_studies",
    "yoruba/hausa/igbo": "igbo_hausa",
    "yoruba": "yoruba",
    "hausa": "igbo_hausa",
    "igbo": "igbo_hausa",
    "data processing": "data_processing",
    "literature in english": "literature_in_english",
    "crs/irk": "christian_religious_studies_islamic_studies",
    "crs": "christian_religious_studies_islamic_studies",
    "irk": "christian_religious_studies_islamic_studies",
    "creative arts": "creative_arts",
    "cultural and creative arts": "creative_arts",
    "economics": "economics",
    "accounting": "financial_accounting",
    "financial accounting": "financial_accounting",
    "commerce": "commerce",
    "government": "government",
    "marketing": "marketing",
}


def score_to_grade(score):
    score = float(score or 0)
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 45:
        return "D"
    if score >= 40:
        return "E"
    return "F"


def build_fastapi_payload(results, profile, test_scores):
    payload = {
        "gender": "Unknown",
        "school_type": "Unknown",
        "department": profile.get("department") or "Science",
        "academic_strength": "Unknown",
        "best_subject_category": "Unknown",
        "confidence_level": "Unknown",
        "career_influence": "Unknown",
        "aptitude_score_10": round(float(test_scores.get("aptitude", 50.0)) / 10, 2),
        "cognitive_score_10": round(float(test_scores.get("cognitive", 50.0)) / 10, 2),
        "psychometric_avg_5": round(float(test_scores.get("psychometric", 60.0)) / 20, 2),
        "sentiment_avg_5": round(float(test_scores.get("sentiment", 60.0)) / 20, 2),
    }
    for key in set(SUBJECT_TO_API_KEY.values()):
        payload[key] = "UNKNOWN"
    for row in results:
        subject = str(row[2]).strip().lower()
        api_key = SUBJECT_TO_API_KEY.get(subject)
        if api_key:
            payload[api_key] = score_to_grade(row[3])
    return payload


def fastapi_ml_predict(results, profile, test_scores):
    payload = build_fastapi_payload(results, profile, test_scores)
    response = requests.post(f"{FASTAPI_BASE_URL}/predict/ml", json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()
    top3 = [(item["career"], item["confidence_percent"]) for item in data.get("top_3", [])]

    # Compute grade counts from actual result scores
    gc = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    scores = [float(r[3]) for r in results] if results else []
    for s in scores:
        gc[score_to_grade(s)] += 1
    avg = round(sum(scores) / max(len(scores), 1), 1)

    return {
        "career_path": data["predicted_career"],
        "confidence": data["confidence_percent"],
        "top3": top3,
        "meta": {
            "session_avg": avg,
            "best_subject": max(results, key=lambda r: float(r[3]))[2] if results else "your strongest subject",
            "best_score": max(scores) if scores else 0,
            "weak_subject": min(results, key=lambda r: float(r[3]))[2] if results else "a subject to strengthen",
            "weak_score": min(scores) if scores else 0,
            "trend": "Stable",
            "strength": "high" if avg >= 65 else ("average" if avg >= 50 else "low"),
            "t1_avg": avg,
            "t2_avg": avg,
            "t3_avg": avg,
            "consistency": 100,
            "sci_apt": 0,
            "arts_apt": 0,
            "com_apt": 0,
            "grade_counts": gc,
        },
    }

# ====================== GEMINI: RECOMMENDATION NARRATIVE ======================
def _fallback_narrative(name, career, confidence, top3, meta):
    t2name = top3[1][0] if len(top3)>1 else "an alternative"
    t3name = top3[2][0] if len(top3)>2 else "another option"
    return f"""#### 🌟 Your Career Recommendation Summary
Hi {name}! Based on a comprehensive analysis of your academic performance and all four assessments, your strongest career match is {career}, with a confidence level of {confidence}%. 
Your overall session average of {meta['session_avg']}%, combined with your outstanding performance in {meta['best_subject']} ({meta['best_score']}%), highlights both your capability and natural alignment with this path. 
These results don’t just reflect what you’ve achieved—they reveal where your strengths are most likely to thrive and succeed in the real world.

#### 🎯 Recommended Career Path: {career}
This is one of the most in-demand and impactful career fields in Nigeria today. Professionals here work across the private sector, federal agencies, and international organisations. Your assessment results — particularly your aptitude score and academic performance — show exactly the potential this field requires.

#### 💼 Five Nigerian Career Roles to Explore
- **Core Specialist** — practise your craft at a federal agency or major private company
- **Consultant / Adviser** — work across multiple organisations solving problems
- **Research & Analysis** — contribute to academia, think-tanks, or government policy
- **Entrepreneurship** — start your own practice, firm, or business
- **NGO / Development Sector** — tackle national challenges with international organisations

#### 📈 Your Competitive Strengths
- Strong academic performance — **{meta['best_subject']}** is your top subject at **{meta['best_score']}%**
- Consistent performance across subjects — shows reliability and focus.
- Assessment scores confirm real aptitude for this career path

#### ⚠️ Areas to Strengthen
Focus extra effort on **{meta['weak_subject']}** ({meta['weak_score']}%) — it appears in WAEC and will matter for admission. Also build reading and comprehension skills through daily practice.

#### 🔄 Your Two Backup Career Options
**{t2name}** is your second-best match — great if your interests evolve. **{t3name}** is also a strong fit and may suit a slightly different academic path.

#### 🚀 Action Steps for Right Now
1. Research what professionals in **{career}** actually do in Nigeria — YouTube and LinkedIn are great starting points
2. Talk to your school counsellor about the right subjects for your SSS class combination
3. Start practising JAMB past questions in your core subjects — aim for consistency
4. Join a relevant school club, science fair, or business competition to start building real experience"""

def generate_recommendation_gemini(name, class_level, department, ml_result, test_scores, results):
    meta  = ml_result["meta"]
    top3  = ml_result["top3"]
    dept_txt = f" ({department} dept.)" if department else ""

    subj_avgs = defaultdict(list)
    for r in results:
        subj_avgs[r[2]].append(float(r[3]))
    summary = " | ".join(f"{s}: {round(sum(v)/len(v),1)}%" for s,v in list(subj_avgs.items())[:6])

    prompt = f"""You are a warm, expert career guidance counsellor at a top Nigerian secondary school.
Write a personalised career recommendation report for a student.

STUDENT PROFILE:
- Name: {name}
- Class: {class_level}{dept_txt}
- Session Average: {meta['session_avg']}%
- Trend: {meta['trend']} | Academic standing: {meta['strength'].upper()}
- Best Subject: {meta['best_subject']} ({meta['best_score']}%)
- Weakest Subject: {meta['weak_subject']} ({meta['weak_score']}%)
- Grade-A count: {meta.get('grade_counts', {}).get('A', 0)} | Grade-F count: {meta.get('grade_counts', {}).get('F', 0)}
- Science aptitude: {meta['sci_apt']}% | Arts: {meta['arts_apt']}% | Commercial: {meta['com_apt']}%
- Subject summary: {summary}

4-TEST SCORES:
- Cognitive (logic & reasoning): {test_scores.get('cognitive', 50)}%
- Aptitude (natural talents): {test_scores.get('aptitude', 50)}%
- Psychometric (personality): {test_scores.get('psychometric', 50)}%
- Sentiment (motivation & mindset): {test_scores.get('sentiment', 50)}%

ML MODEL OUTPUT:
- Primary career: {top3[0][0]} (confidence {top3[0][1]}%)
- 2nd option: {top3[1][0] if len(top3)>1 else 'N/A'} ({top3[1][1] if len(top3)>1 else 0}%)
- 3rd option: {top3[2][0] if len(top3)>2 else 'N/A'} ({top3[2][1] if len(top3)>2 else 0}%)

Write the report using EXACTLY these section headers:

## 🌟 Your Career Recommendation Summary
2–3 sentences directly addressing {name}, referencing their strongest results.

## 🎯 Recommended Career Path: {top3[0][0]}
Two paragraphs: (1) What this career involves in Nigeria — real sectors, agencies (NNPC, CBN, NAFDAC, NTA, MTN, etc.) (2) Exactly why this matches {name}'s data — mention actual scores.

## 💼 Five Nigerian Career Roles to Explore
5 specific job roles in demand in Nigeria, one line each with a Nigerian employer or context.

## 📈 Your Competitive Strengths
Three bullet points rooted in the actual data. Reference real scores and subjects.

## ⚠️ Areas to Strengthen
Two specific, encouraging, actionable suggestions. Reference {meta['weak_subject']} directly.

## 🔄 Your Two Backup Career Options
Short paragraph each on {top3[1][0] if len(top3)>1 else 'Alternative A'} and {top3[2][0] if len(top3)>2 else 'Alternative B'}.

## 🚀 Action Steps for Right Now
Four numbered, concrete steps {name} can take TODAY as a {class_level} student in Nigeria. Include JAMB subject choices, WAEC prep, and free resources.

Tone: warm, direct, encouraging — like a trusted school counsellor talking to a Nigerian teenager.
Do NOT include university suggestions (handled separately). Total: ~650–800 words."""

    try:
        resp = gemini_client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=1200, temperature=0.7))
        return resp.text
    except Exception:
        return _fallback_narrative(name, ml_result["career_path"],
                                   ml_result["confidence"], ml_result["top3"], meta)

# ====================== GEMINI: CHATBOT ======================
def get_chatbot_response(user_message, student_context, history_list):
    msg = user_message.lower()

    if "jamb" in msg:
        extra_instruction = "Focus on JAMB subjects, cutoff marks, and preparation strategy."
    elif "university" in msg:
        extra_instruction = "Recommend Nigerian universities and admission strategy."
    elif "career" in msg:
        extra_instruction = "Explain career paths and real-world roles in Nigeria."
    else:
        extra_instruction = "Give practical career guidance."

    # ------------------ Strong System Prompt ------------------
    system_ctx = f"""
You are a highly experienced Nigerian career counsellor.

Your job is to give SPECIFIC, PRACTICAL, PERSONALISED advice.

You MUST:
- Use the student's data (scores, strengths, career recommendation)
- Mention Nigerian context (JAMB, WAEC, universities, companies)
- Give actionable steps (bullet points)

Response Structure:
1. Direct answer (1–2 sentences)
2. Personalised explanation using their data
3. Practical steps (bullet points)
4. End with one short encouraging sentence

Avoid:
- Generic advice
- Long storytelling

FOCUS:
{extra_instruction}

STUDENT DATA:
{student_context}
"""

    # ------------------ History (last 6 messages only) ------------------
    history = []
    for role, msg in history_list[-6:]:
        history.append(types.Content(
            role="user" if role == "user" else "model",
            parts=[types.Part(text=msg)]
        ))

    # ------------------ Gemini Call ------------------
    try:
        chat = gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_ctx,
                max_output_tokens=350,
                temperature=0.7
            ),
            history=history[:-1] if len(history) > 1 else []
        )

        resp = chat.send_message(user_message)
        response = resp.text.strip()

        # ------------------ Post-processing ------------------
        if len(response.split()) > 220:
            response = " ".join(response.split()[:220]) + "..."

        response = response.replace("•", "\n•")

        return response

    except Exception:
        return "Sorry, something went wrong. Please try again."
    
# Function to translate roles between Gemini-Pro and Streamlit terminology
def translate_role_for_streamlit(user_role):
    if user_role == "model":
        return "assistant"
    else:
        return user_role


# ====================== RENDER SINGLE TEST ======================
def render_test(meta, completed_tests):
    test_key  = meta["key"]
    questions = meta["questions"]

    st.markdown(f"""
    <div class="test-header">
        <h2>{meta['icon']} {meta['label']}</h2>
        <p>{meta['desc']}</p>
    </div>""", unsafe_allow_html=True)

    if test_key in completed_tests:
        score = st.session_state.test_scores.get(test_key, "N/A")
        st.success(f"✅ Already completed — Score: **{score}%**")
        if st.button("🔄 Retake This Test", key=f"retake_{test_key}"):
            save_test_responses(st.session_state.user_id, test_key, {}, 0)
            st.session_state.test_answers.pop(test_key, None)
            st.session_state.test_scores.pop(test_key, None)
            st.session_state.question_attempts[test_key] = st.session_state.question_attempts.get(test_key, 0) + 1
            st.session_state.all_tests_done = False
            st.session_state.rec_cache = None
            st.rerun()
        return

    if test_key not in st.session_state.test_answers:
        st.session_state.test_answers[test_key] = {}

    # Clean display: Department + Test Type (no Q number)
    dept = (st.session_state.department or "General")
    test_name = meta['label'].replace(" Test", "").strip()

    for idx, q in enumerate(questions):
        st.markdown(f"""
        <div class="q-card">
            <div class="q-num">{dept} {test_name}</div>
            <div class="q-text">{q['text']}</div>
        </div>""", unsafe_allow_html=True)
        
        cur = st.session_state.test_answers[test_key].get(q["id"])
        chosen = st.radio(
            label=f"Answer for question {idx+1}", 
            options=q["options"], 
            index=cur,
            key=f"radio_{test_key}_{q['id']}", 
            label_visibility="collapsed"
        )
        if chosen is not None:
            st.session_state.test_answers[test_key][q["id"]] = q["options"].index(chosen)

    st.divider()
    _, col2 = st.columns([3,1])
    with col2:
        if st.button(f"✅ Submit {meta['label']}", type="primary", key=f"submit_{test_key}"):
            answers = st.session_state.test_answers[test_key]
            if len(answers) < len(questions):
                st.error("Please answer all questions before submitting.")
                return
            dept = st.session_state.department or "Science"
            if test_key == "cognitive":
                score = score_cognitive(answers, questions)
            elif test_key == "aptitude":
                score = score_aptitude(answers, questions, dept)
            else:
                score = score_likert(answers, questions)
            save_test_responses(st.session_state.user_id, test_key, answers, score)
            st.session_state.test_scores[test_key] = score
            st.session_state.active_test = None
            st.session_state.rec_cache   = None
            st.success(f"🎉 {meta['label']} submitted! Score: **{score}%**")
            st.rerun()

# ====================== CLEAR USER DATA ON LOGOUT ======================
def clear_user_data():
    """Safely clear all user-specific data on logout"""
    keys_to_clear = [
        "active_test", "test_answers", "test_scores", "all_tests_done",
        "rec_cache", "chat_cache", "upload_dir"
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    
    # Reset login state
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.full_name = None
    st.session_state.class_level = None
    st.session_state.department = None

# ====================== SESSION STATE ======================
for k, v in [("logged_in",False),("user_id",None),("full_name",None),
              ("class_level",None),("department",None),("active_test",None),
              ("test_answers",{}),("test_scores",{}),("all_tests_done",False),
              ("rec_cache",None),("chat_cache",None),("question_sessions",{}),
              ("question_attempts",{}),("processed_files", set())]:
    if k not in st.session_state:
        st.session_state[k] = v


# ====================== MAIN APP ======================
def app():
    if st.session_state.get("logged_in", False):
        keep_alive()
    if st.session_state.get("logged_in", False):
        st.markdown("""
            <div class="hero-banner">
                <h1 class="hero-title">🎓 Student Career Portal</h1>
                <p class="hero-subtitle">Smart Career Path Recommendation for Nigerian Secondary Students</p>
            </div>
        """, unsafe_allow_html=True)

        # ── LOGGED IN ────────────────────────────────────────────────────────────
        # Sidebar — user info + logout only
        dept_txt = f" — {st.session_state.department}" if st.session_state.department else ""
        with st.sidebar:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e3a8a,#3b82f6);
                        border-radius:12px;padding:16px;color:white;margin-bottom:16px;">
                <div style="font-size:1rem;font-weight:700;">👤 {st.session_state.full_name}</div>
                <div style="font-size:0.82rem;opacity:0.9;margin-top:4px;">
                    🎓 {st.session_state.class_level}{dept_txt}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.caption(f"FastAPI model URL: `{FASTAPI_BASE_URL}`")
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                clear_user_data()
                st.success("👋 You have been logged out successfully.")
                st.rerun()
            
        tab_dashboard, tab_upload, tab_test, tab_rec = st.tabs([
            "🏠 Dashboard","📤 Subject Grades","🧠 Take 4 Tests","📊 My Recommendations"
        ])

        # ----------------------- DASHBOARD ----------------------------

        with tab_dashboard:
            # Sleek Profile Header
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 30px; border-radius: 12px; color: white; margin-bottom: 25px;">
                <h2 style="margin: 0; font-weight: 700; color: white;">Welcome Back, {st.session_state.full_name} to Your Smart Career Journey! 👋</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 1rem;">
                    Class: <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 4px; font-weight: 600;">{st.session_state.class_level}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)

            n_tests   = len(get_completed_tests(st.session_state.user_id))
            n_results = len([row for row in get_user_results(st.session_state.user_id) if row[1] == "Current Grade"])
            rec_ready = get_recommendation(st.session_state.user_id) is not None

            c1,c2,c3 = st.columns(3)
            c1.markdown(
                f"""
                <div class="dashboard-card"><div class="card-icon">📋</div><div class="card-title">📋 Subject Grades</div>
                    <div class="card-value">{n_results}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c2.markdown(
                f"""
                <div class="dashboard-card"><div class="card-icon">🧪</div><div class="card-title">🧪 Tests Completed</div>
                    <div class="card-value">{n_tests} / 4</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            status_color = "#10b981" if rec_ready else "#f59e0b"
            status_text = "Ready ✨" if rec_ready else "Pending"
            c3.markdown(
                f"""
                <div class="dashboard-card"><div class="card-icon">📊</div><div class="card-title">📊 Recommendation</div>
                    <div class="card-value">{"Ready" if rec_ready else "Not Ready"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # System Status Warning Callout Box
            if not rec_ready:
                st.info("💡 Enter your current department subject grades and complete all 4 diagnostic assessments to unlock your tailored AI-powered career recommendations report!")
            else:
                st.success("🎉 Your personalized recommendations are fully ready! Click on the **My Recommendations** tab to explore matching universities and chat with your AI counsellor.")

            # High-fidelity Stepping Guide Component
            st.markdown('<div class="guide-container">', unsafe_allow_html=True)
            st.markdown('<div class="guide-title">🚀 Complete Your Journey Steps</div>', unsafe_allow_html=True)

            st.info("Complete all steps to unlock your personalised AI-powered career path!")

            st.divider()
            st.markdown("<br><h3 style='color: #1e293b; font-weight: 700;'>📋 How It Works</h3>", unsafe_allow_html=True)

            # Using a clean vertical step layout
            st.markdown("""
                <div class="step-card" style="border-left-color: #3b82f6;">
                    <div class="step-header">1. Enter Current Subject Grades</div>
                    <div class="step-desc">Navigate to the <b>Subject Grades</b> tab to log the department subjects required by the current FastAPI model.</div>
                </div>
                <div class="step-card" style="border-left-color: #8b5cf6;">
                    <div class="step-header">2. Take Career Assessment Tests</div>
                    <div class="step-desc">Complete the 4 dedicated cognitive and psychological interest parameters designed to understand your core strengths under the <b>Take Tests</b> section.</div>
                </div>
                <div class="step-card" style="border-left-color: #10b981;">
                    <div class="step-header">3. Discover AI Recommendations</div>
                    <div class="step-desc">Once steps 1 and 2 are unlocked, access your completely personalized, data-driven Nigerian career pathway map in <b>My Recommendations</b>.</div>
                </div>
            """, unsafe_allow_html=True)
            pass

        # -------------------- SUBJECT GRADES --------------------
        with tab_upload:
            st.markdown('<div class="subtitle">Step 1 of 3</div>', unsafe_allow_html=True)
            st.markdown('<div class="title">📤 Current Subject Grades</div>', unsafe_allow_html=True)
            st.caption(f"**{st.session_state.class_level}**" +
                       (f" | Dept: **{st.session_state.department}**" if st.session_state.department else ""))

            results = get_user_results(st.session_state.user_id)
            current_results = [row for row in results if row[1] == "Current Grade"]
            total_records = len(current_results)
            avg_score = round(sum(row[3] for row in current_results) / total_records, 1) if total_records else 0.0
            max_score = max((row[3] for row in current_results), default=0)

            m1, m2, m3 = st.columns(3)
            m1.markdown(f'<div class="summary-chip"><div class="chip-val">{total_records}</div><div class="chip-lbl">Subjects Entered</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="summary-chip"><div class="chip-val" style="color:#2563eb;">{avg_score}%</div><div class="chip-lbl">Average Score</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="summary-chip"><div class="chip-val" style="color:#16a34a;">{max_score}</div><div class="chip-lbl">Top Score</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            if current_results:
                st.markdown("<div class='ledger-header'>📂 Current Grade Ledger</div>", unsafe_allow_html=True)
                header_cols = st.columns([3, 1, 1, 1])
                header_cols[0].markdown("**Subject**")
                header_cols[1].markdown("**Score**")
                header_cols[2].markdown("**Grade**")
                header_cols[3].markdown("**Action**")
                for row in current_results:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.markdown(row[2])
                    c2.markdown(f"{row[3]}%")
                    c3.markdown(score_to_grade(row[3]))
                    with c4:
                        if st.button("Delete", key=f"ledger_delete_{row[0]}", help="Remove this subject grade"):
                            delete_academic_result(int(row[0]))
                            st.session_state.rec_cache = None
                            st.success("Subject grade deleted.")
                            st.rerun()
            else:
                st.markdown("""
                    <div style="text-align:center; padding: 40px 20px; border: 2px dashed #cbd5e1; border-radius:24px; margin-top:4px; margin-bottom: 15px; background-color:#f8fafc;">
                        <p style="font-size:2.5rem; margin:0;">empty 📑</p>
                        <h4 style="color:#64748b; margin:10px 0 4px 0;">No Subject Grades Recorded Yet</h4>
                        <p style="color:#94a3b8; font-size:0.85rem; max-width:360px; margin:0 auto;">Add your current department subject scores below. These are converted to A-F grades for the FastAPI model.</p>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown(
                '<div class="upload-card"><div class="upload-section-title"><h3>📊 Upload Results via Excel</h3>' +
                '<subtitle>Drop an Excel or CSV file here to import your subject scores fast.</span></div></div>',
                unsafe_allow_html=True
            )
            uploaded_file = st.file_uploader(
                "Upload Excel File (.xlsx or .csv)",
                type=["xlsx", "csv"],
                help='Required columns: Subject, Score (Exam_Date is optional)',
                key="excel_uploader"
            )
            if uploaded_file is not None:
                file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if file_key not in st.session_state.processed_files:
                    if st.button("📤 Process Uploaded File", type="primary"):
                        try:
                            # Read file
                            if uploaded_file.name.endswith(".csv"):
                                df = pd.read_csv(uploaded_file)
                            else:
                                df = pd.read_excel(uploaded_file)
                            
                            # Standardize column casing/spacing
                            df.columns = df.columns.str.strip().str.title()
                            
                            required_columns = ["Subject", "Score"]
                            missing_columns = [
                                col for col in required_columns
                                if col not in df.columns
                            ]
                            if missing_columns:
                                st.error(
                                    f"Missing columns: {', '.join(missing_columns)}. Required: Subject, Score. Optional: Exam Date"
                                )
                            else:
                                records_saved = 0
                                for _, row in df.iterrows():
                                    exam_date = str(row["Exam Date"]) if "Exam Date" in df.columns else str(datetime.date.today())
                                    success = save_academic_result(
                                        st.session_state.user_id,
                                        "Current Grade",
                                        row["Subject"],
                                        float(row["Score"]),
                                        exam_date
                                    )
                                    if success:
                                        records_saved += 1
                                st.success(
                                    f"✅ {records_saved} new record(s) imported successfully."
                                )
                                st.session_state.processed_files.add(file_key)
                        except Exception as e:
                            st.error(f"Upload failed: {e}")
                else:
                    st.info("This file has already been processed.")
            st.divider()

            with st.form("add_result_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    slist = get_subjects(st.session_state.class_level, st.session_state.department)
                    subj = st.segmented_control("Select Subject *", options=slist, default=None)
                with c2:
                    score = st.text_input("Score (0-100)", value="", placeholder="Enter score, e.g. 85.5")

                if st.form_submit_button("Save Subject Grade", type="primary"):
                    if not subj:
                        st.error("Please select a subject.")
                    else:
                        try:
                            score_float = float(score)
                            if not (0 <= score_float <= 100):
                                st.error("Score must be between 0 and 100.")
                            else:
                                save_academic_result(
                                    st.session_state.user_id,
                                    "Current Grade",
                                    subj,
                                    score_float,
                                    datetime.date.today(),
                                )
                                st.session_state.rec_cache = None
                                st.success(f"✅ Saved: **{subj}** | Score: **{score_float}** | Grade: **{score_to_grade(score_float)}**")
                                st.rerun()
                        except ValueError:
                            st.error("Please enter a valid numeric score (e.g. 85 or 72.5).")

            st.info("💡 Tip: Add all core department subjects before generating your recommendation.")


        # -------------------- TEST TAB --------------------

        with tab_test:
            st.markdown('<div class="title">🧠 Take 4 Tests</div>', unsafe_allow_html=True)
            st.markdown('<div class="subtitle">Step 2 of 4 — Complete all four tests to unlock your personalised career recommendation.</div>', unsafe_allow_html=True)

            completed_tests = get_completed_tests(st.session_state.user_id)
            test_meta = get_dynamic_test_meta()
            n_done = len(completed_tests)
            pct = int(n_done / 4 * 100)

            st.markdown(f"""
            <div style="margin-bottom:6px;"><b>Overall Progress: {n_done} / 4 tests completed</b></div>
            <div class="test-progress-bar">
                <div class="test-progress-fill" style="width:{pct}%;"></div>
            </div>""", unsafe_allow_html=True)

            st.markdown("### 🗂️ Select a Test to Begin")
            cols = st.columns(4)

            for i, meta in enumerate(test_meta):
                with cols[i]:

                    done = meta["key"] in completed_tests
                    badge = "completed-badge" if done else "active-badge"
                    status = "✅ Done" if done else "⏳ Not Started"
                    
                    stxt = f"Score: {st.session_state.test_scores.get(meta['key'],'—')}%" if done else ""

                    st.markdown(f"""
                    <div style="background:white;border-radius:12px;padding:16px;text-align:center;
                            box-shadow:0 2px 10px rgba(0,0,0,0.07);border-top:4px solid #2d6cdf;min-height:165px;">
                        <div style="font-size:28px;">{meta['icon']}</div>
                        <div style="font-weight:700;font-size:14px;margin:6px 0;">{meta['label']}</div>
                        <div style="font-size:12px;color:gray;margin-bottom:8px;">{meta['desc']}</div>
                        <span class="{badge}">{status}</span>
                        <div style="font-size:12px;color:#065f46;margin-top:4px;">{stxt}</div>
                    </div>""", unsafe_allow_html=True)

                    # Updated Button Text
                    btn_text = "🔄 Retake" if done else "▶ Click to Start"
                    if st.button(btn_text, key=f"open_{meta['key']}", use_container_width=True):
                        st.session_state.active_test = meta["key"]
                        st.rerun()

            st.divider()

            if st.session_state.active_test:
                active = next((m for m in test_meta if m["key"] == st.session_state.active_test), None)
                if active:
                    if st.button("← Back to Test List"):
                        st.session_state.active_test = None
                        st.rerun()
                    render_test(active, completed_tests)
            else:
                if n_done == 4:
                    st.success("🎉 **All 4 tests completed!** Go to **📊 My Recommendations** tab.")
                    st.session_state.all_tests_done = True
                elif n_done == 0:
                    st.info("👆 Click **▶ Click to Start** on any test above to begin.")
                else:
                    remaining = [m["label"] for m in test_meta if m["key"] not in completed_tests]
                    st.info(f"👍 Good progress! Still needed: **{', '.join(remaining)}**")
            pass
        
        # -------------------- RECOMMENDATIONN TAB --------------------

        with tab_rec:
            st.markdown('<div class="title">📊 My Personalised Career Recommendations</div>', unsafe_allow_html=True)

            completed_tests = get_completed_tests(st.session_state.user_id)
            test_meta = get_dynamic_test_meta()
            results         = [row for row in get_user_results(st.session_state.user_id) if row[1] == "Current Grade"]

            # Guards
            if len(completed_tests) < 4:
                missing = [m["label"] for m in test_meta if m["key"] not in completed_tests]
                st.warning(f"⚠️ Complete all 4 tests first. Pending: **{', '.join(missing)}**")
                st.info("👉 Go to the **🧠 Take 4 Tests** tab.")
                return

            if not results:
                st.warning("⚠️ Please enter at least one current subject grade first.")
                st.info("👉 Go to the **📤 Subject Grades** tab.")
                return

            existing = st.session_state.rec_cache or get_recommendation(st.session_state.user_id)

            # Generate / Regenerate
            btn_label = "🔄 Regenerate My Recommendations" if existing else "🚀 Generate My Career Recommendations"
            if st.button(btn_label, type="primary"):
                with st.spinner("🤖 Analysing your full profile with XGBoost ML + Gemini AI..."):
                    profile = {"class_level":st.session_state.class_level,
                                "department": st.session_state.department}
                    test_scores = {k: st.session_state.test_scores.get(k, 50.0)
                                    for k in ["cognitive","aptitude","psychometric","sentiment"]}

                    try:
                        ml_result = fastapi_ml_predict(results, profile, test_scores)
                    except Exception as exc:
                        st.error(f"Could not reach FastAPI prediction endpoint `{FASTAPI_BASE_URL}/predict/ml`: {exc}")
                        return

                    narrative = generate_recommendation_gemini(
                        st.session_state.full_name, st.session_state.class_level,
                        st.session_state.department, ml_result, test_scores, results)

                    unis = UNIVERSITY_MAP.get(ml_result["career_path"], [])

                    mentor_prompt = f"""List 4 realistic Nigerian professionals in {ml_result['career_path']}.
        Return a JSON array only. Each item is a string:
        "[Full Name] — [Job Title] at [Nigerian Organisation] — [One sentence: why they are a good mentor]"
        Return ONLY the JSON array. No markdown, no extra text."""
                    try:
                        mr  = gemini_client.models.generate_content(
                            model=GEMINI_MODEL, contents=mentor_prompt,
                            config=types.GenerateContentConfig(max_output_tokens=300, temperature=0.6))
                        raw = mr.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                        mentors = json.loads(raw)
                    except Exception:
                        mentors = [
                            f"Dr. Chukwuemeka Eze — Senior Professional at NNPC — Dedicated mentor with 15+ years experience",
                            f"Mrs. Ngozi Adeyemi — Director, Federal Ministry of Nigeria — Passionate about youth career development",
                            f"Mr. Oluwaseun Bello — Lead Consultant, Lagos — Known for mentoring secondary school students",
                            f"Prof. Amina Suleiman — University of Abuja — Active researcher and student career advocate",
                        ]

                    save_recommendation(st.session_state.user_id, ml_result["career_path"],
                                        ml_result["confidence"], unis, mentors,
                                        narrative, ml_result["top3"])
                    conn2 = sqlite3.connect("career_portal.db")
                    conn2.execute("DELETE FROM chat_history WHERE user_id=?", (st.session_state.user_id,))
                    conn2.commit(); conn2.close()

                    st.session_state.rec_cache  = get_recommendation(st.session_state.user_id)
                    st.session_state.chat_cache = None
                    st.success("✅ Recommendation generated!")
                    st.rerun()

            if not existing:
                st.info("👆 Click **🚀 Generate My Career Recommendations** above to see your personalised career path.")
                return

            rec    = existing
            career = rec["career_path"]
            conf   = rec["confidence"]
            top3   = rec["top3"]
            unis   = rec["universities"]
            mentors= rec["mentors"]
            narr   = rec["narrative"]
            gen_at = rec["generated_at"][:16].replace("T"," ")

            # Hero card
            st.markdown(f"""
            <div class="rec-hero">
                <h1>🎯 {career}</h1>
                <p>ML Confidence: <strong>{conf}%</strong> &nbsp;|&nbsp; Generated: {gen_at}
                &nbsp;|&nbsp; ✨ Powered by Gemini AI</p>
            </div>""", unsafe_allow_html=True)

            # Scores + Test results
            col_l, col_r = st.columns([3,2])
            with col_l:
                st.markdown("#### 📊 Career Match Confidence")
                medals = ["🥇","🥈","🥉"]
                for idx2, (cname, cprob) in enumerate(top3[:3]):
                    st.markdown(f"""
                    <div style="margin-bottom:14px;">
                        <div style="font-size:14px;font-weight:600;">{medals[idx2]} {cname}</div>
                        <div style="font-size:12px;color:gray;margin-bottom:3px;">{cprob}% match</div>
                        <div class="score-bar-bg">
                            <div class="score-bar-fill" style="width:{int(cprob)}%;"></div>
                        </div>
                    </div>""", unsafe_allow_html=True)

            with col_r:
                st.markdown("#### 📝 Your Test Scores")
                for tlabel, tkey in [("🧩 Cognitive","cognitive"),("🎯 Aptitude","aptitude"),
                                        ("🧠 Psychometric","psychometric"),("💬 Sentiment","sentiment")]:
                    sc = st.session_state.test_scores.get(tkey, "—")
                    sv = f"{sc}%" if isinstance(sc,(int,float)) else sc
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;padding:6px 0;
                            border-bottom:1px solid #f0f0f0;font-size:14px;">
                        <span>{tlabel}</span><strong>{sv}</strong>
                    </div>""", unsafe_allow_html=True)

            st.divider()

            # Narrative
            st.markdown("## 📋 **Your Personalised Career Report**")
            st.markdown(narr)
            st.divider()

            # Universities
            st.markdown("#### 🏛️ Recommended Nigerian Universities")
            st.caption(f"Top institutions offering programmes in **{career}**")
            if unis:
                uc1, uc2 = st.columns(2)
                for idx2, u in enumerate(unis[:4]):
                    with (uc1 if idx2%2==0 else uc2):
                        st.markdown(f"""
                        <div class="uni-card">
                            <div style="font-weight:700;font-size:15px;">🏛️ {u['name']}</div>
                            <div style="font-size:13px;color:#1a3c8f;margin:3px 0;">📚 {u['course']}</div>
                            <div style="font-size:12px;color:#444;">🎯 JAMB Cutoff: <strong>{u.get('cutoff','200+')}</strong></div>
                            <div style="font-size:12px;color:gray;margin-top:2px;">📍 {u.get('location','Nigeria')}</div>
                            <a href="{u.get('url','#')}" target="_blank"
                                style="font-size:12px;color:#2d6cdf;text-decoration:none;">
                                🌐 Visit Website ↗</a>
                        </div>""", unsafe_allow_html=True)
            else:
                st.info("University data not available for this career path.")

            st.divider()

            # LinkedIn Mentors
            st.markdown("#### 👥 Suggested LinkedIn Mentors")
            st.caption("Nigerian professionals in your recommended career field — search them on LinkedIn")
            if mentors:
                for m in mentors[:4]:
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:12px 16px;
                            margin-bottom:10px;box-shadow:0 2px 8px rgba(0,0,0,0.06);
                            border-left:4px solid #2d6cdf;font-size:13px;">
                        👤 {m}
                    </div>""", unsafe_allow_html=True)

            st.divider()

            # Chatbot
            st.markdown("#### 💬 Ask Your AI Career Counsellor")
            st.caption("Questions about your recommendation, JAMB scores, university options, or career paths? Ask below!")

            rec = st.session_state.rec_cache or get_recommendation(st.session_state.user_id)
            
            student_ctx = f"""
            Name: {st.session_state.full_name}
            Class: {st.session_state.class_level}
            Department: {st.session_state.department}

            Career Recommendation: {rec['career_path']}
            Confidence: {rec['confidence']}%

            Top 3 Careers: {rec['top3']}

            """

            if st.session_state.chat_cache is None:
                st.session_state.chat_cache = get_chat_history(st.session_state.user_id)
            chat_history = st.session_state.chat_cache

            if not chat_history:
                st.markdown(f"""
                <div class="chat-ai">
                    Hi {st.session_state.full_name}! 👋 I'm your AI career counsellor, powered by Gemini.
                    I've reviewed your full profile and recommended <strong>{career}</strong> for you.
                    Do you have questions about this career, JAMB subject choices, university cut-offs,
                    or how to prepare? I'm here to help! 😊
                </div>""", unsafe_allow_html=True)
            else:
                for role, msg in chat_history:
                    css = "chat-user" if role=="user" else "chat-ai"
                    st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)

            with st.form("chat_form", clear_on_submit=True):
                user_input = st.text_input(
                    "Your message",
                    placeholder="e.g. What JAMB score do I need for UNILAG Medicine?",
                    label_visibility="collapsed")
                if st.form_submit_button("Send 💬", type="primary") and user_input.strip():
                    with st.spinner("Thinking..."):
                        reply = get_chatbot_response(user_input.strip(), student_ctx, chat_history)
                    save_chat_message(st.session_state.user_id, "user",      user_input.strip())
                    save_chat_message(st.session_state.user_id, "assistant", reply)
                    st.session_state.chat_cache = get_chat_history(st.session_state.user_id)
                    st.rerun()
            pass


        return

    # ====================== AUTHENTICATION PAGE (Not Logged In) ======================
    st.markdown("""
        <div class="hero-banner">
            <h1 class="hero-title">🎓 Student Career Portal</h1>
            <p class="hero-subtitle">Smart Career Path Recommendation for Nigerian Secondary Students</p>
        </div>
    """, unsafe_allow_html=True)

    left_spacer, center_content, right_spacer = st.columns([1.1, 1.8, 1.1])
    
    with center_content:
        
        auth_tab = st.tabs(["🔒 Login", "📝 Create Account"])
    
        # ====================== LOGIN TAB ======================
        with auth_tab[0]:
            st.markdown('<div class="auth-title"><div class="auth-card">Login to Your Account</div>', unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=True): 
                email = st.text_input("Email Address", placeholder="student@example.com")
                password = st.text_input("Password", type="password")
                
                # Full width submission block handled via our CSS rules automatically
                submit_login = st.form_submit_button("Sign In")
                
                if submit_login:
                    if not email or not password:
                        st.error("Please enter both email and password.")
                    else:
                        user = login_user(email, password)
                        if user:
                            st.session_state.update({
                                "logged_in": True,
                                "user_id": user[0],
                                "full_name": user[1],
                                "class_level": user[2],
                                "department": user[3],
                                "active_test": None,
                                "test_answers": {},
                                "test_scores": {},
                                "all_tests_done": False,
                                "rec_cache": None,
                                "chat_cache": None
                            })
                            st.success(f"Welcome back, {user[1]}! 🎓")
                            st.rerun()
                        else:
                            st.error("Invalid email or password. Please try again.")

            st.markdown('</div>', unsafe_allow_html=True)
                            
        # ====================== SIGN UP TAB ======================
        with auth_tab[1]:
            st.markdown('<div class="auth-title"><div class="auth-card">Create New Account</div>', unsafe_allow_html=True)
            
            with st.form("signup_form", clear_on_submit=True):
                full_name = st.text_input("Full Name *")
                dob = st.date_input("Date of Birth", 
                                    max_value=datetime.date.today(), 
                                    min_value=datetime.date(1990, 1, 1))
                
                class_level = st.segmented_control(
                    "Class Level *", 
                    options=["SSS 1", "SSS 2", "SSS 3"],
                    default=None
                )
                st.caption('Select Department')
    
                department = st.segmented_control(
                    "Department *", 
                    options=["Science", "Arts", "Commercial"],
                    default=None
                )
    
                email = st.text_input("Email Address *")
                password = st.text_input("Password *", type="password")
                confirm = st.text_input("Confirm Password *", type="password")
                agree = st.checkbox("I agree to the Terms of Service")
    
                submit_signup = st.form_submit_button("Register Account")
                
                if submit_signup:
                    if not agree:
                        st.warning("You must agree to the terms.")
                    elif password != confirm:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.warning("Password must be at least 6 characters long.")
                    elif not full_name or not email:
                        st.warning("Please fill all required fields.")
                    elif class_level in ["SSS 1", "SSS 2", "SSS 3"] and not department:
                        st.warning("Please select your department.")
                    else:
                        dept_to_save = department if class_level in ["SSS 1", "SSS 2", "SSS 3"] else None
                        
                        if create_user(full_name, dob, class_level, dept_to_save, email, password):
                            st.success("🎉 Account created successfully!")
                            st.balloons()
                            st.info("Please go to the Login tab and sign in.")
                        else:
                            st.error("An account with this email already exists.")
                            
            st.markdown('</div>', unsafe_allow_html=True) 


# Call the app
if __name__ == "__main__":
    init_db()
    remove_duplicate_results()
    app()
