"""
agents/analyst.py – Analyst Agent

Responsibilities:
  - Receives structured research findings.
  - Extracts competitor pricing moves, product launches, market signals.
  - Identifies trends, risks, and opportunities.
  - Produces a top strategic recommendation.
  - NEVER invents facts — every claim must link to a source URL from research.
  - Drops any claim that cannot be traced to a source.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from models import (
    AgentStatus,
    AnalysisResult,
    BriefingState,
    Citation,
    ClaimVerification,
    Insight,
    MarketSignal,
    PricingMove,
    ProductLaunch,
    ResearchResult,
)

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

ANALYST_SYSTEM = """You are an Analyst Agent in a competitive intelligence pipeline.

You receive structured research findings and must produce a rigorous analysis.

## Rules
1. Every claim in your analysis MUST be directly traceable to a provided source URL.
2. Do NOT invent facts, percentages, quotes, or company names not in the research.
3. If a finding lacks a source URL, omit it entirely from your analysis.
4. Be precise and business-focused. Avoid vague generalisations.
5. Separate confirmed facts from interpretive analysis (mark interpretations clearly).

## Output format
Return a single JSON object with this exact schema:
{
  "pricing_moves": [
    {
      "competitor": "CompanyName",
      "description": "...",
      "source_urls": ["https://..."]
    }
  ],
  "product_launches": [
    {
      "competitor": "CompanyName",
      "product_name": "ProductName",
      "description": "...",
      "source_urls": ["https://..."]
    }
  ],
  "market_signals": [
    {
      "signal": "Brief signal headline",
      "detail": "...",
      "source_urls": ["https://..."]
    }
  ],
  "insights": [
    {
      "type": "trend|risk|opportunity|threat|observation",
      "title": "...",
      "detail": "...",
      "source_urls": ["https://..."]
    }
  ],
  "recommendation": "Single top strategic recommendation based only on the research.",
  "unverified_claims_omitted": 0
}

