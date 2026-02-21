"""CRUD endpoints for visits."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.database import get_visit, get_all_visits, delete_visit
from api.dependencies import visit_not_found

router = APIRouter()


@router.get("/api/visits")
async def list_visits(
    search: Optional[str] = Query(None, description="Full-text search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    sort: str = Query("date", description="Sort order: date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all visits with optional search, tag filter, and pagination."""
    visits = get_all_visits(search=search, tag=tag, sort=sort, limit=limit, offset=offset)
    return {
        "visits": [v.model_dump() for v in visits],
        "count": len(visits),
        "offset": offset,
        "limit": limit,
    }


@router.get("/api/visits/{visit_id}")
async def get_visit_detail(visit_id: int):
    """Get full details for a specific visit."""
    visit = get_visit(visit_id)
    if not visit:
        visit_not_found(visit_id)
    return visit.model_dump()


@router.delete("/api/visits/{visit_id}")
async def delete_visit_endpoint(visit_id: int):
    """Delete a visit by ID."""
    deleted = delete_visit(visit_id)
    if not deleted:
        visit_not_found(visit_id)
    return {"message": f"Visit {visit_id} deleted"}
