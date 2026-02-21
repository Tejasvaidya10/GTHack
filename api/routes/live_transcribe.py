"""WebSocket endpoint for live transcription."""

import json
import uuid
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from core.live_transcription import (
    create_session, get_session, process_audio_chunk,
    finalize_session, cleanup_session,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/transcribe/live/session")
async def create_live_session():
    """Create a new live transcription session."""
    session_id = str(uuid.uuid4())
    create_session(session_id)
    return {"session_id": session_id}


@router.get("/api/transcribe/live/{session_id}/transcript")
async def get_live_transcript(session_id: str):
    """Get the finalized full transcript for a completed session."""
    result = finalize_session(session_id)
    if result is None:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})
    cleanup_session(session_id)
    return result


@router.websocket("/ws/transcribe/{session_id}")
async def websocket_transcribe(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live audio transcription.

    Protocol:
        Client -> Server: binary frames (WebM/Opus audio chunks)
        Client -> Server: text frame {"type": "stop"} to end session
        Server -> Client: {"type": "session_ready"}
        Server -> Client: {"type": "partial", "chunk_index", "text", "speaker", "entity_count"}
        Server -> Client: {"type": "final", "full_transcript", "duration_seconds"}
        Server -> Client: {"type": "error", "message"}
    """
    session = get_session(session_id)
    if session is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await websocket.send_json({"type": "session_ready", "session_id": session_id})
    logger.info(f"WebSocket connected: session {session_id}")

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                # Binary frame — audio chunk
                audio_bytes = message["bytes"]
                try:
                    result = await process_audio_chunk(session_id, audio_bytes)
                    await websocket.send_json({
                        "type": "partial",
                        "chunk_index": result.chunk_index,
                        "text": result.text,
                        "speaker": result.speaker,
                        "entity_count": result.entity_count,
                    })
                except Exception as e:
                    logger.error(f"Chunk processing error: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })

            elif "text" in message:
                # Text frame — control message
                try:
                    ctrl = json.loads(message["text"])
                    if ctrl.get("type") == "stop":
                        final = finalize_session(session_id)
                        await websocket.send_json({
                            "type": "final",
                            "session_id": session_id,
                            "full_transcript": final["full_transcript"] if final else "",
                            "duration_seconds": final["duration_seconds"] if final else 0,
                        })
                        break
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
