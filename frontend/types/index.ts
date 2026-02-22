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
  duration: string;
  instructions: string;
  evidence: string;
  verified?: number;
}

export interface TestOrdered {
  test_name: string;
  instructions: string;
  timeline: string;
  evidence: string;
  verified?: number;
}

export interface FollowUpItem {
  action: string;
  date_or_timeline: string;
  evidence: string;
  verified?: number;
}

export interface LifestyleRecommendation {
  recommendation: string;
  details: string;
  evidence: string;
  verified?: number;
}

export interface RedFlagForPatient {
  warning: string;
  evidence: string;
  verified?: number;
}

export interface QAItem {
  question: string;
  answer: string;
  evidence: string;
  verified?: number;
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
  findings: string[];
  evidence: string[];
}

export interface ObjectiveSection extends SOAPSection {
  vital_signs: string[];
  physical_exam: string[];
  mental_state_exam: string[];
  lab_results: string[];
}

export interface SOAPNote {
  subjective: SOAPSection;
  objective: ObjectiveSection;
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
  clinical_trials: ClinicalTrial[];
  literature_results: LiteratureResult[];
  transcript_segments: TranscriptSegment[];
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export interface AnalyticsSummary {
  total_visits: number;
  top_conditions: { condition: string; count: number }[];
  top_medications: { medication: string; count: number }[];
  visits_over_time: { date: string; count: number }[];
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

export interface AnalyzeResponse {
  visit_id: number;
  patient_summary: PatientSummary;
  clinician_note: ClinicianNote;
  clinical_trials: ClinicalTrial[];
  literature: LiteratureResult[];
  grounding?: GroundingReport;
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
