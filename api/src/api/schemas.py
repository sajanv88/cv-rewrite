"""API DTOs (Pydantic) and mapping from domain objects to the response shape."""

from __future__ import annotations

import base64

from pydantic import BaseModel

from src.domain import entities as domain
from src.domain.entities import (
    CoachingResult,
    GuideInput,
    InterviewPrep,
    RewrittenCv,
    ScoreReport,
    Verdict,
)
from src.domain.use_cases import InterviewGuideResult, RewriteCvResult


class ScoreDimensionDTO(BaseModel):
    name: str
    weight: int
    score: float


class GapDTO(BaseModel):
    requirement: str
    candidate_has: str
    closable: bool
    how_to_close: str


class ScoreReportDTO(BaseModel):
    overall_score: int
    verdict: str
    dimensions: list[ScoreDimensionDTO]
    why_apply: list[str]
    why_think_twice: list[str]
    gaps: list[GapDTO]
    ats_flags: list[str]


class ExperienceEntryDTO(BaseModel):
    title: str
    company: str
    dates: str
    bullets: list[str]


class EducationEntryDTO(BaseModel):
    qualification: str
    institution: str
    dates: str


class RewrittenCvDTO(BaseModel):
    full_name: str
    contact: str
    professional_summary: str
    experience: list[ExperienceEntryDTO]
    skills: list[str]
    education: list[EducationEntryDTO]
    certifications: list[str]
    rewrite_note: str


class InterviewPrepDTO(BaseModel):
    likely_questions: list[str]
    talking_points: list[str]
    topics_to_prepare: list[str]
    company_research: str | None = None


class RewriteResponse(BaseModel):
    """The response for ``POST /api/rewrite``.

    ``rewritten_cv`` / ``pdf_base64`` are null when the score is below 40, and
    ``interview_prep`` is null when the score is below 70.
    """

    score_report: ScoreReportDTO
    rewritten_cv: RewrittenCvDTO | None = None
    interview_prep: InterviewPrepDTO | None = None
    pdf_base64: str | None = None
    pdf_filename: str | None = None


# --------------------------------------------------------------------------- #
# Domain -> DTO mapping.                                                       #
# --------------------------------------------------------------------------- #


def _score_report_dto(report: ScoreReport) -> ScoreReportDTO:
    return ScoreReportDTO(
        overall_score=report.overall_score,
        verdict=report.verdict.value,
        dimensions=[
            ScoreDimensionDTO(name=d.name, weight=d.weight, score=d.score)
            for d in report.dimensions
        ],
        why_apply=report.why_apply,
        why_think_twice=report.why_think_twice,
        gaps=[
            GapDTO(
                requirement=g.requirement,
                candidate_has=g.candidate_has,
                closable=g.closable,
                how_to_close=g.how_to_close,
            )
            for g in report.gaps
        ],
        ats_flags=report.ats_flags,
    )


def _cv_dto(cv: RewrittenCv) -> RewrittenCvDTO:
    return RewrittenCvDTO(
        full_name=cv.full_name,
        contact=cv.contact,
        professional_summary=cv.professional_summary,
        experience=[
            ExperienceEntryDTO(
                title=e.title, company=e.company, dates=e.dates, bullets=e.bullets
            )
            for e in cv.experience
        ],
        skills=cv.skills,
        education=[
            EducationEntryDTO(
                qualification=ed.qualification,
                institution=ed.institution,
                dates=ed.dates,
            )
            for ed in cv.education
        ],
        certifications=cv.certifications,
        rewrite_note=cv.rewrite_note,
    )


def _prep_dto(prep: InterviewPrep) -> InterviewPrepDTO:
    return InterviewPrepDTO(
        likely_questions=prep.likely_questions,
        talking_points=prep.talking_points,
        topics_to_prepare=prep.topics_to_prepare,
        company_research=prep.company_research,
    )


def _filename_for(cv: RewrittenCv) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in cv.full_name).strip("_")
    return f"{safe or 'candidate'}_CV.pdf"


def to_response(result: RewriteCvResult) -> RewriteResponse:
    coaching: CoachingResult = result.coaching
    cv = coaching.rewritten_cv

    return RewriteResponse(
        score_report=_score_report_dto(coaching.score_report),
        rewritten_cv=_cv_dto(cv) if cv is not None else None,
        interview_prep=(
            _prep_dto(coaching.interview_prep)
            if coaching.interview_prep is not None
            else None
        ),
        pdf_base64=(
            base64.standard_b64encode(result.pdf).decode("ascii")
            if result.pdf is not None
            else None
        ),
        pdf_filename=_filename_for(cv) if cv is not None else None,
    )


# --------------------------------------------------------------------------- #
# Interview guide — request (client sends prior results back) and response.    #
# --------------------------------------------------------------------------- #


class GuideRequest(BaseModel):
    """Context for ``POST /api/interview-guide``.

    The app is stateless, so the client sends back the pieces of the prior
    analysis it already holds. ``interview_prep`` is required (the guide expands
    it); ``rewritten_cv`` grounds the sample answers in real experience.
    """

    job_description: str
    score_report: ScoreReportDTO
    interview_prep: InterviewPrepDTO
    rewritten_cv: RewrittenCvDTO | None = None


class GuideResponse(BaseModel):
    pdf_base64: str
    pdf_filename: str


def _gap_to_domain(g: GapDTO) -> domain.Gap:
    return domain.Gap(
        requirement=g.requirement,
        candidate_has=g.candidate_has,
        closable=g.closable,
        how_to_close=g.how_to_close,
    )


def _prep_to_domain(p: InterviewPrepDTO) -> domain.InterviewPrep:
    return domain.InterviewPrep(
        likely_questions=list(p.likely_questions),
        talking_points=list(p.talking_points),
        topics_to_prepare=list(p.topics_to_prepare),
        company_research=p.company_research,
    )


def _cv_to_domain(cv: RewrittenCvDTO) -> domain.RewrittenCv:
    return domain.RewrittenCv(
        full_name=cv.full_name,
        contact=cv.contact,
        professional_summary=cv.professional_summary,
        experience=[
            domain.ExperienceEntry(
                title=e.title, company=e.company, dates=e.dates, bullets=list(e.bullets)
            )
            for e in cv.experience
        ],
        skills=list(cv.skills),
        education=[
            domain.EducationEntry(
                qualification=ed.qualification,
                institution=ed.institution,
                dates=ed.dates,
            )
            for ed in cv.education
        ],
        certifications=list(cv.certifications),
        rewrite_note=cv.rewrite_note,
    )


def to_guide_input(req: GuideRequest) -> GuideInput:
    return GuideInput(
        job_description=req.job_description,
        overall_score=req.score_report.overall_score,
        verdict=Verdict(req.score_report.verdict),
        interview_prep=_prep_to_domain(req.interview_prep),
        gaps=[_gap_to_domain(g) for g in req.score_report.gaps],
        rewritten_cv=_cv_to_domain(req.rewritten_cv) if req.rewritten_cv else None,
    )


def _guide_filename(name: str | None) -> str:
    base = "".join(c if c.isalnum() else "_" for c in (name or "")).strip("_")
    return f"{base or 'candidate'}_interview_guide.pdf"


def guide_to_response(result: InterviewGuideResult, candidate_name: str | None) -> GuideResponse:
    return GuideResponse(
        pdf_base64=base64.standard_b64encode(result.pdf).decode("ascii"),
        pdf_filename=_guide_filename(candidate_name),
    )
