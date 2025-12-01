from fastapi import APIRouter
from fastapi import Request

router = APIRouter()

@router.post("/chat/test")
async def http_chat(request:Request):
    try: 
        body = await request.json()
    except:
        return {"error": "invalid json"}
    
    chat_id =body.get("chat_id")
    question = body.get("question")
    source = body.get("source")

    if not chat_id:
        return {"error": "missing chat_id"}
    if not question:
        return {"error": "missing question"}
    if not source:
        return {"error": "missing source"}
    return {"chat_id": chat_id, "question": question, "source": source}
    
    user_id = "user123"

    