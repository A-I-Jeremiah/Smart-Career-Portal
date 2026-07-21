"""Shared Gemini helpers for API routes."""
from google import genai

from .config import GEMINI_MODEL, GOOGLE_API_KEY


def get_gemini_client():
    if not GOOGLE_API_KEY:
        return None
    return genai.Client(api_key=GOOGLE_API_KEY.strip())


def gemini_error_detail(exc: Exception) -> str:
    """Return a safe, user-facing reason without leaking credentials."""
    text = str(exc)
    lowered = text.lower()

    if "api_key" in lowered or "api key" in lowered or "permission" in lowered or "403" in lowered:
        return "Gemini rejected the server API key. Check GOOGLE_API_KEY on the FastAPI Render service."
    if "not found" in lowered or "404" in lowered or "model" in lowered:
        return f"Gemini model '{GEMINI_MODEL}' is unavailable for this API key. Use gemini-2.5-flash."
    if "quota" in lowered or "rate" in lowered or "429" in lowered:
        return "Gemini quota or rate limit was reached. Check the Google AI Studio quota/billing for this key."
    if "timeout" in lowered or "connection" in lowered or "network" in lowered:
        return "The server could not connect to Gemini from Render. Try again shortly."

    return "Gemini returned an unexpected error. Check the Render FastAPI logs for the full exception."
