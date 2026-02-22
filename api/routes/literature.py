"""GET /api/literature/{visit_id} — Semantic Scholar papers for a visit."""

import json

from fastapi import APIRouter, HTTPException, Query

from models.database import get_visit, _get_connection
from core.literature_search import search_literature
from api.dependencies import visit_not_found

router = APIRouter()


@router.get("/api/literature/{visit_id}")
async def get_literature(
    visit_id: int,
    refresh: bool = Query(False, description="Force new search instead of cached results"),
):
    """Get relevant literature for a visit's conditions and medications.

    Uses boosted keywords from feedback history to improve search quality.
    Use ?refresh=true to force a new search.
    """
    visit = get_visit(visit_id)
    if not visit:
        visit_not_found(visit_id)

    # Return cached results if available and refresh not requested
    if not refresh and visit.literature_results:
        return [r.model_dump() for r in visit.literature_results]

    # Extract conditions and drugs
    conditions = []
    drugs = []

    if visit.clinician_note:
        conditions = visit.clinician_note.soap_note.assessment.findings
    if visit.patient_summary:
        drugs = [med.name for med in visit.patient_summary.medications]

    if not conditions and not drugs:
        return []

    papers = search_literature(conditions, drugs)

    # Update cached results in database
    if papers:
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE visits SET literature_results_json = ? WHERE id = ?",
                (json.dumps([p.model_dump() for p in papers]), visit_id),
            )
            conn.commit()
        finally:
            conn.close()

    return [r.model_dump() for r in papers]
