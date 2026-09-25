"""Configuration settings for the Role-Based AI System."""

import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma_db"
SQLITE_PATH = DATA_DIR / "app2.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DOCUMENTS_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite:///{SQLITE_PATH}"

# ─── JWT Auth ────────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "role-based-ai-system-super-secret-key-change-in-production-2024",
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24  # 24 hours

# ─── Google Gemini ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# ─── TypeSafe / Jev ──────────────────────────────────────────────────────────
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "")
JEV_MODEL = "jev-latest"

# ─── RAG Settings ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 5

# ─── Roles ───────────────────────────────────────────────────────────────────
ROLES = ["admin", "staff", "user"]

# ─── FastAPI ─────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ─── Streamlit ───────────────────────────────────────────────────────────────
STREAMLIT_PORT = 8501
BACKEND_URL = f"http://localhost:{API_PORT}"
