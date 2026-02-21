"""PDF export endpoints."""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models.database import get_visit
from models.schemas import (
    PatientSummary, ClinicianNote, VisitRecord,
    Medication, TestOrdered, FollowUpItem,
    LifestyleRecommendation, RedFlagForPatient, QAItem,
)
from core.pdf_generator import generate_after_visit_summary
from api.dependencies import visit_not_found

router = APIRouter()


@router.get("/api/export/{visit_id}/pdf")
async def export_pdf(
    visit_id: int,
    include_soap: bool = Query(False, description="Include SOAP note in PDF"),
):
    """Generate and return an After Visit Summary PDF."""
    visit = get_visit(visit_id)
    if not visit:
        visit_not_found(visit_id)

    tmp_dir = tempfile.mkdtemp(prefix="medsift_pdf_")
    output_path = os.path.join(tmp_dir, f"visit_{visit_id}_summary.pdf")

    try:
        generate_after_visit_summary(visit, output_path, include_soap=include_soap)
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=f"MedSift_Visit_{visit_id}_Summary.pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


class ReviewedExportRequest(BaseModel):
    """Request body for doctor-reviewed PDF export."""
    visit_id: int
    approved_summary: dict
    include_soap: bool = False


@router.post("/api/export/reviewed/pdf")
async def export_reviewed_pdf(req: ReviewedExportRequest):
    """Generate PDF from doctor-reviewed/approved patient summary.

    The doctor reviews extracted items and removes anything incorrect
    before this endpoint generates the patient-facing PDF.
    """
    visit = get_visit(req.visit_id)
    if not visit:
        visit_not_found(req.visit_id)

    # Build a VisitRecord with the doctor-approved summary
    approved_ps = PatientSummary.model_validate(req.approved_summary)
    reviewed_visit = visit.model_copy(update={"patient_summary": approved_ps})

    tmp_dir = tempfile.mkdtemp(prefix="medsift_pdf_")
    output_path = os.path.join(tmp_dir, f"visit_{req.visit_id}_reviewed.pdf")

    try:
        generate_after_visit_summary(
            reviewed_visit, output_path, include_soap=req.include_soap,
        )
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=f"MedSift_Visit_{req.visit_id}_Summary.pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
