"""Dynamic assessment routes backed by backend/questions_engine."""
import json
import re
from pathlib import Path
from random import Random, SystemRandom

from fastapi import APIRouter, Depends, HTTPException

from .. import database as db
from ..auth import get_current_user
from ..models.schemas import CompletedTestsResponse, TestScoreResponse, TestSubmitRequest

router = APIRouter(prefix="/tests", tags=["Tests"])

QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "questions_engine" / "assessment_questions.json"

TEST_CATEGORY_MAP = {
    "aptitude": "aptitude",
    "cognitive": "cognitive",
    "psychometric": "psychometric",
    "sentiment": "personality",
}

LIKERT_VALUES = {
    "strongly disagree": 1.0,
    "disagree": 2.0,
    "neutral": 3.0,
    "agree": 4.0,
    "strongly agree": 5.0,
    "never": 1.0,
    "sometimes": 2.0,
    "often": 4.0,
    "always": 5.0,
}


def _load_question_bank() -> list[dict]:
    if not QUESTIONS_PATH.exists():
        raise HTTPException(status_code=500, detail="Question bank file not found.")
    with QUESTIONS_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="Question bank is invalid.")
    return data


def _subject_category(department: str | None) -> str:
    if department == "Arts":
        return "Arts"
    if department == "Commercial":
        return "Commercial"
    return "Science"


def _clean_prompt(prompt: str) -> str:
    if not isinstance(prompt, str):
        return prompt
    clean = re.sub(
        r"\b(?:Science|Arts|Commercial)\s+(?:Aptitude|Cognitive|Psychometric|Personality)\s+Q\d+\s*:\s*",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\bQ\d+\s*:\s*", "", clean, flags=re.IGNORECASE)
    return clean.strip()


def _candidate_questions(test_type: str, department: str | None) -> list[dict]:
    category = TEST_CATEGORY_MAP.get(test_type)
    if not category:
        raise HTTPException(status_code=400, detail="Invalid test type.")

    bank = _load_question_bank()
    subject_category = _subject_category(department)
    questions = [
        q for q in bank
        if q.get("category") == category
        and q.get("options")
        and q.get("prompt")
        and q.get("subject_category") in (subject_category, "General", None)
    ]
    if len(questions) < 10:
        questions = [
            q for q in bank
            if q.get("category") == category and q.get("options") and q.get("prompt")
        ]
    if len(questions) < 10:
        raise HTTPException(status_code=500, detail=f"Not enough {test_type} questions in bank.")
    return list(questions)


def _answer_text(question: dict, submitted_value) -> str:
    options = list(question.get("options", []))
    if isinstance(submitted_value, int):
        return str(options[submitted_value]) if 0 <= submitted_value < len(options) else ""
    return str(submitted_value)


@router.get("/", response_model=CompletedTestsResponse)
def get_test_status(current_user: dict = Depends(get_current_user)):
    completed = db.get_completed_tests(current_user["id"])
    scores = db.get_test_scores(current_user["id"])
    return CompletedTestsResponse(completed=list(completed), scores=scores)


@router.get("/{test_type}/questions")
def get_questions(test_type: str, current_user: dict = Depends(get_current_user)):
    """Return a fresh shuffled set of 10 questions for a test category."""
    questions = _candidate_questions(test_type, current_user.get("department"))
    seeded_value = f"{current_user.get('id')}|{test_type}|{SystemRandom().randint(1, 10**18)}"
    rng = Random(seeded_value)
    rng.shuffle(questions)

    selected = []
    seen_prompts = set()
    for question in questions:
        if len(selected) >= 10:
            break

        prompt_text = _clean_prompt(str(question.get("prompt", "")))
        if prompt_text in seen_prompts:
            continue

        options = list(question.get("options", []))
        rng.shuffle(options)
        selected.append({
            "id": question["id"],
            "text": prompt_text,
            "options": options,
            "category": question["category"],
        })
        seen_prompts.add(prompt_text)

    if len(selected) < 10:
        # Fall back to the first 10 questions if enough unique prompts are not available
        selected = []
        for question in questions[:10]:
            options = list(question.get("options", []))
            rng.shuffle(options)
            selected.append({
                "id": question["id"],
                "text": _clean_prompt(str(question.get("prompt", ""))),
                "options": options,
                "category": question["category"],
            })

    return selected


@router.post("/submit", response_model=TestScoreResponse)
def submit_test(req: TestSubmitRequest, current_user: dict = Depends(get_current_user)):
    answers = req.answers or {}
    test_type = req.test_type
    category = TEST_CATEGORY_MAP.get(test_type)
    if not category:
        raise HTTPException(status_code=400, detail="Invalid test type.")

    bank = _load_question_bank()
    question_map = {q.get("id"): q for q in bank if q.get("category") == category}
    answered = [(qid, question_map.get(qid), value) for qid, value in answers.items()]
    answered = [(qid, q, value) for qid, q, value in answered if q]

    if not answered:
        raise HTTPException(status_code=400, detail="No valid answers submitted.")

    if test_type in ("aptitude", "cognitive"):
        correct = 0
        for _qid, question, value in answered:
            selected = _answer_text(question, value).strip().lower()
            expected = str(question.get("answer", "")).strip().lower()
            if selected == expected:
                correct += 1
        score = round(correct / len(answered) * 10, 2)
        label = f"{score}/10"
    else:
        values = []
        for _qid, question, value in answered:
            selected = _answer_text(question, value).strip().lower()
            if selected in LIKERT_VALUES:
                values.append(LIKERT_VALUES[selected])
            elif isinstance(value, int):
                values.append(float(value + 1))
        score = round(sum(values) / len(values), 2) if values else 3.0
        label = f"{score}/5"

    db.save_test_responses(current_user["id"], test_type, answers, score)
    return TestScoreResponse(
        test_type=test_type,
        score=score,
        message=f"{test_type.capitalize()} test submitted! Score: {label}",
    )


@router.delete("/{test_type}", status_code=204)
def retake_test(test_type: str, current_user: dict = Depends(get_current_user)):
    db.save_test_responses(current_user["id"], test_type, {}, 0.0)
