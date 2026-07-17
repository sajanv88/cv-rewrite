"""Ports — the interfaces the domain depends on, implemented by ``infra``.

Following Clean Architecture, the domain owns these abstractions; the outer
layers provide concrete adapters (Anthropic, fpdf2). The use case is written
against these Protocols and never imports a concrete implementation.
"""

from __future__ import annotations

from typing import Protocol

from .entities import CoachingResult, GuideInput, InterviewGuide, RewrittenCv


class CvCoachService(Protocol):
    """Analyses a CV against a job description and returns structured coaching."""

    def analyze(self, cv_pdf: bytes, job_description: str) -> CoachingResult:
        """Score the CV, and (conditionally) rewrite it and prepare interview tips.

        Args:
            cv_pdf: The candidate's original CV as raw PDF bytes.
            job_description: The target job description as plain text.
        """
        ...

    def prepare_interview_guide(self, request: GuideInput) -> InterviewGuide:
        """Expand a prior analysis into a full, honest interview training guide."""
        ...


class PdfRenderer(Protocol):
    """Renders coaching artefacts into downloadable PDF documents."""

    def render(self, cv: RewrittenCv) -> bytes:
        """Return the rendered CV PDF as raw bytes."""
        ...

    def render_guide(self, guide: InterviewGuide) -> bytes:
        """Return the rendered interview-guide PDF as raw bytes."""
        ...
