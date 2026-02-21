"""Whisper transcription with pyannote.audio speaker diarization."""

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
from app.config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, HF_TOKEN

logger = logging.getLogger(__name__)

# Module-level model cache
_model_cache: dict[str, whisper.Whisper] = {}
_diarization_pipeline = None

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".flac", ".ogg"}

# Pause threshold (seconds) — fallback if pyannote unavailable
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


def _get_diarization_pipeline():
    """Load and cache pyannote speaker diarization pipeline."""
    global _diarization_pipeline
    if _diarization_pipeline is not None:
        return _diarization_pipeline

    if not HF_TOKEN:
        logger.warning("HF_TOKEN not set — falling back to pause-based diarization")
        return None

    try:
        from pyannote.audio import Pipeline
        logger.info("Loading pyannote speaker diarization pipeline...")
        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=HF_TOKEN,
        )
        # Move to GPU if available
        import torch
        if torch.cuda.is_available():
            _diarization_pipeline.to(torch.device("cuda"))
            logger.info("Pyannote pipeline loaded on CUDA")
        else:
            logger.info("Pyannote pipeline loaded on CPU")
        return _diarization_pipeline
    except Exception as e:
        logger.warning(f"Failed to load pyannote pipeline: {e}. Falling back to pause-based diarization.")
        return None


def _diarize_with_pyannote(
    file_path: str,
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    """Assign speaker labels using pyannote.audio neural diarization.

    Runs pyannote on the audio file to detect speaker turns, then matches
    each Whisper segment to the speaker who is talking at that time.
    """
    pipeline = _get_diarization_pipeline()
    if pipeline is None:
        return _diarize_segments_fallback(segments)

    try:
        # Run pyannote diarization (expects 2 speakers for medical visit)
        # __call__ wraps the file path and forwards kwargs to .apply()
        diarization = pipeline(file_path, num_speakers=2)
    except Exception as e:
        logger.warning(f"Pyannote diarization failed: {e}. Using fallback.")
        return _diarize_segments_fallback(segments)

    # Build a mapping of speaker labels from pyannote
    # pyannote returns labels like "SPEAKER_00", "SPEAKER_01"
    # We map the first speaker detected to "Doctor" and the second to "Patient"
    speaker_map = {}
    speaker_counter = 0

    # Collect all pyannote turns into a list for efficient lookup
    turns = []
    # pyannote v4 returns DiarizeOutput; access .speaker_diarization for the Annotation
    annotation = getattr(diarization, "speaker_diarization", diarization)
    for turn, _, speaker_label in annotation.itertracks(yield_label=True):
        if speaker_label not in speaker_map:
            if speaker_counter < len(SPEAKERS):
                speaker_map[speaker_label] = SPEAKERS[speaker_counter]
                speaker_counter += 1
            else:
                speaker_map[speaker_label] = f"Speaker {speaker_counter + 1}"
                speaker_counter += 1
        turns.append((turn.start, turn.end, speaker_map[speaker_label]))

    logger.info(f"Pyannote detected {len(speaker_map)} speakers with {len(turns)} turns")

    # Match each Whisper segment to a pyannote speaker
    labeled = []
    for seg in segments:
        seg_mid = (seg.start_time + seg.end_time) / 2.0
        best_speaker = "Unknown"
        best_overlap = 0.0

        for turn_start, turn_end, speaker in turns:
            # Calculate overlap between segment and turn
            overlap_start = max(seg.start_time, turn_start)
            overlap_end = min(seg.end_time, turn_end)
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker

        # If no overlap found, check which turn the midpoint falls in
        if best_overlap == 0.0:
            for turn_start, turn_end, speaker in turns:
                if turn_start <= seg_mid <= turn_end:
                    best_speaker = speaker
                    break

        labeled.append(TranscriptSegment(
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=f"{best_speaker}: {seg.text}",
        ))

    return labeled


def _diarize_segments_fallback(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Fallback: assign speaker labels based on pause detection.

    Used when pyannote is not available (no HF_TOKEN or import failure).
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
    use_pyannote: bool = True,
) -> TranscriptionResult:
    """Transcribe an audio file using Whisper with speaker diarization.

    Uses pyannote.audio for neural speaker diarization when available,
    falls back to pause-based heuristic otherwise.

    Args:
        file_path: Path to the audio file.
        model_size: Whisper model size (tiny, base, small, medium, large).
                    Defaults to config value.
        use_pyannote: Whether to use pyannote for diarization. Set False for
                      short chunks (live transcription) where it's too slow.

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

    # Add speaker labels — pyannote for full files, fallback for short chunks
    if use_pyannote:
        diarized_segments = _diarize_with_pyannote(file_path, segments)
    else:
        diarized_segments = _diarize_segments_fallback(segments)
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
