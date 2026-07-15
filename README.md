# MarketPulse — AI-Powered Competitive Intelligence Briefing Crew

> A multi-agent system that searches the web, validates source quality, analyses competitor activity, and produces a structured weekly briefing — with every claim cited — in under 3 minutes.

---

## Overview

MarketPulse is built to the **Project 02 · Competitive Intelligence Briefing Crew** specification. It uses a LangGraph pipeline of five specialised agents:

| Agent | Role |
|-------|------|
| **Coordinator** | Validates input, enforces step/source limits, routes workflow |
| **Researcher** | Runs targeted Tavily searches, optionally enriches with Firecrawl, extracts factual findings |
| **Validator** | Deterministic quality gate — checks source count, relevance, and finding coverage before analysis |
| **Analyst** | Analyses findings into pricing moves, product launches, market signals, insights |
| **Writer** | Produces a professional Markdown briefing with inline citations |

Every factual claim in the output is linked to a source URL. Unverified claims are omitted. Source failures are logged and skipped gracefully — the briefing is still produced.

---

## Architecture

```
START
  │
  ▼
coordinator ──(abort)──────────────────────────────────────┐
  │                                                         │
  ▼                                                         │
researcher ──(abort/fail)──────────────────────────────┐   │
  │                                                     │   │
  ▼                                                     │   │
validator ──(validation_failed/abort)──────────────┐   │   │
  │                                                │   │   │
  ▼                                                ▼   ▼   ▼
analyst ────────────────────────────────────────► writer
                                                      │
                                                     END
```

**Shared state** (`BriefingState` TypedDict) flows through every node. Each agent reads what it needs and writes its output back. The graph is a compiled `StateGraph` from LangGraph.

### Key design decisions

- **Coordinator is deterministic** — no LLM call, just validation and limit checks. Fast, predictable.
- **Researcher uses two LLM calls**: one to generate targeted queries, one to parse snippets into structured findings.
- **Validator is deterministic** — no LLM call. Runs four sequential rules (AllSourcesFailed → MinValidSources → TopicRelevance → NoFindings) and short-circuits on the first failure. Produces a structured `ValidationResult` that the Writer uses when rejecting a run.
- **Analyst uses one LLM call**: converts findings to cited analysis. Any finding without a source URL is dropped.
- **Writer uses one LLM call**: produces full Markdown with `[Source N]` inline citations.
- **Graceful degradation**: every agent catches exceptions; the writer always produces output, even when upstream agents fail.

---

## Project Structure

```
rivalsense-crew/
├── app.py              # Streamlit frontend
├── graph.py            # LangGraph workflow: build_graph(), run_briefing(), stream_briefing()
├── models.py           # Pydantic models + BriefingState TypedDict
├── tools.py            # TavilySearchTool, FirecrawlScraperTool
├── config.py           # Settings loaded from .env via pydantic-settings
├── agents/
│   ├── __init__.py
│   ├── coordinator.py  # Coordinator node
│   ├── researcher.py   # Researcher node
│   ├── validator.py    # Validator node (deterministic quality gate)
│   ├── analyst.py      # Analyst node
│   └── writer.py       # Writer node
├── tests/
│   ├── test_models.py  # Pydantic model tests
│   ├── test_tools.py   # Tavily + Firecrawl tool tests (mocked)
│   ├── test_agents.py  # All 5 agent node tests (mocked LLM + tools)
│   └── test_graph.py   # Routing logic + run_briefing/stream_briefing tests
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <your-repo-url> rivalsense-crew
cd rivalsense-crew

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and fill in your API keys:

```env
# Required
OPENAI_API_KEY=sk-or-v1-...        # OpenRouter or OpenAI key
TAVILY_API_KEY=tvly-...

# Optional — choose your model
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini

# Optional — deep scraping
FIRECRAWL_API_KEY=fc-...
FIRECRAWL_ENABLED=false

# Limits (defaults shown)
MAX_SOURCES=20
MAX_STEPS=50

