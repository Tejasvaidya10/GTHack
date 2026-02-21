"""LLM structured extraction using Ollama (local inference)."""

import json
import logging
import os
import re
from typing import Type, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from models.schemas import PatientSummary, ClinicianNote
from core.validation import validate_patient_summary, validate_clinician_note
from app.config import (
    OLLAMA_URL, OLLAMA_MODEL, LLM_TEMPERATURE,
    LLM_MAX_TOKENS, LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _normalize_string_lists(data: dict) -> dict:
    """Recursively convert simple key-value dicts inside lists to strings.
    
    Ollama JSON mode sometimes returns {"BP": "140/90"} instead of "BP: 140/90".
    This normalizes those before Pydantic validation, but preserves structured
    dicts (like action_items) that should remain as objects.
    """
    # Known keys that indicate a dict should stay as a structured object
    STRUCTURED_KEYS = {"action", "priority", "evidence", "name", "dose", "frequency",
                       "recommendation", "warning", "question", "answer", "test_name"}
    
    if isinstance(data, dict):
        return {k: _normalize_string_lists(v) for k, v in data.items()}
    elif isinstance(data, list):
        result = []
        for item in data:
            if isinstance(item, dict):
                # If it has known schema keys, keep it as a dict (structured object)
                if any(k in STRUCTURED_KEYS for k in item.keys()):
                    result.append(_normalize_string_lists(item))
                else:
                    # Simple key-value pair like {"BP": "140/90"} -> "BP: 140/90"
                    parts = []
                    for k, v in item.items():
                        if isinstance(v, str) and v:
                            parts.append(f"{k}: {v}")
                        elif isinstance(v, str) and not v:
                            continue
                        else:
                            parts.append(f"{k}: {v}")
                    if parts:
                        result.append("; ".join(parts))
            elif isinstance(item, str) and item.strip():
                result.append(item)
        return result
    return data



def call_ollama(prompt: str, system_prompt: str) -> str:
    """Call Ollama's local API for text generation.

    Args:
        prompt: The user prompt to send.
        system_prompt: The system prompt for context.

    Returns:
        The generated text response.

    Raises:
        ConnectionError: If Ollama is not running.
        RuntimeError: If the API call fails.
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": LLM_TEMPERATURE,
                    "num_predict": LLM_MAX_TOKENS,
                },
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running: `ollama serve`"
        )
    except requests.Timeout:
        raise RuntimeError(
            f"Ollama request timed out after {LLM_TIMEOUT_SECONDS}s. "
            "The model may be too slow or the input too long."
        )
    except Exception as e:
        raise RuntimeError(f"Ollama API error: {e}")


def _extract_json_from_response(raw: str) -> dict:
    """Extract a JSON object from an LLM response, handling common issues.

    Tries multiple strategies:
    1. Direct json.loads
    2. Strip markdown fences
    3. Find first { to last }
    """
    raw = raw.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find the JSON object boundaries
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(raw[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Could not extract valid JSON from LLM response", raw, 0)


def _extract_with_retry(
    prompt: str,
    system_prompt: str,
    model_class: Type[T],
    max_retries: int = LLM_MAX_RETRIES,
) -> T:
    """Extract structured data with retry logic for malformed JSON.

    Args:
        prompt: The extraction prompt with transcript.
        system_prompt: The system prompt template.
        model_class: The Pydantic model to validate against.
        max_retries: Maximum number of retries on failure.

    Returns:
        A validated Pydantic model instance.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            raw_response = call_ollama(prompt, system_prompt)
            logger.debug(f"LLM response (attempt {attempt + 1}): {raw_response[:200]}...")

            data = _extract_json_from_response(raw_response)
            data = _normalize_string_lists(data)
            return model_class.model_validate(data)

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"JSON parse failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Return ONLY a valid JSON object. No markdown code fences. "
                    "No explanation before or after. Just the raw JSON.\n\n"
                    f"Original request:\n{prompt}"
                )

        except ValidationError as e:
            last_error = e
            logger.warning(f"Pydantic validation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                prompt = (
                    f"Your previous response had validation errors: {e.error_count()} errors. "
                    "Please fix the JSON structure and return ONLY valid JSON.\n\n"
                    f"Original request:\n{prompt}"
                )

    raise RuntimeError(
        f"Failed to extract valid structured data after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
    path = os.path.join(prompt_dir, filename)
    with open(path) as f:
        return f.read()


def extract_patient_summary(transcript: str) -> PatientSummary:
    """Extract patient-facing summary from a transcript.

    Args:
        transcript: The de-identified transcript text.

    Returns:
        PatientSummary with medications, tests, follow-ups, etc.
        Each item is validated against the transcript and marked verified/unverified.
    """
    system_prompt = _load_prompt("extraction_patient.txt")
    prompt = f"Here is the patient-doctor conversation transcript:\n\n{transcript}"

    summary = _extract_with_retry(prompt, system_prompt, PatientSummary)
    return validate_patient_summary(summary, transcript)


def extract_clinician_note(transcript: str) -> ClinicianNote:
    """Extract clinician-facing SOAP note from a transcript.

    Args:
        transcript: The de-identified transcript text.

    Returns:
        ClinicianNote with SOAP note, problem list, and action items.
        Action items are validated against the transcript.
    """
    system_prompt = _load_prompt("extraction_clinician.txt")
    prompt = f"Here is the patient-doctor conversation transcript:\n\n{transcript}"

    note = _extract_with_retry(prompt, system_prompt, ClinicianNote)
    return validate_clinician_note(note, transcript)
