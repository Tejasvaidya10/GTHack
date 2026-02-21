"""Tests for Whisper transcription module.

Mocks Whisper model — no GPU or model download needed.
"""

import wave
import pytest
from unittest.mock import patch, MagicMock

from core.transcription import transcribe_audio, _get_model, _model_cache
from models.schemas import TranscriptionResult


@pytest.fixture
def synthetic_wav(tmp_path):
    """Create a minimal valid WAV file (1 second of silence)."""
    wav_path = str(tmp_path / "test_audio.wav")
    sample_rate = 16000
    num_samples = sample_rate  # 1 second

    with wave.open(wav_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)

    return wav_path


def test_unsupported_format(tmp_path):
    """Unsupported file extension should raise ValueError."""
    bad_file = str(tmp_path / "test.txt")
    with open(bad_file, "w") as f:
        f.write("not audio")

    with pytest.raises(ValueError, match="Unsupported audio format"):
        transcribe_audio(bad_file)


def test_file_not_found():
    """Non-existent file path should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        transcribe_audio("/nonexistent/path/audio.wav")


@patch("core.transcription._get_model")
def test_transcription_mocked_whisper(mock_get_model, synthetic_wav):
    """Mocked Whisper should return a valid TranscriptionResult."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": " Hello, how are you feeling today?",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": " Hello, how are you feeling today?"},
        ],
        "language": "en",
    }
    mock_get_model.return_value = mock_model

    result = transcribe_audio(synthetic_wav)

    assert isinstance(result, TranscriptionResult)
    assert "Hello, how are you feeling today?" in result.text
    assert len(result.segments) == 1
    assert result.language == "en"
    assert result.duration_seconds == 2.5
    mock_model.transcribe.assert_called_once_with(synthetic_wav)


@patch("core.transcription.whisper.load_model")
def test_model_caching(mock_load):
    """Whisper model should be loaded once and cached for subsequent calls."""
    _model_cache.clear()
    mock_load.return_value = MagicMock()

    model1 = _get_model("base")
    model2 = _get_model("base")

    assert model1 is model2
    mock_load.assert_called_once_with("base")

    _model_cache.clear()


@patch("core.transcription._get_model")
def test_multi_segment_result(mock_get_model, synthetic_wav):
    """Multi-segment transcription should calculate duration from last segment."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": " Segment one. Segment two.",
        "segments": [
            {"start": 0.0, "end": 1.5, "text": " Segment one."},
            {"start": 1.5, "end": 3.0, "text": " Segment two."},
        ],
        "language": "en",
    }
    mock_get_model.return_value = mock_model

    result = transcribe_audio(synthetic_wav)

    assert result.duration_seconds == 3.0
    assert len(result.segments) == 2
    assert result.segments[0].start_time == 0.0
    assert result.segments[0].end_time == 1.5
    assert "Segment two." in result.segments[1].text
