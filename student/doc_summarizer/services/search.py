"""Semantic search helper functions."""
from __future__ import annotations

from typing import List, Dict

from student.doc_summarizer.services.embeddings import get_embed, rerank
from student.doc_summarizer.services.vector_store import (
    get_chroma_client,
    get_documents_collection,
)


def perform_search(doc_id: str, query: str) -> List[Dict[str, object]]:
    """Retrieve and rerank chunks for a query within a document."""
    embedder = get_embed()
    query_embed = embedder.embed_query(query)

    chroma_client = get_chroma_client()
    collection = get_documents_collection()

    where_filter = {"sql_doc_id": int(doc_id)} if doc_id.isdigit() else {"source": doc_id}

    try:
        max_results = chroma_client._count(collection.id)
    except Exception:
        max_results = 10

    if max_results == 0:
        return []

    n_results = min(10, max_results)
    results = chroma_client._query(
        collection.id,
        query_embeddings=[query_embed],
        n_results=n_results,
        where=where_filter,
    )

    retrieved_chunks = results.get("documents", [[]])[0]
    if not retrieved_chunks:
        return []

    return rerank(query, retrieved_chunks)
