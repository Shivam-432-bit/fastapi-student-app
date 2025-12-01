import os
import json
import redis
from typing import List, Dict

# Configuration (use env vars where possible)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
MAX_HISTORY = int(os.getenv("CHAT_MAX_HISTORY", 200))
HISTORY_TTL_SECONDS = int(os.getenv("CHAT_HISTORY_TTL", 60 * 60 * 24 * 7))  # 7 days default

# Shared connection pool / client
_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True)
_r = redis.Redis(connection_pool=_pool)


def save_message(user_id: str, role: str, message: str) -> None:
    """Append a chat message to the user's history and trim to `MAX_HISTORY`.

    - `role` should be 'user' or 'assistant'.
    - Trims the list to keep only the most recent `MAX_HISTORY` entries.
    - Sets a TTL on the history key so unused histories expire.
    """
    key = f"chat:{user_id}"
    entry = json.dumps({"role": role, "message": message})
    try:
        _r.rpush(key, entry)
        # keep last MAX_HISTORY entries
        _r.ltrim(key, -MAX_HISTORY, -1)
        # set/refresh TTL
        if HISTORY_TTL_SECONDS > 0:
            _r.expire(key, HISTORY_TTL_SECONDS)
    except Exception:
        # Best-effort: don't let Redis failures crash the app
        return


def get_history(user_id: str) -> List[Dict[str, str]]:
    """Return the user's chat history as a list of dicts (role/message)."""
    key = f"chat:{user_id}"
    try:
        items = _r.lrange(key, 0, -1)
        return [json.loads(i) for i in items]
    except Exception:
        return []


def clear_history(user_id: str) -> None:
    try:
        _r.delete(f"chat:{user_id}")
    except Exception:
        return
