"""App configuration and constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# Ollama LLM settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

# Whisper transcription
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda" if __import__("torch").cuda.is_available() else "cpu")

# Speaker diarization (pyannote.audio)
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/medsift.db")

# External APIs
CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"

# LLM settings
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 4096
LLM_TIMEOUT_SECONDS = 300
LLM_MAX_RETRIES = 2
