"""Shared configuration values for the doc_summarizer package."""
from __future__ import annotations

import os

CHROMA_DB_DIR = "student/chroma_store"
UPLOAD_DIR = "uploads"

ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
]

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
BATCH_EMBED_SIZE = 32
TOP_K_VECTOR = 20
TOP_K_RETURN = 5


def ensure_directories() -> None:
    """Ensure project data directories exist."""
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


# Create directories on import by default.
ensure_directories()
