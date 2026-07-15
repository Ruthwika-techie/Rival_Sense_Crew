"""
config.py – Application-wide settings loaded from environment variables.

All values can be overridden by a .env file in the project root.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ─────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., description="OpenAI / OpenRouter API key")
    openai_base_url: Optional[str] = Field(
        default=None, description="Override base URL for OpenRouter etc."
    )
    llm_model: str = Field(
        default="openai/gpt-4o-mini", description="Model identifier"
    )

    # ── Search ───────────────────────────────────────────────────────────────
    tavily_api_key: str = Field(..., description="Tavily search API key")

    # ── Scraping ─────────────────────────────────────────────────────────────
    firecrawl_api_key: Optional[str] = Field(
        default=None, description="Firecrawl API key (optional)"
    )
    firecrawl_enabled: bool = Field(
        default=False, description="Enable Firecrawl deep scraping"
    )

    # ── Execution limits ─────────────────────────────────────────────────────
    max_sources: int = Field(default=20, ge=1, le=50)
    max_steps: int = Field(default=50, ge=5, le=200)
    max_search_results: int = Field(default=5, ge=1, le=10)
    search_queries_per_run: int = Field(default=4, ge=1, le=10)

    # ── Source quality gate (legacy — superseded by Validator node) ──────────
    min_trusted_sources: int = Field(
        default=2,
        ge=1,
        le=20,
        description=(
            "Legacy fallback minimum trusted sources check in researcher. "
            "Prefer MIN_VALID_SOURCES which is enforced by the Validator node."
        ),
    )

    # ── Validator node ────────────────────────────────────────────────────────
    min_valid_sources: int = Field(
        default=2,
        ge=1,
        le=20,
        description=(
            "Minimum number of valid sources required by the Validator node. "
            "A valid source is non-failed, has a non-empty snippet, and meets "
            "the relevance threshold. If fewer are found, the pipeline stops "
            "before the Analyst with a structured 'No sufficient trusted data' "
            "response."
        ),
    )
    relevance_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum relevance score (0.0–1.0) a source must achieve to be "
            "counted as valid. Relevance is computed as the fraction of topic "
            "keywords found in the source title + snippet (case-insensitive)."
        ),
    )

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with a clean format."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Silence noisy third-party loggers
    for lib in ("httpx", "httpcore", "openai", "langchain", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)
