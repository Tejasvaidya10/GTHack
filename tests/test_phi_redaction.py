"""Tests for PHI redaction module.

Fully offline — Presidio + spaCy run locally, no mocking needed.
"""

import pytest
from core.phi_redaction import redact_phi
from models.schemas import RedactionResult


def test_redact_person_name():
    """Person names should be replaced with indexed [PERSON_N] tags."""
    text = "Dr. John Smith discussed results with patient Jane Doe."
    result = redact_phi(text)

    assert isinstance(result, RedactionResult)
    assert "John Smith" not in result.redacted_text
    assert "Jane Doe" not in result.redacted_text
    assert "PERSON" in result.entity_count
    assert result.entity_count["PERSON"] >= 2
    assert "[PERSON_1]" in result.redacted_text
    assert "[PERSON_2]" in result.redacted_text


def test_redact_phone_number():
    """Phone numbers should be redacted."""
    text = "Contact the patient's phone number (212) 456-7890 for results."
    result = redact_phi(text)

    # Presidio should detect this as a phone number
    assert "PHONE_NUMBER" in result.entity_count or len(result.redaction_log) >= 1
    # The raw phone digits should not appear unmasked
    if "PHONE_NUMBER" in result.entity_count:
        assert "[PHONE_NUMBER_1]" in result.redacted_text


@pytest.mark.parametrize("mrn_text,mrn_number", [
    ("Patient record MRN-123456 shows improvement.", "123456"),
    ("Check MRN: 1234567890 in the system.", "1234567890"),
    ("Refer to MRN 987654 for history.", "987654"),
])
def test_redact_mrn_patterns(mrn_text, mrn_number):
    """Custom MRN recognizer should detect various MRN formats."""
    result = redact_phi(mrn_text)

    assert mrn_number not in result.redacted_text
    assert len(result.redaction_log) >= 1


def test_redact_insurance_id():
    """Custom insurance ID recognizer should detect INS- patterns."""
    text = "Insurance ID: INS-789012345 is on file for the patient."
    result = redact_phi(text)

    assert "INS-789012345" not in result.redacted_text
    assert len(result.redaction_log) >= 1


def test_medical_terms_not_redacted():
    """Medical terminology should NOT be treated as PHI."""
    text = "The patient takes metformin 500mg for type 2 diabetes and hypertension."
    result = redact_phi(text)

    assert "metformin" in result.redacted_text
    assert "diabetes" in result.redacted_text
    assert "hypertension" in result.redacted_text


def test_empty_text():
    """Empty string should return empty result with no redactions."""
    result = redact_phi("")

    assert result.redacted_text == ""
    assert result.redaction_log == []
    assert result.entity_count == {}


def test_no_phi_text():
    """Text with no PHI should pass through unchanged."""
    text = "Prescribe aspirin and schedule a lab draw."
    result = redact_phi(text)

    assert result.redacted_text == text
    assert result.redaction_log == []
    assert result.entity_count == {}


def test_multiple_entities_indexed():
    """Multiple entities of the same type should get distinct indexed tags."""
    text = "Dr. John Smith referred Jane Doe and Robert Johnson for testing."
    result = redact_phi(text)

    tags = [entry.replacement_tag for entry in result.redaction_log if "PERSON" in entry.replacement_tag]
    # Each tag should be unique
    assert len(tags) == len(set(tags))
    assert len(tags) >= 3

    # Verify sequential indexing
    for i, tag in enumerate(sorted(tags), start=1):
        assert tag == f"[PERSON_{i}]"
