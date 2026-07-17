"""Extract plain text from a PDF.

Local models (via Ollama) can't take a native PDF document block the way Claude
can, so the Ollama adapter extracts the CV's text first and sends that. Uses
``pypdf`` (pure-Python).
"""

from __future__ import annotations

import io

from pypdf import PdfReader


def extract_pdf_text(pdf: bytes) -> str:
    """Return the concatenated text of every page, or ``""`` if none is found."""
    reader = PdfReader(io.BytesIO(pdf))
    parts = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(p for p in parts if p).strip()
