"""
models.py – Pydantic schemas for shared agent state, research results,
analysis output, and the final briefing.

All inter-agent data exchange flows through these typed models,
ensuring every factual claim is traceable to a source URL.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing_extensions import TypedDict


# ── Enumerations ──────────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationFailureReason(str, Enum):
    """Enumerated reasons why the Validator node may reject a research batch."""
    INSUFFICIENT_SOURCES = "insufficient_sources"
    TOPIC_NOT_FOUND = "topic_not_found"
    LOW_RELEVANCE = "low_relevance"
    ALL_SOURCES_FAILED = "all_sources_failed"
    NO_FINDINGS = "no_findings"


class ClaimVerification(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


# ── Source / Citation Models ──────────────────────────────────────────────────

class Source(BaseModel):
    """A single web source retrieved during research."""

    url: str = Field(..., description="Canonical URL of the source")
    title: str = Field(default="", description="Page or article title")
    snippet: str = Field(default="", description="Relevant excerpt from the source")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    failed: bool = Field(default=False, description="True if fetch/scrape failed")
    failure_reason: Optional[str] = Field(default=None)

    @field_validator("url", mode="before")
    @classmethod
    def coerce_url(cls, v: Any) -> str:
        return str(v)


class Citation(BaseModel):
    """Links a claim to one or more sources."""

    claim: str
    sources: List[str] = Field(..., description="List of source URLs")
    verified: ClaimVerification = ClaimVerification.VERIFIED


# ── Research Models ───────────────────────────────────────────────────────────

class ResearchItem(BaseModel):
    """A single factual finding from research."""

    category: str = Field(
        ...,
        description="One of: pricing, product_launch, market_signal, other",
    )
    content: str = Field(..., description="Factual description of the finding")
    source_urls: List[str] = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ResearchResult(BaseModel):
    """Aggregated output from the Researcher Agent."""

    topic: str
    items: List[ResearchItem] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    failed_sources: List[Source] = Field(default_factory=list)
    queries_executed: List[str] = Field(default_factory=list)
    total_sources_collected: int = 0
    sources_skipped: int = 0


# ── Validation Models ─────────────────────────────────────────────────────────

class ValidationRuleResult(BaseModel):
    """Outcome of a single validation rule."""

    rule_name: str = Field(..., description="Human-readable rule identifier")
    passed: bool
    reason: str = Field(default="", description="Explanation when rule fails")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional numeric details (e.g. counts, scores) for logging",
    )


class ValidationResult(BaseModel):
    """
    Aggregated output from the Validator node.

    `passed` is True only when ALL rules pass. The first failing rule's
    `reason` is promoted to the top-level `failure_reason` field.
    """

    passed: bool
    rule_results: List[ValidationRuleResult] = Field(default_factory=list)
    failure_reason: Optional[str] = Field(
        default=None,
        description="Human-readable summary of why validation failed",
    )
    failure_code: Optional[str] = Field(
        default=None,
        description="Machine-readable failure code (ValidationFailureReason value)",
    )
    valid_source_count: int = Field(
        default=0,
        description="Number of sources that passed all source-level checks",
    )
    topic_found_in_sources: bool = Field(
        default=False,
        description="True when at least one source references the requested topic",
    )


# ── Analysis Models ───────────────────────────────────────────────────────────

class Insight(BaseModel):
    """A single business insight derived from research."""

    type: str = Field(
        ..., description="One of: trend, risk, opportunity, threat, observation"
    )
    title: str
    detail: str
    supporting_items: List[str] = Field(
        default_factory=list,
        description="ResearchItem content strings this insight is based on",
    )
    citations: List[Citation] = Field(default_factory=list)


class PricingMove(BaseModel):
    competitor: str
    description: str
    citations: List[Citation] = Field(default_factory=list)


class ProductLaunch(BaseModel):
    competitor: str
    product_name: str
    description: str
    citations: List[Citation] = Field(default_factory=list)


class MarketSignal(BaseModel):
    signal: str
    detail: str
    citations: List[Citation] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Aggregated output from the Analyst Agent."""

    topic: str
    pricing_moves: List[PricingMove] = Field(default_factory=list)
    product_launches: List[ProductLaunch] = Field(default_factory=list)
    market_signals: List[MarketSignal] = Field(default_factory=list)
    insights: List[Insight] = Field(default_factory=list)
    recommendation: str = Field(
        default="", description="Top strategic recommendation"
    )
    all_citations: List[Citation] = Field(default_factory=list)
    unverified_claims_omitted: int = Field(
        default=0, description="Count of claims dropped due to missing sources"
    )


# ── Briefing Models ───────────────────────────────────────────────────────────

class RunMetadata(BaseModel):
    """Execution metadata attached to every briefing."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    steps_taken: int = 0
    total_sources: int = 0
    sources_skipped: int = 0
    total_tokens: int = 0
    coordinator_status: AgentStatus = AgentStatus.PENDING
    researcher_status: AgentStatus = AgentStatus.PENDING
    validator_status: AgentStatus = AgentStatus.PENDING
    analyst_status: AgentStatus = AgentStatus.PENDING
    writer_status: AgentStatus = AgentStatus.PENDING
    all_claims_cited: bool = True
    errors: List[str] = Field(default_factory=list)


class BriefingSection(BaseModel):
    title: str
    content: str
    citations: List[Citation] = Field(default_factory=list)


class BriefingOutput(BaseModel):
    """The final structured competitive intelligence briefing."""

    run_metadata: RunMetadata
    executive_summary: str = ""
    competitor_pricing: List[PricingMove] = Field(default_factory=list)
    product_launches: List[ProductLaunch] = Field(default_factory=list)
    market_signals: List[MarketSignal] = Field(default_factory=list)
    insights: List[Insight] = Field(default_factory=list)
    recommendation: str = ""
    all_sources: List[Source] = Field(default_factory=list)
    failed_sources: List[Source] = Field(default_factory=list)
    raw_markdown: str = Field(
        default="", description="Complete briefing in Markdown format"
    )


# ── LangGraph Shared State ────────────────────────────────────────────────────

class BriefingState(TypedDict, total=False):
    """
    Shared mutable state passed between all nodes in the LangGraph graph.

    Using TypedDict so LangGraph can merge partial updates correctly.
    """

    # Input
    topic: str

    # Execution control
    step_count: int
    max_steps: int
    max_sources: int
    abort: bool
    abort_reason: str

    # Source quality gate
    min_trusted_sources: int        # minimum trusted sources required (from settings)
    insufficient_sources: bool      # True when researcher found fewer than min_trusted_sources

    # Per-agent status
    coordinator_status: str
    researcher_status: str
    validator_status: str
    analyst_status: str
    writer_status: str

    # Agent outputs (stored as dicts for JSON serialisation in graph)
    research_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]   # ValidationResult dict
    analysis_result: Optional[Dict[str, Any]]
    briefing_output: Optional[Dict[str, Any]]

    # Validation gate flags
    validation_failed: bool   # True when validator rejected the research batch
    min_valid_sources: int    # passed in from settings via coordinator
    relevance_threshold: float

    # Run metadata (updated incrementally)
    run_metadata: Optional[Dict[str, Any]]

    # Errors accumulated across agents
    errors: List[str]
