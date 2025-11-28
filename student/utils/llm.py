"""Utility helpers for interacting with the local Ollama LLM server."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Configuration (override via environment variables if needed)
# ---------------------------------------------------------------------------

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "llama3:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60"))

GENERATE_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"


@dataclass
class LLMError(Exception):
    """Represents a structured LLM error to propagate user-friendly details."""

    message: str
    model: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def _build_prompt(question: str, context: str) -> str:
    return f"""
You are an answer extraction model.

Use ONLY the information inside the context to answer the question.
If the answer is not explicitly stated in the context, respond exactly with:
"I could not find the answer in the provided document."
Never use phrases such as "according to the context" or "based on the document".
Return a concise statement (one or two sentences max).

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""


def _call_ollama(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": 0,
        "stream": False,
    }

    response = requests.post(
        GENERATE_ENDPOINT,
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )

    # Ollama returns 404 for "model not found", so handle it explicitly
    if response.status_code == 404:
        try:
            detail = response.json().get("error", response.text)
        except ValueError:
            detail = response.text
        raise LLMError(
            message=f"Model '{model}' is not available. Run: ollama pull {model}",
            model=model,
        ) from None

    try:
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise LLMError(f"Error communicating with LLM: {exc}", model=model) from exc

    answer = data.get("response", "").strip()
    if not answer:
        raise LLMError("LLM returned an empty response.", model=model)

    return answer


def _sanitize_answer(answer: str) -> str:
    banned_prefixes = (
        "according to the context",
        "based on the context",
        "according to the document",
        "based on the document",
    )

    cleaned = answer.strip()
    lowered = cleaned.lower()
    for prefix in banned_prefixes:
        if lowered.startswith(prefix):
            stripped = cleaned[len(prefix):]
            cleaned = stripped.lstrip(", .:-")
            lowered = cleaned.lower()
            break
    return cleaned or "I could not find the answer in the provided document."


def answer_with_llm(question: str, context: str) -> str:
    """Generate an answer using Ollama with automatic fallback handling."""
    if not context:
        return "I could not find the answer in the provided document."

    prompt = _build_prompt(question, context)
    models_to_try = [DEFAULT_MODEL]

    if FALLBACK_MODEL and FALLBACK_MODEL not in models_to_try:
        models_to_try.append(FALLBACK_MODEL)

    last_error: Optional[LLMError] = None
    for model in models_to_try:
        try:
            raw_answer = _call_ollama(model, prompt)
            return _sanitize_answer(raw_answer)
        except LLMError as exc:
            last_error = exc
            continue

    # All models failed; report the most recent error.
    if last_error:
        return str(last_error)
    return "Error communicating with LLM: Unknown error"