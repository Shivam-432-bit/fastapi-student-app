import student.core.chromadb_compat  # MUST be first to patch chromadb

from fastapi import FastAPI
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware

from student.core.database import create_tables
from student.doc_summarizer.endpoint import router
from student.routers import auth, students
from student.routers import bulk_upload
from student.api import ws_router
from student.api.chats_router import router as chats_router
from student.api.websocket_test import router as test_ws_router

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

# Allow CORS so browser preflight (OPTIONS) succeeds for SSE/WebSocket endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router.router)
app.include_router(test_ws_router)

app.include_router(router, prefix="/api", tags=["documents"])

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(bulk_upload.router, prefix="/api")
app.include_router(chats_router, tags=["chats"])

# Root endpoint now serves a simple frontend page. API docs remain available at `/docs`.
@app.get("/")
def read_root():
    return FileResponse("student/api/home.html", media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/home")
def read_home():
    return FileResponse("student/api/home.html", media_type="text/html")