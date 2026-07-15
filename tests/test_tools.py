"""
tests/test_tools.py – Unit tests for TavilySearchTool and FirecrawlScraperTool.

All external API calls are mocked — no real network traffic required.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from models import Source


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_settings(**overrides):
    """Return a minimal Settings-like object without touching .env."""
    s = MagicMock()
    s.tavily_api_key = "tvly-test"
    s.firecrawl_api_key = "fc-test"
    s.firecrawl_enabled = False
    s.max_sources = 10
    s.max_search_results = 3
    s.search_queries_per_run = 2
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _tavily_result(url: str, title: str = "Title", content: str = "snippet"):
    return {"url": url, "title": title, "content": content}


# ── TavilySearchTool ──────────────────────────────────────────────────────────

class TestTavilySearchTool:
    def _make_tool(self, **settings_overrides):
        from tools import TavilySearchTool
        tool = TavilySearchTool(_make_settings(**settings_overrides))
        return tool

    def test_search_returns_sources(self):
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                _tavily_result("https://a.com", "A"),
                _tavily_result("https://b.com", "B"),
            ]
        }
        tool._client = mock_client

        sources, error = tool.search("CRM pricing", max_results=3)
        assert error is None
        assert len(sources) == 2
        assert sources[0].url == "https://a.com"
        assert sources[0].title == "A"
        assert not sources[0].failed

    def test_search_handles_failure(self):
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API timeout")
        tool._client = mock_client

        sources, error = tool.search("bad query")
        assert sources == []
        assert "API timeout" in error

    def test_multi_search_deduplicates(self):
        tool = self._make_tool(max_sources=10)
        mock_client = MagicMock()
        # Both queries return the same URL
        mock_client.search.return_value = {
            "results": [_tavily_result("https://duplicate.com")]
        }
        tool._client = mock_client

        good, failed = tool.multi_search(["query1", "query2"])
        urls = [s.url for s in good]
        assert urls.count("https://duplicate.com") == 1, "Duplicates should be removed"

    def test_multi_search_respects_source_cap(self):
        tool = self._make_tool(max_sources=2)
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                _tavily_result(f"https://source{i}.com") for i in range(5)
            ]
        }
        tool._client = mock_client

        good, _ = tool.multi_search(["q1", "q2"], max_total_sources=2)
        assert len(good) <= 2

    def test_multi_search_tracks_failed(self):
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("network error")
        tool._client = mock_client

        good, failed = tool.multi_search(["failing query"])
        assert good == []
        assert len(failed) == 1
        assert failed[0].failed is True

    def test_snippet_truncation(self):
        from tools import _truncate
        long_text = "x" * 1000
        result = _truncate(long_text, max_chars=100)
        assert len(result) <= 103  # 100 + "…"
        assert result.endswith("…")

    def test_short_text_not_truncated(self):
        from tools import _truncate
        short = "hello world"
        assert _truncate(short) == "hello world"


# ── FirecrawlScraperTool ──────────────────────────────────────────────────────

class TestFirecrawlScraperTool:
    def _make_tool(self, enabled=False, **kwargs):
        from tools import FirecrawlScraperTool
        return FirecrawlScraperTool(_make_settings(firecrawl_enabled=enabled, **kwargs))

    def test_scrape_disabled_returns_empty(self):
        tool = self._make_tool(enabled=False)
        result = tool.scrape("https://example.com")
        assert result == ""

    def test_scrape_enabled_calls_api(self):
        tool = self._make_tool(enabled=True)
        mock_client = MagicMock()
        mock_client.scrape_url.return_value = {"markdown": "# Page content\n\nSome text."}
        tool._client = mock_client

        result = tool.scrape("https://example.com")
        assert "Page content" in result

    def test_scrape_handles_failure_gracefully(self):
        tool = self._make_tool(enabled=True)
        mock_client = MagicMock()
        mock_client.scrape_url.side_effect = Exception("scrape failed")
        tool._client = mock_client

        result = tool.scrape("https://broken.com")
        assert result == ""

    def test_enrich_sources_skips_when_disabled(self):
        tool = self._make_tool(enabled=False)
        sources = [Source(url="https://a.com", snippet="original")]
        enriched = tool.enrich_sources(sources)
        assert enriched[0].snippet == "original"

    def test_enrich_sources_preserves_failed(self):
        tool = self._make_tool(enabled=True)
        mock_client = MagicMock()
        mock_client.scrape_url.return_value = {"markdown": "new content"}
        tool._client = mock_client

        failed_src = Source(url="https://fail.com", failed=True, snippet="old")
        good_src = Source(url="https://ok.com", snippet="old snippet")

        enriched = tool.enrich_sources([failed_src, good_src])
        # Failed source should be unchanged
        assert enriched[0].snippet == "old"
        # Good source should be enriched
        assert "new content" in enriched[1].snippet


# ── build_tools factory ───────────────────────────────────────────────────────

def test_build_tools_returns_pair():
    from tools import build_tools
    settings = _make_settings()
    tavily, firecrawl = build_tools(settings)
    from tools import TavilySearchTool, FirecrawlScraperTool
    assert isinstance(tavily, TavilySearchTool)
    assert isinstance(firecrawl, FirecrawlScraperTool)
