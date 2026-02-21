# MedSift AI

**Sift through medical conversations. Surface what matters.**

> Built at [Hacklytics 2026](https://hacklytics.io) @ Georgia Tech

MedSift AI is a fully local, privacy-first healthcare conversation intelligence system. Upload a patient-doctor audio recording and get: an AI-extracted care plan, a structured SOAP note, automated risk scoring with red flag detection, clinical trial matching, and relevant literature — all with PHI automatically redacted before any processing.

**Everything runs locally. No paid APIs. No cloud services. Total cost: $0.**

---

## Architecture

```
  Audio File (.mp3 / .wav / .m4a)
       |
       v
  +---------------------+
  |  OpenAI Whisper      |  Speech-to-Text (local)
  +---------------------+
       |
       v
  +---------------------+
  |  Microsoft Presidio  |  PHI Redaction (local)
  |  + spaCy NER         |  Custom MRN & Insurance ID recognizers
  +---------------------+
       |
       v
  +---------------------+      +-------------------------+
  |  Ollama (LLaMA 3.1) | ---> | Patient Care Plan       |
  |  Local LLM           | ---> | Clinician SOAP Note     |
  +---------------------+      +-------------------------+
       |                               |
       v                               v
  +---------------------+      +-------------------------+
  |  Risk Scoring        |      | ClinicalTrials.gov API  |
  |  (Rule-Based, 0-100) |      | Semantic Scholar API    |
  +---------------------+      +-------------------------+
       |                               |
       +---------------+---------------+
                       |
                       v
  +------------------------------------------+
  |          FastAPI REST Backend             |
  |          (11 endpoints)                  |
  +------------------------------------------+
       |                       |
       v                       v
  +----------------+    +------------------+
  |  SQLite + FTS5 |    |  Streamlit Demo  |
  +----------------+    +------------------+
```

---

## Features

- **Audio Transcription** — OpenAI Whisper running locally, no API keys
- **PHI Redaction** — Microsoft Presidio with custom MRN and Insurance ID recognizers
- **AI Extraction** — LLaMA 3.1 via Ollama extracts patient care plan + clinician SOAP note
- **Risk Scoring** — Deterministic rule-based scoring (0-100) with 5 red flag categories
- **Clinical Trials** — ClinicalTrials.gov API v2, filtered to recruiting studies
- **Literature Search** — Semantic Scholar with feedback-boosted keyword ranking
- **Clinician Feedback Loop** — Rate extractions and papers; system learns which keywords produce useful results
- **PDF Export** — Generate After Visit Summary PDFs with fpdf2
- **Analytics Dashboard** — Risk distribution, common conditions, feedback metrics, boosted keywords

---

## Quick Start

```bash
# Clone the repository
git clone <repo-url> && cd GTHack

# One-command setup (installs deps, downloads models, initializes DB)
chmod +x setup.sh && ./setup.sh

# Start the API server
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Start the demo UI (in a separate terminal)
source venv/bin/activate
streamlit run streamlit_demo/app.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | `brew install python@3.12` or [python.org](https://python.org) |
| Ollama | Latest | [ollama.ai](https://ollama.ai) |
| ffmpeg | Latest | `brew install ffmpeg` or [ffmpeg.org](https://ffmpeg.org) |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transcribe` | Upload audio, transcribe with Whisper, redact PHI |
| `POST` | `/api/analyze` | Run full extraction pipeline (care plan + SOAP + risk + research) |
| `GET` | `/api/visits` | List visits with search, tag filter, pagination |
| `GET` | `/api/visits/{id}` | Get full visit detail |
| `DELETE` | `/api/visits/{id}` | Delete a visit |
| `GET` | `/api/export/{id}/pdf` | Download After Visit Summary PDF |
| `GET` | `/api/trials/{id}` | Get recruiting clinical trials for a visit |
| `GET` | `/api/literature/{id}` | Get literature with feedback-boosted keywords |
| `POST` | `/api/feedback` | Submit clinician feedback on extractions or papers |
| `GET` | `/api/feedback/{id}` | Get feedback for a specific visit |
| `GET` | `/api/feedback/analytics` | Aggregated feedback metrics |
| `GET` | `/api/analytics` | Dashboard analytics (risk distribution, conditions, etc.) |
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |

---

## Project Structure

```
GTHack/
├── app/
│   ├── config.py                 # Configuration constants
│   └── main.py                   # FastAPI application entry point
├── api/
│   ├── dependencies.py           # Shared API dependencies
│   └── routes/                   # 8 route modules
│       ├── transcribe.py         # Audio upload + transcription + PHI redaction
│       ├── analyze.py            # Full analysis pipeline
│       ├── visits.py             # Visit CRUD
│       ├── export.py             # PDF export
│       ├── trials.py             # Clinical trials lookup
│       ├── literature.py         # Literature search with keyword boost
│       ├── feedback.py           # Clinician feedback
│       └── analytics.py          # Dashboard analytics
├── core/
│   ├── transcription.py          # Whisper transcription with model caching
│   ├── phi_redaction.py          # Presidio PHI detection + custom recognizers
│   ├── extraction.py             # Ollama LLM extraction with retry logic
│   ├── risk_scoring.py           # Rule-based risk scoring + red flag detection
│   ├── clinical_trials.py        # ClinicalTrials.gov API v2
│   ├── literature_search.py      # Semantic Scholar API with keyword boost
│   ├── feedback.py               # Feedback loop + keyword extraction
│   └── pdf_generator.py          # After Visit Summary PDF generation
├── models/
│   ├── schemas.py                # 20+ Pydantic data models
│   └── database.py               # SQLite CRUD + FTS5 full-text search
├── prompts/
│   ├── extraction_patient.txt    # Patient-facing extraction prompt
│   └── extraction_clinician.txt  # Clinician SOAP note prompt
├── streamlit_demo/
│   └── app.py                    # Streamlit demo UI (3 pages)
├── tests/
│   ├── test_phi_redaction.py     # 8 tests (offline, no mocking)
│   ├── test_risk_scoring.py      # 10 tests (offline, no mocking)
│   ├── test_extraction.py        # 8 tests (mocked Ollama)
│   └── test_transcription.py     # 5 tests (mocked Whisper)
├── requirements.txt
├── setup.sh                      # One-command setup script
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Transcription | OpenAI Whisper (local) |
| PHI Redaction | Microsoft Presidio + spaCy `en_core_web_lg` |
| LLM Extraction | Ollama + LLaMA 3.1 (local) |
| Backend | FastAPI + Uvicorn |
| Database | SQLite with FTS5 virtual tables |
| PDF Export | fpdf2 |
| Demo UI | Streamlit |
| Testing | pytest + httpx |

---

## Running Tests

```bash
# All tests (31 total)
pytest tests/ -v

# Individual modules
pytest tests/test_phi_redaction.py -v    # Presidio runs locally, no mocking
pytest tests/test_risk_scoring.py -v     # Pure logic, no external deps
pytest tests/test_extraction.py -v       # Mocked Ollama calls
pytest tests/test_transcription.py -v    # Mocked Whisper model
```

---

## Privacy & Security

- **All AI processing runs locally** — no patient data leaves your machine
- **PHI is redacted before** any LLM processing or database storage
- **No cloud APIs** for transcription or extraction
- Only ClinicalTrials.gov and Semantic Scholar are called externally, with de-identified data only

---

## Medical Disclaimer

MedSift AI is a research prototype built at a hackathon. It does **not** provide medical diagnoses, treatment recommendations, or clinical decision support. All AI-generated content must be verified by a qualified healthcare professional. This tool is intended to assist with documentation, not replace clinical judgment.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Built with care at **Hacklytics 2026** — Georgia Tech's premier health + data science hackathon.
