from student.core.celerey_app import celery_app
from sqlalchemy.orm import sessionmaker
from student.core.database import engine, Document

# Import chromadb compat and chromadb here so worker processes initialize the
# vector DB client in their own process (don't reuse a Collection object
# created by the FastAPI process which may be missing internal client state).
import student.core.chromadb_compat
import chromadb

@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, doc_id: int, file_path: str, content_type: str):
    """Process a document: extract text, create embeddings, and store chunks.

    The worker creates its own ChromaDB client and collection to avoid
    sharing a Collection instance across processes (which can lack
    internal `_client` state).
    """
    # Import text-processing helpers inside the task to avoid circular imports
    from student.doc_summarizer.endpoint import extract_text, detect_language, text_splitter, get_embed

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
            raise ValueError("No text chunks generated from document")

        embeddings = get_embed().embed_documents(chunks)

        ids = [f"doc_{doc.id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            "source": doc.filename,
            "sql_doc_id": doc.id,
            "lang": lang,
            "chunk_index": i
        } for i in range(len(chunks))]

        # Create a local ChromaDB client/collection inside the worker process
        CHROMA_DB_DIR = "student/chroma_store"
        chroma_client = chromadb.Client(chromadb.config.Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=CHROMA_DB_DIR
        ))
        collection = chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

        # Use the client's internal _add to avoid relying on a Collection
        # object's private `_client` attribute (compatibility across processes).
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

