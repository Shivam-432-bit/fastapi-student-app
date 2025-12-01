import os
import uuid
import chromadb

from student.doc_summarizer.services.embeddings import get_embed

CHROMA_DB_DIR = "student/chroma_store"
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

try:
    chroma_client = chromadb.Client(chromadb.config.Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=CHROMA_DB_DIR
    ))

    collection = chroma_client.get_or_create_collection(
        name="chat_memory",
        metadata={"hnsw:space": "cosine"}
    )

    if not hasattr(collection, "_client"):
        collection._client = chroma_client
except Exception as exc:
    chroma_client = None
    collection = None


def add_memory(user_id: str, text: str):
    """Add a short memory (text) for a user into the `chat_memory` collection."""
    if collection is None:
        raise RuntimeError("Chroma client not initialized")

    try:
        embedder = get_embed()
        embeddings = embedder.embed_documents([text])
    except Exception as exc:
        print(f"[chroma_memory] embedding error: {exc}")
        return

    doc_id = f"{user_id}_{uuid.uuid4()}"

    chroma_client._add(
        [doc_id],
        collection.id,
        embeddings,
        [{"user_id": user_id}],
        [text]
    )


def search_memory(user_id: str, query: str):
    """Search the `chat_memory` collection for entries relevant to `query`.

    Returns a list of matching document texts (may be empty).
    """
    if collection is None:
        return []

    try:
        embedder = get_embed()
        query_embed = embedder.embed_query(query)

        try:
            max_results = chroma_client._count(collection.id)
        except Exception:
            max_results = 3

        if max_results == 0:
            return []

        n_results = min(3, max_results)

        results = chroma_client._query(
            collection.id,
            query_embeddings=[query_embed],
            n_results=n_results,
            where={"user_id": user_id}
        )

        docs = results.get("documents", [[]])[0]
        return docs or []

    except Exception as exc:
        print(f"[chroma_memory] search error: {exc}")
        return []
