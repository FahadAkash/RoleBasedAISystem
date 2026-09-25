"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import admin_router, auth_router, chat_router
from backend.seed_data import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Create app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Role-Based AI Chatbot",
    description=(
        "Agentic chatbot with role-based access control powered by "
        "Gemini (chat) and TypeSafe Jev (access decisions)."
    ),
    version="1.0.0",
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(admin_router.router)


# ─── Startup ─────────────────────────────────────────────────────────────────


@app.on_event("startup")
def on_startup():
    """Initialize DB and seed demo data on first run."""
    logger.info("Starting Role-Based AI Chatbot...")
    try:
        seed_all()
        logger.info("Database initialized and seeded.")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Still init the DB even if seeding fails
        init_db()


@app.get("/")
def root():
    return {
        "name": "Role-Based AI Chatbot",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
