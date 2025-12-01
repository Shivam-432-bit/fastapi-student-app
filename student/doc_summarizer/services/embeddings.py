"""Embedding and reranker helpers used by the doc_summarizer."""
from __future__ import annotations

from typing import List, Dict

from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

_embed = None
_reranker_tokenizer = None
_reranker_model = None


def get_embed() -> HuggingFaceEmbeddings:
    """Return a singleton HuggingFace embedding model."""
    global _embed
    if _embed is None:
        print("Loading Embedding Model...")
        _embed = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embed


def get_reranker():
    """Return the tokenizer/model pair for reranking results."""
    global _reranker_tokenizer, _reranker_model
    if _reranker_model is None:
        print("Loading Reranker Model...")
        _reranker_tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-reranker-base")
        _reranker_model = AutoModelForSequenceClassification.from_pretrained(
            "BAAI/bge-reranker-base"
        )
        _reranker_model.eval()
    return _reranker_tokenizer, _reranker_model


def rerank(query: str, chunks: List[str]) -> List[Dict[str, object]]:
    """Return top reranked chunks for a query."""
    if not chunks:
        return []

    tokenizer, model = get_reranker()
    pairs = [[query, chunk] for chunk in chunks]
    inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")

    with torch.no_grad():
        scores = model(**inputs).logits.squeeze(-1)

    sorted_idx = torch.argsort(scores, descending=True).tolist()
    sanitized_results: List[Dict[str, object]] = []

    for idx in sorted_idx:
        score = float(scores[idx])
        if score != score or score in (float("inf"), float("-inf")):
            score = 0.0
        clean_text = " ".join(chunks[idx].replace("\n", " ").split())
        sanitized_results.append({"score": round(score, 4), "text": clean_text})

    return sanitized_results[:5]
