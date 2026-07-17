"""Core domain entities for the CV-rewriting problem.

Pure Python — no framework imports. These types are the vocabulary the rest of
the application speaks in. The AI adapter, the PDF renderer, and the API layer
all convert to and from these; nothing here knows those layers exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """Overall recommendation, mirroring the thresholds in ``cv_coach.md``."""

    STRONG = "STRONG"  # 80-100 → rewrite + interview prep
    PARTIAL = "PARTIAL"  # 60-79  → rewrite + flag gaps
    WEAK = "WEAK"  # 40-59  → rewrite what we can, be honest about gaps
    NOT_RECOMMENDED = "NOT_RECOMMENDED"  # <40 → no rewrite


@dataclass
class ScoreDimension:
    """One scored row of the match-scoring table."""

    name: str
    weight: int  # percentage weight (e.g. 30 for "Core skills match")
    score: float  # 0-10


@dataclass
class Gap:
    """A JD requirement the candidate does not fully meet."""

    requirement: str  # what the JD asks for
    candidate_has: str  # what the candidate has instead
    closable: bool
    how_to_close: str  # empty string when not closable


@dataclass
class ScoreReport:
    """The honest assessment of the candidate against the job description."""

    overall_score: int  # weighted total, 0-100
    verdict: Verdict
    dimensions: list[ScoreDimension] = field(default_factory=list)
    why_apply: list[str] = field(default_factory=list)
    why_think_twice: list[str] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    ats_flags: list[str] = field(default_factory=list)


@dataclass
class ExperienceEntry:
    """One role in the rewritten work-experience section."""

    title: str
    company: str
    dates: str
    bullets: list[str] = field(default_factory=list)


@dataclass
class EducationEntry:
    qualification: str
    institution: str
    dates: str


@dataclass
class RewrittenCv:
    """The ATS-safe, single-column CV produced from the original (no lies)."""

    full_name: str
    contact: str
    professional_summary: str
    experience: list[ExperienceEntry] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    rewrite_note: str = ""  # honest note about what was omitted / lacked metrics


@dataclass
class InterviewPrep:
    """Interview preparation, produced only when the score is high enough."""

    likely_questions: list[str] = field(default_factory=list)
    talking_points: list[str] = field(default_factory=list)
    topics_to_prepare: list[str] = field(default_factory=list)
    company_research: str | None = None  # only when the JD names a company


@dataclass
class CoachingResult:
    """Everything the coach produced for one CV / JD pair.

    ``rewritten_cv`` is ``None`` when the score is below 40, and
    ``interview_prep`` is ``None`` when the score is below 70 — exactly the
    conditional outputs described in ``cv_coach.md``.
    """

    score_report: ScoreReport
    rewritten_cv: RewrittenCv | None = None
    interview_prep: InterviewPrep | None = None


# --------------------------------------------------------------------------- #
# Interview training guide — a deeper, PDF-ready expansion of the prep report. #
# --------------------------------------------------------------------------- #


@dataclass
class GuideQuestion:
    """A likely question worked through in detail."""

    question: str
    what_they_assess: str  # what the interviewer is really evaluating
    how_to_answer: str  # approach / structure guidance
    sample_answer: str  # a STAR-shaped model answer grounded in the real CV


@dataclass
class GuideStudyItem:
    """A topic to prepare, with concrete actions."""

    topic: str
    why_it_matters: str
    how_to_prepare: list[str] = field(default_factory=list)


@dataclass
class InterviewGuide:
    """A complete, honest interview-prep training guide for one candidate/role."""

    headline: str
    overview: str
    questions: list[GuideQuestion] = field(default_factory=list)
    star_stories: list[str] = field(default_factory=list)  # ready-to-tell narratives
    study_plan: list[GuideStudyItem] = field(default_factory=list)
    questions_to_ask: list[str] = field(default_factory=list)  # for the candidate to ask
    day_of_checklist: list[str] = field(default_factory=list)
    company_deep_dive: str | None = None  # only when the JD names a company


@dataclass
class GuideInput:
    """Everything the coach needs to build the guide (from a prior analysis).

    The app is stateless, so the client sends this context back from the results
    it already has; nothing is stored server-side.
    """

    job_description: str
    overall_score: int
    verdict: Verdict
    interview_prep: InterviewPrep
    gaps: list[Gap] = field(default_factory=list)
    rewritten_cv: RewrittenCv | None = None
