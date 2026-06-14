"""
Configuration module for the Intelligent Maintenance Wizard.
Loads environment variables and provides centralized settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
KNOWLEDGE_DIR = BASE_DIR / "sample_knowledge"
CHROMA_DIR = BASE_DIR / "chroma_db"
DB_PATH = BASE_DIR / "maintenance_wizard.db"

# ─── LLM Configuration (OpenRouter) ─────────────────────────────────────────
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "meta/llama-3.1-70b-instruct")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Legacy: also check GOOGLE_API_KEY for backwards compatibility
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Determine which API key is available
API_KEY = NVIDIA_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY or GOOGLE_API_KEY
API_PROVIDER = "nvidia" if NVIDIA_API_KEY else ("groq" if GROQ_API_KEY else ("openrouter" if OPENROUTER_API_KEY else ("google" if GOOGLE_API_KEY else "none")))

# ─── Embedding Configuration ────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ─── Server Configuration ───────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# ─── Sensor Simulator Configuration ─────────────────────────────────────────
SENSOR_INTERVAL_SECONDS = int(os.getenv("SENSOR_INTERVAL", "5"))
ANOMALY_PROBABILITY = float(os.getenv("ANOMALY_PROBABILITY", "0.05"))

# ─── RAG Configuration ──────────────────────────────────────────────────────
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.3"))

# ─── Runtime Globals ─────────────────────────────────────────────────────────
LOOP = None  # Set to asyncio event loop at startup

