"""
tests/test_agents.py – Unit tests for all four agent nodes.

All LLM calls, Tavily searches, and Firecrawl scrapes are mocked.
Tests verify routing logic, state mutations, and error handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

from models import (
    AgentStatus,
    AnalysisResult,
    BriefingState,
    ResearchResult,
    ResearchItem,
    RunMetadata,
    Source,
    ValidationResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _base_state(**overrides) -> BriefingState:
    state: BriefingState = {
        "topic": "CRM software market",
        "step_count": 0,
        "max_steps": 50,
        "max_sources": 10,
        "abort": False,
        "abort_reason": "",
        "coordinator_status": "pending",
        "researcher_status": "pending",
        "validator_status": "pending",
        "analyst_status": "pending",
        "writer_status": "pending",
        # validator gate fields
        "validation_failed": False,
        "min_valid_sources": 2,
        "relevance_threshold": 0.3,
        "insufficient_sources": False,
        # agent outputs
        "research_result": None,
        "validation_result": None,
        "analysis_result": None,
        "briefing_output": None,
        "run_metadata": RunMetadata(topic="CRM software market", started_at=datetime.now(timezone.utc)).model_dump(mode="json"),
        "errors": [],
    }
    state.update(overrides)
    return state


def _mock_settings():
    s = MagicMock()
    s.openai_api_key = "sk-test"
    s.openai_base_url = None
    s.llm_model = "gpt-4o-mini"
    s.tavily_api_key = "tvly-test"
    s.firecrawl_enabled = False
    s.firecrawl_api_key = None
    s.max_sources = 10
    s.max_steps = 50
    s.max_search_results = 3
    s.search_queries_per_run = 2
    s.min_trusted_sources = 2
    s.min_valid_sources = 2
    s.relevance_threshold = 0.3
    return s


# ── Coordinator Agent ─────────────────────────────────────────────────────────

class TestCoordinatorNode:
    def test_happy_path(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state())

        assert result["coordinator_status"] == AgentStatus.DONE
        assert result["abort"] is False
        assert result["step_count"] == 1
        assert result["topic"] == "CRM software market"

    def test_empty_topic_aborts(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state(topic=""))

        assert result["abort"] is True
        assert result["coordinator_status"] == AgentStatus.FAILED
        assert "empty" in result["abort_reason"].lower()

    def test_whitespace_topic_aborts(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state(topic="   "))

        assert result["abort"] is True

    def test_step_limit_exceeded_aborts(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state(step_count=99, max_steps=10))

        assert result["abort"] is True
        assert "limit" in result["abort_reason"].lower()

    def test_increments_step_count(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state(step_count=3))

        assert result["step_count"] == 4

    def test_sets_all_agent_statuses(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state())

        assert result["researcher_status"] == AgentStatus.PENDING
        assert result["analyst_status"] == AgentStatus.PENDING
        assert result["writer_status"] == AgentStatus.PENDING

    def test_run_metadata_populated(self):
        from agents.coordinator import coordinator_node
        with patch("agents.coordinator.get_settings", return_value=_mock_settings()):
            result = coordinator_node(_base_state())

        meta = result["run_metadata"]
        assert meta["topic"] == "CRM software market"
        assert "run_id" in meta


# ── Researcher Agent ──────────────────────────────────────────────────────────

class TestResearcherNode:
    def _mock_llm_queries(self):
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(
            content='["CRM pricing 2025", "CRM product launches"]'
        )
        return llm

    def _mock_llm_findings(self):
        findings_json = json.dumps({
            "queries": ["q1"],
            "findings": [
                {
                    "category": "pricing",
                    "content": "Salesforce raised prices 5%.",
                    "source_urls": ["https://salesforce.com/news"],
                }
            ],
        })
        llm = MagicMock()
        llm.invoke.side_effect = [
            MagicMock(content='["CRM pricing 2025"]'),
            MagicMock(content=findings_json),
        ]
        return llm

    def test_skips_on_abort(self):
        from agents.researcher import researcher_node
        result = researcher_node(_base_state(abort=True))
        assert result["researcher_status"] == AgentStatus.SKIPPED

    def test_happy_path(self):
        from agents.researcher import researcher_node

        mock_sources = [Source(url="https://salesforce.com/news", title="SF Blog", snippet="SF raised prices.")]
        mock_tavily = MagicMock()
        mock_tavily.multi_search.return_value = (mock_sources, [])
        mock_firecrawl = MagicMock()
        mock_firecrawl.enrich_sources.return_value = mock_sources

        with patch("agents.researcher.get_settings", return_value=_mock_settings()), \
             patch("agents.researcher._build_llm", return_value=self._mock_llm_findings()), \
             patch("agents.researcher.build_tools", return_value=(mock_tavily, mock_firecrawl)):
            result = researcher_node(_base_state())

        assert result["researcher_status"] == AgentStatus.DONE
        assert result["research_result"] is not None
        rr = ResearchResult.model_validate(result["research_result"])
        assert len(rr.sources) == 1

    def test_search_failure_is_tracked(self):
        from agents.researcher import researcher_node
        from models import Source as Src

        failed_src = Src(url="", title="bad query", failed=True, failure_reason="timeout")
        mock_tavily = MagicMock()
        mock_tavily.multi_search.return_value = ([], [failed_src])
        mock_firecrawl = MagicMock()

        findings_json = json.dumps({"queries": [], "findings": []})
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content='["q1"]'),
            MagicMock(content=findings_json),
        ]

        with patch("agents.researcher.get_settings", return_value=_mock_settings()), \
             patch("agents.researcher._build_llm", return_value=mock_llm), \
             patch("agents.researcher.build_tools", return_value=(mock_tavily, mock_firecrawl)):
            result = researcher_node(_base_state())

        assert "timeout" in " ".join(result["errors"])

    def test_llm_failure_aborts(self):
        from agents.researcher import researcher_node

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM unreachable")

        with patch("agents.researcher.get_settings", return_value=_mock_settings()), \
             patch("agents.researcher._build_llm", return_value=mock_llm), \
             patch("agents.researcher.build_tools", return_value=(MagicMock(), MagicMock())):
            result = researcher_node(_base_state())

        assert result["researcher_status"] == AgentStatus.FAILED
        assert result["abort"] is True


# ── Validator Agent ──────────────────────────────────────────────────────────

class TestValidatorNode:
    """Tests for the deterministic Validator node (no LLM mocking needed)."""

    def _research_with_sources(self, sources=None, items=None) -> dict:
        """Build a research_result dict ready to place in state."""
        if sources is None:
            # Two relevant sources so the default min_valid_sources=2 passes
            sources = [
                Source(
                    url="https://salesforce.com/news",
                    title="Salesforce Blog",
                    snippet="CRM market pricing cuts confirmed by Salesforce in Q1.",
                ),
                Source(
                    url="https://hubspot.com/blog",
                    title="HubSpot CRM News",
                    snippet="HubSpot CRM software market expansion update.",
                ),
            ]
        if items is None:
            items = [
                ResearchItem(
                    category="pricing",
                    content="Salesforce cut starter plan 10%.",
                    source_urls=["https://salesforce.com/news"],
                )
            ]
        rr = ResearchResult(
            topic="CRM software market",
            sources=sources,
            items=items,
        )
        return rr.model_dump(mode="json")

    # ── Baseline happy-path ───────────────────────────────────────────────────

    def test_happy_path_passes_all_rules(self):
        """Valid research with relevant sources and findings -> validation passes."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(research_result=self._research_with_sources())
            )

        assert result["validator_status"] == AgentStatus.DONE
        assert result["validation_failed"] is False
        assert result["validation_result"] is not None
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.passed is True
        assert vr.valid_source_count >= 1
        assert vr.topic_found_in_sources is True

    # ── Abort pass-through ────────────────────────────────────────────────────

    def test_skips_on_abort(self):
        """If abort flag is already set, validator skips without modifying abort."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(_base_state(abort=True, abort_reason="step limit"))

        assert result["validator_status"] == AgentStatus.SKIPPED
        assert result["validation_failed"] is False

    # ── Missing research ──────────────────────────────────────────────────────

    def test_no_research_result_causes_abort(self):
        """Missing research_result must abort the pipeline, not silently pass."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(_base_state(research_result=None))

        assert result["validation_failed"] is True
        assert result["abort"] is True
        assert result["validator_status"] == AgentStatus.FAILED

    # ── AllSourcesFailedRule ──────────────────────────────────────────────────

    def test_all_sources_failed_triggers_rejection(self):
        """If every source is marked failed=True, validation must fail."""
        failed_sources = [
            Source(
                url="https://failed1.com",
                title="Err",
                snippet="",
                failed=True,
                failure_reason="HTTP 503",
            ),
            Source(
                url="https://failed2.com",
                title="Err",
                snippet="",
                failed=True,
                failure_reason="timeout",
            ),
        ]
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    research_result=self._research_with_sources(
                        sources=failed_sources, items=[]
                    )
                )
            )

        assert result["validation_failed"] is True
        assert result["abort"] is True
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.failure_code == "all_sources_failed"

    def test_empty_sources_list_triggers_rejection(self):
        """Zero sources collected is equivalent to all-failed."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    research_result=self._research_with_sources(sources=[], items=[])
                )
            )

        assert result["validation_failed"] is True

    # ── MinValidSourcesRule ───────────────────────────────────────────────────

    def test_insufficient_valid_sources_triggers_rejection(self):
        """Only one valid source when min_valid_sources=2 -> validation fails."""
        one_source = [
            Source(
                url="https://sf.com",
                title="Salesforce Blog",
                snippet="CRM market data from Salesforce.",
            )
        ]
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    min_valid_sources=2,
                    research_result=self._research_with_sources(
                        sources=one_source,
                        items=[
                            ResearchItem(
                                category="pricing",
                                content="SF cut prices.",
                                source_urls=["https://sf.com"],
                            )
                        ],
                    ),
                )
            )

        assert result["validation_failed"] is True
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.failure_code == "insufficient_sources"

    def test_exact_minimum_valid_sources_passes(self):
        """Exactly min_valid_sources valid sources -> rule passes."""
        two_sources = [
            Source(
                url="https://sf.com",
                title="Salesforce",
                snippet="CRM software pricing from Salesforce.",
            ),
            Source(
                url="https://hubspot.com",
                title="HubSpot",
                snippet="HubSpot CRM market update.",
            ),
        ]
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    min_valid_sources=2,
                    research_result=self._research_with_sources(
                        sources=two_sources,
                        items=[
                            ResearchItem(
                                category="pricing",
                                content="CRM pricing updates.",
                                source_urls=["https://sf.com"],
                            )
                        ],
                    ),
                )
            )

        assert result["validation_failed"] is False
        assert result["validator_status"] == AgentStatus.DONE

    # ── TopicRelevanceRule ────────────────────────────────────────────────────

    def test_topic_not_found_in_sources_triggers_rejection(self):
        """Sources with completely unrelated snippets -> TopicRelevanceRule fails."""
        irrelevant_sources = [
            Source(
                url="https://recipes.com",
                title="Cooking Recipes",
                snippet="Best chocolate cake recipe with flour and eggs.",
            ),
            Source(
                url="https://weather.com",
                title="Weather",
                snippet="Sunny skies expected this weekend.",
            ),
        ]
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    topic="CRM software market",
                    min_valid_sources=1,
                    relevance_threshold=0.0,
                    research_result=self._research_with_sources(
                        sources=irrelevant_sources,
                        items=[
                            ResearchItem(
                                category="other",
                                content="Random content.",
                                source_urls=["https://recipes.com"],
                            )
                        ],
                    ),
                )
            )

        assert result["validation_failed"] is True
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.failure_code == "topic_not_found"

    # ── NoFindingsRule ────────────────────────────────────────────────────────

    def test_no_findings_triggers_rejection(self):
        """Sources present but researcher extracted zero findings -> NoFindingsRule fails."""
        good_sources = [
            Source(
                url="https://sf.com",
                title="Salesforce CRM",
                snippet="CRM software pricing Salesforce market update.",
            ),
            Source(
                url="https://hubspot.com",
                title="HubSpot CRM",
                snippet="HubSpot CRM software market share grows.",
            ),
        ]
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    min_valid_sources=1,
                    research_result=self._research_with_sources(
                        sources=good_sources,
                        items=[],
                    ),
                )
            )

        assert result["validation_failed"] is True
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.failure_code == "no_findings"

    # ── State field integrity ─────────────────────────────────────────────────

    def test_step_count_incremented(self):
        """Validator must always increment step_count."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(step_count=3, research_result=self._research_with_sources())
            )

        assert result["step_count"] == 4

    def test_validation_result_stored_on_pass(self):
        """On a passing run, validation_result must be stored in state."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(research_result=self._research_with_sources())
            )

        assert result["validation_result"] is not None
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.passed is True

    def test_validation_result_stored_on_fail(self):
        """On a failing run, validation_result is still persisted for the writer."""
        from agents.validator import validator_node
        with patch("agents.validator.get_settings", return_value=_mock_settings()):
            result = validator_node(
                _base_state(
                    research_result=self._research_with_sources(sources=[], items=[])
                )
            )

        assert result["validation_result"] is not None
        vr = ValidationResult.model_validate(result["validation_result"])
        assert vr.passed is False
        assert vr.failure_reason is not None


# ── Analyst Agent ─────────────────────────────────────────────────────────────

class TestAnalystNode:
    def _research_state(self):
        items = [
            ResearchItem(
                category="pricing",
                content="Salesforce cut starter plan 10%.",
                source_urls=["https://sf.com"],
            )
        ]
        rr = ResearchResult(
            topic="CRM software market",
            items=items,
            sources=[Source(url="https://sf.com", title="SF Blog")],
        )
        return _base_state(research_result=rr.model_dump(mode="json"))

    def _analysis_json(self):
        return json.dumps({
            "pricing_moves": [
                {
                    "competitor": "Salesforce",
                    "description": "Cut starter plan 10%.",
                    "source_urls": ["https://sf.com"],
                }
            ],
            "product_launches": [],
            "market_signals": [],
            "insights": [
                {
                    "type": "opportunity",
                    "title": "Pricing gap",
                    "detail": "Competitor price cut creates opportunity.",
                    "source_urls": ["https://sf.com"],
                }
            ],
            "recommendation": "Revisit our entry pricing.",
            "unverified_claims_omitted": 0,
        })

    def test_skips_on_abort(self):
        from agents.analyst import analyst_node
        result = analyst_node(_base_state(abort=True))
        assert result["analyst_status"] == AgentStatus.SKIPPED

    def test_skips_without_research(self):
        from agents.analyst import analyst_node
        result = analyst_node(_base_state(research_result=None))
        assert result["analyst_status"] == AgentStatus.SKIPPED

    def test_happy_path(self):
        from agents.analyst import analyst_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=self._analysis_json())

        with patch("agents.analyst.get_settings", return_value=_mock_settings()), \
             patch("agents.analyst._build_llm", return_value=mock_llm):
            result = analyst_node(self._research_state())

        assert result["analyst_status"] == AgentStatus.DONE
        ar = AnalysisResult.model_validate(result["analysis_result"])
        assert len(ar.pricing_moves) == 1
        assert ar.pricing_moves[0].competitor == "Salesforce"
        assert ar.recommendation == "Revisit our entry pricing."

    def test_invalid_json_returns_empty_analysis(self):
        from agents.analyst import analyst_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="NOT VALID JSON <<<")

        with patch("agents.analyst.get_settings", return_value=_mock_settings()), \
             patch("agents.analyst._build_llm", return_value=mock_llm):
            result = analyst_node(self._research_state())

        # Should not abort — just return empty analysis
        assert result["analyst_status"] == AgentStatus.DONE
        ar = AnalysisResult.model_validate(result["analysis_result"])
        assert ar.pricing_moves == []


# ── Writer Agent ──────────────────────────────────────────────────────────────

class TestWriterNode:
    def _full_state(self):
        rr = ResearchResult(
            topic="CRM", items=[],
            sources=[Source(url="https://sf.com", title="SF Blog", snippet="SF cut prices.")],
        )
        ar = AnalysisResult(
            topic="CRM",
            recommendation="Act now.",
        )
        return _base_state(
            research_result=rr.model_dump(mode="json"),
            analysis_result=ar.model_dump(mode="json"),
        )

    def test_produces_briefing_on_abort(self):
        from agents.writer import writer_node
        with patch("agents.writer.get_settings", return_value=_mock_settings()):
            result = writer_node(_base_state(abort=True, abort_reason="step limit"))

        assert result["writer_status"] == AgentStatus.DONE
        briefing = result["briefing_output"]
        assert briefing is not None
        assert "error" in briefing["raw_markdown"].lower() or "could not" in briefing["raw_markdown"].lower()

    def test_produces_briefing_without_analysis(self):
        from agents.writer import writer_node
        with patch("agents.writer.get_settings", return_value=_mock_settings()):
            result = writer_node(_base_state(analysis_result=None))

        assert result["briefing_output"] is not None

    def test_happy_path(self):
        from agents.writer import writer_node

        markdown = (
            "# Competitive Intelligence Briefing\n\n"
            "### Executive Summary\nSalesforce cut prices. [Source 1]\n\n"
            "### Competitor Pricing Moves\nSF cut 10%. [Source 1]\n\n"
            "### Sources\n1. https://sf.com — SF Blog\n"
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=markdown)

        with patch("agents.writer.get_settings", return_value=_mock_settings()), \
             patch("agents.writer._build_llm", return_value=mock_llm):
            result = writer_node(self._full_state())

        assert result["writer_status"] == AgentStatus.DONE
        bo = result["briefing_output"]
        assert "Salesforce" in bo["raw_markdown"]
        assert bo["executive_summary"] != ""

    def test_llm_failure_still_produces_briefing(self):
        from agents.writer import writer_node

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM crashed")

        with patch("agents.writer.get_settings", return_value=_mock_settings()), \
             patch("agents.writer._build_llm", return_value=mock_llm):
            result = writer_node(self._full_state())

        # Even on failure the writer should produce a degraded briefing
        assert result["briefing_output"] is not None
        assert "LLM crashed" in result["errors"][-1]
