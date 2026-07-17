"""Shared coaching contract for the LLM adapters.

The "wire" models are the JSON schema the model is constrained to fill (via
Anthropic structured outputs or Ollama's ``format``). Both the Anthropic and
Ollama adapters fill the *same* schema and map it to the framework-free domain
entities with :func:`to_domain`, so the two providers are interchangeable behind
the ``CvCoachService`` port.

Field descriptions are part of the schema and guide the model.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from src.domain import entities as domain
from src.domain.entities import CoachingResult


class CoachError(RuntimeError):
    """Raised when a model fails to return a usable coaching result."""


# --------------------------------------------------------------------------- #
# Wire models — the JSON schema the model is constrained to fill.             #
# --------------------------------------------------------------------------- #


class _Verdict(str, Enum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    WEAK = "WEAK"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class _ScoreDimension(BaseModel):
    name: str = Field(description="Dimension name, e.g. 'Core skills match'.")
    weight: int = Field(description="Percentage weight of this dimension (0-100).")
    score: float = Field(description="Score for this dimension, 0-10.")


class _Gap(BaseModel):
    requirement: str = Field(description="What the job description requires.")
    candidate_has: str = Field(description="What the candidate has instead.")
    closable: bool = Field(description="Whether this gap can realistically be closed.")
    how_to_close: str = Field(
        description="How to close it, or an empty string if not closable."
    )


class _ScoreReport(BaseModel):
    overall_score: int = Field(description="Weighted total score, 0-100.")
    verdict: _Verdict
    dimensions: list[_ScoreDimension]
    why_apply: list[str] = Field(description="Genuine strengths that map to the JD.")
    why_think_twice: list[str] = Field(description="Honest gaps or risks.")
    gaps: list[_Gap]
    ats_flags: list[str] = Field(
        description="Formatting/keyword/parse risks for ATS systems."
    )


class _ExperienceEntry(BaseModel):
    title: str
    company: str
    dates: str
    bullets: list[str] = Field(
        description="Action verb + task + method + result bullets. No invented metrics."
    )


class _EducationEntry(BaseModel):
    qualification: str
    institution: str
    dates: str


class _RewrittenCv(BaseModel):
    full_name: str
    contact: str = Field(description="Single-line contact info (email, phone, links).")
    professional_summary: str = Field(description="3-4 line summary written for this JD.")
    experience: list[_ExperienceEntry]
    skills: list[str] = Field(description="Skills, JD-relevant ones first.")
    education: list[_EducationEntry]
    certifications: list[str]
    rewrite_note: str = Field(
        description="Honest note on omitted experience or CV sections lacking metrics."
    )


class _InterviewPrep(BaseModel):
    likely_questions: list[str]
    talking_points: list[str] = Field(description="STAR-story starters from the CV.")
    topics_to_prepare: list[str]
    company_research: str | None = Field(
        default=None, description="Research brief when the JD names a company; else null."
    )


class _CoachingResult(BaseModel):
    score_report: _ScoreReport
    rewritten_cv: _RewrittenCv | None = Field(
        default=None, description="The rewritten CV. Null when the score is below 40."
    )
    interview_prep: _InterviewPrep | None = Field(
        default=None, description="Interview prep. Null when the score is below 70."
    )


# The task instructions shared by both providers. Each adapter supplies the CV
# to the model in the way that provider supports (Anthropic: a PDF document
# block; Ollama: extracted text appended below), then formats in the JD.
USER_INSTRUCTIONS = (
    "Analyze the CV against the job description below, following every rule in "
    "your instructions. Return the score report always. Include the rewritten CV "
    "only when the overall score is 40 or above (otherwise set rewritten_cv to "
    "null), and interview prep only when the score is 70 or above (otherwise set "
    "interview_prep to null).\n\n"
    "Job description:\n{job_description}"
)


# --------------------------------------------------------------------------- #
# Wire -> domain mapping.                                                      #
# --------------------------------------------------------------------------- #


def to_domain(result: _CoachingResult) -> CoachingResult:
    return CoachingResult(
        score_report=_score_report_to_domain(result.score_report),
        rewritten_cv=(
            _cv_to_domain(result.rewritten_cv)
            if result.rewritten_cv is not None
            else None
        ),
        interview_prep=(
            _prep_to_domain(result.interview_prep)
            if result.interview_prep is not None
            else None
        ),
    )


def _score_report_to_domain(report: _ScoreReport) -> domain.ScoreReport:
    return domain.ScoreReport(
        overall_score=report.overall_score,
        verdict=domain.Verdict(report.verdict.value),
        dimensions=[
            domain.ScoreDimension(name=d.name, weight=d.weight, score=d.score)
            for d in report.dimensions
        ],
        why_apply=list(report.why_apply),
        why_think_twice=list(report.why_think_twice),
        gaps=[
            domain.Gap(
                requirement=g.requirement,
                candidate_has=g.candidate_has,
                closable=g.closable,
                how_to_close=g.how_to_close,
            )
            for g in report.gaps
        ],
        ats_flags=list(report.ats_flags),
    )


def _cv_to_domain(cv: _RewrittenCv) -> domain.RewrittenCv:
    return domain.RewrittenCv(
        full_name=cv.full_name,
        contact=cv.contact,
        professional_summary=cv.professional_summary,
        experience=[
            domain.ExperienceEntry(
                title=e.title,
                company=e.company,
                dates=e.dates,
                bullets=list(e.bullets),
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


def _prep_to_domain(prep: _InterviewPrep) -> domain.InterviewPrep:
    return domain.InterviewPrep(
        likely_questions=list(prep.likely_questions),
        talking_points=list(prep.talking_points),
        topics_to_prepare=list(prep.topics_to_prepare),
        company_research=prep.company_research,
    )
