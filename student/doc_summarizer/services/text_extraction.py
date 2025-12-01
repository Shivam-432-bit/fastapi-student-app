"""Text extraction utilities for documents and images."""
from __future__ import annotations

import io
from typing import Tuple

import easyocr
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageOps

from .embeddings import get_embed  # noqa: F401  # re-export convenience elsewhere if needed

_ocr_reader = None


def get_ocr_reader():
    """Return an EasyOCR reader singleton."""
    global _ocr_reader
    if _ocr_reader is None:
        print("Loading OCR Model...")
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from image bytes using EasyOCR."""
    try:
        reader = get_ocr_reader()
        result = reader.readtext(image_bytes, detail=0)
        return " ".join(result)
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"OCR Error: {exc}")
        return ""


def _enhanced_page_ocr(page) -> str:
    """Run multiple zoom/contrast passes for stubborn pages."""
    stronger = []
    for zoom in (2, 3, 4):
        try:
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img2 = enhancer.enhance(1.5)
            img2 = ImageOps.autocontrast(img2)
            buf = io.BytesIO()
            img2.save(buf, format="PNG")
            ocr_text = extract_text_from_image(buf.getvalue()).strip()
            if ocr_text:
                stronger.append(ocr_text)
                break
        except Exception:
            continue
    return " ".join(stronger)


def extract_text(file_content: bytes, content_type: str) -> str:
    """Extract text from PDFs or images."""
    text = ""

    if content_type == "application/pdf":
        doc = fitz.open(stream=file_content, filetype="pdf")
        full_text = []
        for page in doc:
            page_text = page.get_text()
            if len(page_text.strip()) < 50:
                try:
                    mat = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img_bytes = pix.tobytes("png")
                    ocr_text = extract_text_from_image(img_bytes)
                    full_text.append(ocr_text)
                except Exception:
                    try:
                        pix = page.get_pixmap()
                        img_bytes = pix.tobytes("png")
                        ocr_text = extract_text_from_image(img_bytes)
                        full_text.append(ocr_text)
                    except Exception:
                        full_text.append("")
            else:
                full_text.append(page_text)
        text = "\n".join(full_text)

        if not text or len(text.strip()) < 30:
            stronger_text = []
            for page in doc:
                stronger_text.append(_enhanced_page_ocr(page))
            text = "\n".join(stronger_text)

    elif content_type in {"image/jpeg", "image/png", "image/jpg"}:
        text = extract_text_from_image(file_content)

    return text


def detect_language(text: str) -> str:
    from langdetect import detect

    try:
        return detect(text)
    except Exception:
        return "unknown"
