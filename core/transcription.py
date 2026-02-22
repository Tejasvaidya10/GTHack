"""Whisper transcription with pause-based speaker diarization."""

import os
import logging
import shutil
from typing import Optional

# Ensure ffmpeg is on PATH (winget installs may not update the current process PATH)
if not shutil.which("ffmpeg"):
    _ffmpeg_dir = os.path.join(
        os.path.expanduser("~"),
        "AppData", "Local", "Microsoft", "WinGet", "Packages",
        "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
        "ffmpeg-8.0.1-full_build", "bin",
    )
    if os.path.isdir(_ffmpeg_dir):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import whisper

from models.schemas import TranscriptionResult, TranscriptSegment
from app.config import WHISPER_MODEL_SIZE, WHISPER_DEVICE

logger = logging.getLogger(__name__)

# Module-level model cache
_model_cache: dict[str, whisper.Whisper] = {}

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".flac", ".ogg"}

# Pause threshold (seconds) for speaker change detection
SPEAKER_CHANGE_PAUSE = 1.5

# Speakers for a 2-person medical visit
SPEAKERS = ["Doctor", "Patient"]


def _get_model(model_size: str) -> whisper.Whisper:
    """Load and cache Whisper model."""
    if model_size not in _model_cache:
        logger.info(f"Loading Whisper model: {model_size} on {WHISPER_DEVICE}")
        _model_cache[model_size] = whisper.load_model(model_size, device=WHISPER_DEVICE)
        logger.info(f"Whisper model '{model_size}' loaded successfully on {WHISPER_DEVICE}")
    return _model_cache[model_size]


def _diarize_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Assign speaker labels based on pause detection.

    Alternates between Doctor and Patient when a pause exceeding
    SPEAKER_CHANGE_PAUSE seconds is detected between segments.
    """
    if not segments:
        return segments

    current_speaker_idx = 0
    labeled = []

    for i, seg in enumerate(segments):
        if i > 0:
            pause = seg.start_time - segments[i - 1].end_time
            if pause >= SPEAKER_CHANGE_PAUSE:
                current_speaker_idx = 1 - current_speaker_idx

        speaker = SPEAKERS[current_speaker_idx]
        labeled.append(TranscriptSegment(
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=f"{speaker}: {seg.text}",
        ))

    return labeled


def transcribe_audio(
    file_path: str,
    model_size: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe an audio file using Whisper with speaker diarization.

    Uses pause-based heuristic to assign speaker labels (Doctor / Patient).

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

    # Add speaker labels via pause-based diarization
    diarized_segments = _diarize_segments(segments)
    diarized_text = _format_diarized_transcript(diarized_segments)

    return TranscriptionResult(
        text=diarized_text,
        segments=diarized_segments,
        language=result.get("language", "en"),
        duration_seconds=round(duration, 2),
    )


def _format_diarized_transcript(segments: list[TranscriptSegment]) -> str:
    """Format diarized segments into a readable transcript.

    Merges consecutive segments from the same speaker into single blocks.
    """
    if not segments:
        return ""

    blocks = []
    current_speaker = None
    current_text_parts = []

    for seg in segments:
        if ": " in seg.text:
            speaker, text = seg.text.split(": ", 1)
        else:
            speaker = "Unknown"
            text = seg.text

        if speaker == current_speaker:
            current_text_parts.append(text)
        else:
            if current_speaker is not None:
                blocks.append(f"{current_speaker}: {' '.join(current_text_parts)}")
            current_speaker = speaker
            current_text_parts = [text]

    if current_speaker is not None:
        blocks.append(f"{current_speaker}: {' '.join(current_text_parts)}")

    return "\n\n".join(blocks)
