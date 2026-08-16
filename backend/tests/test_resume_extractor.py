"""Unit tests for document text extraction and sanitization."""

import io
import pytest
import docx

from app.core.exceptions import ValidationError
from app.services.document_extractor import (
    extract_and_sanitize_text,
    sanitize_extracted_text,
    MIME_PDF,
    MIME_DOCX,
)
from tests.test_resume_upload import create_sample_docx, create_sample_pdf


@pytest.mark.asyncio
async def test_extract_valid_docx():
    """Verify text extraction from a valid DOCX document."""
    content_text = (
        "John Doe - Senior Software Engineer\n"
        "Proficient in Python, FastAPI, PostgreSQL, Docker, and Kubernetes.\n"
        "Experience: 5 years building scalable microservices and async systems."
    )
    docx_bytes = create_sample_docx(content_text)
    sanitized, mime = await extract_and_sanitize_text(docx_bytes, "johndoe_cv.docx")

    assert mime == MIME_DOCX
    assert "John Doe" in sanitized
    assert "FastAPI" in sanitized
    assert "PostgreSQL" in sanitized


@pytest.mark.asyncio
async def test_extract_valid_pdf():
    """Verify text extraction from a valid text-based PDF."""
    content_text = (
        "Jane Smith - Full Stack Developer with 4 years experience in Python and React."
    )
    pdf_bytes = create_sample_pdf(content_text)
    sanitized, mime = await extract_and_sanitize_text(pdf_bytes, "janesmith.pdf")

    assert mime == MIME_PDF
    assert "Jane Smith" in sanitized
    assert "React" in sanitized


@pytest.mark.asyncio
async def test_reject_scanned_or_insufficient_text_pdf():
    """Verify that a PDF with less than 50 non-whitespace characters is rejected with 422."""
    short_text = "Hi John"
    pdf_bytes = create_sample_pdf(short_text)

    with pytest.raises(ValidationError) as exc_info:
        await extract_and_sanitize_text(pdf_bytes, "empty_scan.pdf")
    assert "No extractable text found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_reject_scanned_or_insufficient_text_docx():
    """Verify that a DOCX with less than 50 non-whitespace characters is rejected with 422."""
    short_text = "Few words"
    docx_bytes = create_sample_docx(short_text)

    with pytest.raises(ValidationError) as exc_info:
        await extract_and_sanitize_text(docx_bytes, "short.docx")
    assert "No extractable text found" in str(exc_info.value)


def test_sanitize_extracted_text_strips_control_chars_and_bounds():
    """Verify null bytes, control characters are stripped and long text is truncated to 30,000 chars."""
    dirty_text = "Hello\x00\x01\x02World!\n\n\n\n\nTesting control chars.\x7f"
    clean = sanitize_extracted_text(dirty_text)
    assert clean == "Hello\nWorld!\n\nTesting control chars." or "HelloWorld!\n\nTesting control chars." in clean
    assert "\x00" not in clean
    assert "\x01" not in clean

    # Test 30k bound
    huge_text = "A" * 35000
    bounded = sanitize_extracted_text(huge_text)
    assert len(bounded) == 30000
