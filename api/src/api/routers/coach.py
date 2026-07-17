"""HTTP routes for the CV-rewrite feature."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from src.domain.use_cases import PrepareInterviewGuideUseCase, RewriteCvUseCase
from src.infra.coaching_schema import CoachError

from ..schemas import (
    GuideRequest,
    GuideResponse,
    RewriteResponse,
    guide_to_response,
    to_guide_input,
    to_response,
)

router = APIRouter(prefix="/api", tags=["coach"])

_MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB — well under Anthropic's 32 MB request cap


def _get_use_case(request: Request) -> RewriteCvUseCase:
    container = request.app.state.container
    return container.resolve(RewriteCvUseCase)


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_cv(
    request: Request,
    cv: UploadFile = File(..., description="The candidate's CV as a PDF."),
    job_description: str = Form(..., description="The target job description."),
) -> RewriteResponse:
    """Score a CV against a job description, then honestly rewrite it to PDF."""
    content_type = (cv.content_type or "").lower()
    filename = (cv.filename or "").lower()
    if content_type != "application/pdf" and not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="The CV must be a PDF file.")

    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")

    cv_bytes = await cv.read()
    if not cv_bytes:
        raise HTTPException(status_code=400, detail="The uploaded CV is empty.")
    if len(cv_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="The CV PDF is too large (max 20 MB).")

    use_case = _get_use_case(request)
    try:
        # The Anthropic call + PDF render are blocking; keep the event loop free.
        result = await run_in_threadpool(use_case.execute, cv_bytes, job_description)
    except CoachError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return to_response(result)


@router.post("/interview-guide", response_model=GuideResponse)
async def interview_guide(request: Request, body: GuideRequest) -> GuideResponse:
    """Expand a prior analysis into a full interview training guide (PDF)."""
    if not body.interview_prep.likely_questions and not body.interview_prep.talking_points:
        raise HTTPException(
            status_code=400,
            detail="Interview prep is required to build a guide.",
        )

    container = request.app.state.container
    use_case = container.resolve(PrepareInterviewGuideUseCase)
    guide_input = to_guide_input(body)
    try:
        result = await run_in_threadpool(use_case.execute, guide_input)
    except CoachError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    name = body.rewritten_cv.full_name if body.rewritten_cv else None
    return guide_to_response(result, name)
