from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json
import httpx
import os

# Import chromadb compatibility patch before chromadb
import student.core.chromadb_compat
import chromadb
# Restore app env vars after chromadb import (same pattern as other modules)
student.core.chromadb_compat.restore_env()

router = APIRouter()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"

# --------------------------------------------------------
#               VECTOR DB INIT (for context queries)
# --------------------------------------------------------
CHROMA_DB_DIR = "student/chroma_store"
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

try:
    chroma_client = chromadb.Client(chromadb.config.Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=CHROMA_DB_DIR
    ))

    collection = chroma_client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"}
    )

    if not hasattr(collection, "_client"):
        collection._client = chroma_client
except Exception as _exc:
    chroma_client = None
    collection = None


# --------------------------------------------------------
#         HELPER: Get context for the selected file
# --------------------------------------------------------
def get_context_for_file(filename: str) -> str:
    """
    Fetch context from your vector DB based on metadata 'source'.
    """
    # If Chroma isn't available, return empty context so the LLM still runs
    if collection is None or chroma_client is None:
        return ""

    # Import embedding helper lazily to avoid circular imports at module import time
    try:
        from student.doc_summarizer.endpoint import get_embed

        # Create a query embedding for the filename so we can retrieve relevant
        # chunks for that document. This mirrors the logic used in the doc
        # summarizer module.
        query_embed = get_embed().embed_query(filename)

        try:
            max_results = chroma_client._count(collection.id)
        except Exception:
            max_results = 5

        if max_results == 0:
            return ""

        n_results = min(5, max_results)

        results = chroma_client._query(
            collection.id,
            query_embeddings=[query_embed],
            n_results=n_results,
            where={"source": filename}
        )

        docs = results.get("documents", [[]])[0]
        return "\n\n".join(docs)

    except Exception as exc:
        # On failure, don't raise — return an empty context and log the error.
        print(f"[ws_router] Failed to load context for {filename}: {exc}")
        return ""


# --------------------------------------------------------
#                    STREAM OLLAMA
# --------------------------------------------------------
async def stream_ollama(prompt: str):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                yield json.dumps({"error": f"Upstream error: {exc.response.status_code}"})
                return

            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "response" in data:
                    yield data["response"]

                if data.get("done"):
                    break


# --------------------------------------------------------
#                WEBSOCKET ENDPOINT
# --------------------------------------------------------
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            question = data.get("question")
            source = data.get("source")

            if not question:
                await websocket.send_text(json.dumps({"error": "missing question"}))
                continue
            if not source:
                await websocket.send_text(json.dumps({"error": "missing source"}))
                continue

            # Load context based on filename
            context = get_context_for_file(source)

            prompt = f"""
You are a helpful assistant. Answer only using this context:

{context}

User question:
{question}

Answer:
"""

            try:
                async for token in stream_ollama(prompt):
                    await websocket.send_text(token)
            except Exception as exc:
                await websocket.send_text(json.dumps({"error": str(exc)}))

            await websocket.send_text("[END]")

    except WebSocketDisconnect:
        print("WebSocket disconnected")


# --------------------------------------------------------
#                   HTTP STREAM (SSE)
# --------------------------------------------------------
@router.post("/chat/stream")
async def http_chat(request: Request):
    """Streams tokens using Server-Sent Events (SSE)."""
    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    question = body.get("question")
    source = body.get("source")

    if not question:
        return JSONResponse({"error": "missing question"}, status_code=400)
    if not source:
        return JSONResponse({"error": "missing source"}, status_code=400)

    # Load context for selected PDF
    context = get_context_for_file(source)

    prompt = f"""
You are a helpful assistant. Answer only using this context:

{context}

User question:
{question}

Answer:
"""

    async def event_generator():
        try:
            async for token in stream_ollama(prompt):
                yield f"data: {token}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        yield "data: [END]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
