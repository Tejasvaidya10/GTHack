"""Tests for risk scoring module.

Fully offline — pure rule-based logic on Pydantic models, no mocking needed.
"""

import pytest
from core.risk_scoring import calculate_risk_score
from models.schemas import (
    PatientSummary, ClinicianNote, Medication, FollowUpItem,
    SOAPNote, Subjective, Objective, Assessment, Plan,
    RiskAssessment,
)


def _make_patient(**kwargs) -> PatientSummary:
    """Build a PatientSummary with given overrides."""
    return PatientSummary(**kwargs)


def _make_clinician(diagnoses=None, vitals="", chief_complaint="", **kwargs) -> ClinicianNote:
    """Build a ClinicianNote with SOAP sub-models."""
    return ClinicianNote(
        soap_note=SOAPNote(
            subjective=Subjective(chief_complaint=chief_complaint),
            objective=Objective(vitals=vitals),
            assessment=Assessment(diagnoses=diagnoses or []),
        ),
        **kwargs,
    )


def test_empty_data_low_risk():
    """Empty patient summary and clinician note should yield zero risk."""
    result = calculate_risk_score(_make_patient(), _make_clinician())

    assert result.risk_score == 0
    assert result.risk_level == "low"
    assert result.risk_factors == []
    assert result.total_factors_detected == 0


def test_single_medication_score():
    """One medication should add 8 points (first med)."""
    patient = _make_patient(medications=[Medication(name="Lisinopril", dose="10mg")])
    result = calculate_risk_score(patient, _make_clinician())

    assert result.risk_score == 8
    assert len(result.risk_factors) == 1
    assert result.risk_factors[0].points == 8
    assert "Lisinopril" in result.risk_factors[0].factor


def test_multiple_medications_cumulative():
    """Multiple medications should accumulate points (8 + 5 + 5 = 18)."""
    meds = [
        Medication(name="Lisinopril", dose="10mg"),
        Medication(name="Metformin", dose="500mg"),
        Medication(name="Atorvastatin", dose="20mg"),
    ]
    patient = _make_patient(medications=meds)
    result = calculate_risk_score(patient, _make_clinician())

    assert result.risk_score == 18
    med_factors = [f for f in result.risk_factors if "medication" in f.factor.lower()]
    assert len(med_factors) == 3


def test_severe_symptom_points():
    """Severe symptoms in visit summary should add points."""
    patient = _make_patient(visit_summary="Patient reports chest pain and difficulty breathing.")
    result = calculate_risk_score(patient, _make_clinician())

    # chest pain = 15, difficulty breathing = 15
    symptom_factors = [f for f in result.risk_factors if "symptom" in f.factor.lower()]
    assert len(symptom_factors) >= 2
    total_symptom_points = sum(f.points for f in symptom_factors)
    assert total_symptom_points >= 30


def test_non_adherence_detection():
    """Non-adherence cues should be detected and scored."""
    patient = _make_patient(
        visit_summary="Patient says they stopped taking their medication because it's too expensive."
    )
    result = calculate_risk_score(patient, _make_clinician())

    adherence_factors = [f for f in result.risk_factors if "adherence" in f.factor.lower()]
    assert len(adherence_factors) >= 2  # "stopped taking" and "too expensive"


def test_score_caps_at_100():
    """Risk score should never exceed 100."""
    meds = [Medication(name=f"Drug{i}") for i in range(5)]
    patient = _make_patient(
        medications=meds,
        visit_summary=(
            "Patient has chest pain, difficulty breathing, seizure, stroke, "
            "suicidal thoughts. They stopped taking meds, can't afford them, "
            "forgot doses, and ran out of medication."
        ),
    )
    clinician = _make_clinician(
        diagnoses=["Diabetes", "Hypertension", "Heart Disease"],
        vitals="Blood pressure elevated, tachycardia noted",
    )
    result = calculate_risk_score(patient, clinician)

    assert result.risk_score == 100


@pytest.mark.parametrize("summary,expected_level", [
    ("", "low"),                                                           # 0 points
    ("Patient has dizziness.", "low"),                                     # 8 points
    ("Patient has chest pain and difficulty breathing. They stopped taking their medication.", "medium"),  # 30 symptom + 10 non-adherence = 40
    ("Patient has chest pain, suicidal thoughts, stopped taking meds, too expensive, forgot doses.", "high"),  # symptoms + adherence
])
def test_risk_level_boundaries(summary, expected_level):
    """Risk level boundaries: 0-30 low, 31-60 medium, 61+ high."""
    patient = _make_patient(visit_summary=summary)
    result = calculate_risk_score(patient, _make_clinician())

    assert result.risk_level == expected_level


def test_red_flag_emergency():
    """Emergency symptoms should trigger high-severity red flags."""
    patient = _make_patient(visit_summary="Patient experiencing chest pain and shortness of breath.")
    result = calculate_risk_score(patient, _make_clinician())

    emergency_flags = [rf for rf in result.red_flags if rf.category == "emergency_symptom"]
    assert len(emergency_flags) >= 1
    assert all(rf.severity == "high" for rf in emergency_flags)


def test_red_flag_all_categories():
    """Text covering all 5 red flag categories should detect all of them."""
    patient = _make_patient(
        visit_summary=(
            "Patient has chest pain. There is a drug interaction concern. "
            "They can't afford their medication. Symptoms are getting worse. "
            "Patient feels depressed and overwhelmed."
        ),
    )
    result = calculate_risk_score(patient, _make_clinician())

    detected_categories = {rf.category for rf in result.red_flags}
    expected = {"emergency_symptom", "drug_interaction", "adherence_barrier",
                "worsening_condition", "mental_health"}
    assert expected.issubset(detected_categories)


def test_disclaimer_present():
    """Every risk assessment should include a medical disclaimer."""
    result = calculate_risk_score(_make_patient(), _make_clinician())

    assert result.disclaimer
    assert "does not constitute a medical diagnosis" in result.disclaimer
