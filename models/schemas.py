"""Pydantic models for all MedSift AI data structures."""

from datetime import datetime, date
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class NullSafeModel(BaseModel):
    """Base model that coerces None values to defaults for str and list fields.

    LLMs often return null for optional fields. This ensures Pydantic
    validation doesn't fail on those cases.
    """

    @model_validator(mode="before")
    @classmethod
    def coerce_nulls(cls, data):
        if isinstance(data, dict):
            for field_name, field_info in cls.model_fields.items():
                if field_name in data and data[field_name] is None:
                    annotation = field_info.annotation
                    ann_str = str(annotation)
                    if annotation is str or annotation == str:
                        data[field_name] = ""
                    elif "list" in ann_str.lower():
                        data[field_name] = []
                    elif "dict" in ann_str.lower():
                        data[field_name] = {}
        return data


# --- Transcription ---

class TranscriptSegment(BaseModel):
    """A single timestamped segment from the transcript."""
    start_time: float
    end_time: float
    text: str


class TranscriptionResult(BaseModel):
    """Result from Whisper transcription."""
    text: str
    segments: list[TranscriptSegment] = []
    language: str = "en"
    duration_seconds: float = 0.0


# --- PHI Redaction ---

class RedactionEntry(BaseModel):
    """A single detected PHI entity."""
    entity_type: str
    original_position: tuple[int, int]
    replacement_tag: str


class RedactionResult(BaseModel):
    """Result from PHI redaction."""
    redacted_text: str
    redaction_log: list[RedactionEntry] = []
    entity_count: dict[str, int] = {}


# --- Patient-Facing Extraction ---

class Medication(NullSafeModel):
    """An extracted medication."""
    name: str
    dose: str = ""
    frequency: str = ""
    duration: str = ""
    instructions: str = ""
    evidence: str = ""
    verified: bool = True


class TestOrdered(NullSafeModel):
    """An extracted test order."""
    test_name: str
    instructions: str = ""
    timeline: str = ""
    evidence: str = ""
    verified: bool = True


class FollowUpItem(NullSafeModel):
    """An extracted follow-up action."""
    action: str
    date_or_timeline: str = ""
    evidence: str = ""
    verified: bool = True


class LifestyleRecommendation(NullSafeModel):
    """An extracted lifestyle recommendation."""
    recommendation: str
    details: str = ""
    evidence: str = ""
    verified: bool = True


class RedFlagForPatient(NullSafeModel):
    """A red flag warning for the patient."""
    warning: str
    evidence: str = ""
    verified: bool = True


class QAItem(NullSafeModel):
    """A question-answer pair from the visit."""
    question: str
    answer: str
    evidence: str = ""
    verified: bool = True


class PatientSummary(NullSafeModel):
    """Complete patient-facing extraction."""
    visit_summary: str = ""
    medications: list[Medication] = []
    tests_ordered: list[TestOrdered] = []
    follow_up_plan: list[FollowUpItem] = []
    lifestyle_recommendations: list[LifestyleRecommendation] = []
    red_flags_for_patient: list[RedFlagForPatient] = []
    questions_and_answers: list[QAItem] = []


# --- Clinician-Facing SOAP Note ---

class Subjective(NullSafeModel):
    """SOAP Subjective section — bullet-point findings."""
    findings: list[str] = []
    evidence: list[str] = []


class Objective(NullSafeModel):
    """SOAP Objective section — structured subsections."""
    vital_signs: list[str] = []
    physical_exam: list[str] = []
    mental_state_exam: list[str] = []
    lab_results: list[str] = []
    evidence: list[str] = []


class Assessment(NullSafeModel):
    """SOAP Assessment section — diagnoses and impressions as bullets."""
    findings: list[str] = []
    evidence: list[str] = []


class Plan(NullSafeModel):
    """SOAP Plan section — each action item as a bullet."""
    findings: list[str] = []
    evidence: list[str] = []


class SOAPNote(NullSafeModel):
    """Complete SOAP note."""
    subjective: Subjective = Field(default_factory=Subjective)
    objective: Objective = Field(default_factory=Objective)
    assessment: Assessment = Field(default_factory=Assessment)
    plan: Plan = Field(default_factory=Plan)


class ActionItem(NullSafeModel):
    """A clinician action item."""
    action: str
    priority: str = "medium"
    evidence: str = ""
    verified: bool = True

    @field_validator("priority", mode="before")
    @classmethod
    def coerce_priority(cls, v):
        if isinstance(v, str) and v.lower().strip() in ("high", "medium", "low"):
            return v.lower().strip()
        return "medium"


class ClinicianNote(NullSafeModel):
    """Complete clinician-facing extraction."""
    soap_note: SOAPNote = Field(default_factory=SOAPNote)
    problem_list: list[str] = []
    action_items: list[ActionItem] = []


# --- Clinical Trials ---

class ClinicalTrial(BaseModel):
    """A matching clinical trial from ClinicalTrials.gov."""
    nct_id: str
    title: str
    status: str = ""
    conditions: list[str] = []
    interventions: list[str] = []
    location: str = ""
    url: str = ""
    match_explanation: str = ""


# --- Literature Search ---

class LiteratureResult(BaseModel):
    """A paper from Semantic Scholar."""
    paper_id: str
    title: str
    authors: list[str] = []
    year: Optional[int] = None
    journal: Optional[str] = None
    abstract_snippet: str = ""
    citation_count: int = 0
    influential_citation_count: int = 0
    url: str = ""
    relevance_explanation: str = ""


# --- Feedback ---

class FeedbackItem(BaseModel):
    """A single feedback entry from a clinician."""
    feedback_id: Optional[int] = None
    visit_id: int
    feedback_type: str  # "extraction_accuracy" or "literature_relevance"
    item_type: str  # "medication", "diagnosis", "test_ordered", "follow_up", "paper", "trial"
    item_value: str
    rating: str  # "correct", "incorrect", "missing" for extraction; "relevant", "not_relevant" for literature
    paper_url: Optional[str] = None
    clinician_note: Optional[str] = None
    timestamp: Optional[datetime] = None


class BoostedKeyword(BaseModel):
    """A keyword with feedback-derived boost score."""
    keyword: str
    positive_count: int = 0
    negative_count: int = 0
    boost_score: float = 0.0


class FeedbackAnalytics(BaseModel):
    """Aggregated feedback metrics."""
    total_feedback_count: int = 0
    extraction_accuracy_rate: float = 0.0
    literature_relevance_rate: float = 0.0
    accuracy_by_item_type: dict[str, float] = {}
    most_relevant_papers: list[dict] = []
    most_useful_keywords: list[str] = []


# --- Visit Record ---

class VisitRecord(BaseModel):
    """Complete visit record stored in database."""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    visit_date: Optional[date] = None
    visit_type: str = ""
    tags: list[str] = []
    audio_duration_seconds: float = 0.0
    raw_transcript: str = ""
    patient_summary: Optional[PatientSummary] = None
    clinician_note: Optional[ClinicianNote] = None
    clinical_trials: list[ClinicalTrial] = []
    literature_results: list[LiteratureResult] = []
    transcript_segments: list[TranscriptSegment] = []


# --- Analytics ---

class AnalyticsSummary(BaseModel):
    """Dashboard analytics aggregation."""
    total_visits: int = 0
    most_common_conditions: list[dict] = []
    most_common_medications: list[dict] = []
    visits_over_time: list[dict] = []
    extraction_accuracy_rate: float = 0.0
    literature_relevance_rate: float = 0.0
    top_boosted_keywords: list[str] = []
