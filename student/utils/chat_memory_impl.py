# student/utils/chat_memory_impl.py

import os
import json
import time
import redis
from typing import List, Dict
from uuid import uuid4


# ------------------------------------------------------------
# Redis Configuration
# ------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Max messages to keep in each chat
MAX_HISTORY = int(os.getenv("CHAT_MAX_HISTORY", 200))

# Expire chats after 30 days of inactivity
HISTORY_TTL_SECONDS = int(os.getenv("CHAT_HISTORY_TTL", 60 * 60 * 24 * 30))

# Redis client
_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)
_r = redis.Redis(connection_pool=_pool)


# ------------------------------------------------------------
# Redis Key Helpers
# ------------------------------------------------------------
def _chat_key(user_id: str, chat_id: str) -> str:
    """Redis key storing messages for a specific chat."""
    return f"chat:{user_id}:{chat_id}"


def _chat_list_key(user_id: str) -> str:
    """Redis key storing list of chat_ids for this user."""
    return f"chat_list:{user_id}"


def _chat_title_key(user_id: str, chat_id: str) -> str:
    """Redis key storing a readable title for the chat."""
    return f"chat_title:{user_id}:{chat_id}"


# ------------------------------------------------------------
# Chat Creation + Listing
# ------------------------------------------------------------
def create_chat(user_id: str, title: str | None = None) -> str:
    """Create a new chat for a user and return chat_id."""
    chat_id = uuid4().hex
    title = title or f"Chat {chat_id[:6]}"

    try:
        # Add chat to user's chat list (most recent = left)
        _r.lpush(_chat_list_key(user_id), chat_id)

        # Save chat title
        _r.set(_chat_title_key(user_id, chat_id), title)

        # TTL for chat list + title
        if HISTORY_TTL_SECONDS > 0:
            _r.expire(_chat_list_key(user_id), HISTORY_TTL_SECONDS)
            _r.expire(_chat_title_key(user_id, chat_id), HISTORY_TTL_SECONDS)

    except Exception:
        pass  # fail silently — safe

    return chat_id


def list_chats(user_id: str, limit: int = 100) -> List[Dict]:
    """Return list of chats (most recent first) with metadata."""
    key = _chat_list_key(user_id)

    try:
        chat_ids = _r.lrange(key, 0, limit - 1)
    except Exception:
        return []

    result = []

    for cid in chat_ids:
        title = _r.get(_chat_title_key(user_id, cid)) or f"Chat {cid[:6]}"

        # fetch last message from this chat
        try:
            last = _r.lindex(_chat_key(user_id, cid), -1)
            last_msg = json.loads(last)["message"] if last else ""
            last_ts = json.loads(last)["ts"] if last else None
        except Exception:
            last_msg = ""
            last_ts = None

        result.append({
            "chat_id": cid,
            "title": title,
            "last_message": last_msg,
            "ts": last_ts
        })

    return result


# ------------------------------------------------------------
# Message Saving, History Loading, Chat Delete
# ------------------------------------------------------------
def save_message(user_id: str, chat_id: str, role: str, message: str) -> None:
    """Append a message to this chat & make chat most recent."""
    key = _chat_key(user_id, chat_id)

    entry_obj = {
        "id": uuid4().hex,
        "role": role,
        "message": message,
        "ts": int(time.time())
    }
    entry = json.dumps(entry_obj)

    try:
        # Append to message list
        _r.rpush(key, entry)

        # Keep only last MAX_HISTORY messages
        _r.ltrim(key, -MAX_HISTORY, -1)

        # Refresh TTL
        if HISTORY_TTL_SECONDS > 0:
            _r.expire(key, HISTORY_TTL_SECONDS)

        # Move this chat to the top of chat_list
        list_key = _chat_list_key(user_id)

        _r.lrem(list_key, 0, chat_id)   # remove duplicates
        _r.lpush(list_key, chat_id)     # add to top

        if HISTORY_TTL_SECONDS > 0:
            _r.expire(list_key, HISTORY_TTL_SECONDS)

    except Exception:
        return


def get_history(user_id: str, chat_id: str) -> List[Dict]:
    """Return all messages in one chat."""
    key = _chat_key(user_id, chat_id)

    try:
        items = _r.lrange(key, 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        return []


def clear_history(user_id: str, chat_id: str) -> None:
    """Delete entire chat + remove from chat list."""
    try:
        _r.delete(_chat_key(user_id, chat_id))
        _r.lrem(_chat_list_key(user_id), 0, chat_id)
        _r.delete(_chat_title_key(user_id, chat_id))
    except Exception:
        return


def delete_chat(user_id: str, chat_id: str) -> None:
    """Alias to clear_history"""
    clear_history(user_id, chat_id)


def rename_chat(user_id: str, chat_id: str, title: str) -> None:
    """Rename the chat title."""
    try:
        _r.set(_chat_title_key(user_id, chat_id), title)
        if HISTORY_TTL_SECONDS > 0:
            _r.expire(_chat_title_key(user_id, chat_id), HISTORY_TTL_SECONDS)
    except Exception:
        return
