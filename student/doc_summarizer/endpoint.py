from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session, sessionmaker
from student.core.database import engine
from langdetect import detect

# Import compatibility patch before chromadb
import student.core.chromadb_compat
import chromadb
# Restore our app env vars after chromadb import
student.core.chromadb_compat.restore_env()
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image
import io
import os
from datetime import datetime

from student.core.database import get_db, Document
from student.core.models import DocumentResponse

# --------------------------------------------------------
#               VECTOR DB INIT
# --------------------------------------------------------

# Use Client with persist_directory to ensure data survives restarts
CHROMA_DB_DIR = "student/chroma_store"
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
chroma_client = chromadb.Client(chromadb.config.Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=CHROMA_DB_DIR
))

collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)

# chromadb Collection objects expect a private `_client` attribute that is not
# automatically populated when running under Pydantic v2. Attach the client
# explicitly so downstream calls (query, add, etc.) work.
if not hasattr(collection, "_client"):
    collection._client = chroma_client

# --------------------------------------------------------
#               LAZY LOADING MODELS
# --------------------------------------------------------

_embed = None
_reranker_tokenizer = None
_reranker_model = None
_ocr_reader = None
_llm = None

def get_embed():
    global _embed
    if _embed is None:
        print("Loading Embedding Model...")
        _embed = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embed

def get_llm():
    global _llm
    if _llm is None:
        print("Loading Ollama Model...")
        _llm = ChatOllama(model="llama3") 
    return _llm

def get_reranker():
    global _reranker_tokenizer, _reranker_model
    if _reranker_model is None:
        print("Loading Reranker Model...")
        _reranker_tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-reranker-base")
        _reranker_model = AutoModelForSequenceClassification.from_pretrained(
            "BAAI/bge-reranker-base"
        )
        _reranker_model.eval()
    return _reranker_tokenizer, _reranker_model

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        print("Loading OCR Model...")
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader

def rerank(query, chunks):
    """Return chunks sorted by reranker confidence score."""
    if not chunks:
        return []
    
    tokenizer, model = get_reranker()
        
    pairs = [[query, chunk] for chunk in chunks]
    inputs = tokenizer(
        pairs,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    with torch.no_grad():
        scores = model(**inputs).logits.squeeze(-1)

    sorted_idx = torch.argsort(scores, descending=True).tolist()

    sanitized_results = []
    for i in sorted_idx:
        score = float(scores[i])
        
        if score != score or score == float('inf') or score == float('-inf'):
            score = 0.0
            
        clean_text = chunks[i].replace("\n", " ").strip()
        clean_text = " ".join(clean_text.split())

        sanitized_results.append({
            "score": round(score, 4), 
            "text": clean_text
        })

    return sanitized_results[:5]


# --------------------------------------------------------
#               CHUNKING STRATEGY (RECURSIVE)
# --------------------------------------------------------

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", "? ", "! ", "; ", " "]
)

# --------------------------------------------------------
#               ROUTER INIT
# --------------------------------------------------------

router = APIRouter()

# --------------------------------------------------------
#               TEXT EXTRACTION + LANGUAGE DETECTION
# --------------------------------------------------------

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from image bytes using EasyOCR."""
    try:
        reader = get_ocr_reader()
        result = reader.readtext(image_bytes, detail=0)
        return " ".join(result)
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def extract_text(file_content: bytes, content_type: str) -> str:
    """Extract text from PDF or Image."""
    text = ""
    
    if content_type == 'application/pdf':
        doc = fitz.open(stream=file_content, filetype="pdf")
        
        full_text = []
        for page in doc:
            page_text = page.get_text()
            
            if len(page_text.strip()) < 50:
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                ocr_text = extract_text_from_image(img_bytes)
                full_text.append(ocr_text)
            else:
                full_text.append(page_text)
                
        text = "\n".join(full_text)
        
    elif content_type in ['image/jpeg', 'image/png', 'image/jpg']:
        text = extract_text_from_image(file_content)
        
    return text


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

# --------------------------------------------------------
#               LIST DOCUMENTS
# --------------------------------------------------------

@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents available in the system."""
    documents = db.query(Document).order_by(Document.upload_date.desc()).all()
    return documents


# --------------------------------------------------------
#      PROCESS + EMBED + STORE CHUNKS (DOC INGESTION)
# --------------------------------------------------------

@router.post("/upload-and-process", response_model=DocumentResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed_types}")

    try:
        # Import Celery task here to avoid circular import
        from student.workers.tasks import process_document_task
        
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        import uuid
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        new_doc = Document(
            filename=file.filename,
            file_path=file_path,
            upload_date=datetime.now(),
            file_size=len(content),
            content_type=file.content_type,
            status="pending"
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # Use Celery task asynchronously
        process_document_task.delay(new_doc.id, file_path, file.content_type)
        
        return new_doc

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------
#               SEMANTIC SEARCH + RERANKING
# --------------------------------------------------------

def perform_search(doc_id: str, query: str):
    """Helper function to retrieve and rerank chunks."""
    query_embed = get_embed().embed_query(query)
    
    if doc_id.isdigit():
        where_filter = {"sql_doc_id": int(doc_id)}
    else:
        where_filter = {"source": doc_id}

    # Cap n_results to the number of elements in the index to avoid
    # ValueError("Number of requested results ...") under Pydantic v2.
    try:
        max_results = chroma_client._count(collection.id)
    except Exception:
        max_results = 10

    if max_results == 0:
        return []

    n_results = min(10, max_results)

    results = chroma_client._query(
        collection.id,
        query_embeddings=[query_embed],
        n_results=n_results,
        where=where_filter
    )
    
    retrieved_chunks = results['documents'][0]
    
    if not retrieved_chunks:
        return []

    reranked_results = rerank(query, retrieved_chunks)
    return reranked_results

@router.post("/search")
def search_document(doc_id: str, query: str):
    try:
        results = perform_search(doc_id, query)
        
        return {
            "count": len(results),
            "top_match": results[0] if results else None,
            "results": results
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
def ask_document(doc_id: str, query: str):
    """
    Ask a question about a specific document using Ollama (Llama3).
    """
    try:
        results = perform_search(doc_id, query)
        if not results:
            return {"answer": "I couldn't find any relevant information in the document."}
            
        context_text = "\n\n".join([r["text"] for r in results])
        
        llm = get_llm()
        
        prompt = ChatPromptTemplate.from_template("""
        Answer the question based only on the following context:
        
        {context}
        
        Question: {question}
        """)
        
        chain = prompt | llm
        try:
            response = chain.invoke({"context": context_text, "question": query})
        except Exception as e:
            if "Connection refused" in str(e):
                raise HTTPException(status_code=503, detail="Ollama service is not reachable. Please ensure Ollama is running (e.g., 'ollama serve').")
            raise e
        
        return {
            "answer": response.content,
            "sources": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