# Validator quality gate (defaults shown)
MIN_VALID_SOURCES=2
RELEVANCE_THRESHOLD=0.3
```

#### API Key Sources

| Key | Where to get it |
|-----|----------------|
| `OPENAI_API_KEY` | [OpenRouter](https://openrouter.ai) (recommended) or [OpenAI](https://platform.openai.com) |
| `TAVILY_API_KEY` | [Tavily](https://tavily.com) — free tier available |
| `FIRECRAWL_API_KEY` | [Firecrawl](https://firecrawl.dev) — optional |

---

## Running the App

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Enter a topic like:

- `CRM software market`
- `AI coding assistants — GitHub Copilot vs Cursor`
- `Fintech payments infrastructure`

Click **▶ Run Brief** and watch the crew execute in real time.

---

## Running Tests

```bash
pytest
```

All 75+ tests run with mocked APIs — no real keys needed:

```
tests/test_models.py   ......................   # Pydantic model validation
tests/test_tools.py    .................        # Tavily + Firecrawl (mocked)
tests/test_agents.py   ................................  # All 5 nodes (mocked LLM)
tests/test_graph.py    .....................    # Routing + run_briefing
```

---

## Briefing Structure

Every briefing includes these sections:

| Section | Description |
|---------|-------------|
| **Executive Summary** | 2–4 sentence overview with source count |
| **Competitor Pricing Moves** | Price changes, plan restructures, discounting |
| **Product Launches** | New features, products, integrations |
| **Market Signals** | Analyst reports, buyer sentiment, category growth |
| **Key Insights** | Trends, risks, opportunities (labelled by type) |
| **Strategic Recommendation** | One actionable recommendation |
| **Sources** | All URLs collected, failed sources noted |
| **Run Metadata** | Run ID, duration, token count, steps taken |

---

## Spec Compliance

| Requirement | Implementation |
|-------------|----------------|
| Coordinator delegates to Researcher → Validator → Analyst → Writer | `graph.py` StateGraph with conditional edges |
| Source quality gate before analysis | `validator.py` — deterministic 4-rule check, short-circuits on first failure |
| Every claim cited | Writer prompt enforces `[Source N]` citations; analyst drops uncited items |
| No uncited assertions | `all_claims_cited` field in RunMetadata; writer heuristic check |
| Partial failure handling | `multi_search()` catches per-source failures; `failed_sources` tracked |
| Source count bounded | `MAX_SOURCES` cap in `TavilySearchTool.multi_search()` |
| Step count bounded | `MAX_STEPS` checked in coordinator; configurable via env/slider |
| Shared state | `BriefingState` TypedDict passed through all nodes |
| Modular architecture | Separate files per concern; `build_tools()` factory |
| Streamlit frontend | `app.py` with sidebar (5-agent status), tabs, streaming progress |
| Config via env vars | `config.py` using pydantic-settings; `.env.example` provided |
| Logging & error handling | `configure_logging()` in config; per-agent try/except |
| Unit tests | 4 test files covering models, tools, agents, graph |

---

## Validator Quality Gate

The Validator runs four deterministic rules **in order** before the Analyst runs. The first failing rule short-circuits the rest and sends the pipeline directly to the Writer, which produces a structured rejection response.

| Rule | What it checks | Failure code |
|------|---------------|-------------|
| **AllSourcesFailed** | At least one non-failed source exists | `all_sources_failed` |
| **MinValidSources** | ≥ `MIN_VALID_SOURCES` sources are non-failed, have content, and meet `RELEVANCE_THRESHOLD` | `insufficient_sources` |
| **TopicRelevance** | At least one valid source mentions a keyword from the topic | `topic_not_found` |
| **NoFindings** | Researcher extracted ≥ 1 sourced finding | `no_findings` |

Configure the gate via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_VALID_SOURCES` | `2` | Minimum number of valid (non-failed, relevant) sources required |
| `RELEVANCE_THRESHOLD` | `0.3` | Fraction of topic keywords that must appear in a source's title + snippet |

---

## Execution Limits

Prevent runaway execution with these configurable guards:

| Limit | Default | Override |
|-------|---------|---------|
| `MAX_SOURCES` | 20 | `.env` or Streamlit slider |
| `MAX_STEPS` | 50 | `.env` or Streamlit slider |
| `MAX_SEARCH_RESULTS` | 5 per query | `.env` |
| `SEARCH_QUERIES_PER_RUN` | 4 | `.env` |

---

## Troubleshooting

**`OPENAI_API_KEY not found`**
→ Run `copy .env.example .env` and add your keys.

**`ModuleNotFoundError: No module named 'tavily'`**
→ Run `pip install -r requirements.txt` inside your venv.

**Briefing shows "No data available this week"**
→ The Tavily search returned no results. Try a broader topic or check your `TAVILY_API_KEY`.

**Briefing shows "No sufficient trusted data found"**
→ The Validator rejected the research batch. Check the failure code in the sidebar errors panel. Increase `MIN_VALID_SOURCES` threshold or try a broader topic.

**Writer shows `[no source]` badges**
→ Analyst found claims it couldn't trace to URLs. These are flagged but not removed from the markdown — check `all_claims_cited` in the sidebar.

**Streamlit shows stale results**
→ Click ▶ Run Brief again. Each run creates a fresh execution with a new Run ID.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | OpenAI / OpenRouter API key |
| `TAVILY_API_KEY` | ✅ | — | Tavily search API key |
| `OPENAI_BASE_URL` | ❌ | — | Set to `https://openrouter.ai/api/v1` for OpenRouter |
| `LLM_MODEL` | ❌ | `openai/gpt-4o-mini` | Model identifier |
| `FIRECRAWL_API_KEY` | ❌ | — | Firecrawl deep scraping key |
| `FIRECRAWL_ENABLED` | ❌ | `false` | Enable Firecrawl enrichment |
| `MAX_SOURCES` | ❌ | `20` | Max URLs collected per run |
| `MAX_STEPS` | ❌ | `50` | Max LangGraph steps per run |
| `MAX_SEARCH_RESULTS` | ❌ | `5` | Max results per Tavily query |
| `SEARCH_QUERIES_PER_RUN` | ❌ | `4` | Number of search queries generated |
| `MIN_VALID_SOURCES` | ❌ | `2` | Validator: min non-failed relevant sources required |
| `RELEVANCE_THRESHOLD` | ❌ | `0.3` | Validator: min keyword-match fraction for a source to be valid |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |
