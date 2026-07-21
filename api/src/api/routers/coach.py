"""HTTP routes for the CV-rewrite feature."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool

from src.domain.ports import PdfRenderer
from src.domain.use_cases import PrepareInterviewGuideUseCase, RewriteCvUseCase
from src.infra.anthropic_coach import AnthropicCvCoach
from src.infra.coaching_schema import CoachError
from src.infra.settings import Settings

from ..schemas import (
    ConfigResponse,
    GuideRequest,
    GuideResponse,
    RewriteResponse,
    guide_to_response,
    to_guide_input,
    to_response,
)

router = APIRouter(prefix="/api", tags=["coach"])

_MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB — well under Anthropic's 32 MB request cap


def _select_use_case(
    request: Request,
    api_key_header: str | None,
    use_case_cls: type,
) -> object:
    """Pick the use case for this request.

    If the caller supplies their own Anthropic key (BYOK, via the
    ``X-Anthropic-Api-Key`` header), build a per-request Anthropic coach with it.
    Otherwise use the container's configured coach (server Anthropic key, or
    Ollama). If neither a header key nor a server key can serve an Anthropic
    request, fail with a clear 400.
    """
    container = request.app.state.container
    settings: Settings = container.resolve(Settings)

    key = (api_key_header or "").strip()
    if key:
        renderer: PdfRenderer = container.resolve(PdfRenderer)
        coach = AnthropicCvCoach(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            api_key_override=key,
        )
        return use_case_cls(coach, renderer)

    if settings.resolve_provider() == "anthropic" and not settings.anthropic_api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="No Anthropic API key configured. Provide one via the app.",
        )
    return container.resolve(use_case_cls)


@router.get("/config", response_model=ConfigResponse)
def get_config(request: Request) -> ConfigResponse:
    """Whether the client must supply its own Anthropic key (BYOK)."""
    settings: Settings = request.app.state.container.resolve(Settings)
    requires = (
        settings.resolve_provider() == "anthropic"
        and not settings.anthropic_api_key.strip()
    )
    return ConfigResponse(requires_api_key=requires)


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_cv(
    request: Request,
    cv: UploadFile = File(..., description="The candidate's CV as a PDF."),
    job_description: str = Form(..., description="The target job description."),
    x_anthropic_api_key: str | None = Header(default=None),
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

    use_case: RewriteCvUseCase = _select_use_case(
        request, x_anthropic_api_key, RewriteCvUseCase
    )
    try:
        # The Anthropic call + PDF render are blocking; keep the event loop free.
        result = await run_in_threadpool(use_case.execute, cv_bytes, job_description)
    except CoachError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return to_response(result)


@router.post("/interview-guide", response_model=GuideResponse)
async def interview_guide(
    request: Request,
    body: GuideRequest,
    x_anthropic_api_key: str | None = Header(default=None),
) -> GuideResponse:
    """Expand a prior analysis into a full interview training guide (PDF)."""
    if not body.interview_prep.likely_questions and not body.interview_prep.talking_points:
        raise HTTPException(
            status_code=400,
            detail="Interview prep is required to build a guide.",
        )

    use_case: PrepareInterviewGuideUseCase = _select_use_case(
        request, x_anthropic_api_key, PrepareInterviewGuideUseCase
    )
    guide_input = to_guide_input(body)
    try:
        result = await run_in_threadpool(use_case.execute, guide_input)
    except CoachError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    name = body.rewritten_cv.full_name if body.rewritten_cv else None
    return guide_to_response(result, name)
