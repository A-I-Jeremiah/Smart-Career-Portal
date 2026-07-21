# backend/routers/history_router.py
"""Recommendation history and AI chatbot routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from google import genai
from google.genai import types

from ..models.schemas import RecommendationResponse, ChatMessageIn, ChatMessageOut
from ..auth import get_current_user
from ..config import GOOGLE_API_KEY, GEMINI_MODEL
from .. import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History & Chat"])

def _get_gemini():
    if not GOOGLE_API_KEY:
        return None
    return genai.Client(api_key=GOOGLE_API_KEY)


@router.get("/recommendation", response_model=RecommendationResponse)
def get_recommendation(current_user: dict = Depends(get_current_user)):
    """Fetch the latest saved recommendation for the logged-in user."""
    rec = db.get_recommendation(current_user["id"])
    if not rec:
        raise HTTPException(status_code=404, detail="No recommendation found. Run /predict first.")
    return RecommendationResponse(
        career_path  = rec["career_path"],
        confidence   = rec["confidence"],
        top3         = rec["top3"],
        universities = rec["universities"],
        mentors      = rec["mentors"],
        narrative    = rec["narrative"],
        generated_at = rec["generated_at"],
    )


@router.get("/chat", response_model=List[ChatMessageOut])
def get_chat(current_user: dict = Depends(get_current_user)):
    """Fetch chat history for the logged-in user."""
    return db.get_chat_history(current_user["id"])


@router.post("/chat", response_model=ChatMessageOut)
def send_chat(msg: ChatMessageIn, current_user: dict = Depends(get_current_user)):
    """Send a message to the AI career counsellor and get a reply."""
    rec = db.get_recommendation(current_user["id"])
    if not rec:
        raise HTTPException(status_code=404, detail="Generate a recommendation first.")

    history = db.get_chat_history(current_user["id"], limit=40)

    user_msg = msg.message.lower()
    if "jamb" in user_msg:
        focus = "Focus on JAMB subjects, cutoff marks, and preparation strategy."
    elif "university" in user_msg:
        focus = "Recommend Nigerian universities and admission strategy."
    elif "career" in user_msg:
        focus = "Explain career paths and real-world roles in Nigeria."
    else:
        focus = "Give practical career guidance."

    system_ctx = f"""You are a highly experienced Nigerian career counsellor.

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
{focus}

STUDENT DATA:
Name: {current_user['full_name']}
Class: {current_user['class_level']}
Department: {current_user.get('department', 'N/A')}
Career Recommendation: {rec['career_path']}
Confidence: {rec['confidence']}%
Top 3 Careers: {rec['top3']}
"""

    gemini_history = [
        types.Content(
            role="user" if r["role"] == "user" else "model",
            parts=[types.Part(text=r["message"])]
        )
        for r in history[-6:]
    ]

    try:
        gemini = _get_gemini()
        if gemini is None:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        chat = gemini.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_ctx,
                max_output_tokens=350,
                temperature=0.7,
            ),
            history=gemini_history[:-1] if len(gemini_history) > 1 else [],
        )
        resp = chat.send_message(msg.message)
        reply = (resp.text or "").strip()
        if not reply:
            raise RuntimeError(f"Gemini returned an empty response: {resp}")
        if len(reply.split()) > 220:
            reply = " ".join(reply.split()[:220]) + "..."
    except Exception as e:
        # Log the FULL error so failures are visible in server logs instead
        # of always showing the same generic message to the student.
        logger.exception("Gemini chat call failed for user %s: %s", current_user["id"], e)
        reply = "Sorry, something went wrong. Please try again."

    db.save_chat_message(current_user["id"], "user", msg.message)
    db.save_chat_message(current_user["id"], "assistant", reply)

    return ChatMessageOut(role="assistant", message=reply)


@router.delete("/chat", status_code=204)
def clear_chat(current_user: dict = Depends(get_current_user)):
    """Clear chat history for the logged-in user."""
    db.clear_chat_history(current_user["id"])
