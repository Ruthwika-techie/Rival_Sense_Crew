"""
agents/coordinator.py – Coordinator Agent

Responsibilities:
  - Initialise the run (set step counter, limits, metadata).
  - Validate the topic is non-empty.
  - Enforce the max_steps hard limit before every delegation.
  - Log high-level workflow events.
  - Update agent statuses in shared state.

The coordinator does NOT call an LLM — it is a deterministic orchestrator
that routes the pipeline: coordinator → researcher → analyst → writer.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from config import get_settings
from models import AgentStatus, BriefingState, RunMetadata

logger = logging.getLogger(__name__)


def coordinator_node(state: BriefingState) -> Dict[str, Any]:
    """
    LangGraph node: Coordinator Agent.

    Called at the start of every run. Initialises all bookkeeping fields
    and validates preconditions. If anything is already broken it sets
    abort=True so the graph can short-circuit to the writer with an error
    briefing.
    """
    settings = get_settings()

    topic: str = state.get("topic", "").strip()
    step_count: int = state.get("step_count", 0) + 1
    max_steps: int = state.get("max_steps", settings.max_steps)
    max_sources: int = state.get("max_sources", settings.max_sources)
    min_trusted_sources: int = state.get("min_trusted_sources", settings.min_trusted_sources)
    min_valid_sources: int = state.get("min_valid_sources", settings.min_valid_sources)
    relevance_threshold: float = state.get("relevance_threshold", settings.relevance_threshold)
    errors: list = list(state.get("errors", []))

    logger.info("═" * 60)
    logger.info("Coordinator starting — topic: %r", topic)
    logger.info(
        "Limits: max_steps=%d  max_sources=%d  "
        "min_valid_sources=%d  relevance_threshold=%.2f",
        max_steps, max_sources, min_valid_sources, relevance_threshold,
    )

    # ── Build / refresh run metadata ─────────────────────────────────────────
    existing_meta = state.get("run_metadata") or {}
    meta = RunMetadata(
        run_id=existing_meta.get("run_id", RunMetadata().run_id),
        topic=topic,
        started_at=existing_meta.get("started_at") or datetime.utcnow(),
        steps_taken=step_count,
        coordinator_status=AgentStatus.RUNNING,
        researcher_status=AgentStatus.PENDING,
        analyst_status=AgentStatus.PENDING,
        writer_status=AgentStatus.PENDING,
    )

    # ── Validate topic ────────────────────────────────────────────────────────
    if not topic:
        msg = "Coordinator: topic is empty — aborting run."
        logger.error(msg)
        errors.append(msg)
        meta.coordinator_status = AgentStatus.FAILED
        meta.errors = errors
        return {
            "step_count": step_count,
            "max_steps": max_steps,
            "max_sources": max_sources,
            "min_trusted_sources": min_trusted_sources,
            "min_valid_sources": min_valid_sources,
            "relevance_threshold": relevance_threshold,
            "abort": True,
            "abort_reason": msg,
            "insufficient_sources": False,
            "validation_failed": False,
            "coordinator_status": AgentStatus.FAILED,
            "researcher_status": AgentStatus.SKIPPED,
            "validator_status": AgentStatus.SKIPPED,
            "analyst_status": AgentStatus.SKIPPED,
            "writer_status": AgentStatus.PENDING,
            "run_metadata": meta.model_dump(mode="json"),
            "errors": errors,
        }

    # ── Check step budget ────────────────────────────────────────────────────
    if step_count > max_steps:
        msg = f"Coordinator: step limit ({max_steps}) exceeded — aborting."
        logger.error(msg)
        errors.append(msg)
        meta.coordinator_status = AgentStatus.FAILED
        meta.errors = errors
        return {
            "step_count": step_count,
            "abort": True,
            "abort_reason": msg,
            "insufficient_sources": False,
            "validation_failed": False,
            "coordinator_status": AgentStatus.FAILED,
            "validator_status": AgentStatus.SKIPPED,
            "run_metadata": meta.model_dump(mode="json"),
            "errors": errors,
        }

    # ── All good — hand off to researcher ────────────────────────────────────
    meta.coordinator_status = AgentStatus.DONE
    meta.errors = errors

    logger.info("Coordinator done — delegating to Researcher.")

    return {
        "topic": topic,
        "step_count": step_count,
        "max_steps": max_steps,
        "max_sources": max_sources,
        "min_trusted_sources": min_trusted_sources,
        "min_valid_sources": min_valid_sources,
        "relevance_threshold": relevance_threshold,
        "abort": False,
        "abort_reason": "",
        "insufficient_sources": False,
        "validation_failed": False,
        "coordinator_status": AgentStatus.DONE,
        "researcher_status": AgentStatus.PENDING,
        "validator_status": AgentStatus.PENDING,
        "analyst_status": AgentStatus.PENDING,
        "writer_status": AgentStatus.PENDING,
        "run_metadata": meta.model_dump(mode="json"),
        "errors": errors,
    }
