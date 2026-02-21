# MedSift AI — Frontend Requirements

> Backend API: `http://localhost:8000` | Docs: `http://localhost:8000/docs`

---

## Two Portals

MedSift AI has two separate frontends that share the same backend API:

| Portal | Audience | Purpose |
|--------|----------|---------|
| **Patient Portal** | Patients (after their visit) | View their care plan, medications, follow-ups, red flags, and Q&A in plain language |
| **Doctor Portal** | Clinicians / providers | Upload audio, review SOAP notes, assess risk, browse research, provide feedback, view analytics |

Both portals connect to the same FastAPI backend at `http://localhost:8000`.

---

## Starting the Backend

```bash
# Terminal 1: Start the API server
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

The backend must be running before either portal can function. Interactive API docs are at `http://localhost:8000/docs`.

---

# Patient Portal

## Pages

### P1. My Visit Summary

**Purpose:** Patient views their after-visit care plan in plain, friendly language.

**Input:** Visit ID (from URL param, e.g. `/visit/8`)

**API calls:**
- `GET /api/visits/{id}` → full visit record

**Output displayed:**

| Section | Data Source | What to Show |
|---------|-----------|--------------|
| Visit Header | `visit_date`, `visit_type`, `tags` | "Your visit on Feb 21, 2026 — Urgent Care" |
| Visit Summary | `patient_summary.visit_summary` | Plain-text paragraph summarizing the visit |
| Medications | `patient_summary.medications[]` | Table: name, dose, frequency, duration, instructions. Show `evidence` on expand/hover |
| Tests Ordered | `patient_summary.tests_ordered[]` | List: test name, instructions, timeline. Show `evidence` on expand |
| Follow-Up Plan | `patient_summary.follow_up_plan[]` | Checklist: action + date/timeline. Show `evidence` on expand |
| Lifestyle Tips | `patient_summary.lifestyle_recommendations[]` | Cards: recommendation title + details. Show `evidence` on expand |
| When to Seek Urgent Care | `patient_summary.red_flags_for_patient[]` | Red/warning cards with `warning` text. **Always visible, not collapsed** |
| Questions & Answers | `patient_summary.questions_and_answers[]` | Accordion: Q → A pairs from the conversation |
| Risk Level | `risk_assessment.risk_level`, `risk_assessment.risk_score` | Simple badge (green/yellow/red) — no detailed breakdown for patients |
| Disclaimer | `risk_assessment.disclaimer` | Always shown prominently at top and bottom |

**Actions available:**
- **Download PDF** → `GET /api/export/{id}/pdf` (downloads After Visit Summary PDF)
- **Feedback on extractions** → `POST /api/feedback` with `feedback_type: "extraction_accuracy"` for each medication/test/follow-up (simple thumbs up/down)

**UX Notes:**
- Use simple, non-medical language where possible
- Red flags section should be visually prominent (red border, warning icon)
- Evidence quotes should be expandable, not shown by default (avoids overwhelming patients)
- Disclaimer must be visible without scrolling

---

### P2. My Visits (History)

**Purpose:** Patient sees all their past visits and can open any one.

**Input:** None (lists all visits)

**API calls:**
- `GET /api/visits?limit=50&offset=0` → paginated visit list

**Output displayed:**

| Element | Data Source | What to Show |
|---------|-----------|--------------|
| Visit Card | Each item in `visits[]` | Date, visit type, tags, risk level badge (green/yellow/red), summary snippet (first 100 chars of `visit_summary`) |
| Risk Badge | `risk_assessment.risk_level` | Color-coded: green (low), yellow (medium), red (high) |

**Actions available:**
- Click visit card → navigate to **P1. My Visit Summary** for that visit
- Pagination (next/prev using `offset`)

---

# Doctor Portal

## Pages

### D1. Upload & Process (Home)

**Purpose:** Clinician uploads patient-doctor audio recording and runs the full analysis pipeline.

**Inputs (form):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Audio file | File upload (drag & drop) | Yes | Accepts `.mp3`, `.wav`, `.m4a`, `.webm` |
| Visit date | Date picker | No (defaults to today) | ISO format `YYYY-MM-DD` |
| Visit type | Dropdown | No | Options: `routine checkup`, `follow-up`, `specialist`, `urgent care`, `telehealth` |
| Tags | Comma-separated text | No | e.g. `orthopedic, shoulder, sports injury` |

**API calls (sequential):**

