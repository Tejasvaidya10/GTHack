"""POST /api/transcribe — Audio transcription with PHI redaction."""

import hashlib
import json
import os
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from core.transcription import transcribe_audio
from core.phi_redaction import redact_phi
from api.dependencies import get_temp_dir

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Demo cache ────────────────────────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".demo_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _audio_hash(data: bytes) -> str:
    return "tr_" + hashlib.sha256(data).hexdigest()[:16]


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

        # Check demo cache by audio file hash
        audio_key = _audio_hash(contents)
        cache_path = os.path.join(CACHE_DIR, f"{audio_key}.json")
        if os.path.exists(cache_path):
            logger.info(f"Transcription cache HIT — {cache_path}")
            with open(cache_path) as f:
                return json.load(f)

        with open(tmp_path, "wb") as f:
            f.write(contents)

        # Transcribe
        transcription = transcribe_audio(tmp_path)

        # Redact PHI — this runs BEFORE any storage
        redaction = redact_phi(transcription.text)

        # Redact PHI from individual segments as well
        redacted_segments = []
        for seg in transcription.segments:
            seg_redaction = redact_phi(seg.text)
            redacted_segments.append({
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "text": seg_redaction.redacted_text,
            })

        # HIPAA: Only return redacted transcript — never expose raw PHI via API
        result = {
            "transcript": redaction.redacted_text,
            "redacted_transcript": redaction.redacted_text,
            "redaction_log": [entry.model_dump() for entry in redaction.redaction_log],
            "segments": redacted_segments,
            "duration": transcription.duration_seconds,
            "language": transcription.language,
            "entity_count": redaction.entity_count,
        }

        # Save to demo cache
        with open(cache_path, "w") as f:
            json.dump(result, f)
        logger.info(f"Transcription cache SAVED — {cache_path}")

        return result

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
