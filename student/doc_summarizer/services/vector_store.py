"""Chroma vector store helpers."""
from __future__ import annotations

import chromadb

import student.core.chromadb_compat
from student.doc_summarizer.config import CHROMA_DB_DIR

student.core.chromadb_compat.restore_env()

_chroma_client = None
_documents_collection = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client(
            chromadb.config.Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=CHROMA_DB_DIR,
            )
        )
    return _chroma_client


def get_documents_collection():
    global _documents_collection
    if _documents_collection is None:
        client = get_chroma_client()
        _documents_collection = client.get_or_create_collection(
            name="documents", metadata={"hnsw:space": "cosine"}
        )
        if not hasattr(_documents_collection, "_client"):
            _documents_collection._client = client
    return _documents_collection
