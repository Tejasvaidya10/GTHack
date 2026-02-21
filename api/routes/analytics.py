"""GET /api/analytics — Dashboard analytics."""

from fastapi import APIRouter

from models.database import get_analytics

router = APIRouter()


@router.get("/api/analytics")
async def analytics():
    """Get aggregated analytics for the dashboard."""
    summary = get_analytics()
    return summary.model_dump()
