"""
tests/test_models.py – Unit tests for Pydantic models and shared state.
"""

import pytest
from datetime import datetime

from models import (
    AgentStatus,
    AnalysisResult,
    BriefingOutput,
    BriefingState,
    Citation,
    ClaimVerification,
    Insight,
    MarketSignal,
    PricingMove,
    ProductLaunch,
    ResearchItem,
    ResearchResult,
    RunMetadata,
    Source,
)


# ── Source ────────────────────────────────────────────────────────────────────

class TestSource:
    def test_basic_creation(self):
        src = Source(url="https://example.com", title="Test", snippet="content")
        assert src.url == "https://example.com"
        assert not src.failed

    def test_url_coercion(self):
        """HttpUrl objects should be coerced to plain strings."""
        src = Source(url="https://example.com/path?q=1")
        assert isinstance(src.url, str)

    def test_failed_source(self):
        src = Source(url="", title="broken", failed=True, failure_reason="timeout")
        assert src.failed
        assert src.failure_reason == "timeout"

    def test_defaults(self):
        src = Source(url="https://example.com")
        assert src.title == ""
        assert src.snippet == ""
        assert isinstance(src.retrieved_at, datetime)


# ── Citation ──────────────────────────────────────────────────────────────────

class TestCitation:
    def test_verified_citation(self):
        c = Citation(claim="Some fact", sources=["https://a.com"])
        assert c.verified == ClaimVerification.VERIFIED
        assert len(c.sources) == 1

    def test_unverified_citation(self):
        c = Citation(claim="Dubious claim", sources=[], verified=ClaimVerification.UNVERIFIED)
        assert c.verified == ClaimVerification.UNVERIFIED


# ── ResearchItem ──────────────────────────────────────────────────────────────

class TestResearchItem:
    def test_valid_item(self):
        item = ResearchItem(
            category="pricing",
            content="Competitor X cut prices 10%.",
            source_urls=["https://source.com"],
        )
        assert item.category == "pricing"
        assert item.confidence == 1.0

    def test_requires_source_url(self):
        with pytest.raises(Exception):
            ResearchItem(category="pricing", content="No URL.", source_urls=[])

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ResearchItem(
                category="pricing", content="Bad confidence",
                source_urls=["https://x.com"], confidence=1.5
            )


# ── ResearchResult ────────────────────────────────────────────────────────────

class TestResearchResult:
    def test_empty_result(self):
        r = ResearchResult(topic="CRM market")
        assert r.items == []
        assert r.sources == []
        assert r.total_sources_collected == 0

    def test_with_items(self):
        items = [
            ResearchItem(
                category="market_signal",
                content="Market growing 20% YoY.",
                source_urls=["https://report.com"],
            )
        ]
        r = ResearchResult(topic="CRM", items=items, total_sources_collected=1)
        assert len(r.items) == 1


# ── AnalysisResult ────────────────────────────────────────────────────────────

class TestAnalysisResult:
    def test_empty_analysis(self):
        a = AnalysisResult(topic="CRM")
        assert a.pricing_moves == []
        assert a.recommendation == ""
        assert a.unverified_claims_omitted == 0

    def test_full_analysis(self):
        pm = PricingMove(
            competitor="Acme",
            description="Cut prices 15%",
            citations=[Citation(claim="Cut prices", sources=["https://acme.com/blog"])],
        )
        pl = ProductLaunch(
            competitor="Acme",
            product_name="AcmeAI",
            description="New AI feature",
            citations=[],
        )
        ms = MarketSignal(
            signal="Category growth",
            detail="14% YoY growth",
            citations=[],
        )
        a = AnalysisResult(
            topic="CRM",
            pricing_moves=[pm],
            product_launches=[pl],
            market_signals=[ms],
            recommendation="Revisit entry pricing.",
        )
        assert len(a.pricing_moves) == 1
        assert len(a.product_launches) == 1
        assert len(a.market_signals) == 1
        assert a.recommendation == "Revisit entry pricing."


# ── RunMetadata ───────────────────────────────────────────────────────────────

class TestRunMetadata:
    def test_defaults(self):
        m = RunMetadata()
        assert m.coordinator_status == AgentStatus.PENDING
        assert m.steps_taken == 0
        assert m.all_claims_cited is True
        assert len(m.run_id) == 8  # uuid4 first 8 chars

    def test_duration_calculation(self):
        start = datetime(2025, 1, 1, 10, 0, 0)
        end = datetime(2025, 1, 1, 10, 2, 41)
        m = RunMetadata(started_at=start, completed_at=end)
        m.duration_seconds = (end - start).total_seconds()
        assert m.duration_seconds == 161.0

    def test_serialisation(self):
        m = RunMetadata(topic="Test")
        d = m.model_dump(mode="json")
        assert d["topic"] == "Test"
        assert "run_id" in d


# ── BriefingOutput ────────────────────────────────────────────────────────────

class TestBriefingOutput:
    def test_minimal_briefing(self):
        meta = RunMetadata(topic="test")
        b = BriefingOutput(run_metadata=meta)
        assert b.executive_summary == ""
        assert b.raw_markdown == ""

    def test_full_briefing(self):
        meta = RunMetadata(topic="CRM", steps_taken=4)
        b = BriefingOutput(
            run_metadata=meta,
            executive_summary="Two rivals cut prices.",
            raw_markdown="# Brief\n\n## Summary\nTwo rivals cut prices.",
        )
        assert "rivals" in b.executive_summary
        assert b.run_metadata.steps_taken == 4


# ── BriefingState TypedDict ───────────────────────────────────────────────────

class TestBriefingState:
    def test_state_construction(self):
        """BriefingState is a TypedDict — verify it accepts valid keys."""
        state: BriefingState = {
            "topic": "AI tools",
            "step_count": 0,
            "max_steps": 50,
            "max_sources": 20,
            "abort": False,
            "abort_reason": "",
            "errors": [],
        }
        assert state["topic"] == "AI tools"
        assert state["abort"] is False
