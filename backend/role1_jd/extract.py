# backend/role1_jd/extract.py
"""
Text extraction helpers for JD Analytics.

Handles PDF and DOCX file parsing, and prioritises key JD sections
(e.g. "Key Responsibilities", "What We're Looking For") when they exist.
"""

import io
import re
from typing import Optional

import pdfplumber
from docx import Document


# ──────────────────────────────────────────────
# Section headings that carry the strongest skill signal
# ──────────────────────────────────────────────
_PRIORITY_HEADINGS: list[str] = [
    r"key\s+responsibilities",
    r"what\s+we(?:'re|.re)?\s+looking\s+for",
    r"requirements",
    r"qualifications",
    r"skills\s+required",
    r"must\s+have",
    r"nice\s+to\s+have",
    r"preferred\s+qualifications",
]

_HEADING_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#+\s*)?("
    + "|".join(_PRIORITY_HEADINGS)
    + r")\s*[:\-]?\s*\n",
    re.IGNORECASE,
)


# ──────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from a PDF file given its bytes."""
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract raw text from a DOCX file given its bytes."""
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def prioritise_sections(full_text: str) -> str:
    """
    If the document contains known high-signal headings, extract only those
    sections.  Otherwise fall back to the full text.

    This keeps the LLM prompt focused and reduces noise from boilerplate
    (company overview, benefits, etc.).
    """
    matches = list(_HEADING_PATTERN.finditer(full_text))
    if not matches:
        return full_text

    # Collect text from each matched heading to the next heading (or EOF)
    extracted_sections: list[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        extracted_sections.append(full_text[start:end].strip())

    combined = "\n\n".join(extracted_sections)
    # Only use sections if they contain meaningful content (> 50 chars)
    return combined if len(combined) > 50 else full_text
