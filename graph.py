"""
graph.py – LangGraph Workflow Graph

Topology:
    START → coordinator → researcher → validator → analyst → writer → END

Conditional edges:
    - coordinator: if abort=True, jump directly to writer (error briefing)
    - researcher:  if abort=True, jump directly to writer
    - validator:   if validation_failed=True, jump directly to writer
                   (writer produces 'No sufficient trusted data' response)
    - analyst:     always proceed to writer (writer handles missing analysis)

The graph is compiled once and can be invoked synchronously or streamed.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from agents.coordinator import coordinator_node
from agents.researcher import researcher_node
from agents.validator import validator_node
from agents.analyst import analyst_node
from agents.writer import writer_node
from config import configure_logging, get_settings
from models import BriefingOutput, BriefingState, RunMetadata

logger = logging.getLogger(__name__)


# ── Conditional routing ───────────────────────────────────────────────────────

def route_after_coordinator(state: BriefingState) -> str:
    """After coordinator: abort → writer, else → researcher."""
    if state.get("abort"):
        logger.info("Routing: coordinator → writer (abort)")
        return "writer"
    return "researcher"


def route_after_researcher(state: BriefingState) -> str:
    """After researcher: abort (hard failure) → writer, else → validator."""
    if state.get("abort"):
        logger.info("Routing: researcher → writer (abort)")
        return "writer"
    return "validator"


def route_after_validator(state: BriefingState) -> str:
    """
    After validator: validation_failed → writer (structured rejection),
    else → analyst.
    """
    if state.get("validation_failed") or state.get("abort"):
        logger.info(
            "Routing: validator → writer (validation_failed=%s)",
            state.get("validation_failed"),
        )
        return "writer"
    return "analyst"


def route_after_analyst(state: BriefingState) -> str:
    """After analyst: always go to writer."""
    return "writer"


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and return the compiled LangGraph StateGraph."""
    graph = StateGraph(BriefingState)

    # Register nodes
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("validator", validator_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)

    # Entry point
    graph.add_edge(START, "coordinator")

    # coordinator → researcher | writer
    graph.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {"researcher": "researcher", "writer": "writer"},
    )

    # researcher → validator | writer
    graph.add_conditional_edges(
        "researcher",
        route_after_researcher,
        {"validator": "validator", "writer": "writer"},
    )

    # validator → analyst | writer
    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {"analyst": "analyst", "writer": "writer"},
    )

    # analyst → writer (always)
    graph.add_conditional_edges(
        "analyst",
        route_after_analyst,
        {"writer": "writer"},
    )

    # writer is the terminal node
    graph.add_edge("writer", END)

    return graph.compile()


# Singleton compiled graph (imported by app.py and tests)
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ── Public run API ────────────────────────────────────────────────────────────

def run_briefing(
    topic: str,
    max_sources: Optional[int] = None,
    max_steps: Optional[int] = None,
) -> BriefingOutput:
    """
    Run the full competitive intelligence pipeline for a given topic.

    Returns a BriefingOutput regardless of success or failure.
    """
    configure_logging()

    try:
        graph = get_graph()

        # Load settings for defaults; fall back to hardcoded defaults so that
        # callers (e.g. tests) that mock get_graph but not get_settings still work.
        try:
            settings = get_settings()
            _max_steps = max_steps or settings.max_steps
            _max_sources = max_sources or settings.max_sources
            _min_trusted = settings.min_trusted_sources
            _min_valid = settings.min_valid_sources
            _relevance = settings.relevance_threshold
        except Exception:
            _max_steps = max_steps or 50
            _max_sources = max_sources or 20
            _min_trusted = 2
            _min_valid = 2
            _relevance = 0.3

        initial_state: BriefingState = {
            "topic": topic.strip(),
            "step_count": 0,
            "max_steps": _max_steps,
            "max_sources": _max_sources,
            "min_trusted_sources": _min_trusted,
            "min_valid_sources": _min_valid,
            "relevance_threshold": _relevance,
            "abort": False,
            "abort_reason": "",
            "insufficient_sources": False,
            "validation_failed": False,
            "coordinator_status": "pending",
            "researcher_status": "pending",
            "validator_status": "pending",
            "analyst_status": "pending",
            "writer_status": "pending",
            "research_result": None,
            "validation_result": None,
            "analysis_result": None,
            "briefing_output": None,
            "run_metadata": RunMetadata(
                topic=topic.strip(),
                started_at=datetime.utcnow(),
            ).model_dump(mode="json"),
            "errors": [],
        }

        logger.info("Starting briefing run for topic: %r", topic)

        final_state = graph.invoke(initial_state)
    except Exception as exc:
        logger.exception("Graph execution failed: %s", exc)
        try:
            started_at = initial_state["run_metadata"]["started_at"]
        except NameError:
            started_at = datetime.utcnow()
        meta = RunMetadata(
            topic=topic,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            errors=[str(exc)],
        )
        return BriefingOutput(
            run_metadata=meta,
            raw_markdown=f"# Briefing Failed\n\nFatal error: {exc}",
        )

    briefing_raw = final_state.get("briefing_output")
    if briefing_raw:
        return BriefingOutput.model_validate(briefing_raw)

    meta = RunMetadata(
        topic=topic,
        errors=final_state.get("errors", ["No briefing output produced"]),
    )
    return BriefingOutput(
        run_metadata=meta,
        raw_markdown="# Briefing Failed\n\nNo output was produced by the pipeline.",
    )


def stream_briefing(
    topic: str,
    max_sources: Optional[int] = None,
    max_steps: Optional[int] = None,
):
    """
    Generator that yields LangGraph node-by-node state updates.

    Each yielded item is a dict: {"node": str, "state": BriefingState}.
    """
    configure_logging()

    graph = get_graph()

    # Load settings for defaults; fall back to hardcoded defaults so that
    # callers (e.g. tests) that mock get_graph but not get_settings still work.
    try:
        settings = get_settings()
        _max_steps = max_steps or settings.max_steps
        _max_sources = max_sources or settings.max_sources
        _min_trusted = settings.min_trusted_sources
        _min_valid = settings.min_valid_sources
        _relevance = settings.relevance_threshold
    except Exception:
        _max_steps = max_steps or 50
        _max_sources = max_sources or 20
        _min_trusted = 2
        _min_valid = 2
        _relevance = 0.3

    initial_state: BriefingState = {
        "topic": topic.strip(),
        "step_count": 0,
        "max_steps": _max_steps,
        "max_sources": _max_sources,
        "min_trusted_sources": _min_trusted,
        "min_valid_sources": _min_valid,
        "relevance_threshold": _relevance,
        "abort": False,
        "abort_reason": "",
        "insufficient_sources": False,
        "validation_failed": False,
        "coordinator_status": "pending",
        "researcher_status": "pending",
        "validator_status": "pending",
        "analyst_status": "pending",
        "writer_status": "pending",
        "research_result": None,
        "validation_result": None,
        "analysis_result": None,
        "briefing_output": None,
        "run_metadata": RunMetadata(
            topic=topic.strip(),
            started_at=datetime.utcnow(),
        ).model_dump(mode="json"),
        "errors": [],
    }

    graph = get_graph()
    for event in graph.stream(initial_state):
        for node_name, partial_state in event.items():
            yield {"node": node_name, "state": partial_state}
