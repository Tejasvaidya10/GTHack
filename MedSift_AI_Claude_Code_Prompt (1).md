# MedSift AI — Claude Code Build Prompt

## Project Overview

Build **MedSift AI**, a fully local, zero-cost, AI-powered healthcare conversation intelligence system. It takes a patient-doctor visit audio recording, transcribes it, redacts PHI, extracts structured clinical data, generates a patient-friendly care plan and a clinician-friendly SOAP note, runs risk scoring with red flag detection, optionally links to clinical trials, stores everything in a local database, and provides an analytics dashboard.

**Everything runs locally. No paid APIs. No cloud services. Total cost: $0.**

---

## Tech Stack (Mandatory)

| Component | Tool | Notes |
|---|---|---|
| Language | Python 3.10+ | Entire backend in Python |
| Transcription | `openai-whisper` (local) | Use `base` or `small` model. NOT the OpenAI API. Install via `pip install openai-whisper` |
| LLM | Ollama + `llama3:8b` | Local inference. All prompts go through Ollama's API at `http://localhost:11434` |
| PHI Redaction | Microsoft Presidio | `presidio-analyzer` + `presidio-anonymizer`. Add custom recognizers for MRNs and insurance IDs |
| Database | SQLite | Single file DB. No Supabase, no Postgres |
| PDF Export | `fpdf2` | For generating After Visit Summary PDFs |
| Clinical Trials | ClinicalTrials.gov API v2 | Free public API, no key needed. `https://clinicaltrials.gov/api/v2/studies` |
| Literature Search | Semantic Scholar API | Free, no key needed. `https://api.semanticscholar.org/graph/v1/paper/search` — for retrieving published research papers ranked by citation count |
| Frontend | **SKIP FOR NOW** | Frontend will be built separately in Figma + coded later. Build only the backend, API layer, and a minimal Streamlit test interface for demo/testing |

---

## Project Structure

Create this exact directory structure:

```
medsift-ai/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.sh                     # One-command setup script
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   └── config.py                # App configuration and constants
│
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── transcribe.py        # POST /api/transcribe
│   │   ├── analyze.py           # POST /api/analyze
│   │   ├── visits.py            # CRUD for visits
│   │   ├── export.py            # GET /api/export/{visit_id}/pdf
│   │   ├── trials.py            # GET /api/trials/{visit_id}
│   │   ├── literature.py        # GET /api/literature/{visit_id}
│   │   ├── feedback.py          # POST /api/feedback
│   │   └── analytics.py         # GET /api/analytics
│   └── dependencies.py          # Shared dependencies
│
├── core/
│   ├── __init__.py
│   ├── transcription.py         # Whisper transcription logic
│   ├── phi_redaction.py         # Presidio PHI detection + masking
│   ├── extraction.py            # LLM structured extraction (care plan + SOAP)
│   ├── risk_scoring.py          # Risk score + red flag detection
│   ├── clinical_trials.py       # ClinicalTrials.gov integration
│   ├── literature_search.py     # Semantic Scholar literature retrieval
│   ├── feedback.py              # Clinician feedback loop logic
│   └── pdf_generator.py         # PDF export logic
│
├── models/
│   ├── __init__.py
│   ├── schemas.py               # Pydantic models for all data structures
│   └── database.py              # SQLite setup, models, CRUD operations
│
├── prompts/
│   ├── extraction_patient.txt   # Prompt for patient-facing extraction
│   ├── extraction_clinician.txt # Prompt for clinician-facing SOAP note
│   └── risk_scoring.txt         # Prompt for risk scoring
│
├── tests/
│   ├── __init__.py
│   ├── test_transcription.py
│   ├── test_phi_redaction.py
│   ├── test_extraction.py
│   ├── test_risk_scoring.py
│   └── sample_audio/            # Put a sample .wav or .mp3 here for testing
│       └── sample_visit.mp3
│
├── streamlit_demo/
│   └── app.py                   # Minimal Streamlit test UI for demo/testing
│
└── data/
    └── medsift.db               # SQLite database (auto-created)
```

---

## Detailed Module Specifications

### 1. `core/transcription.py` — Whisper Transcription

```python
# Interface:
def transcribe_audio(file_path: str, model_size: str = "base") -> TranscriptionResult
```

