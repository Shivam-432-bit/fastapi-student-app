import student.core.chromadb_compat  # MUST be first to patch chromadb

from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError

from student.core.database import create_tables
from student.doc_summarizer.endpoint import router
from student.routers import auth, students
from student.routers import bulk_upload

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

# Create FastAPI app
app = FastAPI(
    title="Student API with JWT",
    description="A modular FastAPI application for student management with JWT authentication",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api", tags=["documents"])

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(bulk_upload.router, prefix="/api")

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Student API v2.0 - Modular Architecture",
        "status": "healthy",
        "documentation": "/docs",
        "version": "2.0.0",
        "features": [
            "JWT Authentication",
            "Role-based Access Control", 
            "Student Management",
            "Bulk Upload (CSV/Excel)",
            "RAG-powered Search",
            "Modular Architecture"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)