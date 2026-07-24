# backend/role1_jd/router.py
"""
FastAPI router for the JD Analytics module (Role 1).

Endpoint:  POST /extract
Mounted at prefix /api/jd in main.py  →  full path becomes POST /api/jd/extract

Flow:
  1. Accept a PDF or DOCX upload (multipart/form-data) with optional
     query params `company` and `role`.
  2. Extract raw text from the uploaded file.
  3. Prioritise high-signal sections (Key Responsibilities, etc.) if present.
  4. Call the shared LLM pipeline (shared/llm_client.py → extract_skills).
  5. Validate the result against the shared ExtractedSkillList Pydantic schema.
  6. Persist the validated JSON to data/extracted/jd_<filename>.json.
  7. Return the validated JSON response.
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

# ── Shared imports (reuse, do NOT duplicate) ──
from shared.schemas import ExtractedSkillList, Skill
from shared.llm_client import extract_skills

# ── Local helpers ──
from role1_jd.extract import (
    extract_text_from_docx,
    extract_text_from_pdf,
    prioritise_sections,
)

logger = logging.getLogger("role1_jd")

router = APIRouter()

# Allowed MIME types and extensions
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}

# Base directory for persisted extractions
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "extracted"


# ────────────────────────────────────────────────────────────────────
# Helper: validate and read uploaded file
# ────────────────────────────────────────────────────────────────────

def _get_extension(filename: str) -> str:
    """Return the lower-cased file extension."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


async def _read_file_bytes(file: UploadFile) -> bytes:
    """Read file content; raise 400 on empty file."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return content


def _validate_file_type(file: UploadFile) -> str:
    """
    Validate the uploaded file by extension and content-type.
    Returns the normalised extension (.pdf | .docx).
    """
    ext = _get_extension(file.filename or "")
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF and DOCX are accepted.",
        )
    # Content-type check (lenient — some clients send generic types)
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        # Only warn, don't reject — extension is the source of truth
        logger.warning(
            "Content-Type '%s' does not match extension '%s'; proceeding anyway.",
            file.content_type,
            ext,
        )
    return ext


# ────────────────────────────────────────────────────────────────────
# Helper: persist extraction result
# ────────────────────────────────────────────────────────────────────

def _save_result(filename: str, data: dict) -> Path:
    """
    Save the validated extraction result as JSON.
    Returns the path to the saved file.
    """
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Strip the original extension, prefix with jd_
    base_name = os.path.splitext(filename)[0]
    out_path = _DATA_DIR / f"jd_{base_name}.json"
    try:
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save extraction result: {exc}",
        ) from exc
    return out_path


# ────────────────────────────────────────────────────────────────────
# Endpoint: POST /extract
# ────────────────────────────────────────────────────────────────────

@router.post("/extract", response_model=ExtractedSkillList)
async def extract_jd_skills(
    file: UploadFile = File(..., description="Job Description file (PDF or DOCX)"),
    company: Optional[str] = Query(None, description="Company name"),
    role: Optional[str] = Query(None, description="Role / job title"),
):
    """
    Extract skills from a Job Description document.

    Accepts a PDF or DOCX file, extracts text, sends it through the shared
    LLM pipeline, validates the output against the shared Pydantic schema,
    persists the result as JSON, and returns it.
    """

    # 1. Validate file type
    ext = _validate_file_type(file)

    # 2. Read file bytes
    file_bytes = await _read_file_bytes(file)

    # 3. Extract raw text based on file type
    try:
        if ext == ".pdf":
            raw_text = extract_text_from_pdf(file_bytes)
        else:
            raw_text = extract_text_from_docx(file_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract text from the uploaded {ext.upper()} file. "
                   f"It may be corrupt or password-protected. Error: {exc}",
        ) from exc

    if not raw_text or not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="The uploaded document contains no extractable text.",
        )

    # 4. Prioritise high-signal sections if available
    focused_text = prioritise_sections(raw_text)

    # 5. Call shared LLM extraction pipeline
    try:
        llm_result = extract_skills(text=focused_text, doc_type="job description")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned malformed JSON: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM extraction failed: {exc}",
        ) from exc

    # 6. Build and validate response with the shared Pydantic model
    try:
        result = ExtractedSkillList(
            source_type="jd",
            source_file=file.filename or "unknown",
            company=company,
            role=role,
            skills=[Skill(**s) for s in llm_result.get("skills", [])],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM output failed schema validation: {exc}",
        ) from exc

    # 7. Persist to disk
    _save_result(file.filename or "unknown", result.model_dump())

    logger.info(
        "Extracted %d skills from '%s' (company=%s, role=%s)",
        len(result.skills),
        file.filename,
        company,
        role,
    )

    return result
