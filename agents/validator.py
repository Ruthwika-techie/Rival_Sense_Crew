"""
agents/validator.py – Validator Node

Position in pipeline:
    coordinator → researcher → [validator] → analyst → writer

Responsibilities:
  - Run a configurable set of validation rules against the ResearchResult
    produced by the Researcher node.
  - Stop the pipeline before the Analyst/Writer when validation fails.
  - Return a fully structured ValidationResult that the Writer uses to
    generate a 'No sufficient trusted data found' response.
  - Never call an LLM — all logic is deterministic and rule-based.
  - Be modular: new rules are added by implementing _ValidationRule and
    appending them to _build_rules().

Rules (evaluated in order, short-circuit on first failure):
  1. AllSourcesFailedRule  — fail fast if every single source is failed.
  2. MinValidSourcesRule   — at least N sources must be non-failed with a
                             non-empty snippet AND meet the relevance threshold.
  3. TopicRelevanceRule    — at least one valid source must mention a keyword
                             from the requested topic.
  4. NoFindingsRule        — research must contain at least one sourced finding.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from config import get_settings
from models import (
    AgentStatus,
    BriefingState,
    ResearchResult,
    Source,
    ValidationFailureReason,
    ValidationResult,
    ValidationRuleResult,
)

logger = logging.getLogger(__name__)


# ── Relevance helper ──────────────────────────────────────────────────────────

def _topic_keywords(topic: str) -> List[str]:
    """
    Extract meaningful keywords from a topic string.

    Strips common stop words so single-word checks don't pass on generic
    words like 'the', 'and', 'of'.
    """
    STOP = {
        "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
        "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "about", "vs", "versus",
    }
    words = re.findall(r"[a-z0-9]+", topic.lower())
    return [w for w in words if w not in STOP and len(w) > 1]


def _relevance_score(source: Source, keywords: List[str]) -> float:
    """
    Return a relevance score in [0, 1].

    Score = fraction of topic keywords that appear in the source's
    combined title + snippet text (case-insensitive substring match).
    Returns 0.0 if there are no keywords or the source has no text.
    """
    if not keywords:
        return 1.0  # no keywords → every source is relevant
    text = (source.title + " " + source.snippet).lower()
    if not text.strip():
        return 0.0
    hits = sum(1 for kw in keywords if kw in text)
    return hits / len(keywords)


# ── Base rule interface ───────────────────────────────────────────────────────

class _ValidationRule(ABC):
    """
    Abstract base class for a single validation rule.

    Subclass this and implement `check` to add a new rule.
    The rule name is used for logging and in the ValidationRuleResult.
    """

    name: str = "unnamed_rule"

    @abstractmethod
    def check(
        self,
        topic: str,
        research: ResearchResult,
        keywords: List[str],
        min_valid_sources: int,
        relevance_threshold: float,
    ) -> ValidationRuleResult:
        """Run the rule and return a ValidationRuleResult."""
        ...


# ── Concrete rules ────────────────────────────────────────────────────────────

class AllSourcesFailedRule(_ValidationRule):
    """Fail immediately if every retrieved source has failed=True."""

    name = "all_sources_failed"

    def check(self, topic, research, keywords, min_valid_sources, relevance_threshold):
        all_sources = research.sources
        if not all_sources:
            return ValidationRuleResult(
                rule_name=self.name,
                passed=False,
                reason="No sources were collected at all.",
                details={"total_sources": 0},
            )
        all_failed = all(s.failed for s in all_sources)
        if all_failed:
            return ValidationRuleResult(
                rule_name=self.name,
                passed=False,
                reason=(
                    f"All {len(all_sources)} collected source(s) are marked as failed. "
                    "Check your TAVILY_API_KEY and network connectivity."
                ),
                details={"total_sources": len(all_sources), "failed": len(all_sources)},
            )
        return ValidationRuleResult(
            rule_name=self.name,
            passed=True,
            details={"total_sources": len(all_sources)},
        )


class MinValidSourcesRule(_ValidationRule):
    """
    Require at least `min_valid_sources` sources that are:
      - not failed
      - have a non-empty snippet
      - achieve relevance_score >= relevance_threshold
    """

    name = "min_valid_sources"

    def check(self, topic, research, keywords, min_valid_sources, relevance_threshold):
        valid_sources: List[Source] = []
        for src in research.sources:
            if src.failed:
                continue
            if not src.snippet or not src.snippet.strip():
                continue
            score = _relevance_score(src, keywords)
            if score >= relevance_threshold:
                valid_sources.append(src)

        count = len(valid_sources)
        if count < min_valid_sources:
            return ValidationRuleResult(
                rule_name=self.name,
                passed=False,
                reason=(
                    f"Only {count} valid source(s) found for topic '{topic}'; "
                    f"need at least {min_valid_sources}. "
                    f"A valid source must be non-failed, have content, and achieve "
                    f"relevance ≥ {relevance_threshold:.0%}."
                ),
                details={
                    "valid_count": count,
                    "required": min_valid_sources,
                    "relevance_threshold": relevance_threshold,
                },
            )
        return ValidationRuleResult(
            rule_name=self.name,
            passed=True,
            details={"valid_count": count, "required": min_valid_sources},
        )


class TopicRelevanceRule(_ValidationRule):
    """
    Verify that at least one valid source actually mentions the requested topic.

    This guards against cases where searches return results but none are
    about the requested company or market.
    """

    name = "topic_relevance"

    def check(self, topic, research, keywords, min_valid_sources, relevance_threshold):
        if not keywords:
            # Cannot verify relevance without keywords — pass with a note
            return ValidationRuleResult(
                rule_name=self.name,
                passed=True,
                reason="No topic keywords extracted; relevance check skipped.",
            )

        # Check valid (non-failed, non-empty) sources for ANY keyword hit
        found = False
        for src in research.sources:
            if src.failed:
                continue
            if not src.snippet and not src.title:
                continue
            if _relevance_score(src, keywords) > 0:
                found = True
                break

        if not found:
            return ValidationRuleResult(
                rule_name=self.name,
                passed=False,
                reason=(
                    f"None of the retrieved sources appear to be about '{topic}'. "
                    f"Keywords checked: {keywords}. "
                    "The search may have returned unrelated results."
                ),
                details={"keywords": keywords, "topic": topic},
            )
        return ValidationRuleResult(
            rule_name=self.name,
            passed=True,
            details={"keywords": keywords},
        )


class NoFindingsRule(_ValidationRule):
    """
    Require the researcher to have extracted at least one sourced finding.

    If the LLM extracted zero findings from the sources, analysis would
    produce empty output — nothing to write a briefing about.
    """

    name = "no_findings"

    def check(self, topic, research, keywords, min_valid_sources, relevance_threshold):
        sourced = [item for item in research.items if item.source_urls]
        if not sourced:
            return ValidationRuleResult(
                rule_name=self.name,
                passed=False,
                reason=(
                    f"Researcher extracted 0 sourced findings for '{topic}'. "
                    "Sources may be present but contain no usable intelligence."
                ),
                details={"total_findings": len(research.items), "sourced_findings": 0},
            )
        return ValidationRuleResult(
            rule_name=self.name,
            passed=True,
            details={"sourced_findings": len(sourced)},
        )


# ── Rule registry ─────────────────────────────────────────────────────────────

def _build_rules() -> List[_ValidationRule]:
    """
    Return the ordered list of validation rules.

    To add a new rule: implement _ValidationRule, then append an instance here.
    Rules are evaluated in order; the first failure stops evaluation.
    """
    return [
        AllSourcesFailedRule(),
        MinValidSourcesRule(),
        TopicRelevanceRule(),
        NoFindingsRule(),
    ]


# ── Validator node ────────────────────────────────────────────────────────────

def validator_node(state: BriefingState) -> Dict[str, Any]:
    """
    LangGraph node: Validator.

    Position: researcher → validator → (analyst | writer)

    Reads:  research_result, topic, min_valid_sources, relevance_threshold, abort
    Writes: validation_result, validation_failed, validator_status,
            abort, abort_reason, step_count, run_metadata, errors
    """
    settings = get_settings()
    errors: list = list(state.get("errors", []))
    step_count: int = state.get("step_count", 0) + 1
    topic: str = state.get("topic", "")
    min_valid_sources: int = state.get("min_valid_sources", settings.min_valid_sources)
    relevance_threshold: float = state.get("relevance_threshold", settings.relevance_threshold)

    meta: dict = dict(state.get("run_metadata") or {})
    meta["validator_status"] = AgentStatus.RUNNING

    # ── Pass-through if already aborted upstream ──────────────────────────────
    if state.get("abort"):
        logger.info("Validator skipped (abort flag already set).")
        return {
            "step_count": step_count,
            "validator_status": AgentStatus.SKIPPED,
            "validation_failed": False,
            "run_metadata": meta,
        }

    # ── Require research to be present ───────────────────────────────────────
    research_raw = state.get("research_result")
    if not research_raw:
        msg = "Validator: no research_result in state — cannot validate."
        logger.error(msg)
        errors.append(msg)
        meta["validator_status"] = AgentStatus.FAILED
        return {
            "step_count": step_count,
            "validator_status": AgentStatus.FAILED,
            "validation_failed": True,
            "abort": True,
            "abort_reason": msg,
            "run_metadata": meta,
            "errors": errors,
        }

    try:
        research = ResearchResult.model_validate(research_raw)
    except Exception as exc:
        msg = f"Validator: could not parse research_result: {exc}"
        logger.error(msg)
        errors.append(msg)
        meta["validator_status"] = AgentStatus.FAILED
        return {
            "step_count": step_count,
            "validator_status": AgentStatus.FAILED,
            "validation_failed": True,
            "abort": True,
            "abort_reason": msg,
            "run_metadata": meta,
            "errors": errors,
        }

    keywords = _topic_keywords(topic)
    logger.info(
        "Validator starting — topic: %r  keywords: %s  "
        "min_valid_sources: %d  relevance_threshold: %.2f",
        topic, keywords, min_valid_sources, relevance_threshold,
    )

    # ── Run all rules ─────────────────────────────────────────────────────────
    rules = _build_rules()
    rule_results: List[ValidationRuleResult] = []
    first_failure: ValidationRuleResult | None = None

    for rule in rules:
        result = rule.check(
            topic=topic,
            research=research,
            keywords=keywords,
            min_valid_sources=min_valid_sources,
            relevance_threshold=relevance_threshold,
        )
        rule_results.append(result)
        logger.info(
            "  Rule %-25s → %s%s",
            result.rule_name,
            "PASS" if result.passed else "FAIL",
            f" | {result.reason}" if not result.passed else "",
        )
        if not result.passed and first_failure is None:
            first_failure = result
            break  # short-circuit: stop at first failing rule

    # ── Count valid sources for the ValidationResult summary ─────────────────
    valid_source_count = sum(
        1 for s in research.sources
        if not s.failed
        and s.snippet
        and s.snippet.strip()
        and _relevance_score(s, keywords) >= relevance_threshold
    )
    topic_found = any(
        _relevance_score(s, keywords) > 0
        for s in research.sources
        if not s.failed
    )

    passed = first_failure is None

    # Map rule name → ValidationFailureReason code
    _RULE_TO_CODE: dict[str, str] = {
        AllSourcesFailedRule.name:  ValidationFailureReason.ALL_SOURCES_FAILED,
        MinValidSourcesRule.name:   ValidationFailureReason.INSUFFICIENT_SOURCES,
        TopicRelevanceRule.name:    ValidationFailureReason.TOPIC_NOT_FOUND,
        NoFindingsRule.name:        ValidationFailureReason.NO_FINDINGS,
    }

    validation = ValidationResult(
        passed=passed,
        rule_results=rule_results,
        failure_reason=first_failure.reason if first_failure else None,
        failure_code=(
            _RULE_TO_CODE.get(first_failure.rule_name) if first_failure else None
        ),
        valid_source_count=valid_source_count,
        topic_found_in_sources=topic_found,
    )

    if passed:
        logger.info(
            "Validator PASSED — %d valid source(s), topic found: %s",
            valid_source_count, topic_found,
        )
        meta["validator_status"] = AgentStatus.DONE
        return {
            "step_count": step_count,
            "validator_status": AgentStatus.DONE,
            "validation_result": validation.model_dump(mode="json"),
            "validation_failed": False,
            "run_metadata": meta,
            "errors": errors,
        }

    else:
        abort_reason = (
            f"Validation failed [{first_failure.rule_name}]: {first_failure.reason}"
        )
        logger.warning("Validator FAILED — %s", abort_reason)
        errors.append(abort_reason)
        meta["validator_status"] = AgentStatus.FAILED

        return {
            "step_count": step_count,
            "validator_status": AgentStatus.FAILED,
            "validation_result": validation.model_dump(mode="json"),
            "validation_failed": True,
            "abort": True,
            "abort_reason": abort_reason,
            "run_metadata": meta,
            "errors": errors,
        }
