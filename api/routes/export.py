"""GET /api/export/{visit_id}/pdf — PDF export."""

import os
import tempfile

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from models.database import get_visit
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
