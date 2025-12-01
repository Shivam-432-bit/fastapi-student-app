from student.core.celerey_app import celery_app
from sqlalchemy.orm import sessionmaker
from student.core.database import engine, Document

# Ensure each worker process initializes its own Chroma client state.
import student.core.chromadb_compat
from student.doc_summarizer.services.chunking import text_splitter
from student.doc_summarizer.services.embeddings import get_embed
from student.doc_summarizer.services.text_extraction import extract_text, detect_language
from student.doc_summarizer.services.vector_store import (
    get_chroma_client,
    get_documents_collection,
)


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, doc_id: int, file_path: str, content_type: str):
    """Process a document: extract text, create embeddings, and store chunks.

    The worker creates its own ChromaDB client and collection to avoid
    sharing a Collection instance across processes (which can lack
    internal `_client` state).
    """
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError(f"Document with id {doc_id} not found")

        doc.status = "processing"
        db.commit()

        with open(file_path, "rb") as f:
            content = f.read()

        text = extract_text(content, content_type)
        lang = detect_language(text)

        chunks = text_splitter.split_text(text)
        if not chunks:
            # Provide more debug info for failures so we can see why splitting failed
            sample = (text or "")[:200]
            print(f"[Celery] No chunks for doc {doc.id}. extracted_text_len={len(text or '')} sample={sample!r}")
            raise ValueError("No text chunks generated from document")

        embeddings = get_embed().embed_documents(chunks)

        ids = [f"doc_{doc.id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            "source": doc.filename,
            "sql_doc_id": doc.id,
            "lang": lang,
            "chunk_index": i
        } for i in range(len(chunks))]

        chroma_client = get_chroma_client()
        collection = get_documents_collection()

        # Insert embeddings via the shared client to ensure persistence across processes.
        chroma_client._add(
            ids,
            collection.id,
            embeddings,
            metadatas,
            chunks
        )

        # Ensure data is flushed to disk so future processes (API, workers)
        # can see the new embeddings immediately.
        try:
            chroma_client.persist()
        except Exception:
            pass

        doc.status = "completed"
        doc.error_message = None
        db.commit()
        print(f"✅ [Celery] Document {doc_id} processing complete.")
        return "success"

    except Exception as e:
        print(f"❌ [Celery] Error processing document {doc_id}: {e}")
        # Mark the DB record as failed before retrying so we have a trace.
        try:
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
        except Exception:
            pass
        # Retry the task (this will raise a Retry exception to Celery)
        raise self.retry(exc=e, countdown=5)

    finally:
        db.close()

