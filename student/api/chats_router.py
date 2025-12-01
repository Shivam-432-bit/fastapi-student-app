# student/api/chats_router.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
from student.utils.chat_memory_impl import (
    create_chat, list_chats, get_history, delete_chat, rename_chat
)

router = APIRouter()


# For now use static user (replace with auth later)
def _get_user_id():
    return "user123"


@router.get("/api/chats")
async def api_list_chats():
    user_id = _get_user_id()
    chats = list_chats(user_id)
    return {"chats": chats}


@router.post("/api/chats/new")
async def api_create_chat(payload: Dict):
    user_id = _get_user_id()
    title = payload.get("title") if payload else None
    cid = create_chat(user_id, title)
    return {"chat_id": cid, "title": title or f"Chat {cid[:6]}"}


@router.get("/api/chats/{chat_id}")
async def api_get_chat(chat_id: str):
    user_id = _get_user_id()
    history = get_history(user_id, chat_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    title = None  # optional: get title if you need
    return {"chat_id": chat_id, "title": title, "history": history}


@router.delete("/api/chats/{chat_id}")
async def api_delete_chat(chat_id: str):
    user_id = _get_user_id()
    delete_chat(user_id, chat_id)
    return JSONResponse({"status": "ok"})


@router.post("/api/chats/{chat_id}/rename")
async def api_rename_chat(chat_id: str, payload: Dict):
    user_id = _get_user_id()
    title = (payload or {}).get("title")
    if not title:
        raise HTTPException(status_code=400, detail="missing title")
    rename_chat(user_id, chat_id, title)
    return {"status": "ok", "chat_id": chat_id, "title": title}
