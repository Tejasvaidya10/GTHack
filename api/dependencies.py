"""Shared dependencies for API routes."""

import os
import tempfile
from typing import Optional

from fastapi import HTTPException


def get_temp_dir() -> str:
    """Get a temporary directory for file uploads."""
    tmp = os.path.join(tempfile.gettempdir(), "medsift_uploads")
    os.makedirs(tmp, exist_ok=True)
    return tmp


def visit_not_found(visit_id: int):
    """Raise 404 for missing visit."""
    raise HTTPException(status_code=404, detail=f"Visit {visit_id} not found")
