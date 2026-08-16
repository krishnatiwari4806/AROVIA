"""Resume Management Service implementing atomic lifecycle, validation, and storage operations."""

import logging
import os
import uuid
from typing import Optional

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ParsedResumeData, ResumeParsedDataUpdateRequest
from app.services.document_extractor import (
    MAX_EXTRACTED_CHARACTERS,
    extract_and_sanitize_text,
    verify_file_magic_bytes,
)
from app.services.gemini_service import GeminiService, get_gemini_service

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024  # 64 KB chunks for streaming size enforcement


class ResumeService:
    """Service orchestrating candidate resume ingestion, extraction, and atomic lifecycle."""

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or get_gemini_service()

    async def upload_resume(
        self,
        db: AsyncSession,
        current_user: User,
        file: UploadFile,
    ) -> Resume:
        """Atomically process, extract, store, and link candidate resume.

        Enforces the atomic lifecycle order:
        1. Streaming size enforcement (<= 5 MB)
        2. Magic byte signature verification
        3. Plain text extraction & sanitization
        4. Gemini structured schema parsing
        5. Persist new file to storage
        6. Create or replace DB record
        7. Commit database transaction (with rollback guard cleaning new file)
        8. Delete old file from storage (only after successful commit)
        """
        original_filename = file.filename or "resume.pdf"
        max_size = settings.MAX_RESUME_SIZE_BYTES if settings else 5 * 1024 * 1024

        # 1. Read file stream in chunks enforcing size limit
        file_chunks: list[bytes] = []
        total_size = 0

        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size:
                raise ValidationError(
                    "File exceeds maximum allowed size of 5 MB.",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            file_chunks.append(chunk)

        content = b"".join(file_chunks)

        if not content:
            raise ValidationError(
                "Uploaded file is empty.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # 2. Magic byte verification
        mime_type = verify_file_magic_bytes(content, original_filename)

        # 3. Plain text extraction & sanitization
        sanitized_text, _ = await extract_and_sanitize_text(content, original_filename)

        # 4. Gemini structured parsing
        parsed_data: ParsedResumeData = await self.gemini_service.parse_resume(sanitized_text)

        # 5. Persist new file to storage
        storage_dir = settings.RESUME_STORAGE_DIR if settings else "storage/resumes"
        os.makedirs(storage_dir, exist_ok=True)

        ext = ".pdf" if mime_type == "application/pdf" else ".docx"
        new_file_uuid = str(uuid.uuid4())
        new_file_name = f"{new_file_uuid}{ext}"
        new_file_path = os.path.abspath(os.path.join(storage_dir, new_file_name))

        # Write new file to disk
        with open(new_file_path, "wb") as f:
            f.write(content)

        # Set 0600 permissions if supported on OS
        try:
            os.chmod(new_file_path, 0o600)
        except OSError:
            pass

        # 6. Create or replace DB record
        stmt = select(Resume).where(Resume.user_id == current_user.id)
        result = await db.execute(stmt)
        existing_resume = result.scalars().first()

        old_file_path: Optional[str] = None

        if existing_resume:
            old_file_path = existing_resume.file_path
            existing_resume.file_name = original_filename
            existing_resume.file_path = new_file_path
            existing_resume.file_size_bytes = total_size
            existing_resume.mime_type = mime_type
            existing_resume.raw_text = sanitized_text
            existing_resume.parsed_data = parsed_data.model_dump()
            target_resume = existing_resume
        else:
            target_resume = Resume(
                user_id=current_user.id,
                file_name=original_filename,
                file_path=new_file_path,
                file_size_bytes=total_size,
                mime_type=mime_type,
                raw_text=sanitized_text,
                parsed_data=parsed_data.model_dump(),
            )
            db.add(target_resume)

        # 7. Commit database transaction with rollback guard
        try:
            await db.commit()
            await db.refresh(target_resume)
        except Exception as exc:
            # Clean up the newly written file on failure
            if os.path.exists(new_file_path):
                try:
                    os.remove(new_file_path)
                except OSError as rm_err:
                    logger.error(f"Failed to clean up newly written file on DB error: {rm_err}")
            await db.rollback()
            raise exc

        # 8. Delete old file from storage (only after successful commit)
        if old_file_path and old_file_path != new_file_path and os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except OSError as del_err:
                logger.warning(f"Failed to delete old resume file {old_file_path}: {del_err}")

        return target_resume

    async def get_user_resume(self, db: AsyncSession, current_user: User) -> Resume:
        """Retrieve candidate active resume record."""
        stmt = select(Resume).where(Resume.user_id == current_user.id)
        result = await db.execute(stmt)
        resume = result.scalars().first()

        if not resume:
            raise NotFoundError("No active resume found for this user.", error_code="RESUME_NOT_FOUND")
        return resume

    async def update_parsed_data(
        self,
        db: AsyncSession,
        current_user: User,
        update_data: ResumeParsedDataUpdateRequest,
    ) -> Resume:
        """Update/override extracted career data in candidate active resume."""
        resume = await self.get_user_resume(db, current_user)

        current_parsed = dict(resume.parsed_data or {})

        if update_data.skills is not None:
            current_parsed["skills"] = update_data.skills
        if update_data.experience_years is not None:
            current_parsed["experience_years"] = update_data.experience_years
        if update_data.domains is not None:
            current_parsed["domains"] = update_data.domains
        if update_data.education is not None:
            current_parsed["education"] = [
                item.model_dump() for item in update_data.education
            ]
        if update_data.summary is not None:
            current_parsed["summary"] = update_data.summary

        # Validate with schema
        validated = ParsedResumeData.model_validate(current_parsed)
        resume.parsed_data = validated.model_dump()

        await db.commit()
        await db.refresh(resume)
        return resume

    async def delete_resume(self, db: AsyncSession, current_user: User) -> None:
        """Delete active resume from database and remove associated storage file."""
        resume = await self.get_user_resume(db, current_user)
        file_path = resume.file_path

        # Delete database row
        await db.delete(resume)
        await db.commit()

        # Delete physical file from disk
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as exc:
                logger.warning(f"Failed to remove resume file {file_path} from disk: {exc}")


def get_resume_service() -> ResumeService:
    """Dependency provider for ResumeService."""
    return ResumeService()
