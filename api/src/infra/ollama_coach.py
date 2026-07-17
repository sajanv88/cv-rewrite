"""``CvCoachService`` adapter backed by a local Ollama model.

Unlike Claude, local models can't take a native PDF document block, so the CV's
text is extracted first (``pdf_text``) and sent inline. Responses are constrained
with Ollama's structured-output ``format`` (a JSON schema), then validated and
mapped to the domain via the shared schemas.

Quality depends on the chosen model — a capable instruct model that honours JSON
schemas (e.g. a recent Llama / Qwen / Mistral) is recommended.
"""

from __future__ import annotations

from typing import TypeVar

import httpx
import ollama
from pydantic import BaseModel, ValidationError

from src.domain.entities import CoachingResult, GuideInput, InterviewGuide

from .coaching_schema import CoachError, USER_INSTRUCTIONS, _CoachingResult, to_domain
from .guide_schema import _InterviewGuide, build_guide_prompt, guide_to_domain
from .pdf_text import extract_pdf_text
from .prompts import load_system_prompt

_M = TypeVar("_M", bound=BaseModel)


class OllamaCvCoach:
    """Concrete ``CvCoachService`` using a local Ollama model with JSON output."""

    def __init__(self, host: str, model: str, num_ctx: int = 8192) -> None:
        self._host = host or "http://localhost:11434"
        self._client = ollama.Client(host=host or None)
        self._model = model
        self._num_ctx = num_ctx
        self._system = load_system_prompt()

    def analyze(self, cv_pdf: bytes, job_description: str) -> CoachingResult:
        cv_text = extract_pdf_text(cv_pdf)
        if not cv_text:
            raise CoachError(
                "Could not extract any text from the CV PDF. If it's a scanned "
                "image, the local model can't read it — use the Anthropic provider."
            )

        user = (
            "The candidate's CV (extracted from their PDF) is provided below, "
            "followed by the job description.\n\n"
            f"=== CV ===\n{cv_text}\n\n"
            + USER_INSTRUCTIONS.format(job_description=job_description)
        )
        return to_domain(self._chat_json(user, _CoachingResult, "coaching result"))

    def prepare_interview_guide(self, request: GuideInput) -> InterviewGuide:
        user = build_guide_prompt(request)
        return guide_to_domain(self._chat_json(user, _InterviewGuide, "interview guide"))

    # -- shared structured-chat helper -------------------------------------- #

    def _chat_json(self, user: str, schema: type[_M], what: str) -> _M:
        """Run one structured chat and validate the JSON reply against ``schema``."""
        try:
            response = self._client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system},
                    {"role": "user", "content": user},
                ],
                format=schema.model_json_schema(),
                options={"temperature": 0, "num_ctx": self._num_ctx},
            )
        except ollama.ResponseError as exc:  # model missing, bad request, etc.
            raise CoachError(f"Ollama error: {exc}") from exc
        except (httpx.HTTPError, ConnectionError) as exc:  # daemon unreachable
            raise CoachError(
                f"Could not reach Ollama at {self._host}. "
                "Is `ollama serve` running and the model pulled?"
            ) from exc

        content = (response.message.content or "").strip()
        if not content:
            raise CoachError("The Ollama model returned an empty response.")

        try:
            return schema.model_validate_json(content)
        except ValidationError as exc:
            raise CoachError(
                f"The Ollama model did not return a valid {what}: {exc}"
            ) from exc