```
Step 1: POST /api/transcribe
  Input:  multipart/form-data with `file`
  Output: { transcript, redacted_transcript, redaction_log, segments, duration, language, entity_count }

Step 2: POST /api/analyze
  Input:  { transcript: <redacted_transcript from step 1>, visit_date, visit_type, tags }
  Output: { visit_id, patient_summary, clinician_note, risk_assessment, clinical_trials, literature }
```

**Progress states:** `Transcribing audio...` → `Redacting PHI...` → `Analyzing with AI...` → `Searching trials & literature...` → `Done`

**Output displayed (5 tabs):**

#### Tab 1: Care Plan
| Section | Data Source | What to Show |
|---------|-----------|--------------|
| Visit Summary | `patient_summary.visit_summary` | Paragraph |
| Medications | `patient_summary.medications[]` | Table: name, dose, frequency, duration, instructions + evidence |
| Tests Ordered | `patient_summary.tests_ordered[]` | Table: test, instructions, timeline + evidence |
| Follow-Up Plan | `patient_summary.follow_up_plan[]` | Checklist with dates + evidence |
| Lifestyle Recs | `patient_summary.lifestyle_recommendations[]` | List with details + evidence |
| Red Flags | `patient_summary.red_flags_for_patient[]` | Warning cards |
| Q&A | `patient_summary.questions_and_answers[]` | Q/A pairs |

#### Tab 2: SOAP Note
| Section | Data Source | What to Show |
|---------|-----------|--------------|
| Subjective | `clinician_note.soap_note.subjective` | CC, HPI, ROS + evidence quotes |
| Objective | `clinician_note.soap_note.objective` | Vitals, PE findings + evidence |
| Assessment | `clinician_note.soap_note.assessment` | Diagnoses list, differential dx, clinical impression + evidence |
| Plan | `clinician_note.soap_note.plan` | Medications, tests, referrals, follow-up, patient education + evidence |
| Problem List | `clinician_note.problem_list[]` | Bulleted list |
| Action Items | `clinician_note.action_items[]` | List with priority badges (red=high, yellow=medium, green=low) |

#### Tab 3: Risk Assessment
| Section | Data Source | What to Show |
|---------|-----------|--------------|
| Score Gauge | `risk_assessment.risk_score` | Gauge or progress bar 0-100 |
| Risk Level | `risk_assessment.risk_level` | Badge: green (low), yellow (medium), red (high) |
| Risk Factors | `risk_assessment.risk_factors[]` | List: factor description + points + evidence |
| Red Flags | `risk_assessment.red_flags[]` | Cards: flag, severity badge, category, evidence, recommended action |
| Disclaimer | `risk_assessment.disclaimer` | Always shown prominently |

#### Tab 4: Trials & Literature
| Column | Data Source | What to Show |
|--------|-----------|--------------|
| Clinical Trials (left) | `clinical_trials[]` | Title (linked), NCT ID, status, conditions, interventions, location, match explanation |
| Published Research (right) | `literature[]` | Title (linked), authors, year, journal, citation count, abstract snippet, relevance explanation, source tag ([PubMed] or [Semantic Scholar]) |

**Feedback buttons on each paper/trial:** 👍 Relevant / 👎 Not relevant → `POST /api/feedback`

#### Tab 5: Export
| Action | API Call | Output |
|--------|----------|--------|
| Download Patient PDF | `GET /api/export/{visit_id}/pdf` | PDF file download |
| Download with SOAP | `GET /api/export/{visit_id}/pdf?include_soap=true` | PDF with SOAP note appended |

---

### D2. Visit History

**Purpose:** Browse, search, and manage all past visits.

**Inputs:**

| Field | Type | API Param | Notes |
|-------|------|-----------|-------|
| Search | Text input | `?search=` | Full-text search on transcripts |
| Tag filter | Chip/pill selector | `?tag=` | Filter by visit tags |
| Sort | Dropdown | `?sort=date` | Sort by date (default) |

**API calls:**
- `GET /api/visits?search=&tag=&sort=date&limit=50&offset=0`

**Output displayed:**

| Element | Data Source | What to Show |
|---------|-----------|--------------|
| Visit Card | Each `visits[]` item | Date, type, tags, risk badge, summary snippet |
| Risk Badge | `risk_assessment.risk_level` | Color-coded |
| Medication Count | `patient_summary.medications.length` | "3 medications" |
| Red Flag Count | `risk_assessment.red_flags.length` | "2 red flags" (if > 0, show in red) |

