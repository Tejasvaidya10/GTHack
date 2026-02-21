"""PHI detection and masking using Microsoft Presidio."""

import logging
from collections import defaultdict
from typing import Optional

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from models.schemas import RedactionResult, RedactionEntry

logger = logging.getLogger(__name__)

# Module-level engine cache
_analyzer: Optional[AnalyzerEngine] = None
_anonymizer: Optional[AnonymizerEngine] = None


def _build_custom_recognizers() -> list[PatternRecognizer]:
    """Build custom recognizers for medical-specific PHI patterns."""
    mrn_recognizer = PatternRecognizer(
        supported_entity="MEDICAL_RECORD_NUMBER",
        name="MRN Recognizer",
        patterns=[
            Pattern("MRN with dash", r"\bMRN[-]?\d{6,10}\b", 0.9),
            Pattern("MRN with colon", r"\bMRN:\s*\d{6,10}\b", 0.9),
            Pattern("MRN with space", r"\bMRN\s+\d{6,10}\b", 0.85),
        ],
        context=["medical record", "MRN", "record number", "patient id"],
    )

    insurance_recognizer = PatternRecognizer(
        supported_entity="INSURANCE_ID",
        name="Insurance ID Recognizer",
        patterns=[
            Pattern("INS with dash", r"\bINS[-]?\d{6,12}\b", 0.9),
            Pattern("INS with colon", r"\bINS:\s*\d{6,12}\b", 0.9),
            Pattern("Insurance ID format", r"\b[A-Z]{3}\d{9,12}\b", 0.6),
            Pattern("Policy number", r"\bpolicy\s*#?\s*\d{6,12}\b", 0.7),
        ],
        context=["insurance", "policy", "coverage", "member id", "subscriber"],
    )

    return [mrn_recognizer, insurance_recognizer]


def _get_analyzer() -> AnalyzerEngine:
    """Get or create the cached analyzer engine."""
    global _analyzer
    if _analyzer is None:
        logger.info("Initializing Presidio AnalyzerEngine...")
        _analyzer = AnalyzerEngine()
        for recognizer in _build_custom_recognizers():
            _analyzer.registry.add_recognizer(recognizer)
        logger.info("Presidio AnalyzerEngine initialized with custom recognizers")
    return _analyzer


def _get_anonymizer() -> AnonymizerEngine:
    """Get or create the cached anonymizer engine."""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


# Entity types to detect
# NOTE: DATE_TIME is intentionally excluded — Presidio redacts all dates/times
# including clinically relevant ones (e.g. "this happened yesterday", "pain started
# 2 hours ago"). In medical conversations, when symptoms/injuries started is critical
# clinical information, not PHI. True PHI dates (DOB) are rare in doctor-patient audio.
ENTITY_TYPES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "LOCATION",
    "US_SSN",
    "MEDICAL_RECORD_NUMBER",
    "INSURANCE_ID",
    "US_DRIVER_LICENSE",
    "CREDIT_CARD",
]


def redact_phi(text: str) -> RedactionResult:
    """Detect and redact PHI from text.

    Replaces detected entities with indexed tags like [PERSON_1], [PHONE_1], etc.

    Args:
        text: The input text to redact.

    Returns:
        RedactionResult with redacted text, log of replacements, and entity counts.
    """
    if not text or not text.strip():
        return RedactionResult(redacted_text=text, redaction_log=[], entity_count={})

    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()

    # Detect entities
    results = analyzer.analyze(
        text=text,
        entities=ENTITY_TYPES,
        language="en",
        score_threshold=0.5,
    )

    if not results:
        return RedactionResult(redacted_text=text, redaction_log=[], entity_count={})

    # Sort by start position for consistent processing
    results = sorted(results, key=lambda r: r.start)

    # Count entities by type for indexed replacement tags
    entity_counters: dict[str, int] = defaultdict(int)
    entity_count: dict[str, int] = defaultdict(int)
    redaction_log: list[RedactionEntry] = []

    # Build operator configs for each entity with indexed tags
    # We need to do manual replacement to get indexed tags
    redacted_text = text
    offset = 0  # Track offset as we replace text

    for result in sorted(results, key=lambda r: r.start):
        entity_counters[result.entity_type] += 1
        entity_count[result.entity_type] += 1
        idx = entity_counters[result.entity_type]
        tag = f"[{result.entity_type}_{idx}]"

        # Calculate adjusted positions
        adj_start = result.start + offset
        adj_end = result.end + offset

        redaction_log.append(RedactionEntry(
            entity_type=result.entity_type,
            original_position=(result.start, result.end),
            replacement_tag=tag,
        ))

        # Replace in text
        redacted_text = redacted_text[:adj_start] + tag + redacted_text[adj_end:]
        offset += len(tag) - (result.end - result.start)

    return RedactionResult(
        redacted_text=redacted_text,
        redaction_log=redaction_log,
        entity_count=dict(entity_count),
    )
