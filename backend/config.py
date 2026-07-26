# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level above backend/)
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
# Platform-provided environment variables must win in production. Locally,
# .env still supplies values that are not already exported in the shell.
load_dotenv(ENV_PATH, override=False)

# ── Paths ────────────────────────────────────────────────────────────────────
MODEL_PATH         = ROOT_DIR / "backend" / "models" / "xgb_best_model.pkl"
LABEL_ENCODER_PATH = ROOT_DIR / "backend" / "models" / "label_encoder.pkl"
DATABASE_PATH      = str(ROOT_DIR / "career_portal.db")

# ── Gemini ───────────────────────────────────────────────────────────────────
def _clean_env_value(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    return cleaned


GOOGLE_API_KEY = _clean_env_value(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


# ── JWT ──────────────────────────────────────────────────────────────────────
SECRET_KEY        = os.getenv("SECRET_KEY", "smart-career-portal-secret-key-2025")
ALGORITHM         = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ── Department alignment filter (post-processing) ───────────────────────────
DEPT_FILTER_ENABLED = os.getenv("DEPT_FILTER_ENABLED", "true").lower() == "true"
DEPT_PRIMARY_BOOST = float(os.getenv("DEPT_PRIMARY_BOOST", "4.0"))
DEPT_SECONDARY_BOOST = float(os.getenv("DEPT_SECONDARY_BOOST", "1.5"))
DEPT_CROSS_PENALTY = float(os.getenv("DEPT_CROSS_PENALTY", "0.05"))
DEPT_HARD_BLOCK_CROSS = os.getenv("DEPT_HARD_BLOCK_CROSS", "false").lower() == "true"
DEPT_CROSS_OVERRIDE_RAW_CONF = float(os.getenv("DEPT_CROSS_OVERRIDE_RAW_CONF", "0.60"))
DEPT_TOP_K = int(os.getenv("DEPT_TOP_K", "3"))
