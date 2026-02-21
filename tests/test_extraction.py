"""Tests for LLM extraction module.

Mocks Ollama HTTP calls — no local LLM needed.
"""

import json
import pytest
import requests
from unittest.mock import patch, MagicMock

from core.extraction import (
    _extract_json_from_response,
    _extract_with_retry,
    extract_patient_summary,
    extract_clinician_note,
    call_ollama,
)
from models.schemas import PatientSummary, ClinicianNote


# --- Test fixtures ---

VALID_PATIENT_JSON = json.dumps({
    "visit_summary": "Patient visited for routine checkup.",
    "medications": [
        {
            "name": "Metformin",
            "dose": "500mg",
            "frequency": "twice daily",
            "duration": "ongoing",
            "instructions": "Take with food",
            "evidence": "Doctor said take metformin 500mg twice daily",
        }
    ],
    "tests_ordered": [],
    "follow_up_plan": [],
    "lifestyle_recommendations": [],
    "red_flags_for_patient": [],
    "questions_and_answers": [],
})

VALID_CLINICIAN_JSON = json.dumps({
    "soap_note": {
        "subjective": {
            "findings": [
                "Patient presents for annual exam.",
                "No acute complaints.",
                "Currently taking Metformin 500mg twice daily.",
            ],
            "evidence": ["Patient said they are here for their annual checkup"],
        },
        "objective": {
            "vital_signs": ["BP: 120/80", "HR: 72", "Temp: 98.6"],
            "physical_exam": ["Normal exam, no abnormalities noted."],
            "mental_state_exam": [],
            "lab_results": [],
            "evidence": ["Vitals recorded during visit"],
        },
        "assessment": {
            "findings": ["Type 2 Diabetes - stable on current regimen."],
            "evidence": ["Discussion about diabetes management"],
        },
        "plan": {
            "findings": [
                "Continue Metformin 500mg BID.",
                "Order HbA1c lab.",
                "Return in 3 months for follow-up.",
                "Discussed diet and exercise.",
            ],
            "evidence": ["Doctor ordered HbA1c and scheduled follow-up"],
        },
    },
    "problem_list": ["Type 2 Diabetes - stable"],
    "action_items": [
        {
            "action": "Order HbA1c lab",
            "priority": "medium",
            "evidence": "Doctor said we need to check your HbA1c",
        }
    ],
})


# --- JSON parsing tests ---

def test_extract_json_clean():
    """Direct JSON string should parse correctly."""
    data = '{"key": "value", "num": 42}'
    result = _extract_json_from_response(data)
    assert result == {"key": "value", "num": 42}


def test_extract_json_markdown_fenced():
    """JSON wrapped in markdown code fences should parse correctly."""
    data = '```json\n{"key": "value"}\n```'
    result = _extract_json_from_response(data)
    assert result == {"key": "value"}


def test_extract_json_text_around():
    """JSON embedded in surrounding text should be extracted (strategy 3)."""
    data = 'Here is the result:\n{"key": "value"}\nDone!'
    result = _extract_json_from_response(data)
    assert result == {"key": "value"}


def test_extract_json_invalid_raises():
    """Non-JSON text should raise JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        _extract_json_from_response("This is not JSON at all")


# --- Retry logic tests ---

@patch("core.extraction.call_ollama")
def test_retry_bad_then_good(mock_ollama):
    """Retry should recover after first bad JSON response."""
    mock_ollama.side_effect = ["not valid json {{{", VALID_PATIENT_JSON]

    result = _extract_with_retry("test prompt", "test system", PatientSummary, max_retries=2)

    assert isinstance(result, PatientSummary)
    assert result.visit_summary == "Patient visited for routine checkup."
    assert mock_ollama.call_count == 2


# --- End-to-end extraction tests ---

@patch("core.extraction._load_prompt", return_value="dummy prompt")
@patch("core.extraction.call_ollama", return_value=VALID_PATIENT_JSON)
def test_extract_patient_summary_mocked(mock_ollama, mock_prompt):
    """extract_patient_summary should return validated PatientSummary."""
    result = extract_patient_summary("Doctor patient conversation here")

    assert isinstance(result, PatientSummary)
    assert len(result.medications) == 1
    assert result.medications[0].name == "Metformin"
    assert result.medications[0].dose == "500mg"
    mock_ollama.assert_called_once()


@patch("core.extraction._load_prompt", return_value="dummy prompt")
@patch("core.extraction.call_ollama", return_value=VALID_CLINICIAN_JSON)
def test_extract_clinician_note_mocked(mock_ollama, mock_prompt):
    """extract_clinician_note should return validated ClinicianNote."""
    result = extract_clinician_note("Doctor patient conversation here")

    assert isinstance(result, ClinicianNote)
    assert "Type 2 Diabetes" in result.soap_note.assessment.findings[0]
    assert len(result.action_items) == 1
    assert result.action_items[0].action == "Order HbA1c lab"
    mock_ollama.assert_called_once()


# --- Connection error test ---

@patch("core.extraction.requests.post", side_effect=requests.ConnectionError("Connection refused"))
def test_ollama_connection_error(mock_post):
    """call_ollama should raise ConnectionError when Ollama is unreachable."""
    with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
        call_ollama("test prompt", "system prompt")
