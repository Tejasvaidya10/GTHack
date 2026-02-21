"""Whisper transcription logic."""

import os
import logging
from typing import Optional

import whisper

from models.schemas import TranscriptionResult, TranscriptSegment
from app.config import WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

# Module-level model cache
_model_cache: dict[str, whisper.Whisper] = {}

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".flac", ".ogg"}


def _get_model(model_size: str) -> whisper.Whisper:
    """Load and cache Whisper model."""
    if model_size not in _model_cache:
        logger.info(f"Loading Whisper model: {model_size}")
        _model_cache[model_size] = whisper.load_model(model_size)
        logger.info(f"Whisper model '{model_size}' loaded successfully")
    return _model_cache[model_size]


def transcribe_audio(
    file_path: str,
    model_size: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe an audio file using Whisper.

    Args:
        file_path: Path to the audio file.
        model_size: Whisper model size (tiny, base, small, medium, large).
                    Defaults to config value.

    Returns:
        TranscriptionResult with full text, segments, language, and duration.

    Raises:
        FileNotFoundError: If the audio file doesn't exist.
        ValueError: If the file format is not supported.
        RuntimeError: If transcription fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format: {ext}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    size = model_size or WHISPER_MODEL_SIZE
    model = _get_model(size)

    try:
        result = model.transcribe(file_path)
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}") from e

    segments = [
        TranscriptSegment(
            start_time=seg["start"],
            end_time=seg["end"],
            text=seg["text"].strip(),
        )
        for seg in result.get("segments", [])
    ]

    # Calculate duration from last segment end time
    duration = segments[-1].end_time if segments else 0.0

    return TranscriptionResult(
        text=result["text"].strip(),
        segments=segments,
        language=result.get("language", "en"),
        duration_seconds=round(duration, 2),
    )
