"""Punq dependency-injection container — wires ports to their adapters."""

from __future__ import annotations

import logging

import punq

from src.domain.ports import CvCoachService, PdfRenderer
from src.domain.use_cases import PrepareInterviewGuideUseCase, RewriteCvUseCase
from src.infra.anthropic_coach import AnthropicCvCoach
from src.infra.ollama_coach import OllamaCvCoach
from src.infra.pdf_renderer import Fpdf2Renderer
from src.infra.settings import Settings

logger = logging.getLogger(__name__)


def _build_coach(settings: Settings) -> CvCoachService:
    """Pick the CV-coach adapter for the resolved LLM provider."""
    provider = settings.resolve_provider()
    if provider == "ollama":
        logger.info("LLM provider: ollama (model=%s, host=%s)", settings.ollama_model, settings.ollama_host)
        return OllamaCvCoach(
            host=settings.ollama_host,
            model=settings.ollama_model,
            num_ctx=settings.ollama_num_ctx,
        )

    logger.info("LLM provider: anthropic (model=%s)", settings.anthropic_model)
    return AnthropicCvCoach(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        max_tokens=settings.max_tokens,
    )


def build_container(settings: Settings | None = None) -> punq.Container:
    """Build the application container.

    Binds the domain's ports (`CvCoachService`, `PdfRenderer`) to their concrete
    infrastructure adapters and registers the use case, whose constructor
    dependencies are resolved by type. The coach adapter is chosen at build time
    from ``settings.resolve_provider()`` (Anthropic or Ollama).
    """
    settings = settings or Settings()

    container = punq.Container()
    container.register(Settings, instance=settings)
    container.register(CvCoachService, instance=_build_coach(settings))
    container.register(PdfRenderer, instance=Fpdf2Renderer())
    container.register(RewriteCvUseCase)
    container.register(PrepareInterviewGuideUseCase)
    return container
