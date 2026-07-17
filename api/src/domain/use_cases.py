"""Application use cases — the orchestration of the domain's ports."""

from __future__ import annotations

from dataclasses import dataclass

from .entities import CoachingResult, GuideInput, InterviewGuide
from .ports import CvCoachService, PdfRenderer


@dataclass
class RewriteCvResult:
    """The full output of one rewrite request.

    ``pdf`` is ``None`` when the coach declined to rewrite the CV (score < 40),
    mirroring ``CoachingResult.rewritten_cv``.
    """

    coaching: CoachingResult
    pdf: bytes | None


class RewriteCvUseCase:
    """Analyse a CV + JD, then render the rewritten CV to PDF when one exists."""

    def __init__(self, coach: CvCoachService, renderer: PdfRenderer) -> None:
        self._coach = coach
        self._renderer = renderer

    def execute(self, cv_pdf: bytes, job_description: str) -> RewriteCvResult:
        coaching = self._coach.analyze(cv_pdf, job_description)

        pdf: bytes | None = None
        if coaching.rewritten_cv is not None:
            pdf = self._renderer.render(coaching.rewritten_cv)

        return RewriteCvResult(coaching=coaching, pdf=pdf)


@dataclass
class InterviewGuideResult:
    """A generated interview guide and its rendered PDF."""

    guide: InterviewGuide
    pdf: bytes


class PrepareInterviewGuideUseCase:
    """Expand a prior analysis into an interview guide and render it to PDF."""

    def __init__(self, coach: CvCoachService, renderer: PdfRenderer) -> None:
        self._coach = coach
        self._renderer = renderer

    def execute(self, request: GuideInput) -> InterviewGuideResult:
        guide = self._coach.prepare_interview_guide(request)
        pdf = self._renderer.render_guide(guide)
        return InterviewGuideResult(guide=guide, pdf=pdf)
