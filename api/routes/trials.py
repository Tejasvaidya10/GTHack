"""GET /api/trials/{visit_id} — Clinical trials for a visit."""

from fastapi import APIRouter, HTTPException

from models.database import get_visit
from core.clinical_trials import find_relevant_trials
from api.dependencies import visit_not_found

router = APIRouter()


@router.get("/api/trials/{visit_id}")
async def get_trials(visit_id: int):
    """Get relevant clinical trials for a visit's conditions and medications."""
    visit = get_visit(visit_id)
    if not visit:
        visit_not_found(visit_id)

    # Extract conditions and drugs from visit data
    conditions = []
    drugs = []

    if visit.clinician_note:
        conditions = visit.clinician_note.soap_note.assessment.findings
    if visit.patient_summary:
        drugs = [med.name for med in visit.patient_summary.medications]

    if not conditions and not drugs:
        return []

    trials = find_relevant_trials(conditions, drugs)
    return [t.model_dump() for t in trials]
