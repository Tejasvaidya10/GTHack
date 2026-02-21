"""Risk score calculation and red flag detection.

Uses a hybrid approach: rule-based scoring augmented by pattern matching.
Does NOT diagnose — only highlights what was explicitly mentioned.
"""

import logging
import re

from models.schemas import (
    PatientSummary, ClinicianNote, RiskAssessment,
    RiskFactor, RedFlag,
)
from app.config import RISK_LOW_MAX, RISK_MEDIUM_MAX

logger = logging.getLogger(__name__)

# Severe symptom keywords and their point values
SEVERE_SYMPTOMS = {
    "chest pain": 15,
    "shortness of breath": 15,
    "difficulty breathing": 15,
    "severe pain": 15,
    "confusion": 15,
    "fainting": 15,
    "loss of consciousness": 15,
    "seizure": 15,
    "stroke": 15,
    "suicidal": 15,
    "self-harm": 15,
    "bleeding heavily": 15,
    "vomiting blood": 15,
    "blood in stool": 12,
    "severe headache": 12,
    "high fever": 10,
    "dizziness": 8,
    "numbness": 8,
    "weakness": 8,
    "swelling": 8,
}

# Non-adherence cue keywords
NON_ADHERENCE_CUES = [
    "can't afford", "cannot afford", "too expensive", "cost",
    "forget", "forgot", "don't remember", "skip",
    "confused about", "don't understand", "not sure how",
    "stopped taking", "quit taking", "ran out",
    "side effects", "makes me sick", "don't want to take",
]

# Red flag patterns with categories
RED_FLAG_PATTERNS = {
    "emergency_symptom": [
        "chest pain", "difficulty breathing", "shortness of breath",
        "stroke symptoms", "severe allergic reaction", "anaphylaxis",
        "suicidal ideation", "suicidal thoughts", "want to hurt",
        "loss of consciousness", "seizure",
    ],
    "drug_interaction": [
        "drug interaction", "interact with", "contraindicated",
        "don't mix", "shouldn't take together",
    ],
    "adherence_barrier": [
        "can't afford", "cannot afford", "too expensive",
        "no insurance", "lost insurance", "can't get to",
        "transportation", "no ride", "pharmacy closed",
    ],
    "worsening_condition": [
        "getting worse", "not improving", "worsening",
        "no improvement", "symptoms worse", "pain increased",
        "more frequent", "spreading",
    ],
    "mental_health": [
        "depressed", "depression", "anxiety", "panic attack",
        "can't sleep", "insomnia", "stressed", "overwhelmed",
        "hopeless", "suicidal",
    ],
}


def _scan_text_for_keywords(text: str, keywords: list[str]) -> list[tuple[str, str]]:
    """Scan text for keyword matches, return list of (keyword, evidence_snippet)."""
    text_lower = text.lower()
    matches = []
    for keyword in keywords:
        idx = text_lower.find(keyword.lower())
        if idx != -1:
            # Extract surrounding context as evidence
            start = max(0, idx - 40)
            end = min(len(text), idx + len(keyword) + 40)
            evidence = text[start:end].strip()
            if start > 0:
                evidence = "..." + evidence
            if end < len(text):
                evidence = evidence + "..."
            matches.append((keyword, evidence))
    return matches


