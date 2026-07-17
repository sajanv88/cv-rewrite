"""``CvCoachService`` adapter backed by the Anthropic API.

The candidate's CV is sent to Claude as a native PDF document block (no separate
parser needed), together with the job description. The response is constrained to
a JSON schema via structured outputs (``messages.parse``), so we get a validated
object back rather than free-form markdown. The shared wire schema and the
domain mapping live in ``coaching_schema``.
"""

from __future__ import annotations

import base64

import anthropic

from src.domain.entities import CoachingResult, GuideInput, InterviewGuide

from .coaching_schema import CoachError, USER_INSTRUCTIONS, _CoachingResult, to_domain
from .guide_schema import _InterviewGuide, build_guide_prompt, guide_to_domain
from .prompts import load_system_prompt

# Anthropic accepts the CV as a PDF document block, so the instructions refer to
# the attached document rather than inline text.
_USER_INSTRUCTIONS = "Analyze the attached CV (PDF).\n\n" + USER_INSTRUCTIONS


class AnthropicCvCoach:
    """Concrete ``CvCoachService`` using Claude with structured JSON output."""

    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        # An empty key would *shadow* an ANTHROPIC_API_KEY env var / `ant` profile,
        # so fall back to None and let the SDK resolve credentials itself.
        self._client = anthropic.Anthropic(api_key=api_key or None)
        self._model = model
        self._max_tokens = max_tokens
        self._system = load_system_prompt()

    def analyze(self, cv_pdf: bytes, job_description: str) -> CoachingResult:
        cv_b64 = base64.standard_b64encode(cv_pdf).decode("utf-8")

        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self._system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": cv_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": _USER_INSTRUCTIONS.format(
                                    job_description=job_description
                                ),
                            },
                        ],
                    }
                ],
                output_format=_CoachingResult,
            )
        except anthropic.APIError as exc:  # network/auth/rate-limit/etc.
            raise CoachError(f"Anthropic API error: {exc}") from exc

        if response.stop_reason == "refusal":
            raise CoachError("The model declined to process this request.")

        parsed = response.parsed_output
        if parsed is None:
            raise CoachError(
                "The model did not return a valid coaching result "
                f"(stop_reason={response.stop_reason})."
            )

        return to_domain(parsed)

    def prepare_interview_guide(self, request: GuideInput) -> InterviewGuide:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self._system,
                messages=[{"role": "user", "content": build_guide_prompt(request)}],
                output_format=_InterviewGuide,
            )
        except anthropic.APIError as exc:
            raise CoachError(f"Anthropic API error: {exc}") from exc

        if response.stop_reason == "refusal":
            raise CoachError("The model declined to build the interview guide.")

        parsed = response.parsed_output
        if parsed is None:
            raise CoachError(
                "The model did not return a valid interview guide "
                f"(stop_reason={response.stop_reason})."
            )

        return guide_to_domain(parsed)
