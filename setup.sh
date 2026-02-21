#!/usr/bin/env bash
set -euo pipefail

# ================================================
#  MedSift AI — One-Command Setup
#  Hacklytics 2026 @ Georgia Tech
# ================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "================================================"
echo "  MedSift AI — One-Command Setup"
echo "  Hacklytics 2026 @ Georgia Tech"
echo "================================================"
echo ""

# -- Step 1: Check Python --
info "Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    error "Python not found. Install Python 3.10+ first."
    exit 1
fi
PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Found Python $PYTHON_VERSION"

# -- Step 2: Check ffmpeg --
info "Checking ffmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    warn "ffmpeg not found (required by Whisper)."
    if [[ "${OSTYPE:-}" == "darwin"* ]]; then
        info "Installing via Homebrew..."
        brew install ffmpeg
    else
        warn "Please install ffmpeg manually: https://ffmpeg.org/download.html"
    fi
else
    info "ffmpeg is available"
fi

# -- Step 3: Check Ollama --
info "Checking Ollama..."
if ! command -v ollama &>/dev/null; then
    warn "Ollama not found."
    if [[ "${OSTYPE:-}" == "darwin"* ]]; then
        info "Installing via Homebrew..."
        brew install ollama
    else
        warn "Install Ollama from https://ollama.ai then re-run this script."
        warn "Continuing without Ollama..."
    fi
else
    info "Ollama is available"
fi

# -- Step 4: Create virtual environment --
if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    $PYTHON -m venv venv
fi
info "Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# -- Step 5: Install Python dependencies --
info "Installing Python packages..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# -- Step 6: Download spaCy model --
info "Downloading spaCy language model (en_core_web_lg)..."
python -m spacy download en_core_web_lg -q

# -- Step 7: Pull Ollama model --
if command -v ollama &>/dev/null; then
    info "Pulling Ollama model (llama3.1:latest)..."
    ollama pull llama3.1:latest || warn "Could not pull model. Make sure 'ollama serve' is running."
fi

# -- Step 8: Create .env if missing --
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        info "Creating .env from .env.example..."
        cp .env.example .env
    fi
fi

# -- Step 9: Create data directory --
mkdir -p data

# -- Step 10: Initialize database --
info "Initializing database..."
python -c "from models.database import init_db; init_db()" || warn "DB init failed (non-fatal)"

# -- Step 11: Run tests --
info "Running tests to verify installation..."
python -m pytest tests/ -v --tb=short || warn "Some tests did not pass (see output above)"

# -- Done --
echo ""
echo "================================================"
echo "  Setup complete!"
echo ""
echo "  Start the API:"
echo "    source venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Start the demo UI (separate terminal):"
echo "    source venv/bin/activate"
echo "    streamlit run streamlit_demo/app.py"
echo ""
echo "  Run tests:"
echo "    pytest tests/ -v"
echo "================================================"
echo ""