**Actions per visit:**
- Click → navigate to **D3. Visit Detail**
- Delete → `DELETE /api/visits/{id}` (with confirmation dialog)
- Quick PDF export → `GET /api/export/{id}/pdf`

**Pagination:** Next/Prev buttons using `limit` and `offset`

---

### D3. Visit Detail

**Purpose:** Full view of a single past visit with feedback capability.

**Input:** Visit ID (from URL param)

**API calls:**
- `GET /api/visits/{id}` → full visit record
- `GET /api/trials/{id}` → clinical trials (if refreshing)
- `GET /api/literature/{id}?refresh=false` → literature (use `?refresh=true` for refresh)

**Output displayed:** Same 5 tabs as D1 (Care Plan, SOAP, Risk, Trials & Literature, Export)

**Additional feedback UI per extracted item:**

| Item Type | Feedback Buttons | API Call |
|-----------|-----------------|----------|
| Medication | ✅ Correct / ❌ Incorrect / ⚠️ Missing | `POST /api/feedback` with `feedback_type: "extraction_accuracy"`, `item_type: "medication"` |
| Diagnosis | ✅ / ❌ / ⚠️ | `feedback_type: "extraction_accuracy"`, `item_type: "diagnosis"` |
| Test Ordered | ✅ / ❌ / ⚠️ | `feedback_type: "extraction_accuracy"`, `item_type: "test_ordered"` |
| Follow-Up | ✅ / ❌ / ⚠️ | `feedback_type: "extraction_accuracy"`, `item_type: "follow_up"` |
| Paper | 👍 Relevant / 👎 Not relevant | `feedback_type: "literature_relevance"`, `item_type: "paper"` |
| Trial | 👍 / 👎 | `feedback_type: "literature_relevance"`, `item_type: "trial"` |

Each feedback item can also include an optional `clinician_note` text field.

**Refresh Literature button:** `GET /api/literature/{id}?refresh=true` — re-runs PubMed + Semantic Scholar with updated boosted keywords from feedback.

---

### D4. Analytics Dashboard

**Purpose:** Aggregate metrics and trends across all visits.

**Input:** None

**API calls:**
- `GET /api/analytics`
- `GET /api/feedback/analytics`

**Output displayed:**

| Chart/Metric | Data Source | Visualization |
|-------------|-----------|---------------|
| Total Visits | `analytics.total_visits` | Big number |
| Avg Risk Score | `analytics.average_risk_score` | Big number with color |
| Extraction Accuracy | `analytics.extraction_accuracy_rate` | Percentage with progress bar |
| Literature Relevance | `analytics.literature_relevance_rate` | Percentage with progress bar |
| Risk Distribution | `analytics.risk_distribution` | Pie or bar chart (low/medium/high counts) |
| Top Conditions | `analytics.most_common_conditions[]` | Horizontal bar chart (top 10) — `{ condition, count }` |
| Top Medications | `analytics.most_common_medications[]` | Horizontal bar chart (top 10) — `{ medication, count }` |
| Visits Over Time | `analytics.visits_over_time[]` | Line or bar chart by month — `{ month, count }` |
| Red Flag Frequency | `analytics.red_flag_frequency` | Bar chart by category |
| Accuracy by Type | `feedback_analytics.accuracy_by_item_type` | Grouped bar/progress bars per item type |
| Top-Rated Papers | `feedback_analytics.most_relevant_papers[]` | List: title, positive_votes / total_votes |
| Useful Keywords | `feedback_analytics.most_useful_keywords[]` | Tag cloud or comma-separated list |
| Boosted Keywords | `analytics.top_boosted_keywords[]` | Tag cloud — these are keywords boosted by feedback for better literature results |

---

## API Endpoints Reference

### Core Pipeline

| Method | Endpoint | Input | Output |
|--------|----------|-------|--------|
| `POST` | `/api/transcribe` | `multipart/form-data` with `file` (mp3/wav/m4a/webm) | `{ transcript, redacted_transcript, redaction_log, segments[], duration, language, entity_count }` |
| `POST` | `/api/analyze` | `{ transcript, visit_date?, visit_type?, tags[], include_trials?, include_literature? }` | `{ visit_id, patient_summary, clinician_note, risk_assessment, clinical_trials[], literature[] }` |

### Visits CRUD

