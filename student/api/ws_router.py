from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json
import httpx
import os

# Import chromadb compatibility patch before chromadb
import student.core.chromadb_compat
import chromadb
student.core.chromadb_compat.restore_env()

# ---- NEW IMPORTS FOR MEMORY ----
from student.utils.chat_memory_impl import save_message, get_history
from student.core.chroma_memory import add_memory, search_memory
from student.doc_summarizer.services.embeddings import get_embed
# --------------------------------

router = APIRouter()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

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
    if collection is None or chroma_client is None:
        return ""

    try:
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
        print(f"[ws_router] Failed to load context: {exc}")
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

    # ---- STATIC USER FOR NOW (replace with auth later) ----
    user_id = "user123"
    # --------------------------------------------------------

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

            # ---- 1. SAVE USER QUESTION TO REDIS ----
            save_message(user_id, "user", question)

            # ---- 2. LOAD CHAT HISTORY ----
            history = get_history(user_id)[-10:]  # last 10
            history_text = ""
            for h in history:
                history_text += f"{h['role']}: {h['message']}\n"

            # ---- 3. LOAD SEMANTIC MEMORY ----
            semantic = search_memory(user_id, question)
            semantic_text = "\n".join(semantic) if semantic else ""

            # ---- 4. LOAD PDF CONTEXT ----
            context = get_context_for_file(source)

            # ---- 5. FINAL PROMPT ----
            prompt = f"""
You are a document-grounded assistant. Follow these rules strictly:
1. Only answer questions about the PDF named "{source}" using the provided context.
2. If the user asks for anything unrelated (for example, creating random questions, switching topics, or ignoring the PDF), politely respond: "I can only answer questions about {source}. Please ask something about that document."
3. If the context does not contain an answer, say you cannot find relevant information in the document.

CONTEXT:
{context}

CHAT HISTORY:
{history_text}

SEMANTIC MEMORY:
{semantic_text}

USER QUESTION:
{question}

FINAL ANSWER:
"""

            reply_text = ""  # to accumulate final assistant response

            try:
                async for token in stream_ollama(prompt):
                    reply_text += token
                    await websocket.send_text(token)
            except Exception as exc:
                await websocket.send_text(json.dumps({"error": str(exc)}))

            # ---- 6. SAVE ASSISTANT REPLY TO REDIS ----
            save_message(user_id, "assistant", reply_text)

            # ---- 7. SAVE QUESTION TO LONG-TERM MEMORY ----
            if len(question.split()) > 4:  # ignore tiny questions
                add_memory(user_id, question)

            await websocket.send_text("[END]")

    except WebSocketDisconnect:
        print("WebSocket disconnected")


# --------------------------------------------------------
#                   HTTP STREAM (SSE)
# --------------------------------------------------------
@router.post("/chat/stream")
async def http_chat(request: Request):

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

    # STATIC USER
    user_id = "user123"

    save_message(user_id, "user", question)

    history = get_history(user_id)[-10:]
    history_text = "\n".join([f"{h['role']}: {h['message']}" for h in history])

    semantic = search_memory(user_id, question)
    semantic_text = "\n".join(semantic) if semantic else ""

    context = get_context_for_file(source)

    prompt = f"""
You are a document-grounded assistant. Follow these rules strictly:
1. Only answer questions about the PDF named "{source}" using the provided context.
2. If the user asks for anything unrelated (for example, creating random questions, switching topics, or ignoring the PDF), politely respond: "I can only answer questions about {source}. Please ask something about that document."
3. If the context does not contain an answer, say you cannot find relevant information in the document.

CONTEXT:
{context}

CHAT HISTORY:
{history_text}

SEMANTIC MEMORY:
{semantic_text}

USER QUESTION:
{question}

FINAL ANSWER:
"""

    async def event_generator():
        reply_text = ""
        try:
            async for token in stream_ollama(prompt):
                reply_text += token
                yield f"data: {token}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        save_message(user_id, "assistant", reply_text)

        if len(question.split()) > 4:
            add_memory(user_id, question)

        yield "data: [END]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