def calculate_risk_score(
    patient_summary: PatientSummary,
    clinician_note: ClinicianNote,
) -> RiskAssessment:
    """Calculate risk score and detect red flags.

    Uses rule-based scoring based on extracted clinical data.
    Does NOT diagnose — only highlights what was mentioned in the conversation.

    Args:
        patient_summary: Patient-facing extracted data.
        clinician_note: Clinician-facing SOAP note.

    Returns:
        RiskAssessment with score, level, factors, and red flags.
    """
    risk_factors: list[RiskFactor] = []
    red_flags: list[RedFlag] = []
    total_score = 0

    # Combine all text for keyword scanning
    all_text_parts = [patient_summary.visit_summary]
    for med in patient_summary.medications:
        all_text_parts.extend([med.name, med.instructions, med.evidence])
    for test in patient_summary.tests_ordered:
        all_text_parts.extend([test.test_name, test.evidence])
    for fu in patient_summary.follow_up_plan:
        all_text_parts.extend([fu.action, fu.evidence])
    for lr in patient_summary.lifestyle_recommendations:
        all_text_parts.extend([lr.recommendation, lr.evidence])
    for rf in patient_summary.red_flags_for_patient:
        all_text_parts.extend([rf.warning, rf.evidence])
    for qa in patient_summary.questions_and_answers:
        all_text_parts.extend([qa.question, qa.answer, qa.evidence])

    # Add clinician note text
    soap = clinician_note.soap_note
    all_text_parts.extend([
        soap.subjective.chief_complaint,
        soap.subjective.history_of_present_illness,
        soap.subjective.review_of_systems,
        soap.objective.vitals,
        soap.objective.physical_exam_findings,
        soap.assessment.clinical_impression,
        soap.plan.follow_up,
        soap.plan.patient_education,
    ])
    all_text_parts.extend(soap.subjective.evidence)
    all_text_parts.extend(soap.objective.evidence)
    all_text_parts.extend(soap.assessment.evidence)
    all_text_parts.extend(soap.plan.evidence)

    all_text = " ".join(t for t in all_text_parts if t)

    # --- Rule-based scoring ---

    # 1. New medications: +10 per medication
    for med in patient_summary.medications:
        points = 10
        total_score += points
        risk_factors.append(RiskFactor(
            factor=f"New medication started: {med.name} {med.dose}".strip(),
            points=points,
            evidence=med.evidence,
        ))

    # 2. Multiple chronic conditions: +12 if >= 2 diagnoses
    diagnoses = clinician_note.soap_note.assessment.diagnoses
    if len(diagnoses) >= 2:
        points = 12
        total_score += points
        risk_factors.append(RiskFactor(
            factor=f"Multiple chronic conditions: {', '.join(diagnoses[:3])}",
            points=points,
            evidence="; ".join(clinician_note.soap_note.assessment.evidence[:2]) if clinician_note.soap_note.assessment.evidence else "",
        ))

    # 3. Severe symptoms: +points per symptom found
    for symptom, points in SEVERE_SYMPTOMS.items():
        matches = _scan_text_for_keywords(all_text, [symptom])
        if matches:
            total_score += points
            risk_factors.append(RiskFactor(
                factor=f"Severe symptom mentioned: {symptom}",
                points=points,
                evidence=matches[0][1],
            ))

    # 4. Non-adherence cues: +10 each
    for cue in NON_ADHERENCE_CUES:
        matches = _scan_text_for_keywords(all_text, [cue])
        if matches:
            total_score += 10
            risk_factors.append(RiskFactor(
                factor=f"Non-adherence cue: {cue}",
                points=10,
                evidence=matches[0][1],
            ))

    # 5. Urgent follow-up: +15
    for fu in patient_summary.follow_up_plan:
        timeline = fu.date_or_timeline.lower()
        if any(term in timeline for term in ["emergency", "er", "urgent", "immediately", "asap", "1 week", "one week", "3 days", "2 days", "tomorrow"]):
            total_score += 15
            risk_factors.append(RiskFactor(
                factor=f"Urgent follow-up required: {fu.action}",
                points=15,
                evidence=fu.evidence,
            ))
            break  # Only count once

    # 6. Abnormal vitals mentioned: +10
    vitals_text = clinician_note.soap_note.objective.vitals.lower()
    abnormal_terms = ["elevated", "high", "low", "abnormal", "irregular", "tachycardia", "bradycardia", "hypertension", "hypotension"]
    for term in abnormal_terms:
        if term in vitals_text:
            total_score += 10
            risk_factors.append(RiskFactor(
                factor=f"Abnormal vitals mentioned: {term}",
                points=10,
                evidence=clinician_note.soap_note.objective.vitals,
            ))
            break

    # 7. Mental health concerns: +8
    mental_matches = _scan_text_for_keywords(all_text, RED_FLAG_PATTERNS["mental_health"])
    if mental_matches:
        total_score += 8
        risk_factors.append(RiskFactor(
            factor=f"Mental health concern mentioned: {mental_matches[0][0]}",
            points=8,
            evidence=mental_matches[0][1],
        ))

    # Cap at 100
    total_score = min(total_score, 100)

    # --- Red flag detection ---
    for category, patterns in RED_FLAG_PATTERNS.items():
        matches = _scan_text_for_keywords(all_text, patterns)
        for keyword, evidence in matches:
            severity = "high" if category in ("emergency_symptom", "drug_interaction") else "medium"

            recommended_actions = {
                "emergency_symptom": "Seek immediate medical attention or call 911",
                "drug_interaction": "Review medication list with pharmacist or provider",
                "adherence_barrier": "Discuss patient assistance programs or generic alternatives",
                "worsening_condition": "Schedule urgent follow-up appointment",
                "mental_health": "Screen with PHQ-9/GAD-7 and consider referral",
            }

            red_flags.append(RedFlag(
                flag=f"{keyword} detected in conversation",
                severity=severity,
                category=category,
                evidence=evidence,
                recommended_action=recommended_actions.get(category, "Review with care team"),
            ))

    # Determine risk level
    if total_score <= RISK_LOW_MAX:
        risk_level = "low"
    elif total_score <= RISK_MEDIUM_MAX:
        risk_level = "medium"
    else:
        risk_level = "high"

    return RiskAssessment(
        risk_score=total_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        red_flags=red_flags,
        total_factors_detected=len(risk_factors),
    )