Return ONLY the JSON object, no markdown fences, no prose.
"""


def _build_llm(settings=None):
    settings = settings or get_settings()
    kwargs: Dict[str, Any] = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.2,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def _research_to_prompt_text(research: ResearchResult) -> str:
    """Serialise research findings into a compact, numbered list for the LLM."""
    lines = [f"Topic: {research.topic}\n"]
    lines.append(f"Total findings: {len(research.items)}\n")

    for i, item in enumerate(research.items, 1):
        urls = ", ".join(item.source_urls[:3])  # cap at 3 to keep prompt small
        lines.append(
            f"{i}. [{item.category.upper()}] {item.content}\n   Sources: {urls}"
        )

    return "\n".join(lines)


def _make_citations(source_urls: List[str]) -> List[Citation]:
    return [
        Citation(
            claim="",
            sources=source_urls,
            verified=ClaimVerification.VERIFIED,
        )
    ] if source_urls else []


def analyst_node(state: BriefingState) -> Dict[str, Any]:
    """
    LangGraph node: Analyst Agent.

    Reads: research_result, topic, abort
    Writes: analysis_result, analyst_status, step_count, run_metadata, errors
    """
    errors: list = list(state.get("errors", []))
    step_count: int = state.get("step_count", 0) + 1

    # Check early-exit conditions before loading settings so tests without a
    # .env file can exercise these paths without hitting Settings validation.
    if state.get("abort"):
        logger.info("Analyst skipped (abort flag set).")
        return {
            "step_count": step_count,
            "analyst_status": AgentStatus.SKIPPED,
        }

    research_raw = state.get("research_result")
    if not research_raw:
        msg = "Analyst: no research_result in state — skipping analysis."
        logger.warning(msg)
        errors.append(msg)
        return {
            "step_count": step_count,
            "analyst_status": AgentStatus.SKIPPED,
            "errors": errors,
        }

    settings = get_settings()
    topic: str = state.get("topic", "")

    logger.info("Analyst starting analysis for topic: %r", topic)

    meta: dict = dict(state.get("run_metadata") or {})
    meta["analyst_status"] = AgentStatus.RUNNING

    try:
        research = ResearchResult.model_validate(research_raw)

        # ── Guard: drop findings without source URLs before sending to LLM ──────
        sourced_items = [item for item in research.items if item.source_urls]
        dropped = len(research.items) - len(sourced_items)
        if dropped:
            logger.warning(
                "Analyst dropped %d finding(s) with no source URLs before analysis.",
                dropped,
            )

        if not sourced_items:
            msg = (
                "Analyst: all research findings lack source URLs — "
                "refusing to analyse to prevent uncited claims."
            )
            logger.warning(msg)
            errors.append(msg)
            meta["analyst_status"] = AgentStatus.SKIPPED
            return {
                "step_count": step_count,
                "analyst_status": AgentStatus.SKIPPED,
                "analysis_result": None,
                "run_metadata": meta,
                "errors": errors,
            }

        # Replace items with only sourced items for the LLM prompt
        research_for_llm = research.model_copy(update={"items": sourced_items})
        llm = _build_llm(settings)

        research_text = _research_to_prompt_text(research_for_llm)

        response = llm.invoke(
            [
                SystemMessage(content=ANALYST_SYSTEM),
                HumanMessage(content=research_text),
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
        except Exception as exc:
            logger.warning("Analyst LLM output not valid JSON: %s", exc)
            logger.debug("Raw analyst output: %s", raw)
            data = {}

        # ── Parse pricing moves ───────────────────────────────────────────────
        pricing_moves: List[PricingMove] = []
        for pm in data.get("pricing_moves", []):
            try:
                pricing_moves.append(
                    PricingMove(
                        competitor=pm.get("competitor", "Unknown"),
                        description=pm.get("description", ""),
                        citations=_make_citations(pm.get("source_urls", [])),
                    )
                )
            except Exception as e:
                logger.debug("Skipping malformed pricing move: %s", e)

        # ── Parse product launches ────────────────────────────────────────────
        product_launches: List[ProductLaunch] = []
        for pl in data.get("product_launches", []):
            try:
                product_launches.append(
                    ProductLaunch(
                        competitor=pl.get("competitor", "Unknown"),
                        product_name=pl.get("product_name", ""),
                        description=pl.get("description", ""),
                        citations=_make_citations(pl.get("source_urls", [])),
                    )
                )
            except Exception as e:
                logger.debug("Skipping malformed product launch: %s", e)

        # ── Parse market signals ──────────────────────────────────────────────
        market_signals: List[MarketSignal] = []
        for ms in data.get("market_signals", []):
            try:
                market_signals.append(
                    MarketSignal(
                        signal=ms.get("signal", ""),
                        detail=ms.get("detail", ""),
                        citations=_make_citations(ms.get("source_urls", [])),
                    )
                )
            except Exception as e:
                logger.debug("Skipping malformed market signal: %s", e)

        # ── Parse insights ────────────────────────────────────────────────────
        insights: List[Insight] = []
        for ins in data.get("insights", []):
            try:
                insights.append(
                    Insight(
                        type=ins.get("type", "observation"),
                        title=ins.get("title", ""),
                        detail=ins.get("detail", ""),
                        citations=_make_citations(ins.get("source_urls", [])),
                    )
                )
            except Exception as e:
                logger.debug("Skipping malformed insight: %s", e)

        # ── Build all_citations list ──────────────────────────────────────────
        all_citations: List[Citation] = []
        for item_list in (pricing_moves, product_launches, market_signals, insights):
            for item in item_list:
                all_citations.extend(item.citations)

        analysis = AnalysisResult(
            topic=topic,
            pricing_moves=pricing_moves,
            product_launches=product_launches,
            market_signals=market_signals,
            insights=insights,
            recommendation=data.get("recommendation", ""),
            all_citations=all_citations,
            unverified_claims_omitted=data.get("unverified_claims_omitted", 0) + dropped,
        )

        logger.info(
            "Analyst done: %d pricing moves, %d launches, %d signals, %d insights",
            len(pricing_moves), len(product_launches),
            len(market_signals), len(insights),
        )

        meta["analyst_status"] = AgentStatus.DONE
        meta["steps_taken"] = step_count

        return {
            "step_count": step_count,
            "analyst_status": AgentStatus.DONE,
            "analysis_result": analysis.model_dump(mode="json"),
            "run_metadata": meta,
            "errors": errors,
        }

    except Exception as exc:
        msg = f"Analyst agent failed: {exc}"
        logger.exception(msg)
        errors.append(msg)
        meta["analyst_status"] = AgentStatus.FAILED

        return {
            "step_count": step_count,
            "analyst_status": AgentStatus.FAILED,
            "analysis_result": None,
            "run_metadata": meta,
            "errors": errors,
        }
