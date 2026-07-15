"""
agents/writer.py – Writer Agent

Responsibilities:
  - Receive analysis results and produce a polished competitive briefing.
  - Sections: Executive Summary, Competitor Pricing, Product Launches,
    Market Signals, Key Insights, Recommendation, Sources, Run Metadata.
  - Every sentence must cite a source using [Source N] inline markers.
  - Never add information not present in the analysis.
  - Works even when upstream agents partially failed (graceful degradation).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from models import (
    AgentStatus,
    AnalysisResult,
    BriefingOutput,
    BriefingState,
    ResearchResult,
    RunMetadata,
    Source,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

WRITER_SYSTEM = """You are a Writer Agent for a competitive intelligence service.

Your task is to produce a professional, structured weekly briefing from the
analysis data provided. The audience is senior strategy and sales leaders.

## Rules
1. Every factual claim MUST include an inline source citation like [Source N].
2. Do NOT invent, extrapolate, or add information not in the provided data.
3. If a section has no data, write "No data available this week." — do not pad with speculation.
4. Be concise and direct. Executives read in 3 minutes.
5. Use professional, confident, present-tense language.
6. NEVER generate generic, templated, or filler content when research data is absent
   or unrelated to the topic. If no verified data exists for a section, that section
   MUST state "No data available this week." only — nothing else.
7. If the research data provided is empty, contains zero findings, or is clearly
   unrelated to the requested topic, you MUST refuse to write a substantive briefing.
   Output ONLY the structured "No Sufficient Data" template provided to you.

## Required sections (use these exact Markdown headings):
### Executive Summary
### Competitor Pricing Moves
### Product Launches
### Market Signals
### Key Insights & Recommendations
### Sources

## Source citation format
Number each unique URL and reference it inline: [Source 1], [Source 2], etc.
At the end, list all sources in a numbered "Sources" section.

