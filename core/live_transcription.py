"""Live transcription with chunked Whisper processing.

Buffers audio chunks from the browser, transcribes each with Whisper,
applies PHI redaction, and accumulates results across chunks.
"""

import asyncio
import os
import logging
import tempfile
import time
from dataclasses import dataclass, field
from typing import Optional

from core.transcription import transcribe_audio
from core.phi_redaction import redact_phi
from models.schemas import TranscriptSegment

logger = logging.getLogger(__name__)

LIVE_TEMP_DIR = os.path.join(tempfile.gettempdir(), "medsift_live")


@dataclass
class ChunkResult:
    """Result from processing a single audio chunk."""
    chunk_index: int
    text: str
    segments: list[TranscriptSegment]
    entity_count: dict[str, int]


@dataclass
class SessionState:
    """State for a live transcription session."""
    session_id: str
    full_segments: list[TranscriptSegment] = field(default_factory=list)
    full_text_blocks: list[str] = field(default_factory=list)
    chunk_index: int = 0
    cumulative_offset: float = 0.0
    total_duration: float = 0.0
    last_active: float = field(default_factory=time.monotonic)


# Module-level session registry
_sessions: dict[str, SessionState] = {}

SESSION_TIMEOUT_SECONDS = 1800  # 30 minutes


def create_session(session_id: str) -> SessionState:
    """Create a new live transcription session."""
    _cleanup_expired_sessions()
    session = SessionState(session_id=session_id)
    _sessions[session_id] = session
    logger.info(f"Live session created: {session_id}")
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    """Get an existing session by ID."""
    return _sessions.get(session_id)


def cleanup_session(session_id: str) -> None:
    """Remove a session and its temp files."""
    _sessions.pop(session_id, None)
    # Clean up any remaining temp files for this session
    if os.path.exists(LIVE_TEMP_DIR):
        for f in os.listdir(LIVE_TEMP_DIR):
            if f.startswith(session_id):
                try:
                    os.remove(os.path.join(LIVE_TEMP_DIR, f))
                except OSError:
                    pass
    logger.info(f"Live session cleaned up: {session_id}")


def _cleanup_expired_sessions() -> None:
    """Remove sessions that have been inactive for too long."""
    now = time.monotonic()
    expired = [
        sid for sid, s in _sessions.items()
        if now - s.last_active > SESSION_TIMEOUT_SECONDS
    ]
    for sid in expired:
        cleanup_session(sid)


async def process_audio_chunk(
    session_id: str,
    raw_audio_bytes: bytes,
) -> ChunkResult:
    """Process a single audio chunk from the browser.

    Writes the WebM bytes to a temp file, transcribes with Whisper in a
    thread pool, applies PHI redaction, and accumulates results in the
    session state.
    """
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    session.last_active = time.monotonic()
    os.makedirs(LIVE_TEMP_DIR, exist_ok=True)

    chunk_idx = session.chunk_index
    tmp_path = os.path.join(LIVE_TEMP_DIR, f"{session_id}_{chunk_idx}.webm")

    # Write raw WebM/Opus bytes from browser to temp file
    with open(tmp_path, "wb") as f:
        f.write(raw_audio_bytes)

    try:
        # Run blocking Whisper call in thread pool
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(
            None, lambda: transcribe_audio(tmp_path)
        )
    finally:
        # HIPAA: delete temp audio immediately
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Adjust timestamps to cumulative offset
    offset_segments = []
    for seg in transcription.segments:
        offset_segments.append(TranscriptSegment(
            start_time=seg.start_time + session.cumulative_offset,
            end_time=seg.end_time + session.cumulative_offset,
            text=seg.text,
        ))

    # PHI redaction on each segment
    redacted_segments = []
    total_entity_count: dict[str, int] = {}
    for seg in offset_segments:
        result = redact_phi(seg.text)
        redacted_segments.append(TranscriptSegment(
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=result.redacted_text,
        ))
        for etype, count in result.entity_count.items():
            total_entity_count[etype] = total_entity_count.get(etype, 0) + count

    # Update cumulative offset for next chunk
    if transcription.duration_seconds > 0:
        session.cumulative_offset += transcription.duration_seconds

    # Accumulate results
    session.full_segments.extend(redacted_segments)
    chunk_text = " ".join(seg.text for seg in redacted_segments)
    session.full_text_blocks.append(chunk_text)
    session.total_duration += transcription.duration_seconds
    session.chunk_index += 1

    return ChunkResult(
        chunk_index=chunk_idx,
        text=chunk_text,
        segments=redacted_segments,
        entity_count=total_entity_count,
    )


def finalize_session(session_id: str) -> Optional[dict]:
    """Finalize a session and return the complete transcript."""
    session = get_session(session_id)
    if session is None:
        return None

    segments = session.full_segments
    full_transcript = " ".join(seg.text for seg in segments)

    return {
        "full_transcript": full_transcript,
        "segments": [
            {"start_time": s.start_time, "end_time": s.end_time, "text": s.text}
            for s in segments
        ],
        "duration_seconds": round(session.total_duration, 2),
        "total_chunks": session.chunk_index,
    }
