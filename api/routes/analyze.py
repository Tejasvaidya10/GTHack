"""POST /api/analyze — Full pipeline analysis of a transcript."""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.extraction import extract_patient_summary, extract_clinician_note
from core.clinical_trials import find_relevant_trials
from core.literature_search import search_literature
from core.phi_redaction import redact_phi
from models.schemas import VisitRecord
from models.database import save_visit

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request body for /api/analyze."""
    transcript: str
    visit_date: Optional[str] = None
    visit_type: str = ""
    tags: list[str] = []
    include_trials: bool = True
    include_literature: bool = True


@router.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Run full analysis pipeline on a transcript.

    Extracts patient summary, clinician SOAP note,
    and optionally searches clinical trials and literature.
    Saves everything to the database.
    """
    if not req.transcript or not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    try:
        # HIPAA: Re-run PHI redaction to ensure no raw PHI is processed or stored,
        # even if the caller sends unredacted text
        redaction = redact_phi(req.transcript)
        safe_transcript = redaction.redacted_text

        # Extract patient-facing summary
        logger.info("Extracting patient summary...")
        patient_summary = extract_patient_summary(safe_transcript)

        # Extract clinician SOAP note
        logger.info("Extracting clinician note...")
        clinician_note = extract_clinician_note(safe_transcript)

        # Extract conditions and drugs for trial/literature search
        conditions = clinician_note.soap_note.assessment.findings
        drugs = [med.name for med in patient_summary.medications]

        # Clinical trials search
        clinical_trials = []
        if req.include_trials and (conditions or drugs):
            logger.info("Searching clinical trials...")
            try:
                clinical_trials = find_relevant_trials(conditions, drugs)
            except Exception as e:
                logger.warning(f"Clinical trials search failed: {e}")

        # Literature search
        literature_results = []
        if req.include_literature and (conditions or drugs):
            logger.info("Searching literature...")
            try:
                literature_results = search_literature(conditions, drugs)
            except Exception as e:
                logger.warning(f"Literature search failed: {e}")

        # Parse visit date
        visit_date = None
        if req.visit_date:
            try:
                visit_date = date.fromisoformat(req.visit_date)
            except ValueError:
                visit_date = date.today()
        else:
            visit_date = date.today()

        # Save to database
        visit = VisitRecord(
            visit_date=visit_date,
            visit_type=req.visit_type,
            tags=req.tags,
            raw_transcript=safe_transcript,  # HIPAA: only store redacted text
            patient_summary=patient_summary,
            clinician_note=clinician_note,
            clinical_trials=clinical_trials,
            literature_results=literature_results,
        )

        visit_id = save_visit(visit)
        logger.info(f"Visit saved with ID: {visit_id}")

        return {
            "visit_id": visit_id,
            "patient_summary": patient_summary.model_dump(),
            "clinician_note": clinician_note.model_dump(),
            "clinical_trials": [t.model_dump() for t in clinical_trials],
            "literature": [r.model_dump() for r in literature_results],
        }

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
