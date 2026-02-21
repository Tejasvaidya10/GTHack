"""POST /api/transcribe — Audio transcription with PHI redaction."""

import os
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from core.transcription import transcribe_audio
from core.phi_redaction import redact_phi
from api.dependencies import get_temp_dir

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribe an audio file and redact PHI.

    Accepts audio file upload (multipart/form-data).
    Runs Whisper transcription then Presidio PHI redaction.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    supported = {".mp3", ".wav", ".m4a", ".webm", ".flac", ".ogg"}
    if ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Supported: {', '.join(sorted(supported))}",
        )

    # Save to temp file
    tmp_dir = get_temp_dir()
    tmp_path = os.path.join(tmp_dir, f"upload_{file.filename}")

    try:
        contents = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)

        # Transcribe
        transcription = transcribe_audio(tmp_path)

        # Redact PHI — this runs BEFORE any storage
        redaction = redact_phi(transcription.text)

        return {
            "transcript": transcription.text,
            "redacted_transcript": redaction.redacted_text,
            "redaction_log": [entry.model_dump() for entry in redaction.redaction_log],
            "segments": [seg.model_dump() for seg in transcription.segments],
            "duration": transcription.duration_seconds,
            "language": transcription.language,
            "entity_count": redaction.entity_count,
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
