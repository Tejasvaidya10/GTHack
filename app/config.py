"""App configuration and constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# Ollama LLM settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:latest")

# Whisper transcription
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
def _detect_device() -> str:
    """Detect best available device: CUDA > MPS (Apple Silicon) > CPU."""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"

WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", _detect_device())

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/medsift.db")

# External APIs
CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"

# LLM settings
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 8192
LLM_TIMEOUT_SECONDS = 600
LLM_MAX_RETRIES = 2
