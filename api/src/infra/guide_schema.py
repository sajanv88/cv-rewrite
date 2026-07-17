"""Shared contract for the interview-guide generation, used by both adapters.

The wire models are the JSON schema the model fills; ``guide_to_domain`` maps
them to domain entities; ``build_guide_prompt`` turns a ``GuideInput`` into the
user message. The system prompt stays ``cv_coach.md`` so the same honesty rules
(never fabricate) apply.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain import entities as domain
from src.domain.entities import GuideInput, InterviewGuide


# --------------------------------------------------------------------------- #
# Wire models.                                                                 #
# --------------------------------------------------------------------------- #


class _GuideQuestion(BaseModel):
    question: str
    what_they_assess: str = Field(
        description="What the interviewer is really evaluating with this question."
    )
    how_to_answer: str = Field(description="How to structure a strong answer.")
    sample_answer: str = Field(
        description=(
            "A STAR-shaped model answer grounded ONLY in the candidate's real "
            "experience from their CV. Never invent employers, metrics, or skills."
        )
    )


class _GuideStudyItem(BaseModel):
    topic: str
    why_it_matters: str
    how_to_prepare: list[str] = Field(description="Concrete, actionable prep steps.")


class _InterviewGuide(BaseModel):
    headline: str = Field(description="Guide title, e.g. 'Interview Guide — <role> at <company>'.")
    overview: str = Field(description="A short orienting paragraph for the candidate.")
    questions: list[_GuideQuestion]
    star_stories: list[str] = Field(
        description="Ready-to-tell STAR narratives expanded from the candidate's real experience."
    )
    study_plan: list[_GuideStudyItem]
    questions_to_ask: list[str] = Field(
        description="Smart questions the candidate should ask the interviewer."
    )
    day_of_checklist: list[str] = Field(description="Practical day-of-interview tips.")
    company_deep_dive: str | None = Field(
        default=None, description="Company research brief when the JD names a company; else null."
    )


# --------------------------------------------------------------------------- #
# Prompt building.                                                             #
# --------------------------------------------------------------------------- #

_GUIDE_TASK = """\
Using the candidate's analysis below, write a COMPLETE interview-preparation \
training guide for this specific role. Rules:

- Ground every sample answer and STAR story ONLY in the candidate's real \
experience shown in their CV. Never invent employers, roles, metrics, or skills.
- For each likely question: explain what the interviewer is really assessing, \
how to structure a strong answer, and give a concrete STAR-shaped sample answer \
built from the candidate's actual background.
- Turn the candidate's talking points into ready-to-tell STAR narratives.
- Build a study plan from the identified gaps and topics to prepare, with \
concrete actions.
- Add smart questions for the candidate to ask, and a practical day-of checklist.
- Include a company deep-dive only if the job description names a company; \
otherwise set company_deep_dive to null.
"""


def _fmt_cv(cv: domain.RewrittenCv | None) -> str:
    if cv is None:
        return "(no rewritten CV available)"
    lines = [f"Name: {cv.full_name}", f"Summary: {cv.professional_summary}"]
    if cv.experience:
        lines.append("Experience:")
        for e in cv.experience:
            lines.append(f"  - {e.title} at {e.company} ({e.dates})")
            lines.extend(f"      * {b}" for b in e.bullets)
    if cv.skills:
        lines.append("Skills: " + ", ".join(cv.skills))
    if cv.education:
        lines.append("Education: " + "; ".join(
            f"{ed.qualification}, {ed.institution} ({ed.dates})" for ed in cv.education
        ))
    if cv.certifications:
        lines.append("Certifications: " + ", ".join(cv.certifications))
    return "\n".join(lines)


def _fmt_prep(prep: domain.InterviewPrep) -> str:
    lines = []
    if prep.likely_questions:
        lines.append("Likely questions:")
        lines.extend(f"  - {q}" for q in prep.likely_questions)
    if prep.talking_points:
        lines.append("Talking points:")
        lines.extend(f"  - {t}" for t in prep.talking_points)
    if prep.topics_to_prepare:
        lines.append("Topics to prepare:")
        lines.extend(f"  - {t}" for t in prep.topics_to_prepare)
    if prep.company_research:
        lines.append("Company research so far: " + prep.company_research)
    return "\n".join(lines) or "(none)"


def _fmt_gaps(gaps: list[domain.Gap]) -> str:
    if not gaps:
        return "(none)"
    return "\n".join(
        f"  - {g.requirement} — candidate has: {g.candidate_has}"
        + (f" — how to close: {g.how_to_close}" if g.closable and g.how_to_close else " — hard gap")
        for g in gaps
    )


def build_guide_prompt(request: GuideInput) -> str:
    """Assemble the user message for guide generation from the prior analysis."""
    return (
        f"{_GUIDE_TASK}\n"
        f"=== JOB DESCRIPTION ===\n{request.job_description}\n\n"
        f"=== MATCH ===\nOverall score: {request.overall_score}/100 "
        f"(verdict: {request.verdict.value})\n\n"
        f"=== GAPS ===\n{_fmt_gaps(request.gaps)}\n\n"
        f"=== PREP REPORT ===\n{_fmt_prep(request.interview_prep)}\n\n"
        f"=== CANDIDATE CV (honest, already rewritten) ===\n{_fmt_cv(request.rewritten_cv)}\n"
    )


# --------------------------------------------------------------------------- #
# Wire -> domain.                                                              #
# --------------------------------------------------------------------------- #


def guide_to_domain(guide: _InterviewGuide) -> InterviewGuide:
    return InterviewGuide(
        headline=guide.headline,
        overview=guide.overview,
        questions=[
            domain.GuideQuestion(
                question=q.question,
                what_they_assess=q.what_they_assess,
                how_to_answer=q.how_to_answer,
                sample_answer=q.sample_answer,
            )
            for q in guide.questions
        ],
        star_stories=list(guide.star_stories),
        study_plan=[
            domain.GuideStudyItem(
                topic=s.topic,
                why_it_matters=s.why_it_matters,
                how_to_prepare=list(s.how_to_prepare),
            )
            for s in guide.study_plan
        ],
        questions_to_ask=list(guide.questions_to_ask),
        day_of_checklist=list(guide.day_of_checklist),
        company_deep_dive=guide.company_deep_dive,
    )
