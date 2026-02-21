"""Post-extraction validation for LLM-generated data.

Verifies that extracted items have evidence grounded in the transcript,
filters out empty/invalid entries, and marks unverified items.
"""

import logging

from models.schemas import PatientSummary, ClinicianNote

logger = logging.getLogger(__name__)


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
    """Validate a PatientSummary against the source transcript.

    - Filters out items with empty required fields
    - Checks evidence fields against transcript
    - Sets verified=False on items with missing or ungrounded evidence
    """
    # Medications: filter empty names, verify evidence
    valid_meds = []
    for med in summary.medications:
        if not med.name.strip():
            continue
        med.verified = _check_evidence(med.evidence, transcript)
        valid_meds.append(med)

    # Tests: filter empty test names
    valid_tests = []
    for test in summary.tests_ordered:
        if not test.test_name.strip():
            continue
        test.verified = _check_evidence(test.evidence, transcript)
        valid_tests.append(test)

    # Follow-ups: filter empty actions
    valid_followups = []
    for fu in summary.follow_up_plan:
        if not fu.action.strip():
            continue
        fu.verified = _check_evidence(fu.evidence, transcript)
        valid_followups.append(fu)

    # Lifestyle recommendations: filter empty
    valid_lifestyle = []
    for rec in summary.lifestyle_recommendations:
        if not rec.recommendation.strip():
            continue
        rec.verified = _check_evidence(rec.evidence, transcript)
        valid_lifestyle.append(rec)

    # Red flags: filter empty
    valid_flags = []
    for rf in summary.red_flags_for_patient:
        if not rf.warning.strip():
            continue
        rf.verified = _check_evidence(rf.evidence, transcript)
        valid_flags.append(rf)

    # Q&A: filter empty questions
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

    # Log stats
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
    """Validate a ClinicianNote against the source transcript.

    - Filters empty action items and problem list entries
    - Verifies action item evidence against transcript
    - Priority is already coerced by the schema validator
    """
    # Filter empty strings from SOAP bullet-point lists
    soap = note.soap_note
    soap.subjective.findings = [f for f in soap.subjective.findings if f.strip()]
    soap.objective.vital_signs = [v for v in soap.objective.vital_signs if v.strip()]
    soap.objective.physical_exam = [p for p in soap.objective.physical_exam if p.strip()]
    soap.objective.mental_state_exam = [m for m in soap.objective.mental_state_exam if m.strip()]
    soap.objective.lab_results = [l for l in soap.objective.lab_results if l.strip()]
    soap.assessment.findings = [f for f in soap.assessment.findings if f.strip()]
    soap.plan.findings = [f for f in soap.plan.findings if f.strip()]

    # Filter empty action items, verify evidence
    valid_actions = []
    for item in note.action_items:
        if not item.action.strip():
            continue
        item.verified = _check_evidence(item.evidence, transcript)
        valid_actions.append(item)

    note.action_items = valid_actions

    # Filter empty problem list entries
    note.problem_list = [p for p in note.problem_list if p.strip()]

    verified = sum(1 for a in valid_actions if a.verified)
    logger.info(f"Clinician note validation: {verified}/{len(valid_actions)} action items verified")

    return note