| Method | Endpoint | Params | Output |
|--------|----------|--------|--------|
| `GET` | `/api/visits` | `?search=&tag=&sort=date&limit=50&offset=0` | `{ visits[], count, offset, limit }` |
| `GET` | `/api/visits/{id}` | — | Full `VisitRecord` |
| `DELETE` | `/api/visits/{id}` | — | `{ message }` |

### Export & Research

| Method | Endpoint | Params | Output |
|--------|----------|--------|--------|
| `GET` | `/api/export/{id}/pdf` | `?include_soap=false` | PDF file download |
| `GET` | `/api/trials/{id}` | — | `{ visit_id, trials[], search_conditions, search_drugs }` |
| `GET` | `/api/literature/{id}` | `?refresh=false` | `{ visit_id, papers[], cached, search_conditions, search_drugs }` |

### Feedback Loop

| Method | Endpoint | Input/Params | Output |
|--------|----------|--------------|--------|
| `POST` | `/api/feedback` | `{ visit_id, feedback_type, item_type, item_value, rating, paper_url?, clinician_note? }` | `{ feedback_id, message }` |
| `GET` | `/api/feedback/analytics` | — | `{ total_feedback_count, extraction_accuracy_rate, literature_relevance_rate, accuracy_by_item_type, most_relevant_papers, most_useful_keywords }` |
| `GET` | `/api/feedback/{visit_id}` | — | `{ visit_id, feedback[], count }` |

### Analytics

| Method | Endpoint | Output |
|--------|----------|--------|
| `GET` | `/api/analytics` | `{ total_visits, risk_distribution, most_common_conditions, most_common_medications, red_flag_frequency, visits_over_time, average_risk_score, extraction_accuracy_rate, literature_relevance_rate, top_boosted_keywords }` |

---

## Data Shapes (TypeScript)

```typescript
// --- Transcription ---
interface TranscriptSegment {
  start_time: number;
  end_time: number;
  text: string; // Includes "Doctor: " or "Patient: " prefix
}

// --- Patient Summary ---
interface Medication {
  name: string;
  dose: string;
  frequency: string;
  duration: string;
  instructions: string;
  evidence: string; // Direct quote from transcript
}

interface TestOrdered {
  test_name: string;
  instructions: string;
  timeline: string;
  evidence: string;
}

interface FollowUpItem {
  action: string;
  date_or_timeline: string;
  evidence: string;
}

interface LifestyleRecommendation {
  recommendation: string;
  details: string;
  evidence: string;
}

interface RedFlagForPatient {
  warning: string;
  evidence: string;
}

interface QAItem {
  question: string;
  answer: string;
  evidence: string;
}

interface PatientSummary {
  visit_summary: string;
  medications: Medication[];
  tests_ordered: TestOrdered[];
  follow_up_plan: FollowUpItem[];
  lifestyle_recommendations: LifestyleRecommendation[];
  red_flags_for_patient: RedFlagForPatient[];
  questions_and_answers: QAItem[];
}

// --- SOAP Note ---
interface SOAPNote {
  subjective: {
    chief_complaint: string;
    history_of_present_illness: string;
    review_of_systems: string;
    evidence: string[];
  };
  objective: {
    vitals: string;
    physical_exam_findings: string;
    evidence: string[];
  };
  assessment: {
    diagnoses: string[];
    differential_diagnoses: string[];
    clinical_impression: string;
    evidence: string[];
  };
  plan: {
    medications: string[];
    tests_ordered: string[];
    referrals: string[];
    follow_up: string;
    patient_education: string;
    evidence: string[];
  };
}

interface ActionItem {
  action: string;
  priority: "high" | "medium" | "low";
  evidence: string;
}

interface ClinicianNote {
  soap_note: SOAPNote;
  problem_list: string[];
  action_items: ActionItem[];
}

// --- Risk Assessment ---
interface RiskFactor {
  factor: string;
  points: number;
  evidence: string;
}

interface RedFlag {
  flag: string;
  severity: "high" | "medium" | "low";
  category: string; // emergency_symptom | injury_trauma | drug_interaction | adherence_barrier | worsening_condition | mental_health
  evidence: string;
  recommended_action: string;
}

interface RiskAssessment {
  risk_score: number;       // 0-100
  risk_level: "low" | "medium" | "high";
  risk_factors: RiskFactor[];
  red_flags: RedFlag[];
  total_factors_detected: number;
  disclaimer: string;       // ALWAYS display this
}

// --- Clinical Trials ---
interface ClinicalTrial {
  nct_id: string;
  title: string;
  status: string;
  conditions: string[];
  interventions: string[];
  location: string;
  url: string;
  match_explanation: string;
}

// --- Literature ---
interface LiteratureResult {
  paper_id: string;
  title: string;
  authors: string[];        // Max 5
  year: number | null;
  journal: string | null;
  abstract_snippet: string; // First 200 chars
  citation_count: number;
  influential_citation_count: number;
  url: string;
  relevance_explanation: string; // Prefixed with [PubMed] or [Semantic Scholar]
}

// --- Feedback ---
interface FeedbackRequest {
  visit_id: number;
  feedback_type: "extraction_accuracy" | "literature_relevance";
  item_type: "medication" | "diagnosis" | "test_ordered" | "follow_up" | "paper" | "trial";
  item_value: string;
  rating: "correct" | "incorrect" | "missing" | "relevant" | "not_relevant";
  paper_url?: string;
  clinician_note?: string;
}

// --- Visit Record ---
interface VisitRecord {
  id: number;
  created_at: string;
  visit_date: string;
  visit_type: string;
  tags: string[];
  audio_duration_seconds: number;
  raw_transcript: string;           // PHI-redacted (never contains raw PHI)
  patient_summary: PatientSummary | null;
  clinician_note: ClinicianNote | null;
  risk_assessment: RiskAssessment | null;
  clinical_trials: ClinicalTrial[];
  literature_results: LiteratureResult[];
  transcript_segments: TranscriptSegment[];
}
```

