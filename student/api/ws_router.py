from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json
import httpx
import os

# Chroma compatibility
import student.core.chromadb_compat
import chromadb
student.core.chromadb_compat.restore_env()

# Memory system
from student.utils.chat_memory_impl import save_message, get_history
from student.core.chroma_memory import add_memory, search_memory
from student.doc_summarizer.services.embeddings import get_embed

router = APIRouter()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

# --------------------------------------------------------
#   VECTOR DB INIT
# --------------------------------------------------------
CHROMA_DB_DIR = "student/chroma_store"
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

try:
    chroma_client = chromadb.Client(
        chromadb.config.Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=CHROMA_DB_DIR
        )
    )

    collection = chroma_client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"}
    )

    if not hasattr(collection, "_client"):
        collection._client = chroma_client

except Exception:
    chroma_client = None
    collection = None


# --------------------------------------------------------
#   LOAD CONTEXT FOR A GIVEN PDF FILE
# --------------------------------------------------------
def get_context_for_file(filename: str) -> str:
    if not collection or not chroma_client:
        return ""

    try:
        embedding = get_embed().embed_query(filename)

        try:
            max_results = chroma_client._count(collection.id)
        except Exception:
            max_results = 5

        if max_results == 0:
            return ""

        n = min(5, max_results)

        results = chroma_client._query(
            collection.id,
            query_embeddings=[embedding],
            n_results=n,
            where={"source": filename}
        )

        docs = results.get("documents", [[]])[0]
        return "\n\n".join(docs)

    except Exception as exc:
        print("[ws_router] Context load error:", exc)
        return ""


# --------------------------------------------------------
#   STREAM OLLAMA (Server → Client Tokens)
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
                yield json.dumps({"error": f"Ollama error: {exc.response.status_code}"})
                return

            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except ValueError:
                    continue

                if "response" in data:
                    yield data["response"]

                if data.get("done"):
                    break


# --------------------------------------------------------
#   NEW IMPROVED PROMPT
# --------------------------------------------------------
def build_prompt(question, source, context, history_text, semantic_text):

    return f"""
You are a helpful PDF assistant for the document "{source}".

Your behavior rules:
1. Use the provided PDF context whenever it contains relevant information.
2. You ARE allowed to summarize the PDF, describe what the PDF contains, explain concepts that appear in the PDF, or answer broad questions like “What is in this PDF?”.
3. If the PDF context is partial, you may infer the answer from the document's overall topic.
4. Only refuse questions that are *completely* unrelated to the PDF (e.g., “write a poem”, “tell a joke”, “give dating advice”).
5. If information is truly not found anywhere in the PDF and cannot be inferred, say: “I could not find that information in the document.”

CONTEXT EXTRACTS:
{context}

CHAT HISTORY (last 10 turns):
{history_text}

RELEVANT MEMORY:
{semantic_text}

USER QUESTION:
{question}

Final Answer:
"""


# --------------------------------------------------------
#                WEBSOCKET CHAT
# --------------------------------------------------------
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    user_id = "user123"

    try:
        while True:

            msg = await websocket.receive_text()
            data = json.loads(msg)

            chat_id = data.get("chat_id")
            question = data.get("question")
            source = data.get("source")

            if not chat_id:
                await websocket.send_text(json.dumps({"error": "missing chat_id"}))
                continue

            if not question:
                await websocket.send_text(json.dumps({"error": "missing question"}))
                continue

            if not source:
                await websocket.send_text(json.dumps({"error": "missing source"}))
                continue

            # Save user message
            save_message(user_id, chat_id, "user", question)

            # Load last messages
            history = get_history(user_id, chat_id)[-10:]
            history_text = "\n".join(f"{h['role']}: {h['message']}" for h in history)

            # Semantic memory search
            semantic = search_memory(user_id, question)
            semantic_text = "\n".join(semantic) if semantic else ""

            # PDF Context
            context = get_context_for_file(source)

            # Build prompt
            prompt = build_prompt(question, source, context, history_text, semantic_text)

            reply_text = ""

            # Stream to client
            try:
                async for token in stream_ollama(prompt):
                    reply_text += token
                    await websocket.send_text(token)
            except Exception as exc:
                await websocket.send_text(json.dumps({"error": str(exc)}))

            save_message(user_id, chat_id, "assistant", reply_text)

            if len(question.split()) > 4:
                add_memory(user_id, question)

            await websocket.send_text("[END]")

    except WebSocketDisconnect:
        print("WebSocket disconnected")


# --------------------------------------------------------
#                 SSE / HTTP STREAM
# --------------------------------------------------------
@router.post("/chat/stream")
async def http_chat(request: Request):

    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    chat_id = body.get("chat_id")
    question = body.get("question")
    source = body.get("source")

    if not chat_id:
        return JSONResponse({"error": "missing chat_id"}, status_code=400)

    if not question:
        return JSONResponse({"error": "missing question"}, status_code=400)

    if not source:
        return JSONResponse({"error": "missing source"}, status_code=400)

    user_id = "user123"

    save_message(user_id, chat_id, "user", question)

    history = get_history(user_id, chat_id)[-10:]
    history_text = "\n".join(f"{h['role']}: {h['message']}" for h in history)

    semantic = search_memory(user_id, question)
    semantic_text = "\n".join(semantic) if semantic else ""

    context = get_context_for_file(source)

    prompt = build_prompt(question, source, context, history_text, semantic_text)

    async def event_generator():

        reply_text = ""

        try:
            async for token in stream_ollama(prompt):
                reply_text += token
                yield f"data: {token}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        save_message(user_id, chat_id, "assistant", reply_text)

        if len(question.split()) > 4:
            add_memory(user_id, question)

        yield "data: [END]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
      