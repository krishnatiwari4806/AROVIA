"""Resume API endpoints for candidate resume upload, review, update, and deletion."""

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.resume import (
    ResumeParsedDataUpdateRequest,
    ResumeResponse,
    ResumeUploadResponse,
)
from app.services.resume_service import ResumeService, get_resume_service

router = APIRouter()


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload, extract, and parse candidate resume",
)
@limiter.limit("5/minute")
async def upload_resume(
    request: Request,
    file: UploadFile = File(..., description="PDF or DOCX resume document (max 5 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeUploadResponse:
    """Upload a candidate resume file (.pdf or .docx).

    Validates size (5 MB limit), magic bytes, extracts text, invokes Gemini for structured parsing,
    and atomically saves the resume (replacing any prior upload).
    """
    resume = await resume_service.upload_resume(db=db, current_user=current_user, file=file)
    return ResumeUploadResponse(
        message="Resume successfully uploaded and parsed.",
        resume=ResumeResponse.model_validate(resume),
    )


@router.get(
    "/me",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active candidate resume and parsed career profile",
)
async def get_my_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """Retrieve the candidate's active uploaded resume and structured extracted skills."""
    resume = await resume_service.get_user_resume(db=db, current_user=current_user)
    return ResumeResponse.model_validate(resume)


@router.put(
    "/me/parsed",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update or override extracted resume career profile",
)
async def update_my_parsed_resume(
    update_data: ResumeParsedDataUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """Candidate manual edit or override for AI-extracted skills, domains, or summary."""
    resume = await resume_service.update_parsed_data(
        db=db, current_user=current_user, update_data=update_data
    )
    return ResumeResponse.model_validate(resume)


@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete active candidate resume",
)
async def delete_my_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> MessageResponse:
    """Permanently delete candidate resume from database and remove file from storage."""
    await resume_service.delete_resume(db=db, current_user=current_user)
    return MessageResponse(message="Resume successfully deleted.")
