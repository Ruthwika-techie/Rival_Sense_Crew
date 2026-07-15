"""
agents/researcher.py – Researcher Agent

Responsibilities:
  - Generate targeted search queries for the topic.
  - Execute searches via Tavily (with retries).
  - Optionally enrich sources via Firecrawl.
  - Return only factual findings with source URLs.
  - Track failed sources and respect source caps.
  - NEVER fabricate information — only what's in the search snippets.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from models import (
    AgentStatus,
    BriefingState,
    ResearchItem,
    ResearchResult,
    Source,
)
from tools import build_tools

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

RESEARCHER_SYSTEM = """You are a Researcher Agent in a competitive intelligence pipeline.

Your task is to generate targeted search queries for a given market topic,
then summarise the raw search results into structured findings.

## Rules
1. Only report information that is DIRECTLY supported by the provided source snippets.
2. Do NOT invent, infer, or extrapolate beyond what the sources state.
3. Each finding MUST reference at least one source URL.
4. Categorise each finding as one of: pricing, product_launch, market_signal, other.
5. Be concise — one finding per distinct fact.

## Output format
Return a JSON object with this exact schema:
{
  "queries": ["query1", "query2", ...],
  "findings": [
    {
      "category": "pricing",
      "content": "Competitor X reduced its starter plan by 15% in June 2025.",
      "source_urls": ["https://..."]
    },
    ...
  ]
}

