"""Application settings, loaded from the environment / a ``.env`` file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values are read from environment variables (case-insensitive) or a local
    ``.env`` file. ``ANTHROPIC_API_KEY`` is the only value you must supply.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider: "auto" (default), "anthropic", or "ollama".
    #   auto  -> Anthropic when ANTHROPIC_API_KEY is set, otherwise Ollama.
    #   anthropic / ollama -> force that provider.
    llm_provider: str = "auto"

    # Anthropic (cloud)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 16000

    # Ollama (local). Used when the resolved provider is "ollama". The model must
    # already be pulled (`ollama pull <model>`). num_ctx must be large enough to
    # hold the CV text + job description + schema.
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_num_ctx: int = 8192

    def resolve_provider(self) -> str:
        """The concrete provider to use, applying the 'auto' rule."""
        provider = self.llm_provider.strip().lower()
        if provider in ("anthropic", "ollama"):
            return provider
        # auto: prefer Anthropic when a key is configured, else fall back to Ollama.
        return "anthropic" if self.anthropic_api_key.strip() else "ollama"

   
    static_dir: str = "static"

   
    cors_origins: list[str] = []
