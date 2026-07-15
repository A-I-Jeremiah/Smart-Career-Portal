# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level above backend/)
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── Paths ────────────────────────────────────────────────────────────────────
MODEL_PATH         = ROOT_DIR / "backend" / "models" / "xgb_best_model.pkl"
LABEL_ENCODER_PATH = ROOT_DIR / "backend" / "models" / "label_encoder.pkl"
DATABASE_PATH      = str(ROOT_DIR / "career_portal.db")

# ── Gemini ───────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"

# ── JWT ──────────────────────────────────────────────────────────────────────
SECRET_KEY        = os.getenv("SECRET_KEY", "smart-career-portal-secret-key-2025")
ALGORITHM         = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours