from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError

from student.core.database import create_tables
from student.doc_summarizer.endpoint import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

# Create FastAPI app
app = FastAPI(
    title="Student API with RAG",
    description="A FastAPI application with RAG-powered document search and AI Q&A",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api", tags=["documents"])

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Student API v2.0 - RAG Implementation",
        "status": "healthy",
        "documentation": "/docs",
        "version": "2.0.0",
        "features": [
            "Document Upload (PDF, Images)",
            "OCR for Scanned Documents",
            "Semantic Search",
            "AI-Powered Q&A with Ollama",
            "Persistent Vector Storage"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
