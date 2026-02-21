"""Feedback endpoints — submit, retrieve, and analytics."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.feedback import submit_feedback, get_feedback_for_visit, get_feedback_analytics
from models.schemas import FeedbackItem

router = APIRouter()


class FeedbackRequest(BaseModel):
    """Request body for POST /api/feedback."""
    visit_id: int
    feedback_type: str  # "extraction_accuracy" or "literature_relevance"
    item_type: str
    item_value: str
    rating: str
    paper_url: Optional[str] = None
    clinician_note: Optional[str] = None


@router.post("/api/feedback")
async def post_feedback(req: FeedbackRequest):
    """Submit clinician feedback on an extraction or literature recommendation."""
    # Validate feedback_type
    if req.feedback_type not in ("extraction_accuracy", "literature_relevance"):
        raise HTTPException(
            status_code=400,
            detail="feedback_type must be 'extraction_accuracy' or 'literature_relevance'",
        )

    # Validate rating
    valid_ratings = {
        "extraction_accuracy": {"correct", "incorrect", "missing"},
        "literature_relevance": {"relevant", "not_relevant"},
    }
    if req.rating not in valid_ratings[req.feedback_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating '{req.rating}' for {req.feedback_type}. "
                   f"Valid: {valid_ratings[req.feedback_type]}",
        )

    feedback = FeedbackItem(
        visit_id=req.visit_id,
        feedback_type=req.feedback_type,
        item_type=req.item_type,
        item_value=req.item_value,
        rating=req.rating,
        paper_url=req.paper_url,
        clinician_note=req.clinician_note,
    )

    feedback_id = submit_feedback(feedback)
    return {"feedback_id": feedback_id, "message": "Feedback recorded"}


@router.get("/api/feedback/analytics")
async def feedback_analytics():
    """Get aggregated feedback analytics."""
    analytics = get_feedback_analytics()
    return analytics.model_dump()


@router.get("/api/feedback/{visit_id}")
async def get_visit_feedback(visit_id: int):
    """Get all feedback for a specific visit."""
    items = get_feedback_for_visit(visit_id)
    return {
        "visit_id": visit_id,
        "feedback": [item.model_dump() for item in items],
        "count": len(items),
    }