- Load Whisper model (cache it after first load, don't reload every call)
- Accept audio file path (support .mp3, .wav, .m4a, .webm)
- Return a `TranscriptionResult` Pydantic model containing:
  - `text`: full transcript string
  - `segments`: list of segments with start_time, end_time, and text (for evidence linking later)
  - `language`: detected language
  - `duration_seconds`: total audio duration
- Handle errors gracefully (file not found, corrupted audio, unsupported format)

---

### 2. `core/phi_redaction.py` — PHI Redaction

```python
# Interface:
def redact_phi(text: str) -> RedactionResult
```

- Use `presidio-analyzer` with the default NLP engine (spaCy `en_core_web_lg`)
- Detect these entity types at minimum:
  - PERSON (names)
  - PHONE_NUMBER
  - EMAIL_ADDRESS
  - LOCATION (street addresses)
  - US_SSN
- Add **custom recognizers** for:
  - Medical Record Numbers (MRN): pattern like `MRN-\d{6,10}` or `MRN: \d+`
  - Insurance IDs: pattern like `INS-\d+` or common insurance ID formats
- Use `presidio-anonymizer` to replace detected entities with placeholder tags like `[PERSON_1]`, `[PHONE_1]`, `[LOCATION_1]` etc.
- Return a `RedactionResult` containing:
  - `redacted_text`: the de-identified transcript
  - `redaction_log`: list of what was found and masked (entity type, original position, replacement tag)
  - `entity_count`: count by entity type

---

### 3. `core/extraction.py` — LLM Structured Extraction

This is the most critical module. It calls Ollama's local API to extract structured clinical data.

```python
# Interface:
def extract_patient_summary(transcript: str) -> PatientSummary
def extract_clinician_note(transcript: str) -> ClinicianNote
```

**Ollama API call pattern:**
```python
import requests
import json

def call_ollama(prompt: str, system_prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3:8b",
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temp for consistent extraction
                "num_predict": 4096
            }
        }
    )
    return response.json()["response"]
```

**Patient-facing extraction must return (as JSON):**
```json
{
  "visit_summary": "Plain language summary of what was discussed",
  "medications": [
    {
      "name": "Metformin",
      "dose": "500mg",
      "frequency": "twice daily",
      "duration": "ongoing",
      "instructions": "Take with food",
      "evidence": "Doctor said: 'Let's start you on Metformin 500mg twice a day'"
    }
  ],
  "tests_ordered": [
    {
      "test_name": "HbA1c",
      "instructions": "Fasting blood draw",
      "timeline": "Within 2 weeks",
      "evidence": "Transcript segment supporting this"
    }
  ],
  "follow_up_plan": [
    {
      "action": "Return visit in 3 months",
      "date_or_timeline": "3 months",
      "evidence": "transcript quote"
    }
  ],
  "lifestyle_recommendations": [
    {
      "recommendation": "Reduce sugar intake",
      "details": "Limit sugary drinks, aim for <25g added sugar daily",
      "evidence": "transcript quote"
    }
  ],
  "red_flags_for_patient": [
    {
      "warning": "Seek emergency care if blood sugar drops below 70",
      "evidence": "transcript quote"
    }
  ],
  "questions_and_answers": [
    {
      "question": "Can I still eat rice?",
      "answer": "Yes, but switch to brown rice and limit portions",
      "evidence": "transcript quote"
    }
  ]
}
```

**Clinician-facing SOAP note must return (as JSON):**
```json
{
  "soap_note": {
    "subjective": {
      "chief_complaint": "...",
      "history_of_present_illness": "...",
      "review_of_systems": "...",
      "evidence": ["transcript quotes"]
    },
    "objective": {
      "vitals": "...",
      "physical_exam_findings": "...",
      "evidence": ["transcript quotes"]
    },
    "assessment": {
      "diagnoses": ["Type 2 Diabetes Mellitus"],
      "differential_diagnoses": [],
      "clinical_impression": "...",
      "evidence": ["transcript quotes"]
    },
    "plan": {
      "medications": [],
      "tests_ordered": [],
      "referrals": [],
      "follow_up": "...",
      "patient_education": "...",
      "evidence": ["transcript quotes"]
    }
  },
  "problem_list": ["Type 2 DM - new diagnosis", "Obesity - BMI 32"],
  "action_items": [
    {
      "action": "Order HbA1c",
      "priority": "high",
      "evidence": "transcript quote"
    }
  ]
}
```

**CRITICAL PROMPT ENGINEERING RULES:**
- Every extracted item MUST include an `evidence` field with a direct quote or reference from the transcript
- If something is not mentioned in the transcript, do NOT fabricate it. Return empty/null
- Use low temperature (0.1) for consistent structured output
- Ask the model to return ONLY valid JSON, no markdown formatting, no preamble
- If the model returns malformed JSON, implement a retry with a stricter prompt (up to 2 retries)
- Parse the JSON response and validate against Pydantic models

---

### 4. `core/risk_scoring.py` — Risk Score + Red Flag Detection

```python
# Interface:
def calculate_risk_score(patient_summary: PatientSummary, clinician_note: ClinicianNote) -> RiskAssessment
```

This module uses a **hybrid approach**: rule-based scoring augmented by LLM analysis.

**Rule-based signals (each contributes points to a 0-100 score):**
- New medication started → +10 points per med
- Medication dose changed → +8 points
- Severe symptoms described (chest pain, shortness of breath, severe pain, confusion, etc.) → +15 points each
- Multiple chronic conditions mentioned (≥2) → +12 points
- Non-adherence cues detected (cost concerns, forgetting meds, confusion about instructions) → +10 points each
- Urgent follow-up required (ER visit, < 1 week follow-up) → +15 points
- Abnormal vitals mentioned → +10 points
- Mental health concerns mentioned → +8 points

**Risk buckets:**
- 0-30: Low risk (green)
- 31-60: Medium risk (yellow)
- 61-100: High risk (red)

**Red flag detection:**
Scan the extracted data for urgent situations:
- Chest pain, difficulty breathing, suicidal ideation, stroke symptoms, severe allergic reaction
- Drug interactions mentioned
- Patient expressed they can't afford medication
- Symptoms worsening despite treatment

**Return a `RiskAssessment` model:**
```json
{
  "risk_score": 65,
  "risk_level": "high",
  "risk_factors": [
    {
      "factor": "New medication started: Metformin",
      "points": 10,
      "evidence": "transcript quote"
    },
    {
      "factor": "Multiple chronic conditions: diabetes, hypertension",
      "points": 12,
      "evidence": "transcript quote"
    }
  ],
  "red_flags": [
    {
      "flag": "Patient expressed inability to afford insulin",
      "severity": "high",
      "category": "adherence_barrier",
      "evidence": "transcript quote",
      "recommended_action": "Discuss patient assistance programs or generic alternatives"
    }
  ],
  "total_factors_detected": 5
}
```

**IMPORTANT: The system does NOT diagnose. It only highlights what was explicitly mentioned in the conversation. Add a disclaimer to every risk assessment output.**

---

### 5. `core/clinical_trials.py` — Clinical Trials Linking

```python
# Interface:
def find_relevant_trials(conditions: list[str], drugs: list[str], keywords: list[str]) -> list[ClinicalTrial]
```

- Use ClinicalTrials.gov API v2: `https://clinicaltrials.gov/api/v2/studies`
- Query parameters:
  - `query.cond` for conditions
  - `query.intr` for interventions/drugs
  - `filter.overallStatus` = `RECRUITING` (only show active trials)
  - `pageSize` = 5 (limit results)
- For each result, return:
  - Trial title (nctId, briefTitle)
  - Status
  - Conditions being studied
  - Interventions
  - Location (if available)
  - URL to the trial page: `https://clinicaltrials.gov/study/{nctId}`
  - A "why it matches" explanation generated from the extracted visit data
- Handle API errors gracefully. If the API is down, return an empty list with a message, don't crash.

---

### 6. `core/literature_search.py` — Semantic Scholar Literature Retrieval

```python
# Interface:
def search_literature(conditions: list[str], drugs: list[str], keywords: list[str]) -> list[LiteratureResult]
```

- Use the Semantic Scholar Academic Graph API: `https://api.semanticscholar.org/graph/v1/paper/search`
- Free, no API key required (rate limited to 100 requests/5 minutes without a key)
- Query construction:
  - Combine conditions, drugs, and keywords into a search query string
  - Example: conditions=["Type 2 Diabetes"], drugs=["Metformin"] → query="Type 2 Diabetes Metformin treatment"
- Request parameters:
  - `query`: the constructed search string
  - `limit`: 10 (top 10 papers)
  - `fields`: `title,abstract,url,year,citationCount,influentialCitationCount,authors,journal`
- Ranking: Sort returned papers by `influentialCitationCount` (descending), then by `year` (most recent first) as a tiebreaker
- For each result, return a `LiteratureResult` Pydantic model:
```json
{
  "paper_id": "semantic_scholar_paper_id",
  "title": "Metformin for Type 2 Diabetes: A Systematic Review",
  "authors": ["Author A", "Author B"],
  "year": 2023,
  "journal": "The Lancet",
  "abstract_snippet": "First 200 chars of abstract...",
  "citation_count": 450,
  "influential_citation_count": 32,
  "url": "https://www.semanticscholar.org/paper/...",
  "relevance_explanation": "Matches extracted condition 'Type 2 Diabetes' and medication 'Metformin'"
}
```
- Generate the `relevance_explanation` by matching which extracted entities from the visit correspond to the paper's topic. This does NOT require an LLM call — simple string matching of conditions/drugs against the paper title and abstract is sufficient.
- Handle rate limiting gracefully: if you get a 429 response, wait 1 second and retry once. If it fails again, return what you have.
- This complements ClinicalTrials.gov: trials show active recruiting studies, Semantic Scholar shows published research. Both are valuable for different reasons.

---

### 7. `core/feedback.py` — Clinician Feedback Loop

```python
# Interface:
def submit_feedback(feedback: FeedbackItem) -> int          # Returns feedback_id
def get_feedback_for_visit(visit_id: int) -> list[FeedbackItem]
def get_feedback_analytics() -> FeedbackAnalytics
def get_boosted_keywords() -> list[BoostedKeyword]           # Keywords that improve search based on positive feedback
```

This module implements a feedback loop where clinicians can rate the accuracy of extracted items and the relevance of recommended literature. This is the "ML learning loop" that demonstrates the system gets smarter over time.

**How it works:**

1. **Extraction accuracy feedback**: After reviewing a care plan or SOAP note, the clinician can mark each extracted item (medication, diagnosis, test, etc.) as:
   - `correct` — the extraction is accurate
   - `incorrect` — the extraction is wrong or hallucinated
   - `missing` — something important was mentioned but not extracted

2. **Literature relevance feedback**: For each recommended paper (from Semantic Scholar) or trial (from ClinicalTrials.gov), the clinician can give:
   - 👍 (`relevant` = true) — this paper/trial is useful
   - 👎 (`relevant` = false) — this is not relevant

3. **Feedback-boosted search**: Over time, the system uses accumulated feedback to improve future literature searches:
   - Track which keywords/conditions led to positively-rated papers
   - When the same condition appears in a new visit, boost those proven-good keywords in the search query
   - This is Content-Based Filtering — simple but effective and demonstrable

**Pitch angle for judges:** "We start with content-based filtering (keyword matching). As clinicians provide feedback, we build a proprietary dataset that enables us to move toward collaborative filtering — recommending papers that similar clinicians found useful. We're solving the cold-start problem in medical recommendation systems."

**FeedbackItem Pydantic model:**
```json
{
  "feedback_id": 1,
  "visit_id": 42,
  "feedback_type": "extraction_accuracy",
  "item_type": "medication",
  "item_value": "Metformin 500mg",
  "rating": "correct",
  "clinician_note": "Dose is accurate",
  "timestamp": "2026-02-21T14:30:00Z"
}
```

```json
{
  "feedback_id": 2,
  "visit_id": 42,
  "feedback_type": "literature_relevance",
  "item_type": "paper",
  "item_value": "Metformin for Type 2 Diabetes: A Systematic Review",
  "rating": "relevant",
  "paper_url": "https://www.semanticscholar.org/paper/...",
  "timestamp": "2026-02-21T14:32:00Z"
}
```

**FeedbackAnalytics model (for dashboard):**
```json
{
  "total_feedback_count": 156,
  "extraction_accuracy_rate": 0.87,
  "literature_relevance_rate": 0.72,
  "accuracy_by_item_type": {
    "medication": 0.92,
    "diagnosis": 0.85,
    "test_ordered": 0.88,
    "follow_up": 0.79
  },
  "most_relevant_papers": [
    {"title": "...", "positive_votes": 5, "total_votes": 6}
  ],
  "most_useful_keywords": ["metformin", "diabetes management", "HbA1c targets"]
}
```

---

### 8. `core/pdf_generator.py` — PDF Export

```python
# Interface:
def generate_after_visit_summary(visit_data: dict, output_path: str) -> str
```

Use `fpdf2` to generate a clean, professional PDF containing:

**Page 1: Header**
- "MedSift AI — After Visit Summary"
- Visit date, visit type
- Disclaimer: "This summary was generated by AI from a recorded conversation. Please verify all information with your healthcare provider."

**Page 2+: Content sections**
- Visit Summary (plain language)
- Medications (table format: name, dose, frequency, instructions)
- Tests Ordered (table format: test, instructions, timeline)
- Follow-Up Plan (checklist style)
- Lifestyle Recommendations
- Red Flags / When to Seek Urgent Care (highlighted in bold or red)
- Questions & Answers from the visit

**Optional last page: SOAP Note** (if clinician export is requested)

---

### 9. `models/schemas.py` — Pydantic Models

Define ALL data models here. Every module imports from this file.

Key models to define:
- `TranscriptionResult`
- `RedactionResult`
- `Medication`, `TestOrdered`, `FollowUpItem`, `LifestyleRecommendation`, `RedFlagForPatient`, `QAItem`
- `PatientSummary` (contains all patient-facing fields)
- `SOAPNote` with `Subjective`, `Objective`, `Assessment`, `Plan` sub-models
- `ClinicianNote` (contains SOAP + problem list + action items)
- `RiskFactor`, `RedFlag`, `RiskAssessment`
- `ClinicalTrial`
- `LiteratureResult`
- `FeedbackItem`, `FeedbackAnalytics`, `BoostedKeyword`
- `VisitRecord` (the complete record stored in DB: all of the above combined)
- `AnalyticsSummary` (for dashboard aggregations)

---

### 10. `models/database.py` — SQLite Database

```python
# Interface:
def init_db() -> None                              # Create tables if not exist
def save_visit(visit: VisitRecord) -> int           # Returns visit_id
def get_visit(visit_id: int) -> VisitRecord
def get_all_visits() -> list[VisitRecord]
def search_visits(query: str) -> list[VisitRecord]  # Full-text search
def get_analytics() -> AnalyticsSummary
def delete_visit(visit_id: int) -> bool
def save_feedback(feedback: FeedbackItem) -> int    # Returns feedback_id
def get_feedback(visit_id: int) -> list[FeedbackItem]
def get_feedback_analytics() -> FeedbackAnalytics
def get_boosted_keywords() -> list[BoostedKeyword]
```

**Tables:**

`visits` table:
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- created_at (TIMESTAMP)
- visit_date (DATE)
- visit_type (TEXT) — e.g., "routine checkup", "follow-up", "specialist"
- tags (TEXT) — JSON array of tags
- audio_duration_seconds (REAL)
- raw_transcript (TEXT) — de-identified transcript
- patient_summary_json (TEXT) — JSON blob of PatientSummary
- clinician_note_json (TEXT) — JSON blob of ClinicianNote
- risk_assessment_json (TEXT) — JSON blob of RiskAssessment
- clinical_trials_json (TEXT) — JSON blob of trial results
- literature_results_json (TEXT) — JSON blob of Semantic Scholar results
- transcript_segments_json (TEXT) — JSON blob of timestamped segments

`feedback` table:
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- visit_id (INTEGER, FOREIGN KEY → visits.id)
- feedback_type (TEXT) — "extraction_accuracy" or "literature_relevance"
- item_type (TEXT) — "medication", "diagnosis", "test_ordered", "follow_up", "paper", "trial"
- item_value (TEXT) — the specific item being rated (e.g., "Metformin 500mg" or paper title)
- rating (TEXT) — "correct", "incorrect", "missing" for extraction; "relevant", "not_relevant" for literature
- paper_url (TEXT, NULLABLE) — URL if rating a paper/trial
- clinician_note (TEXT, NULLABLE) — optional free-text note from clinician
- created_at (TIMESTAMP)

`keyword_boost` table (derived/materialized from feedback):
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- keyword (TEXT)
- positive_count (INTEGER) — times this keyword led to positively-rated papers
- negative_count (INTEGER) — times this keyword led to negatively-rated papers
- boost_score (REAL) — positive_count / (positive_count + negative_count)
- last_updated (TIMESTAMP)

Create a **full-text search** index on raw_transcript and tags for keyword search.

---

### 11. `api/` — FastAPI REST API

Build a FastAPI app with these endpoints:

**`POST /api/transcribe`**
- Accepts audio file upload (multipart/form-data)
- Runs Whisper transcription
- Runs PHI redaction
- Returns: `{ transcript, redacted_transcript, redaction_log, segments, duration }`

**`POST /api/analyze`**
- Accepts: `{ transcript: str, visit_date: str, visit_type: str, tags: list[str] }`
- Runs patient extraction, clinician extraction, risk scoring
- Optionally runs clinical trials search and literature search
- Saves everything to SQLite
- Returns: `{ visit_id, patient_summary, clinician_note, risk_assessment, clinical_trials, literature }`

**`GET /api/visits`**
- Returns all visits (paginated)
- Query params: `?search=keyword&tag=diabetes&sort=date`

**`GET /api/visits/{visit_id}`**
- Returns full visit record

**`DELETE /api/visits/{visit_id}`**
- Deletes a visit

**`GET /api/export/{visit_id}/pdf`**
- Generates and returns PDF file

**`GET /api/trials/{visit_id}`**
- Returns clinical trials for a specific visit (can re-fetch if needed)

**`GET /api/literature/{visit_id}`**
- Returns Semantic Scholar papers for a specific visit
- Uses boosted keywords from feedback history to improve search quality
- Query param: `?refresh=true` to force a new search instead of cached results

**`POST /api/feedback`**
- Accepts: `{ visit_id: int, feedback_type: str, item_type: str, item_value: str, rating: str, paper_url?: str, clinician_note?: str }`
- Saves feedback to the `feedback` table
- If feedback_type is "literature_relevance", also updates the `keyword_boost` table
- Returns: `{ feedback_id, message: "Feedback recorded" }`

**`GET /api/feedback/{visit_id}`**
- Returns all feedback for a specific visit

**`GET /api/feedback/analytics`**
- Returns feedback analytics: extraction accuracy rate by item type, literature relevance rate, most useful keywords, trending papers

**`GET /api/analytics`**
- Returns aggregated analytics:
  - Total visits count
  - Risk level distribution (count of low/medium/high)
  - Most common conditions (top 10)
  - Most common medications (top 10)
  - Red flag frequency by category
  - Visits over time (by week/month)
  - Average risk score trend
  - Extraction accuracy rate (from feedback)
  - Literature relevance rate (from feedback)
  - Top boosted keywords

Enable CORS so the future frontend can connect.

---

### 12. `streamlit_demo/app.py` — Minimal Test Interface

Build a simple Streamlit app for testing and demo purposes. This is NOT the final frontend (that comes from Figma), but it lets us test the full pipeline.

**Pages/sections:**
1. **Upload & Process**: File uploader for audio → shows transcript → shows redacted version → shows care plan + SOAP note + risk score
2. **Visit History**: List of past visits with search
3. **Visit Detail**: Click a visit to see full details, with:
   - 👍/👎 buttons next to each recommended paper and trial
   - ✅/❌ buttons next to each extracted item (medication, diagnosis, test) to rate accuracy
   - Optional text field for clinician notes on each item
4. **Literature & Trials**: Display recommended papers (sorted by influential citations) and recruiting trials side by side
5. **Analytics Dashboard**: Charts showing:
   - Condition frequency, risk distribution, visit timeline
   - Extraction accuracy rate over time (from feedback)
   - Literature relevance rate (from feedback)
   - Top boosted keywords (keywords that consistently lead to useful papers)
   - Most highly rated papers across all visits
6. **PDF Export**: Button to download After Visit Summary PDF

Use `requests` to call the FastAPI backend (run both simultaneously).

---

### 13. `setup.sh` — One-Command Setup

```bash
#!/bin/bash
# MedSift AI - Setup Script

echo "Setting up MedSift AI..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy model for Presidio
python -m spacy download en_core_web_lg

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Please install from https://ollama.ai"
    echo "Then run: ollama pull llama3:8b"
    exit 1
fi

# Pull Llama 3 model
ollama pull llama3:8b

# Initialize database
python -c "from models.database import init_db; init_db()"

echo "Setup complete!"
echo "Start the API: uvicorn app.main:app --reload"
echo "Start the demo: streamlit run streamlit_demo/app.py"
```

---

### 14. `requirements.txt`

```
# Core
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
pydantic>=2.0.0

# Transcription
openai-whisper>=20231117
torch>=2.0.0

# PHI Redaction
presidio-analyzer>=2.2.0
presidio-anonymizer>=2.2.0
spacy>=3.7.0

# LLM
requests>=2.31.0

# Database
# (sqlite3 is built into Python)

# PDF
fpdf2>=2.7.0

# Demo UI
streamlit>=1.28.0

# Utilities
python-dotenv>=1.0.0
```

---

## Key Implementation Rules

1. **Evidence snippets are mandatory.** Every extracted item (medication, test, follow-up, red flag) must include an `evidence` field with a direct transcript quote. If the model can't provide evidence, mark the item as `"confidence": "low"`.

2. **JSON output from LLM must be validated.** Parse LLM responses with `json.loads()`, validate against Pydantic models, and retry up to 2 times on failure. Log malformed responses for debugging.

3. **PHI redaction runs BEFORE any storage or LLM analysis.** The raw transcript with PHI should only exist in memory temporarily. Only the redacted version gets stored or sent to the LLM.

4. **Risk scoring does NOT diagnose.** It highlights what was mentioned. Every risk assessment output must include a disclaimer.

5. **Graceful degradation.** If Ollama is not running, return a clear error. If ClinicalTrials.gov is unreachable, skip trials and proceed. If Whisper fails on a file, return a helpful error message. Never crash the whole app.

6. **Model caching.** Load the Whisper model once at startup, not per request. Same for the Presidio analyzer engine.

7. **All configuration in `config.py` and `.env`.** Ollama URL, model name, Whisper model size, database path — all configurable, not hardcoded.

8. **Feedback loop is lightweight but visible.** The feedback system doesn't need to be complex — a simple thumbs up/down that gets stored and a keyword boost table that influences future searches is enough. The goal is to demonstrate the *concept* of a learning loop, not build a full recommendation engine. Make sure the analytics dashboard shows feedback metrics prominently so judges can see the loop in action.

9. **Literature search uses boosted keywords.** When searching Semantic Scholar, check the `keyword_boost` table first. If certain keywords have a high boost_score (from positive feedback history), prepend them to the search query or weight them more heavily. This is the concrete proof that the system "learns."

10. **Dual research sources.** ClinicalTrials.gov and Semantic Scholar serve different purposes. Trials = active recruiting studies (useful for patients). Semantic Scholar = published peer-reviewed research (useful for clinicians). Always present both when available, clearly labeled.

---

## Build Order (Suggested)

Build and test in this order:

1. `models/schemas.py` — Define all Pydantic models first (including FeedbackItem, LiteratureResult, BoostedKeyword)
2. `models/database.py` — SQLite setup (all 3 tables: visits, feedback, keyword_boost)
3. `core/transcription.py` — Whisper pipeline
4. `core/phi_redaction.py` — Presidio pipeline
5. `core/extraction.py` — LLM extraction (most complex, spend time on prompts)
6. `core/risk_scoring.py` — Risk scoring
7. `core/clinical_trials.py` — ClinicalTrials.gov API
8. `core/literature_search.py` — Semantic Scholar API (include keyword boost logic)
9. `core/feedback.py` — Feedback loop logic
10. `core/pdf_generator.py` — PDF export
11. `api/routes/*` — FastAPI endpoints (including /feedback and /literature)
12. `app/main.py` — Wire everything together
13. `streamlit_demo/app.py` — Test UI with feedback buttons
14. `tests/` — Write tests
15. `setup.sh` + `README.md` — Polish

---

## README.md Content

Generate a professional README with:
- Project name and tagline: **MedSift AI — Sift through medical conversations. Surface what matters.**
- Problem statement (2-3 sentences)
- Architecture diagram (use a text/ASCII diagram)
- Features list
- Tech stack table
- Setup instructions (prerequisites: Python 3.10+, Ollama, ffmpeg)
- API documentation (list all endpoints)
- Screenshots placeholder section
- Hacklytics 2026 badge/mention
- License: MIT
- Disclaimer: "This tool is for informational purposes only. It does not provide medical diagnoses or replace professional medical advice."

---

## Final Notes

- This is a hackathon project for **Hacklytics 2026** at Georgia Tech
- The frontend will be designed in Figma and built separately — do not build any Next.js/React frontend
- The Streamlit demo is ONLY for testing the pipeline, not the final UI
- Prioritize getting the core pipeline working end-to-end over polish
- Use descriptive variable names and add docstrings to every function
- Keep the code clean and well-organized — judges will read it
