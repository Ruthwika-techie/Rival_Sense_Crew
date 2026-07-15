"""
tests/test_graph.py – Unit tests for LangGraph routing and the run_briefing API.

Tests verify:
  - Conditional routing functions (no graph compilation needed)
  - run_briefing() end-to-end with fully mocked agents
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from models import (
    AgentStatus,
    AnalysisResult,
    BriefingOutput,
    BriefingState,
    ResearchResult,
    RunMetadata,
    Source,
)


# ── Routing function tests ────────────────────────────────────────────────────

class TestRoutingFunctions:
    """Test the conditional edge functions independently."""

    def test_coordinator_routes_to_researcher_on_success(self):
        from graph import route_after_coordinator
        state: BriefingState = {"abort": False, "topic": "CRM"}
        assert route_after_coordinator(state) == "researcher"

    def test_coordinator_routes_to_writer_on_abort(self):
        from graph import route_after_coordinator
        state: BriefingState = {"abort": True, "abort_reason": "empty topic"}
        assert route_after_coordinator(state) == "writer"

    def test_researcher_routes_to_validator_on_success(self):
        from graph import route_after_researcher
        state: BriefingState = {"abort": False}
        assert route_after_researcher(state) == "validator"

    def test_researcher_routes_to_writer_on_abort(self):
        from graph import route_after_researcher
        state: BriefingState = {"abort": True}
        assert route_after_researcher(state) == "writer"

    def test_analyst_always_routes_to_writer(self):
        from graph import route_after_analyst
        for abort_flag in (True, False):
            state: BriefingState = {"abort": abort_flag}
            assert route_after_analyst(state) == "writer"

    def test_validator_routes_to_analyst_on_pass(self):
        """When validation succeeds, route to analyst."""
        from graph import route_after_validator
        state: BriefingState = {"validation_failed": False, "abort": False}
        assert route_after_validator(state) == "analyst"

    def test_validator_routes_to_writer_on_validation_failed(self):
        """When validation_failed is True, skip analyst and go to writer."""
        from graph import route_after_validator
        state: BriefingState = {"validation_failed": True, "abort": False}
        assert route_after_validator(state) == "writer"

    def test_validator_routes_to_writer_on_abort(self):
        """If abort is set (e.g. missing research_result), go directly to writer."""
        from graph import route_after_validator
        state: BriefingState = {"validation_failed": False, "abort": True}
        assert route_after_validator(state) == "writer"

    def test_validator_routes_to_writer_when_both_flags_set(self):
        """Both abort and validation_failed set -> writer."""
        from graph import route_after_validator
        state: BriefingState = {"validation_failed": True, "abort": True}
        assert route_after_validator(state) == "writer"


# ── run_briefing integration ──────────────────────────────────────────────────

class TestRunBriefing:
    """Integration tests that mock the graph.invoke call."""

    def _make_briefing_dict(self, topic: str = "CRM") -> dict:
        meta = RunMetadata(
            topic=topic,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=45.2,
            steps_taken=4,
            total_sources=12,
            coordinator_status=AgentStatus.DONE,
            researcher_status=AgentStatus.DONE,
            analyst_status=AgentStatus.DONE,
            writer_status=AgentStatus.DONE,
        )
        briefing = BriefingOutput(
            run_metadata=meta,
            executive_summary="Two rivals cut prices.",
            recommendation="Revisit entry pricing.",
            raw_markdown="# Brief\n\n## Executive Summary\nTwo rivals cut prices.",
        )
        return briefing.model_dump(mode="json")

    def test_returns_briefing_output(self):
        from graph import run_briefing

        fake_final_state = {
            "briefing_output": self._make_briefing_dict("CRM software"),
            "errors": [],
        }

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.invoke.return_value = fake_final_state
            mock_get_graph.return_value = mock_graph

            result = run_briefing("CRM software")

        assert isinstance(result, BriefingOutput)
        assert result.run_metadata.topic == "CRM software"
        assert result.executive_summary == "Two rivals cut prices."

    def test_handles_graph_exception(self):
        from graph import run_briefing

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.invoke.side_effect = RuntimeError("Graph exploded")
            mock_get_graph.return_value = mock_graph

            result = run_briefing("test topic")

        assert isinstance(result, BriefingOutput)
        assert "Graph exploded" in result.raw_markdown
        assert len(result.run_metadata.errors) > 0

    def test_empty_topic_still_returns_briefing(self):
        """Even with an empty topic, run_briefing should not raise."""
        from graph import run_briefing

        # Coordinator will abort — writer still produces degraded briefing
        fake_final_state = {
            "briefing_output": self._make_briefing_dict(""),
            "errors": ["topic is empty"],
        }

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.invoke.return_value = fake_final_state
            mock_get_graph.return_value = mock_graph

            result = run_briefing("")

        assert isinstance(result, BriefingOutput)

    def test_respects_max_sources_override(self):
        from graph import run_briefing

        captured_state = {}

        def capturing_invoke(state):
            captured_state.update(state)
            return {"briefing_output": self._make_briefing_dict(), "errors": []}

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.invoke.side_effect = capturing_invoke
            mock_get_graph.return_value = mock_graph

            run_briefing("AI tools", max_sources=7, max_steps=25)

        assert captured_state.get("max_sources") == 7
        assert captured_state.get("max_steps") == 25

    def test_no_briefing_output_in_state(self):
        """If the graph produces no briefing_output, run_briefing should still return something."""
        from graph import run_briefing

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.invoke.return_value = {"errors": ["something went wrong"]}
            mock_get_graph.return_value = mock_graph

            result = run_briefing("test")

        assert isinstance(result, BriefingOutput)
        assert result.raw_markdown != ""


# ── stream_briefing ───────────────────────────────────────────────────────────

class TestStreamBriefing:
    def test_yields_node_events(self):
        from graph import stream_briefing

        fake_events = [
            {"coordinator": {"coordinator_status": "done"}},
            {"researcher": {"researcher_status": "done"}},
            {"validator": {"validator_status": "done", "validation_failed": False}},
            {"analyst": {"analyst_status": "done"}},
            {"writer": {"briefing_output": {}, "writer_status": "done"}},
        ]

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.stream.return_value = iter(fake_events)
            mock_get_graph.return_value = mock_graph

            events = list(stream_briefing("CRM"))

        assert len(events) == 5
        assert events[0]["node"] == "coordinator"
        assert events[2]["node"] == "validator"
        assert events[4]["node"] == "writer"

    def test_stream_event_structure(self):
        from graph import stream_briefing

        fake_events = [
            {"coordinator": {"coordinator_status": "done", "step_count": 1}},
        ]

        with patch("graph.get_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.stream.return_value = iter(fake_events)
            mock_get_graph.return_value = mock_graph

            events = list(stream_briefing("Test"))

        event = events[0]
        assert "node" in event
        assert "state" in event
        assert event["state"]["coordinator_status"] == "done"
