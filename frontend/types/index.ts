// ─── Transcription ───────────────────────────────────────────────────────────
export interface TranscriptSegment {
  start_time: number;
  end_time: number;
  text: string;
}

export interface TranscriptionResult {
  text: string;
  segments: TranscriptSegment[];
  language: string;
  duration_seconds: number;
}

export interface RedactionLog {
  entity_type: string;
  start: number;
  end: number;
  replacement: string;
}

export interface RedactionResult {
  redacted_text: string;
  redaction_log: RedactionLog[];
  entity_count: Record<string, number>;
}

// ─── Patient Summary ──────────────────────────────────────────────────────────
export interface Medication {
  name: string;
  dose: string;
  frequency: string;
  duration?: string;
  instructions: string;
  evidence?: string;
  status?: "active" | "review" | "stopped";
}

export interface TestOrdered {
  test_name: string;
  instructions: string;
  timeline: string;
  evidence: string;
}

export interface FollowUpItem {
  action: string;
  date_or_timeline: string;
  evidence: string;
}

export interface LifestyleRecommendation {
  recommendation: string;
  details: string;
  evidence: string;
}

export interface RedFlagForPatient {
  warning: string;
  evidence: string;
}

export interface QAItem {
  question: string;
  answer: string;
  evidence: string;
}

export interface PatientSummary {
  visit_summary: string;
  medications: Medication[];
  tests_ordered: TestOrdered[];
  follow_up_plan: FollowUpItem[];
  lifestyle_recommendations: LifestyleRecommendation[];
  red_flags_for_patient: RedFlagForPatient[];
  questions_and_answers: QAItem[];
}

// ─── Clinician SOAP Note ──────────────────────────────────────────────────────
export interface SOAPSection {
  chief_complaint?: string;
  history_of_present_illness?: string;
  review_of_systems?: string;
  vitals?: string;
  physical_exam_findings?: string;
  diagnoses?: string[];
  differential_diagnoses?: string[];
  clinical_impression?: string;
  medications?: Medication[];
  tests_ordered?: TestOrdered[];
  referrals?: string[];
  follow_up?: string;
  patient_education?: string;
  evidence: string[];
}

export interface SOAPNote {
  subjective: SOAPSection;
  objective: SOAPSection;
  assessment: SOAPSection;
  plan: SOAPSection;
}

export interface ActionItem {
  action: string;
  priority: "high" | "medium" | "low";
  evidence: string;
}

export interface ClinicianNote {
  soap_note: SOAPNote;
  problem_list: string[];
  action_items: ActionItem[];
}

// ─── Risk Assessment ──────────────────────────────────────────────────────────
export type RiskLevel = "low" | "medium" | "high";

export interface RiskFactor {
  factor: string;
  points: number;
  evidence: string;
}

export interface RedFlag {
  flag: string;
  severity: "high" | "medium" | "low";
  category: string;
  evidence: string;
  recommended_action: string;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: RiskLevel;
  risk_factors: RiskFactor[];
  red_flags: RedFlag[];
  total_factors_detected: number;
}

// ─── Clinical Trials ──────────────────────────────────────────────────────────
export interface ClinicalTrial {
  nct_id: string;
  brief_title: string;
  status: string;
  conditions: string[];
  interventions: string[];
  location?: string;
  url: string;
  why_it_matches: string;
}

// ─── Literature ───────────────────────────────────────────────────────────────
export interface LiteratureResult {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  journal: string;
  abstract_snippet: string;
  citation_count: number;
  influential_citation_count: number;
  url: string;
  relevance_explanation: string;
}

// ─── Feedback ─────────────────────────────────────────────────────────────────
export type FeedbackType = "extraction_accuracy" | "literature_relevance";
export type ExtractionRating = "correct" | "incorrect" | "missing";
export type LiteratureRating = "relevant" | "not_relevant";

export interface FeedbackItem {
  feedback_id?: number;
  visit_id: number;
  feedback_type: FeedbackType;
  item_type: string;
  item_value: string;
  rating: ExtractionRating | LiteratureRating;
  paper_url?: string;
  clinician_note?: string;
  timestamp?: string;
}

export interface BoostedKeyword {
  keyword: string;
  positive_count: number;
  negative_count: number;
  boost_score: number;
}

export interface FeedbackAnalytics {
  total_feedback_count: number;
  extraction_accuracy_rate: number;
  literature_relevance_rate: number;
  accuracy_by_item_type: Record<string, number>;
  most_relevant_papers: { title: string; positive_votes: number; total_votes: number }[];
  most_useful_keywords: string[];
}

// ─── Visit Record ─────────────────────────────────────────────────────────────
export interface VisitRecord {
  id: number;
  created_at: string;
  visit_date: string;
  visit_type: string;
  tags: string[];
  audio_duration_seconds: number;
  raw_transcript: string;
  patient_summary: PatientSummary;
  clinician_note: ClinicianNote;
  risk_assessment: RiskAssessment;
  clinical_trials: ClinicalTrial[];
  literature_results: LiteratureResult[];
  transcript_segments: TranscriptSegment[];
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export interface AnalyticsSummary {
  total_visits: number;
  risk_distribution: { low: number; medium: number; high: number };
  top_conditions: { condition: string; count: number }[];
  top_medications: { medication: string; count: number }[];
  red_flag_frequency: Record<string, number>;
  visits_over_time: { date: string; count: number }[];
  avg_risk_score: number;
  extraction_accuracy_rate: number;
  literature_relevance_rate: number;
  top_boosted_keywords: BoostedKeyword[];
}

// ─── API Responses ────────────────────────────────────────────────────────────
export interface TranscribeResponse {
  transcript: string;
  redacted_transcript: string;
  redaction_log: RedactionLog[];
  segments: TranscriptSegment[];
  duration: number;
}

export interface AnalyzeResponse {
  visit_id: number;
  patient_summary: PatientSummary;
  clinician_note: ClinicianNote;
  risk_assessment: RiskAssessment;
  clinical_trials: ClinicalTrial[];
  literature: LiteratureResult[];
}

// ─── Auth (simulated) ─────────────────────────────────────────────────────────
export type UserRole = "patient" | "clinician";

export interface AuthUser {
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
  sms_consent?: boolean;
}
// ─── Grounding / Hallucination Detection ──────────────────────────────────────
export interface GroundingItem {
  category: string;
  item: string;
  index: number;
  score: number;
  evidence_match: number;
  claim_support: number;
  has_evidence: boolean;
  flag: "grounded" | "likely_grounded" | "uncertain" | "likely_hallucinated";
}

export interface GroundingReport {
  overall_score: number;
  overall_flag: "grounded" | "likely_grounded" | "uncertain" | "likely_hallucinated";
  total_items: number;
  grounded_count: number;
  flagged_count: number;
  items: GroundingItem[];
}
