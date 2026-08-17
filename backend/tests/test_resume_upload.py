"""Unit tests for resume upload validation and magic bytes detection."""

import io
import pytest
import docx

from app.core.exceptions import ValidationError
from app.services.document_extractor import (
    verify_file_magic_bytes,
    MIME_PDF,
    MIME_DOCX,
)


def create_sample_docx(text: str) -> bytes:
    """Helper to create a valid in-memory DOCX file."""
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_sample_pdf(text: str) -> bytes:
    """Helper to create a valid minimal PDF with text."""
    # A standard single-page PDF containing a stream
    content_stream = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET".encode("latin1")
    stream_len = len(content_stream)
    
    pdf_template = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(stream_len).encode("ascii") + b" >>\nstream\n" +
        content_stream +
        b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000305 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n388\n%%EOF\n"
    )
    return pdf_template


def test_magic_bytes_valid_pdf():
    """Verify valid PDF magic bytes '%PDF-' are accepted with .pdf extension."""
    pdf_bytes = create_sample_pdf("Software Engineer Resume")
    mime = verify_file_magic_bytes(pdf_bytes, "resume.pdf")
    assert mime == MIME_PDF


def test_magic_bytes_valid_docx():
    """Verify valid DOCX zip archive is accepted with .docx extension."""
    docx_bytes = create_sample_docx("Software Engineer Resume with 5 years experience")
    mime = verify_file_magic_bytes(docx_bytes, "candidate_cv.docx")
    assert mime == MIME_DOCX


def test_magic_bytes_spoofed_pdf_extension():
    """Verify plain text or binary file renamed to .pdf is rejected."""
    fake_pdf = b"This is just a text file renamed to resume.pdf"
    with pytest.raises(ValidationError) as exc_info:
        verify_file_magic_bytes(fake_pdf, "resume.pdf")
    assert "Invalid file format or corrupted signature" in str(exc_info.value)


def test_magic_bytes_spoofed_docx_extension():
    """Verify non-zip file renamed to .docx is rejected."""
    fake_docx = b"Not a real docx file contents"
    with pytest.raises(ValidationError) as exc_info:
        verify_file_magic_bytes(fake_docx, "resume.docx")
    assert "Invalid file format or corrupted signature" in str(exc_info.value)


def test_magic_bytes_extension_mismatch():
    """Verify valid PDF content with .docx extension is rejected."""
    pdf_bytes = create_sample_pdf("Software Engineer Resume")
    with pytest.raises(ValidationError) as exc_info:
        verify_file_magic_bytes(pdf_bytes, "resume.docx")
    assert "does not match" in str(exc_info.value)


def test_magic_bytes_empty_file():
    """Verify 0-byte file is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        verify_file_magic_bytes(b"", "empty.pdf")
    assert "empty" in str(exc_info.value).lower()
