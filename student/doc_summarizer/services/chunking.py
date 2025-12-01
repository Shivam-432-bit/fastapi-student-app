"""Chunking helpers for document ingestion."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from student.doc_summarizer.config import CHUNK_SIZE, CHUNK_OVERLAP

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", "? ", "! ", "; ", " "],
)
