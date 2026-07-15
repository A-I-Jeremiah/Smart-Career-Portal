# backend/routers/results_router.py
"""Academic results CRUD routes."""
import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models.schemas import AcademicResultIn, AcademicResultOut
from ..auth import get_current_user
from .. import database as db

router = APIRouter(prefix="/results", tags=["Academic Results"])


@router.get("/", response_model=List[AcademicResultOut])
def get_results(current_user: dict = Depends(get_current_user)):
    """Get all academic results for the logged-in user."""
    return db.get_user_results(current_user["id"])


@router.post("/", response_model=AcademicResultOut, status_code=201)
def add_result(result: AcademicResultIn, current_user: dict = Depends(get_current_user)):
    """Manually add a single academic result."""
    exam_date = result.exam_date or str(datetime.date.today())
    inserted = db.save_academic_result(
        user_id=current_user["id"],
        result_type=result.result_type,
        subject=result.subject,
        score=result.score,
        exam_date=exam_date,
    )
    if not inserted:
        raise HTTPException(status_code=409, detail="Duplicate result entry.")

    # Fetch the inserted row to return it
    rows = db.get_user_results(current_user["id"])
    for row in rows:
        if (row["result_type"] == result.result_type
                and row["subject"] == result.subject
                and row["score"] == result.score):
            return row
    raise HTTPException(status_code=500, detail="Could not retrieve saved result.")


@router.delete("/{result_id}", status_code=204)
def delete_result(result_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a specific academic result owned by the logged-in user."""
    db.delete_academic_result(result_id, current_user["id"])
