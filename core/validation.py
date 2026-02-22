"""Post-extraction validation and hallucination detection.

Verifies that extracted items have evidence grounded in the transcript,
computes per-item and overall grounding scores, and flags potential
hallucinations for clinician review.
"""

import logging
import re
from difflib import SequenceMatcher

from models.schemas import PatientSummary, ClinicianNote

logger = logging.getLogger(__name__)


# ── Grounding Score Engine ────────────────────────────────────────────────────

def _stem(word: str) -> str:
    """Poor-man s stemmer: strip common suffixes for matching."""
    w = word.lower()
    for suffix in ("ation", "ment", "ized", "izing", "tion", "sion", "ing", "ness", "ity", "ous", "ive", "able", "ible", "ally", "ful", "less", "er", "ed", "ly", "es", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[:-len(suffix)]
    return w


# Common medical abbreviations/synonyms
MEDICAL_SYNONYMS = {
    'rehab': 'rehabilitation', 'rehabilitation': 'rehab',
    'exam': 'examination', 'examination': 'exam',
    'xray': 'x-ray', 'x-ray': 'xray',
    'bp': 'blood pressure', 'hr': 'heart rate',
    'immobilizer': 'immobilized', 'immobilized': 'immobilizer',
    'immobilization': 'immobilized',
    'meds': 'medications', 'medications': 'meds',
    'htn': 'hypertension', 'dm': 'diabetes',
    'sob': 'shortness of breath',
}


def _expand_synonyms(words: set) -> set:
    """Expand word set with known medical synonyms."""
    expanded = set(words)
    for w in words:
        if w in MEDICAL_SYNONYMS:
            syn = MEDICAL_SYNONYMS[w]
            expanded.add(_stem(syn))
            expanded.add(syn)
    return expanded


def _word_overlap_score(text: str, transcript: str) -> float:
    """Compute word overlap ratio between text and transcript (0.0–1.0)."""
    if not text or not transcript:
        return 0.0
    text_words = set(w.lower() for w in re.findall(r'\b\w{3,}\b', text))
    transcript_words = set(w.lower() for w in re.findall(r'\b\w{3,}\b', transcript))
    if not text_words:
        return 0.0
    # Direct overlap
    overlap = text_words & transcript_words
    # Synonym-expanded overlap
    expanded_text = _expand_synonyms(text_words)
    expanded_transcript = _expand_synonyms(transcript_words)
    synonym_overlap = expanded_text & expanded_transcript
    best_overlap = max(len(overlap), len(synonym_overlap))
    return min(1.0, best_overlap / len(text_words))


def _fuzzy_substring_score(evidence: str, transcript: str) -> float:
    """Find best fuzzy match of evidence in transcript (0.0–1.0).
    
    Slides a window across the transcript and finds the best match ratio.
    For performance, samples windows rather than checking every position.
    """
    if not evidence or not transcript:
        return 0.0
    evidence_lower = evidence.lower().strip()
    transcript_lower = transcript.lower()
    
    # Exact match
    if evidence_lower in transcript_lower:
        return 1.0
    
    # Sliding window fuzzy match (sampled for performance)
    window_size = len(evidence_lower)
    if window_size > len(transcript_lower):
        return _word_overlap_score(evidence, transcript)
    
    best_ratio = 0.0
    step = max(1, window_size // 4)  # Sample every quarter-window
    for i in range(0, len(transcript_lower) - window_size + 1, step):
        chunk = transcript_lower[i:i + window_size]
        ratio = SequenceMatcher(None, evidence_lower, chunk).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            if ratio > 0.9:  # Early exit on very good match
                break
    return best_ratio


def _compute_item_grounding(
    claim: str,
    evidence: str,
    transcript: str,
) -> dict:
    """Compute grounding score for a single extracted item.
    
    Returns:
        {
            "score": 0-100 int,
            "evidence_match": 0.0-1.0,    # How well evidence maps to transcript
            "claim_support": 0.0-1.0,      # How well claim words appear in transcript
            "has_evidence": bool,
            "flag": "grounded" | "likely_grounded" | "uncertain" | "likely_hallucinated"
        }
    """
    result = {
        "score": 0,
        "evidence_match": 0.0,
        "claim_support": 0.0,
        "has_evidence": bool(evidence and evidence.strip()),
        "flag": "likely_hallucinated",
    }
    
    # Score 1: Does the evidence quote exist in the transcript? (0–50 points)
    if evidence and evidence.strip():
        evidence_score = _fuzzy_substring_score(evidence, transcript)
        result["evidence_match"] = round(evidence_score, 3)
    else:
        evidence_score = 0.0
    
    # Score 2: Do the claim's key terms appear in the transcript? (0–50 points)
    claim_score = _word_overlap_score(claim, transcript)
    result["claim_support"] = round(claim_score, 3)
    
    # Combined score: evidence match (50%) + claim support (50%)
    # If no evidence provided, claim support is the only signal (capped at 60)
    if result["has_evidence"]:
        combined = (evidence_score * 40) + (claim_score * 60)
    else:
        combined = min(claim_score * 100, 85)  # No evidence = score from claim words, max 85
    
    score = int(round(combined))
    score = max(0, min(100, score))
    result["score"] = score
    
    # Flag thresholds
    if score >= 75:
        result["flag"] = "grounded"
    elif score >= 50:
        result["flag"] = "likely_grounded"
    elif score >= 30:
        result["flag"] = "uncertain"
    else:
        result["flag"] = "likely_hallucinated"
    
    return result


def compute_grounding_report(
    patient_summary: PatientSummary,
    clinician_note: ClinicianNote,
    transcript: str,
) -> dict:
    """Compute a full grounding/hallucination report for the extraction.
    
    Returns a report with:
    - overall_score: 0-100
    - overall_flag: grounded/likely_grounded/uncertain/likely_hallucinated
    - total_items, grounded_count, flagged_count
    - items: list of per-item scores grouped by category
    """
    items = []
    
    # Patient summary items
    for i, med in enumerate(patient_summary.medications):
        g = _compute_item_grounding(
            claim=f"{med.name} {med.dose} {med.frequency}".strip(),
            evidence=med.evidence,
            transcript=transcript,
        )
        items.append({"category": "medication", "item": med.name, "index": i, **g})
    
    for i, test in enumerate(patient_summary.tests_ordered):
        g = _compute_item_grounding(
            claim=test.test_name,
            evidence=test.evidence,
            transcript=transcript,
        )
        items.append({"category": "test_ordered", "item": test.test_name, "index": i, **g})
    
    for i, fu in enumerate(patient_summary.follow_up_plan):
        g = _compute_item_grounding(
            claim=fu.action,
            evidence=fu.evidence,
            transcript=transcript,
        )
        items.append({"category": "follow_up", "item": fu.action, "index": i, **g})
    
    for i, rec in enumerate(patient_summary.lifestyle_recommendations):
        g = _compute_item_grounding(
            claim=rec.recommendation,
            evidence=rec.evidence,
            transcript=transcript,
        )
        items.append({"category": "lifestyle", "item": rec.recommendation, "index": i, **g})
    
    for i, rf in enumerate(patient_summary.red_flags_for_patient):
        g = _compute_item_grounding(
            claim=rf.warning,
            evidence=rf.evidence,
            transcript=transcript,
        )
        items.append({"category": "red_flag", "item": rf.warning, "index": i, **g})
    
    # Clinician note: SOAP findings grounded in transcript
    for i, finding in enumerate(clinician_note.soap_note.subjective.findings):
        g = _compute_item_grounding(claim=finding, evidence="", transcript=transcript)
        items.append({"category": "soap_subjective", "item": finding, "index": i, **g})
    
    for i, finding in enumerate(clinician_note.soap_note.assessment.findings):
        g = _compute_item_grounding(claim=finding, evidence="", transcript=transcript)
        items.append({"category": "soap_assessment", "item": finding, "index": i, **g})
    
    for i, finding in enumerate(clinician_note.soap_note.plan.findings):
        g = _compute_item_grounding(claim=finding, evidence="", transcript=transcript)
        items.append({"category": "soap_plan", "item": finding, "index": i, **g})
    
    # Action items
    for i, action in enumerate(clinician_note.action_items):
        g = _compute_item_grounding(
            claim=action.action,
            evidence=action.evidence,
            transcript=transcript,
        )
        items.append({"category": "action_item", "item": action.action, "index": i, **g})
    
    # Compute overall score
    total = len(items)
    if total == 0:
        return {
            "overall_score": 0,
            "overall_flag": "uncertain",
            "total_items": 0,
            "grounded_count": 0,
            "flagged_count": 0,
            "items": [],
        }
    
    avg_score = sum(it["score"] for it in items) / total
    overall_score = int(round(avg_score))
    
    grounded_count = sum(1 for it in items if it["flag"] in ("grounded", "likely_grounded"))
    flagged_count = sum(1 for it in items if it["flag"] in ("uncertain", "likely_hallucinated"))
    
    if overall_score >= 75:
        overall_flag = "grounded"
    elif overall_score >= 50:
        overall_flag = "likely_grounded"
    elif overall_score >= 30:
        overall_flag = "uncertain"
    else:
        overall_flag = "likely_hallucinated"
    
    return {
        "overall_score": overall_score,
        "overall_flag": overall_flag,
        "total_items": total,
        "grounded_count": grounded_count,
        "flagged_count": flagged_count,
        "items": items,
    }


# ── Original Validation (unchanged) ──────────────────────────────────────────

def _check_evidence(evidence: str, transcript: str) -> bool:
    """Check if evidence text is grounded in the transcript.

    Uses two strategies:
    1. Exact case-insensitive substring match
    2. Loose match — 60%+ of key words (>3 chars) appear in transcript
    """
    if not evidence or not evidence.strip():
        return False

    transcript_lower = transcript.lower()
    evidence_lower = evidence.strip().lower()

    # Strategy 1: exact substring
    if evidence_lower in transcript_lower:
        return True

    # Strategy 2: loose keyword match
    words = [w for w in evidence_lower.split() if len(w) > 3]
    if not words:
        return False
    matches = sum(1 for w in words if w in transcript_lower)
    return matches / len(words) >= 0.6


def validate_patient_summary(
    summary: PatientSummary,
    transcript: str,
) -> PatientSummary:
    """Validate a PatientSummary against the source transcript."""
    valid_meds = []
    for med in summary.medications:
        if not med.name.strip():
            continue
        med.verified = _check_evidence(med.evidence, transcript)
        valid_meds.append(med)

    valid_tests = []
    for test in summary.tests_ordered:
        if not test.test_name.strip():
            continue
        test.verified = _check_evidence(test.evidence, transcript)
        valid_tests.append(test)

    valid_followups = []
    for fu in summary.follow_up_plan:
        if not fu.action.strip():
            continue
        fu.verified = _check_evidence(fu.evidence, transcript)
        valid_followups.append(fu)

    valid_lifestyle = []
    for rec in summary.lifestyle_recommendations:
        if not rec.recommendation.strip():
            continue
        rec.verified = _check_evidence(rec.evidence, transcript)
        valid_lifestyle.append(rec)

    valid_flags = []
    for rf in summary.red_flags_for_patient:
        if not rf.warning.strip():
            continue
        rf.verified = _check_evidence(rf.evidence, transcript)
        valid_flags.append(rf)

    valid_qa = []
    for qa in summary.questions_and_answers:
        if not qa.question.strip():
            continue
        qa.verified = _check_evidence(qa.evidence, transcript)
        valid_qa.append(qa)

    summary.medications = valid_meds
    summary.tests_ordered = valid_tests
    summary.follow_up_plan = valid_followups
    summary.lifestyle_recommendations = valid_lifestyle
    summary.red_flags_for_patient = valid_flags
    summary.questions_and_answers = valid_qa

    total = (len(valid_meds) + len(valid_tests) + len(valid_followups)
             + len(valid_lifestyle) + len(valid_flags) + len(valid_qa))
    verified = sum(
        1 for items in [valid_meds, valid_tests, valid_followups,
                        valid_lifestyle, valid_flags, valid_qa]
        for item in items if item.verified
    )
    logger.info(f"Patient summary validation: {verified}/{total} items verified")

    return summary


def validate_clinician_note(
    note: ClinicianNote,
    transcript: str,
) -> ClinicianNote:
    """Validate a ClinicianNote against the source transcript."""
    soap = note.soap_note
    soap.subjective.findings = [f for f in soap.subjective.findings if f.strip()]
    soap.objective.vital_signs = [v for v in soap.objective.vital_signs if v.strip()]
    soap.objective.physical_exam = [p for p in soap.objective.physical_exam if p.strip()]
    soap.objective.mental_state_exam = [m for m in soap.objective.mental_state_exam if m.strip()]
    soap.objective.lab_results = [l for l in soap.objective.lab_results if l.strip()]
    soap.assessment.findings = [f for f in soap.assessment.findings if f.strip()]
    soap.plan.findings = [f for f in soap.plan.findings if f.strip()]

    valid_actions = []
    for item in note.action_items:
        if not item.action.strip():
            continue
        item.verified = _check_evidence(item.evidence, transcript)
        valid_actions.append(item)

    note.action_items = valid_actions
    note.problem_list = [p for p in note.problem_list if p.strip()]

    verified = sum(1 for a in valid_actions if a.verified)
    logger.info(f"Clinician note validation: {verified}/{len(valid_actions)} action items verified")

    return note