Return ONLY the JSON object, no markdown fences, no prose.
"""


def _build_llm(settings=None):
    settings = settings or get_settings()
    kwargs: Dict[str, Any] = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.1,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def _generate_queries(llm, topic: str, num_queries: int) -> List[str]:
    """Ask the LLM to produce N targeted search queries for the topic."""
    prompt = (
        f"Generate exactly {num_queries} precise web search queries to gather "
        f"competitive intelligence about: {topic}\n\n"
        "Focus on: competitor pricing changes, product launches, market share, "
        "analyst reports, and customer sentiment.\n\n"
        "Return ONLY a JSON array of strings, e.g. [\"query1\", \"query2\"]"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        queries = json.loads(raw)
        if isinstance(queries, list):
            return [str(q) for q in queries[:num_queries]]
    except Exception:
        pass
    # Fallback: split on newlines
    return [line.strip("- ").strip() for line in raw.splitlines() if line.strip()][:num_queries]


def _parse_findings(llm, topic: str, sources: List[Source]) -> List[ResearchItem]:
    """Ask the LLM to summarise source snippets into structured findings."""
    if not sources:
        return []

    # Build a compact source digest
    source_text_parts = []
    for i, src in enumerate(sources, 1):
        source_text_parts.append(
            f"[{i}] URL: {src.url}\n    Title: {src.title}\n    Snippet: {src.snippet}"
        )
    source_text = "\n\n".join(source_text_parts)

    user_msg = (
        f"Topic: {topic}\n\n"
        f"Below are {len(sources)} sources retrieved from web search.\n"
        "Extract all distinct competitive intelligence findings.\n\n"
        f"{source_text}"
    )

    response = llm.invoke(
        [
            SystemMessage(content=RESEARCHER_SYSTEM),
            HumanMessage(content=user_msg),
        ]
    )

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()

    try:
        data = json.loads(raw)
        findings_raw = data.get("findings", [])
    except Exception as exc:
        logger.warning("Failed to parse researcher LLM output as JSON: %s", exc)
        logger.debug("Raw output: %s", raw)
        return []

    items: List[ResearchItem] = []
    for f in findings_raw:
        try:
            item = ResearchItem(
                category=f.get("category", "other"),
                content=f.get("content", ""),
                source_urls=f.get("source_urls", []),
            )
            if item.content and item.source_urls:
                items.append(item)
        except Exception as exc:
            logger.debug("Skipping malformed finding: %s | %s", f, exc)

    return items


def researcher_node(state: BriefingState) -> Dict[str, Any]:
    """
    LangGraph node: Researcher Agent.

    Reads: topic, max_sources, min_trusted_sources, abort
    Writes: research_result, researcher_status, insufficient_sources,
            step_count, run_metadata, errors
    """
    errors: list = list(state.get("errors", []))
    step_count: int = state.get("step_count", 0) + 1

    # Honour abort flag — check before loading settings so tests without a
    # .env file can exercise the early-exit path without hitting Settings validation.
    if state.get("abort"):
        logger.info("Researcher skipped (abort flag set).")
        return {
            "step_count": step_count,
            "researcher_status": AgentStatus.SKIPPED,
        }

    settings = get_settings()
    topic: str = state.get("topic", "")
    max_sources: int = state.get("max_sources", settings.max_sources)
    min_trusted_sources: int = state.get("min_trusted_sources", settings.min_trusted_sources)

    logger.info("Researcher starting for topic: %r", topic)

    meta: dict = dict(state.get("run_metadata") or {})
    meta["researcher_status"] = AgentStatus.RUNNING

    try:
        llm = _build_llm(settings)
        tavily, firecrawl = build_tools(settings)

        # 1. Generate queries
        queries = _generate_queries(llm, topic, settings.search_queries_per_run)
        logger.info("Generated %d queries: %s", len(queries), queries)

        # 2. Execute searches
        good_sources, failed_sources = tavily.multi_search(
            queries=queries,
            max_results_per_query=settings.max_search_results,
            max_total_sources=max_sources,
        )
        logger.info(
            "Search complete: %d good sources, %d failed",
            len(good_sources), len(failed_sources),
        )

        if failed_sources:
            for fs in failed_sources:
                errors.append(f"Search failed: {fs.failure_reason or fs.title}")

        # 3. Optional Firecrawl enrichment
        if settings.firecrawl_enabled:
            good_sources = firecrawl.enrich_sources(good_sources)

        # ── Source quality gate ───────────────────────────────────────────────
        # A trusted source must not be marked failed AND must have a non-empty snippet.
        trusted_sources = [
            s for s in good_sources if not s.failed and s.snippet and s.snippet.strip()
        ]
        trusted_count = len(trusted_sources)
        logger.info(
            "Trusted sources: %d / %d (minimum required: %d)",
            trusted_count, len(good_sources), min_trusted_sources,
        )

        if trusted_count < min_trusted_sources:
            msg = (
                f"Insufficient trusted sources for topic {topic!r}: "
                f"found {trusted_count}, need at least {min_trusted_sources}. "
                "Aborting pipeline to prevent hallucination."
            )
            logger.warning(msg)
            errors.append(msg)

            result = ResearchResult(
                topic=topic,
                items=[],
                sources=good_sources,
                failed_sources=failed_sources,
                queries_executed=queries,
                total_sources_collected=len(good_sources),
                sources_skipped=len(failed_sources),
            )

            meta["researcher_status"] = AgentStatus.DONE
            meta["total_sources"] = len(good_sources)
            meta["sources_skipped"] = len(failed_sources)
            meta["steps_taken"] = step_count

            return {
                "step_count": step_count,
                "researcher_status": AgentStatus.DONE,
                "research_result": result.model_dump(mode="json"),
                "insufficient_sources": True,
                "abort": True,
                "abort_reason": msg,
                "run_metadata": meta,
                "errors": errors,
            }

        # 4. Parse findings from LLM — only from trusted sources
        items = _parse_findings(llm, topic, trusted_sources)
        logger.info("Researcher extracted %d findings.", len(items))

        result = ResearchResult(
            topic=topic,
            items=items,
            sources=good_sources,
            failed_sources=failed_sources,
            queries_executed=queries,
            total_sources_collected=len(good_sources),
            sources_skipped=len(failed_sources),
        )

        meta["researcher_status"] = AgentStatus.DONE
        meta["total_sources"] = len(good_sources)
        meta["sources_skipped"] = len(failed_sources)
        meta["steps_taken"] = step_count

        return {
            "step_count": step_count,
            "researcher_status": AgentStatus.DONE,
            "research_result": result.model_dump(mode="json"),
            "insufficient_sources": False,
            "run_metadata": meta,
            "errors": errors,
        }

    except Exception as exc:
        msg = f"Researcher agent failed: {exc}"
        logger.exception(msg)
        errors.append(msg)
        meta["researcher_status"] = AgentStatus.FAILED

        return {
            "step_count": step_count,
            "researcher_status": AgentStatus.FAILED,
            "research_result": None,
            "insufficient_sources": False,
            "run_metadata": meta,
            "errors": errors,
            "abort": True,
            "abort_reason": msg,
        }
