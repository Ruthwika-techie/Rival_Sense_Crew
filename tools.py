"""
tools.py – Search and scraping tools used by the Researcher Agent.

Design principles:
  - Every function returns typed results with source URLs.
  - Source failures are caught, logged, and returned as failed Source objects
    so the caller can skip them gracefully.
  - Configurable limits prevent runaway API usage.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import Settings, get_settings
from models import Source

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(text: str, max_chars: int = 800) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


# ── Tavily Search ─────────────────────────────────────────────────────────────

class TavilySearchTool:
    """
    Wraps the Tavily search API.

    Returns a list of Source objects; failures are logged and returned as
    failed=True so the orchestrator can track them without crashing.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client = None  # lazy init

    def _get_client(self):
        if self._client is None:
            from tavily import TavilyClient  # type: ignore

            self._client = TavilyClient(api_key=self.settings.tavily_api_key)
        return self._client

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _search_raw(self, query: str, max_results: int) -> list:
        client = self._get_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
        )
        return response.get("results", [])

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
    ) -> Tuple[List[Source], Optional[str]]:
        """
        Execute a Tavily search.

        Returns (sources, error_message). If search fails entirely, sources
        is empty and error_message describes the failure.
        """
        max_results = max_results or self.settings.max_search_results
        logger.info("Tavily search: %r (max_results=%d)", query, max_results)

        try:
            raw = self._search_raw(query, max_results)
        except Exception as exc:
            msg = f"Tavily search failed for query '{query}': {exc}"
            logger.warning(msg)
            return [], msg

        sources: List[Source] = []
        for item in raw:
            url = item.get("url", "")
            if not url:
                continue
            sources.append(
                Source(
                    url=url,
                    title=item.get("title", ""),
                    snippet=_truncate(item.get("content", "")),
                )
            )

        logger.info("Tavily returned %d sources for %r", len(sources), query)
        return sources, None

    def multi_search(
        self,
        queries: List[str],
        max_results_per_query: Optional[int] = None,
        max_total_sources: Optional[int] = None,
    ) -> Tuple[List[Source], List[Source]]:
        """
        Run multiple queries and deduplicate by URL.

        Returns (good_sources, failed_sources).
        max_total_sources caps the combined result set.
        """
        max_total = max_total_sources or self.settings.max_sources
        seen_urls: set[str] = set()
        good: List[Source] = []
        failed: List[Source] = []

        for query in queries:
            if len(good) >= max_total:
                logger.info("Source cap (%d) reached — stopping search.", max_total)
                break

            sources, error = self.search(query, max_results_per_query)

            if error:
                failed.append(
                    Source(url="", title=query, snippet=error, failed=True, failure_reason=error)
                )
                continue

            for src in sources:
                if len(good) >= max_total:
                    break
                if src.url not in seen_urls:
                    seen_urls.add(src.url)
                    good.append(src)

        return good, failed


# ── Firecrawl Scraper ─────────────────────────────────────────────────────────

class FirecrawlScraperTool:
    """
    Optional deep-scraping using Firecrawl.

    If FIRECRAWL_ENABLED=false or the key is missing, scrape() is a no-op
    that returns an empty string so the researcher degrades gracefully.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.settings.firecrawl_api_key:
                raise RuntimeError("FIRECRAWL_API_KEY is not set.")
            from firecrawl import FirecrawlApp  # type: ignore

            self._client = FirecrawlApp(api_key=self.settings.firecrawl_api_key)
        return self._client

    def scrape(self, url: str) -> str:
        """
        Scrape a single URL and return clean Markdown text.

        Returns empty string if Firecrawl is disabled or the scrape fails.
        """
        if not self.settings.firecrawl_enabled:
            return ""

        logger.info("Firecrawl scraping: %s", url)
        try:
            client = self._get_client()
            result = client.scrape_url(url, params={"formats": ["markdown"]})
            markdown = result.get("markdown", "")
            return _truncate(markdown, max_chars=3000)
        except Exception as exc:
            logger.warning("Firecrawl failed for %s: %s", url, exc)
            return ""

    def enrich_sources(self, sources: List[Source]) -> List[Source]:
        """
        Attempt to enrich each source's snippet with scraped content.

        Failures are swallowed and the original snippet is preserved.
        """
        if not self.settings.firecrawl_enabled:
            return sources

        enriched = []
        for src in sources:
            if src.failed:
                enriched.append(src)
                continue
            deeper = self.scrape(src.url)
            if deeper:
                src = src.model_copy(update={"snippet": deeper})
            enriched.append(src)
        return enriched


# ── Convenience factory ───────────────────────────────────────────────────────

def build_tools(settings: Optional[Settings] = None):
    """Return (tavily_tool, firecrawl_tool) for use by agents."""
    s = settings or get_settings()
    return TavilySearchTool(s), FirecrawlScraperTool(s)