---

## Feedback System UX

### Extraction Accuracy Feedback (Doctor Portal only)
- **Where:** Next to each extracted item (medication, test, diagnosis, follow-up)
- **Buttons:** ✅ Correct | ❌ Incorrect | ⚠️ Missing
- **API call:** `POST /api/feedback` with `feedback_type: "extraction_accuracy"`
- **Valid ratings:** `correct`, `incorrect`, `missing`

### Literature Relevance Feedback (Doctor Portal only)
- **Where:** Next to each paper and clinical trial
- **Buttons:** 👍 Relevant | 👎 Not relevant
- **API call:** `POST /api/feedback` with `feedback_type: "literature_relevance"`
- **Valid ratings:** `relevant`, `not_relevant`
- **Effect:** Updates keyword boost scores → future literature searches return better results

### Patient Feedback (Patient Portal)
- **Where:** Next to each medication and test on the patient summary
- **Buttons:** 👍 Looks right | 👎 Doesn't look right
- **API call:** Same `POST /api/feedback` endpoint
- **Keep it simple** — patients don't need the "missing" option

---

## Portal Summary

### Patient Portal — Screen Map

```
P1. My Visit Summary         /visit/:id
    Input:  visit_id (URL param)
    Output: Care plan, medications, tests, follow-ups, red flags, Q&A, PDF download

P2. My Visits                /visits
    Input:  none
    Output: List of visit cards with date, type, risk badge, summary snippet
```

### Doctor Portal — Screen Map

```
D1. Upload & Process         /upload
    Input:  Audio file + visit date + visit type + tags
    Output: Transcript, care plan, SOAP note, risk score, trials, literature, PDF

D2. Visit History            /visits
    Input:  Search query, tag filter, sort
    Output: Paginated visit list with risk badges, delete, PDF export

D3. Visit Detail             /visit/:id
    Input:  visit_id (URL param)
    Output: Full visit with all tabs + feedback buttons on every item

D4. Analytics Dashboard      /analytics
    Input:  none
    Output: Charts for risk distribution, conditions, medications, timeline, feedback metrics
```

---

## CORS

Backend allows all origins (`*`), so no CORS issues for local development.

---

## Important Notes

- Backend is fully functional at `http://localhost:8000`
- Interactive API docs at `http://localhost:8000/docs` (Swagger UI)
- Transcription takes ~30-60s for a 5-min audio file (Whisper base model, CPU)
- LLM analysis takes ~1-2 min per transcript (Ollama + llama3.1 local)
- **HIPAA:** All PHI is redacted before storage. The `raw_transcript` field in the database is already redacted. No raw PHI is ever returned by any API endpoint.
- **Always** show the `disclaimer` from RiskAssessment prominently
- The `evidence` field on every extracted item is the direct transcript quote — key for trust
- Literature results are tagged with `[PubMed]` or `[Semantic Scholar]` in `relevance_explanation` — PubMed results are prioritized
- Risk scoring uses rule-based scoring (0-100) with symptom cap of 30 points — not a diagnosis tool
