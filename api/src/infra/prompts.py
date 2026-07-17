"""Loads the CV-coach system prompt from ``cv_coach.md``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# api/src/infra/prompts.py -> parents[2] == api/
_PROMPT_PATH = Path(__file__).resolve().parents[2] / "cv_coach.md"


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Return the cv-coach system prompt (cached after first read)."""
    return _PROMPT_PATH.read_text(encoding="utf-8")
