from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session, sessionmaker

from student.core.database import engine, get_db, Document
from student.core.models import DocumentResponse
from student.doc_summarizer.config import ALLOWED_CONTENT_TYPES, UPLOAD_DIR
from student.doc_summarizer.services.search import perform_search
from student.doc_summarizer.services.vector_store import get_documents_collection
from student.utils.llm import answer_with_llm

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """Return documents ordered by most recent upload."""
    return db.query(Document).order_by(Document.upload_date.desc()).all()


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/upload-and-process", response_model=DocumentResponse)
async def upload_and_process(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    try:
        from student.workers.tasks import process_document_task

        safe_filename = f"{uuid4()}_{file.filename}"
        file_path = f"{UPLOAD_DIR}/{safe_filename}"

        content = await file.read()
        with open(file_path, "wb") as fh:
            fh.write(content)

        new_doc = Document(
            filename=file.filename,
            file_path=file_path,
            upload_date=datetime.now(),
            file_size=len(content),
            content_type=file.content_type,
            status="pending",
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        process_document_task.delay(new_doc.id, file_path, file.content_type)
        return new_doc

    except Exception as exc:  # pragma: no cover - surfaced to client
        print(f"[upload] error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search")
def search_document(doc_id: str, query: str):
    try:
        results = perform_search(doc_id, query)
        return {
            "count": len(results),
            "top_match": results[0] if results else None,
            "results": results,
        }
    except Exception as exc:
        print(f"[search] error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ask")
def ask_document(doc_id: str, query: str):
    try:
        results = perform_search(doc_id, query)
        if not results:
            return {"answer": "I couldn't find any relevant information in the document."}

        context_text = "\n\n".join([r["text"] for r in results])
        answer = answer_with_llm(query, context_text)
        if answer.startswith("Error communicating with LLM"):
            raise HTTPException(status_code=503, detail=answer)

        return {"answer": answer, "sources": results}

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[ask] error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/pdf/list")
async def list_pdfs():
    collection = get_documents_collection()
    if collection is None:
        return {"files": []}

    try:
        items = collection.get()
        raw_metas = items.get("metadatas", [])
        sources = set()

        for meta in raw_metas:
            if not meta:
                continue
            if isinstance(meta, dict):
                src = meta.get("source")
                if isinstance(src, str) and src.lower().endswith(".pdf"):
                    sources.add(src)
                continue
            if isinstance(meta, (list, tuple)):
                for inner in meta:
                    if not inner or not isinstance(inner, dict):
                        continue
                    src = inner.get("source")
                    if isinstance(src, str) and src.lower().endswith(".pdf"):
                        sources.add(src)
                continue
            try:
                src = meta.get("source")
            except Exception:
                src = None
            if isinstance(src, str) and src.lower().endswith(".pdf"):
                sources.add(src)

        return {"files": sorted(sources)}

    except Exception as exc:
        print("Error loading PDF list:", exc)
        return {"files": []}