Return ONLY the Markdown briefing. No JSON, no preamble.
"""


def _build_llm(settings=None):
    settings = settings or get_settings()
    kwargs: Dict[str, Any] = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.3,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def _analysis_to_prompt(
    analysis: AnalysisResult,
    sources: List[Source],
) -> str:
    """Convert analysis + sources to a numbered prompt for the Writer LLM."""

    # Build source index
    url_to_idx: Dict[str, int] = {}
    source_lines: List[str] = []
    idx = 1
    for src in sources:
        if src.url and not src.failed:
            if src.url not in url_to_idx:
                url_to_idx[src.url] = idx
                source_lines.append(f"[Source {idx}] {src.url} — {src.title}")
                idx += 1

    def refs(source_urls: List[str]) -> str:
        nums = [str(url_to_idx[u]) for u in source_urls if u in url_to_idx]
        if not nums:
            return "[no source]"
        return " ".join(f"[Source {n}]" for n in nums)

    lines = [f"## Topic: {analysis.topic}\n"]

    # Pricing moves
    if analysis.pricing_moves:
        lines.append("### Competitor Pricing Data")
        for pm in analysis.pricing_moves:
            src_refs = refs(
                [url for c in pm.citations for url in c.sources]
            )
            lines.append(f"- **{pm.competitor}**: {pm.description} {src_refs}")

    # Product launches
    if analysis.product_launches:
        lines.append("\n### Product Launches Data")
        for pl in analysis.product_launches:
            src_refs = refs(
                [url for c in pl.citations for url in c.sources]
            )
            lines.append(
                f"- **{pl.competitor} — {pl.product_name}**: {pl.description} {src_refs}"
            )

    # Market signals
    if analysis.market_signals:
        lines.append("\n### Market Signals Data")
        for ms in analysis.market_signals:
            src_refs = refs(
                [url for c in ms.citations for url in c.sources]
            )
            lines.append(f"- **{ms.signal}**: {ms.detail} {src_refs}")

    # Insights
    if analysis.insights:
        lines.append("\n### Insights Data")
        for ins in analysis.insights:
            src_refs = refs(
                [url for c in ins.citations for url in c.sources]
            )
            lines.append(
                f"- [{ins.type.upper()}] **{ins.title}**: {ins.detail} {src_refs}"
            )

    # Recommendation
    if analysis.recommendation:
        lines.append(f"\n### Recommendation\n{analysis.recommendation}")

    # Source index
    if source_lines:
        lines.append("\n### Source Index for Citation")
        lines.extend(source_lines)

    return "\n".join(lines)


def _build_error_briefing(topic: str, errors: List[str], meta: RunMetadata) -> str:
    error_text = "\n".join(f"- {e}" for e in errors) if errors else "- Unknown error"
    return (
        f"# Competitive Intelligence Briefing — {topic}\n\n"
        f"**⚠️ Briefing could not be completed due to errors.**\n\n"
        f"### Errors\n{error_text}\n\n"
        f"### Run Metadata\n"
        f"- Run ID: {meta.run_id}\n"
        f"- Started: {meta.started_at}\n"
        f"- Steps: {meta.steps_taken}\n"
    )


def _build_insufficient_data_briefing(
    topic: str,
    meta: RunMetadata,
    abort_reason: str,
    sources_found: int,
    min_trusted: int,
) -> str:
    """
    Return a structured, non-hallucinated 'No Sufficient Data' briefing.

    This is the ONLY output produced when the researcher found fewer trusted
    sources than MIN_TRUSTED_SOURCES. No LLM is called — content is deterministic.
    """
    return (
        f"# Competitive Intelligence Briefing — {topic}\n\n"
        f"> **⚠️ Insufficient Data — Briefing Not Generated**\n\n"
        f"The pipeline was halted because the research phase could not collect "
        f"enough verified, trusted sources to produce a reliable briefing.\n\n"
        f"| Detail | Value |\n"
        f"|--------|-------|\n"
        f"| Topic | `{topic}` |\n"
        f"| Trusted sources found | {sources_found} |\n"
        f"| Minimum required | {min_trusted} |\n"
        f"| Run ID | `{meta.run_id}` |\n"
        f"| Started | {meta.started_at} |\n"
        f"| Duration | {meta.duration_seconds:.1f}s |\n\n"
        f"### Why no briefing was produced\n\n"
        f"{abort_reason}\n\n"
        f"### Recommended actions\n\n"
        f"- Broaden the search topic and try again.\n"
        f"- Verify that `TAVILY_API_KEY` is valid and has remaining credits.\n"
        f"- Increase `MAX_SOURCES` or `SEARCH_QUERIES_PER_RUN` in your `.env`.\n"
        f"- If this topic is niche, consider adding domain-specific seed URLs.\n\n"
        f"### Executive Summary\n\nNo data available this week.\n\n"
        f"### Competitor Pricing Moves\n\nNo data available this week.\n\n"
        f"### Product Launches\n\nNo data available this week.\n\n"
        f"### Market Signals\n\nNo data available this week.\n\n"
        f"### Key Insights & Recommendations\n\nNo data available this week.\n\n"
        f"### Sources\n\nNo trusted sources were collected for this run.\n"
    )


def _build_validation_failed_briefing(
    topic: str,
    meta: RunMetadata,
    validation_raw: Optional[dict],
) -> str:
    """
    Return a deterministic, structured 'No sufficient trusted data found'
    Markdown briefing when the Validator node has rejected the research batch.

    No LLM is called. Content is derived purely from the ValidationResult.
    """
    # Extract validation details
    failure_reason = "Validation did not pass."
    failure_code = "unknown"
    valid_source_count = 0
    topic_found = False
    rule_rows = ""

    if validation_raw:
        failure_reason = validation_raw.get("failure_reason") or failure_reason
        failure_code = validation_raw.get("failure_code") or failure_code
        valid_source_count = validation_raw.get("valid_source_count", 0)
        topic_found = validation_raw.get("topic_found_in_sources", False)
        rules = validation_raw.get("rule_results", [])
        if rules:
            rule_rows = "\n".join(
                f"| `{r['rule_name']}` | {'✅ Pass' if r['passed'] else '❌ Fail'} "
                f"| {r.get('reason', '')} |"
                for r in rules
            )

    duration_str = (
        f"{meta.duration_seconds:.1f}s" if meta.duration_seconds is not None else "—"
    )

    rules_table = (
        f"\n### Validation Rule Details\n\n"
        f"| Rule | Result | Reason |\n"
        f"|------|--------|--------|\n"
        f"{rule_rows}\n"
        if rule_rows else ""
    )

    return (
        f"# Competitive Intelligence Briefing — {topic}\n\n"
        f"> **⚠️ No Sufficient Trusted Data Found**\n\n"
        f"The Validator node stopped the pipeline before analysis because the "
        f"research results did not meet the required quality threshold.\n\n"
        f"| Detail | Value |\n"
        f"|--------|-------|\n"
        f"| Topic | `{topic}` |\n"
        f"| Failure code | `{failure_code}` |\n"
        f"| Valid sources found | {valid_source_count} |\n"
        f"| Topic found in sources | {'Yes' if topic_found else 'No'} |\n"
        f"| Run ID | `{meta.run_id}` |\n"
        f"| Started | {meta.started_at} |\n"
        f"| Duration | {duration_str} |\n\n"
        f"### Reason\n\n"
        f"{failure_reason}\n"
        f"{rules_table}\n"
        f"### Recommended actions\n\n"
        f"- Ensure the topic is specific enough to return relevant results "
        f"(e.g. 'Salesforce CRM pricing 2025' rather than just 'CRM').\n"
        f"- Check that `TAVILY_API_KEY` is valid and has remaining credits.\n"
        f"- Increase `MAX_SOURCES` or `SEARCH_QUERIES_PER_RUN` in your `.env`.\n"
        f"- Lower `RELEVANCE_THRESHOLD` (current behaviour requires sources to "
        f"mention topic keywords).\n"
        f"- Increase `MIN_VALID_SOURCES` tolerance or broaden the search topic.\n\n"
        f"### Executive Summary\n\nNo sufficient trusted data found.\n\n"
        f"### Competitor Pricing Moves\n\nNo data available this week.\n\n"
        f"### Product Launches\n\nNo data available this week.\n\n"
        f"### Market Signals\n\nNo data available this week.\n\n"
        f"### Key Insights & Recommendations\n\nNo data available this week.\n\n"
        f"### Sources\n\nNo valid sources passed validation for this run.\n"
    )


def writer_node(state: BriefingState) -> Dict[str, Any]:
    """
    LangGraph node: Writer Agent.

    Reads: analysis_result, research_result, topic, abort, errors, run_metadata
    Writes: briefing_output, writer_status, step_count, run_metadata
    """
    settings = get_settings()
    errors: list = list(state.get("errors", []))
    step_count: int = state.get("step_count", 0) + 1
    topic: str = state.get("topic", "Unknown Topic")

    meta_raw: dict = dict(state.get("run_metadata") or {})
    meta_raw["writer_status"] = AgentStatus.RUNNING
    meta_raw["steps_taken"] = step_count

    # Reconstruct RunMetadata — fill in sensible defaults for missing fields
    try:
        run_meta = RunMetadata.model_validate(meta_raw)
    except Exception:
        run_meta = RunMetadata(topic=topic)

    run_meta.completed_at = datetime.utcnow()
    if run_meta.started_at:
        run_meta.duration_seconds = (
            run_meta.completed_at - run_meta.started_at
        ).total_seconds()
    run_meta.errors = errors

    # Retrieve sources from research
    research_raw = state.get("research_result") or {}
    research_sources: List[Source] = []
    failed_sources: List[Source] = []
    if research_raw:
        try:
            research = ResearchResult.model_validate(research_raw)
            research_sources = research.sources
            failed_sources = research.failed_sources
        except Exception:
            pass

    # ── Validation failure gate ───────────────────────────────────────────────
    # When the Validator node rejected the research batch, produce a structured
    # 'No sufficient trusted data found' response. No LLM call is made.
    if state.get("validation_failed"):
        logger.warning(
            "Writer: validation_failed flag is set — returning structured "
            "'No Sufficient Trusted Data' response without calling LLM."
        )
        validation_raw = state.get("validation_result")
        markdown = _build_validation_failed_briefing(
            topic=topic,
            meta=run_meta,
            validation_raw=validation_raw,
        )
        run_meta.writer_status = AgentStatus.DONE
        run_meta.all_claims_cited = True  # no claims were made

        briefing = BriefingOutput(
            run_metadata=run_meta,
            executive_summary="No sufficient trusted data found.",
            raw_markdown=markdown,
            all_sources=research_sources,
            failed_sources=failed_sources,
        )
        return {
            "step_count": step_count,
            "writer_status": AgentStatus.DONE,
            "briefing_output": briefing.model_dump(mode="json"),
            "run_metadata": run_meta.model_dump(mode="json"),
            "errors": errors,
        }

    # ── Insufficient sources gate (legacy researcher-level check) ─────────────
    # When the researcher found fewer trusted sources than the configured minimum,
    # we MUST NOT call the LLM. Produce a deterministic structured response instead.
    if state.get("insufficient_sources"):
        logger.warning(
            "Writer: insufficient_sources flag is set — returning structured "
            "'No Sufficient Data' response without calling LLM."
        )
        settings = get_settings()
        abort_reason = state.get("abort_reason", "Insufficient trusted sources.")
        sources_found = len(research_sources)
        min_trusted = state.get("min_trusted_sources", settings.min_trusted_sources)

        markdown = _build_insufficient_data_briefing(
            topic=topic,
            meta=run_meta,
            abort_reason=abort_reason,
            sources_found=sources_found,
            min_trusted=min_trusted,
        )
        run_meta.writer_status = AgentStatus.DONE
        run_meta.all_claims_cited = True  # no claims were made

        briefing = BriefingOutput(
            run_metadata=run_meta,
            executive_summary="No sufficient data found.",
            raw_markdown=markdown,
            all_sources=research_sources,
            failed_sources=failed_sources,
        )
        return {
            "step_count": step_count,
            "writer_status": AgentStatus.DONE,
            "briefing_output": briefing.model_dump(mode="json"),
            "run_metadata": run_meta.model_dump(mode="json"),
            "errors": errors,
        }

    # Check abort (non-insufficient-sources abort) — still produce a degraded briefing
    if state.get("abort"):
        logger.warning("Writer running in degraded mode (abort=True).")
        markdown = _build_error_briefing(topic, errors, run_meta)
        run_meta.writer_status = AgentStatus.DONE
        briefing = BriefingOutput(
            run_metadata=run_meta,
            executive_summary="Briefing could not be completed. See run metadata for errors.",
            raw_markdown=markdown,
            all_sources=research_sources,
            failed_sources=failed_sources,
        )
        return {
            "step_count": step_count,
            "writer_status": AgentStatus.DONE,
            "briefing_output": briefing.model_dump(mode="json"),
            "run_metadata": run_meta.model_dump(mode="json"),
            "errors": errors,
        }

    analysis_raw = state.get("analysis_result")
    if not analysis_raw:
        logger.warning("Writer: no analysis_result — producing empty briefing.")
        markdown = _build_error_briefing(topic, ["No analysis data available."], run_meta)
        run_meta.writer_status = AgentStatus.DONE
        briefing = BriefingOutput(
            run_metadata=run_meta,
            raw_markdown=markdown,
            all_sources=research_sources,
            failed_sources=failed_sources,
        )
        return {
            "step_count": step_count,
            "writer_status": AgentStatus.DONE,
            "briefing_output": briefing.model_dump(mode="json"),
            "run_metadata": run_meta.model_dump(mode="json"),
        }

    logger.info("Writer composing briefing for topic: %r", topic)

    try:
        analysis = AnalysisResult.model_validate(analysis_raw)
        llm = _build_llm(settings)

        prompt_text = _analysis_to_prompt(analysis, research_sources)
        response = llm.invoke(
            [
                SystemMessage(content=WRITER_SYSTEM),
                HumanMessage(content=prompt_text),
            ]
        )

        markdown = response.content.strip()
        logger.info("Writer produced %d chars of Markdown.", len(markdown))

        # Check all claims are cited (heuristic: no [no source] in output)
        all_claims_cited = "[no source]" not in markdown
        run_meta.all_claims_cited = all_claims_cited

        run_meta.writer_status = AgentStatus.DONE
        run_meta.coordinator_status = AgentStatus.DONE
        run_meta.researcher_status = AgentStatus.DONE
        run_meta.analyst_status = AgentStatus.DONE

        briefing = BriefingOutput(
            run_metadata=run_meta,
            executive_summary=_extract_section(markdown, "Executive Summary"),
            competitor_pricing=analysis.pricing_moves,
            product_launches=analysis.product_launches,
            market_signals=analysis.market_signals,
            insights=analysis.insights,
            recommendation=analysis.recommendation,
            all_sources=research_sources,
            failed_sources=failed_sources,
            raw_markdown=markdown,
        )

        return {
            "step_count": step_count,
            "writer_status": AgentStatus.DONE,
            "briefing_output": briefing.model_dump(mode="json"),
            "run_metadata": run_meta.model_dump(mode="json"),
            "errors": errors,
        }

    except Exception as exc:
        msg = f"Writer agent failed: {exc}"
        logger.exception(msg)
        errors.append(msg)
        run_meta.writer_status = AgentStatus.FAILED

        markdown = _build_error_briefing(topic, errors, run_meta)
        briefing = BriefingOutput(
            run_metadata=run_meta,
            raw_markdown=markdown,
            all_sources=research_sources,
            failed_sources=failed_sources,
        )

        return {
            "step_count": step_count,
            "writer_status": AgentStatus.FAILED,
            "briefing_output": briefing.model_dump(mode="json"),
            "run_metadata": run_meta.model_dump(mode="json"),
            "errors": errors,
        }


def _extract_section(markdown: str, heading: str) -> str:
    """Extract the content of a Markdown section by heading name."""
    lines = markdown.splitlines()
    in_section = False
    result: List[str] = []
    for line in lines:
        if line.strip().lstrip("#").strip().lower() == heading.lower():
            in_section = True
            continue
        if in_section:
            if line.startswith("#"):
                break
            result.append(line)
    return "\n".join(result).strip()
