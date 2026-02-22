"""GET /api/grounding/{visit_id} — Hallucination detection scores."""

from fastapi import APIRouter

from models.database import get_visit
from core.validation import compute_grounding_report
from api.dependencies import visit_not_found
from models.schemas import PatientSummary, ClinicianNote

router = APIRouter()


@router.get("/api/grounding/{visit_id}")
async def get_grounding(visit_id: int):
    """Compute grounding/hallucination detection scores for a visit."""
    visit = get_visit(visit_id)
    if not visit:
        visit_not_found(visit_id)

    ps = visit.patient_summary or PatientSummary()
    cn = visit.clinician_note or ClinicianNote()

    return compute_grounding_report(ps, cn, visit.raw_transcript)
