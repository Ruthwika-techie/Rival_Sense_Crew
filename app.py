"""
app.py – MarketPulse Streamlit Frontend

Premium dark "fintech / Bloomberg / Linear" glassmorphism redesign.
Layout & functionality are unchanged from the original:
  - Sidebar: crew run status + reliability + run stats
  - Main area: topic input, run button, then briefing sections as cards
Only presentation (CSS/markup) has been restyled — no logic, routing,
state, or agent-workflow changes.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="MarketPulse — Competitive Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* ══════════════════════════ TOKENS ══════════════════════════ */
:root {
    --bg-void:      #0a0812;
    --bg-charcoal:  #0d0b18;
    --bg-plum:      #150f28;
    --bg-plum-2:    #1a1330;
    --glass:        rgba(255,255,255,0.035);
    --glass-strong: rgba(255,255,255,0.06);
    --border-soft:  rgba(255,255,255,0.08);
    --border-med:   rgba(255,255,255,0.14);
    --text-hi:      #f3f1fa;
    --text-mid:     #b6b1cc;
    --text-low:     #7c7796;
    --violet:       #8b5cf6;
    --violet-2:     #a78bfa;
    --magenta:      #c026d3;
    --emerald:      #34d399;
    --amber:        #fbbf24;
    --cyan:         #22d3ee;
    --rose:         #fb7185;
    --grad-brand:   linear-gradient(135deg, #8b5cf6 0%, #c026d3 100%);
    --grad-blue:    linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
    --grad-green:   linear-gradient(135deg, #10b981 0%, #34d399 100%);
    --grad-amber:   linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
    --grad-rose:    linear-gradient(135deg, #f43f5e 0%, #fb7185 100%);
    --grad-cyan:    linear-gradient(135deg, #0891b2 0%, #22d3ee 100%);
    --radius-lg:    20px;
    --radius-md:    16px;
    --radius-sm:    10px;
}

/* ══════════════════════════ GLOBAL ══════════════════════════ */
html, body, [data-testid="stApp"] {
    background:
        radial-gradient(ellipse 1200px 600px at 15% -10%, rgba(139,92,246,0.16), transparent 60%),
        radial-gradient(ellipse 900px 700px at 110% 10%, rgba(192,38,211,0.10), transparent 55%),
        linear-gradient(160deg, var(--bg-void) 0%, var(--bg-charcoal) 45%, var(--bg-plum) 100%);
    font-family: 'Inter', 'Manrope', sans-serif;
    color: var(--text-hi);
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1440px; }

h1, h2, h3, h4 { font-family: 'Manrope', 'Inter', sans-serif; letter-spacing: -0.01em; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.35); border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }

/* subtle financial grid + world-map texture across the whole app */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.5;
    background-image:
        radial-gradient(rgba(167,139,250,0.10) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
    background-size: 46px 46px, 64px 64px, 64px 64px;
    background-position: 0 0, 0 0, 0 0;
    mask-image: radial-gradient(ellipse 90% 70% at 50% 0%, black 30%, transparent 90%);
}

/* ══════════════════════════ SIDEBAR ══════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0714 0%, #0d0a1c 60%, #0a0714 100%) !important;
    border-right: 1px solid var(--border-soft);
}
[data-testid="stSidebar"] * { color: var(--text-hi) !important; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #ffffff !important; }

.mp-logo-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.2rem 0 0.9rem 0;
}
.mp-logo-icon {
    width: 42px; height: 42px; border-radius: 12px;
    background: var(--grad-brand);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.08), 0 6px 18px rgba(139,92,246,0.35);
}
.mp-logo-text { line-height: 1.15; }
.mp-logo-text .name { font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 1.12rem; color: #fff !important; }
.mp-logo-text .name .pulse { color: var(--violet-2) !important; }
.mp-logo-text .sub { font-size: 0.72rem; color: var(--text-low) !important; font-weight: 500; }

[data-testid="stSidebar"] .sidebar-label {
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    color: var(--violet-2) !important;
    text-transform: uppercase;
    margin-top: 1.35rem;
    margin-bottom: 0.55rem;
}

/* agent row cards */
.agent-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.5rem 0.55rem;
    border-radius: var(--radius-sm);
    margin-bottom: 0.4rem;
    background: var(--glass);
    border: 1px solid var(--border-soft);
    transition: background 0.15s ease, border-color 0.15s ease;
}
.agent-row:hover { background: var(--glass-strong); border-color: var(--border-med); }
.agent-icon {
    width: 34px; height: 34px; min-width: 34px; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.92rem;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.07);
}
.agent-meta { flex: 1; min-width: 0; }
.agent-meta .a-name { font-size: 0.85rem; font-weight: 700; color: var(--text-hi) !important; line-height: 1.2; }
.agent-meta .a-sub  { font-size: 0.68rem; color: var(--text-low) !important; line-height: 1.2; }
.agent-status { font-size: 0.72rem; font-weight: 700; white-space: nowrap; display: flex; align-items: center; gap: 5px; }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }

.status-done    { color: var(--emerald) !important; } .status-done .dot    { background: var(--emerald); box-shadow: 0 0 8px var(--emerald); }
.status-running { color: var(--amber)   !important; } .status-running .dot { background: var(--amber); box-shadow: 0 0 8px var(--amber); animation: pulse-dot 1.1s infinite; }
.status-pending { color: var(--text-low)!important; } .status-pending .dot { background: var(--text-low); }
.status-failed  { color: var(--rose)    !important; } .status-failed .dot  { background: var(--rose); box-shadow: 0 0 8px var(--rose); }
.status-skipped { color: #fb923c        !important; } .status-skipped .dot { background: #fb923c; }
.status-pass    { color: var(--emerald) !important; } .status-pass .dot    { background: var(--emerald); box-shadow: 0 0 8px var(--emerald); }

@keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }

/* reliability / run key-value rows */
.kv-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 10px; margin-bottom: 5px;
    background: var(--glass);
    border: 1px solid var(--border-soft);
    border-radius: 9px;
    font-size: 0.8rem;
}
.kv-row .k { color: var(--text-mid) !important; }
.kv-row .v { font-weight: 700; color: var(--text-hi) !important; }

.err-box {
    background: rgba(244,63,94,0.10);
    border: 1px solid rgba(244,63,94,0.35);
    border-radius: 10px;
    padding: 0.65rem 0.85rem;
    color: #fda4af !important;
    font-size: 0.78rem;
    margin-top: 0.4rem;
}

/* sidebar buttons */
[data-testid="stSidebar"] div.stButton > button {
    background: var(--grad-brand) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    box-shadow: 0 8px 24px rgba(139,92,246,0.35);
}
[data-testid="stSidebar"] div.stButton > button:hover { filter: brightness(1.08); }

/* ══════════════════════════ MAIN HEADER ══════════════════════════ */
.mp-header {
    position: relative;
    overflow: hidden;
    background:
        linear-gradient(115deg, rgba(139,92,246,0.22) 0%, rgba(192,38,211,0.10) 40%, rgba(13,11,24,0.4) 100%),
        linear-gradient(135deg, #120e22 0%, #1c1533 100%);
    border: 1px solid var(--border-soft);
    padding: 1.6rem 2rem;
    border-radius: var(--radius-lg);
    margin-bottom: 1.4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 20px 50px -20px rgba(80,40,140,0.5);
}
.mp-header::after {
    content: "";
    position: absolute; inset: 0;
    background-image: radial-gradient(rgba(255,255,255,0.14) 1px, transparent 1.4px);
    background-size: 26px 26px;
    -webkit-mask-image: linear-gradient(120deg, transparent 20%, black 55%, transparent 85%);
    mask-image: linear-gradient(120deg, transparent 20%, black 55%, transparent 85%);
    opacity: 0.5;
    pointer-events: none;
}
.mp-header h1 {
    color: #ffffff; margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: -0.02em;
    position: relative; z-index: 1;
}
.mp-header .sub {
    color: var(--text-mid); font-size: 0.86rem; margin-top: 4px; font-weight: 500;
    position: relative; z-index: 1;
}
.mp-header .sub .arrow { color: var(--violet-2); margin: 0 2px; }
.mp-header .badge {
    color: var(--amber); font-size: 0.78rem; text-align: right; font-weight: 700;
    background: rgba(251,191,36,0.10); border: 1px solid rgba(251,191,36,0.3);
    padding: 6px 14px; border-radius: 999px; position: relative; z-index: 1; white-space: nowrap;
}

/* ══════════════════════════ PREVIEW STRIP ══════════════════════════ */
.preview-card {
    background: var(--glass);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    padding: 1.1rem 1.2rem;
    height: 100%;
    transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}
.preview-card:hover { transform: translateY(-2px); border-color: var(--border-med); background: var(--glass-strong); }
.preview-icon {
    width: 42px; height: 42px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem; margin-bottom: 0.7rem;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
}
.preview-card h4 { margin: 0 0 0.3rem 0; font-size: 0.98rem; font-weight: 700; color: var(--text-hi); }
.preview-card p { margin: 0; font-size: 0.79rem; color: var(--text-low); line-height: 1.5; }

/* ══════════════════════════ BRIEFING CARDS ══════════════════════════ */
.brief-card {
    background: var(--glass);
    backdrop-filter: blur(14px);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.15s ease, background 0.15s ease;
}
.brief-card:hover { border-color: var(--border-med); background: var(--glass-strong); }
.brief-card-head { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.6rem; }
.brief-icon {
    width: 38px; height: 38px; min-width: 38px; border-radius: 11px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
}
.brief-card h3 {
    margin: 0; font-size: 1.02rem; font-weight: 700; color: var(--text-hi);
}
.brief-card h3 .tag {
    font-size: 0.68rem; font-weight: 700; color: var(--violet-2);
    margin-left: 6px; letter-spacing: 0.06em;
}
.brief-card p { color: var(--text-mid); font-size: 0.89rem; line-height: 1.65; margin: 0; }

.cite-badge {
    display: inline-block;
    background: rgba(139,92,246,0.14);
    color: var(--violet-2);
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 999px;
    padding: 2px 11px;
    font-size: 0.72rem;
    font-weight: 600;
    margin: 3px 4px 0 0;
    text-decoration: none;
}
.cite-badge:hover { background: rgba(139,92,246,0.26); }

/* ── Source pill ── */
.source-pill {
    display: inline-block;
    background: rgba(255,255,255,0.04);
    color: var(--text-mid);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 0.74rem;
    margin: 3px 4px 3px 0;
    border: 1px solid var(--border-soft);
}
.source-pill-fail {
    background: rgba(244,63,94,0.08);
    color: #fda4af;
    border-color: rgba(244,63,94,0.3);
}

/* ── Side info panels (verification / how it works) ── */
.info-panel {
    background: var(--glass);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    padding: 1.3rem 1.4rem;
    margin-bottom: 1rem;
}
.info-panel h4 {
    display: flex; align-items: center; gap: 0.55rem;
    margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 700; color: var(--text-hi);
}
.info-panel p.desc { color: var(--text-low); font-size: 0.79rem; line-height: 1.55; margin: 0 0 0.9rem 0; }
.shield-ring {
    width: 118px; height: 118px; border-radius: 50%;
    margin: 0.4rem auto 1rem auto;
    background: radial-gradient(circle, rgba(139,92,246,0.18) 0%, transparent 70%);
    border: 2px solid rgba(139,92,246,0.4);
    display: flex; align-items: center; justify-content: center;
    font-size: 2.1rem;
    box-shadow: 0 0 30px rgba(139,92,246,0.25) inset;
}
.check-row {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.79rem; color: var(--text-mid); padding: 5px 0;
    border-bottom: 1px dashed var(--border-soft);
}
.check-row:last-child { border-bottom: none; }
.check-row .yes { color: var(--emerald); font-weight: 700; }

.flow-step { display: flex; gap: 0.6rem; align-items: flex-start; margin-bottom: 0.7rem; }
.flow-step .fs-icon {
    width: 30px; height: 30px; min-width: 30px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; font-size: 0.82rem;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.07);
}
.flow-step .fs-name { font-size: 0.83rem; font-weight: 700; color: var(--text-hi); line-height: 1.25; }
.flow-step .fs-sub { font-size: 0.72rem; color: var(--text-low); }

/* ── Feature strip (bottom) ── */
.feature-card {
    background: var(--glass);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    padding: 1.2rem 1.3rem;
    height: 100%;
}
.feature-card .f-icon {
    width: 44px; height: 44px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; margin-bottom: 0.65rem;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
}
.feature-card h4 { margin: 0 0 0.3rem 0; font-size: 0.94rem; font-weight: 700; color: var(--text-hi); }
.feature-card p { margin: 0; font-size: 0.79rem; color: var(--text-low); line-height: 1.5; }

/* ══════════════════════════ INPUT ROW ══════════════════════════ */
[data-testid="stTextInput"] input {
    background: var(--glass) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
    color: var(--text-hi) !important;
    padding: 0.7rem 1rem !important;
    font-size: 0.92rem !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--text-low) !important; }
[data-testid="stTextInput"] input:focus {
    border-color: var(--violet) !important;
    box-shadow: 0 0 0 3px rgba(139,92,246,0.18) !important;
}

div.stButton > button {
    background: var(--grad-brand);
    color: white;
    border: none;
    padding: 0.68rem 2rem;
    border-radius: 12px;
    font-weight: 700;
    font-size: 0.95rem;
    width: 100%;
    box-shadow: 0 8px 24px rgba(139,92,246,0.32);
    transition: filter 0.15s ease, transform 0.15s ease;
}
div.stButton > button:hover { filter: brightness(1.1); transform: translateY(-1px); }
div.stButton > button:disabled { opacity: 0.45; box-shadow: none; }

/* ══════════════════════════ TABS ══════════════════════════ */
[data-testid="stTabs"] button[role="tab"] {
    color: var(--text-low) !important;
    font-weight: 600 !important;
    font-size: 0.87rem !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--text-hi) !important;
    border-bottom: 2px solid var(--violet) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] { background: var(--border-soft) !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--violet) !important; }

/* ══════════════════════════ EXPANDERS ══════════════════════════ */
[data-testid="stExpander"] {
    background: var(--glass);
    border: 1px solid var(--border-soft) !important;
    border-radius: var(--radius-md) !important;
}
[data-testid="stExpander"] summary { color: var(--text-hi) !important; font-weight: 600 !important; }

/* ══════════════════════════ MISC TEXT ══════════════════════════ */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li { color: var(--text-mid); }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 { color: var(--text-hi); }

hr, [data-testid="stDivider"] { border-color: var(--border-soft) !important; }

.stDownloadButton button {
    background: var(--glass-strong) !important;
    color: var(--text-hi) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: 10px !important;
}

.welcome-box {
    text-align: center; padding: 4rem 1.5rem; color: var(--text-low);
    background: var(--glass);
    border: 1px dashed var(--border-med);
    border-radius: var(--radius-lg);
}
.welcome-box .w-icon {
    width: 68px; height: 68px; border-radius: 18px; margin: 0 auto 1.2rem auto;
    background: var(--grad-brand);
    display: flex; align-items: center; justify-content: center; font-size: 1.8rem;
    box-shadow: 0 10px 30px rgba(139,92,246,0.35);
}
.welcome-box h3 { color: var(--text-hi); font-weight: 700; margin-bottom: 0.4rem; }
.welcome-box p { font-size: 0.88rem; max-width: 480px; margin: 0 auto; line-height: 1.6; }
</style>
""",
    unsafe_allow_html=True,
)



# ── Chart / table helpers ─────────────────────────────────────────────────────
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

_PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#b6b1cc"),
    margin=dict(l=0, r=0, t=28, b=0),
    transition=dict(duration=0),
    uirevision="stable",
)

# Shared plotly config: hide toolbar, no animation to prevent jitter on rerun
_PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "staticPlot": False,
    "scrollZoom": False,
}

# Colour palette matching the dark theme
_PALETTE = [
    "#8b5cf6", "#22d3ee", "#34d399", "#fbbf24",
    "#fb7185", "#6366f1", "#f97316", "#a78bfa",
]


def _bar_chart(labels: list, values: list, title: str, colour: str = "#8b5cf6") -> go.Figure:
    """Horizontal bar chart for competitor comparisons."""
    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker=dict(
            color=colour,
            line=dict(color="rgba(255,255,255,0.08)", width=1),
        ),
        text=[str(v) for v in values],
        textposition="outside",
        textfont=dict(size=11, color="#b6b1cc"),
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        height=300,
        title=dict(text=title, font=dict(size=13, color="#f3f1fa"), x=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#f3f1fa")),
    )
    return fig


def _donut_chart(labels: list, values: list, title: str) -> go.Figure:
    """Donut chart for distribution breakdowns."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=_PALETTE, line=dict(color="rgba(0,0,0,0.4)", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#f3f1fa"),
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text=title, font=dict(size=13, color="#f3f1fa"), x=0),
        showlegend=False,
        height=280,
    )
    return fig


def _scatter_timeline(items: list, title: str) -> go.Figure:
    """Dot-plot timeline for product launch / signal items."""
    fig = go.Figure()
    for i, (label, category) in enumerate(items):
        colour = _PALETTE[i % len(_PALETTE)]
        fig.add_trace(go.Scatter(
            x=[i + 1], y=[label],
            mode="markers+text",
            marker=dict(size=16, color=colour,
                        line=dict(color="rgba(255,255,255,0.2)", width=2)),
            text=[category],
            textposition="middle right",
            textfont=dict(size=10, color="#b6b1cc"),
            showlegend=False,
            hovertemplate=f"{label}<extra></extra>",
        ))
    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text=title, font=dict(size=13, color="#f3f1fa"), x=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   range=[0, max(len(items) + 1, 2)]),
        yaxis=dict(showgrid=False, autorange="reversed",
                   tickfont=dict(size=11, color="#f3f1fa")),
        height=max(200, len(items) * 52),
    )
    return fig


# ── Session state initialisation ──────────────────────────────────────────────

def init_session():
    defaults = {
        "briefing": None,
        "running": False,
        "stream_log": [],
        "last_topic": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Status helpers ────────────────────────────────────────────────────────────

_STATUS_ICONS = {
    "done":    ("done",    "Done"),
    "running": ("running", "Running"),
    "pending": ("pending", "Pending"),
    "failed":  ("failed",  "Failed"),
    "skipped": ("skipped", "Skipped"),
}

# gradient backgrounds cycled across the five agent icons, in order
_AGENT_ICON_STYLE = [
    ("👥", "var(--grad-brand)"),   # Coordinator
    ("🔍", "var(--grad-blue)"),    # Researcher
    ("🛡️", "var(--grad-cyan)"),    # Validator
    ("📈", "var(--grad-green)"),   # Analyst
    ("✍️", "var(--grad-rose)"),    # Writer
]


def _status_html(status: str) -> str:
    cls, label = _STATUS_ICONS.get(status.lower(), ("pending", status.title() or "Pending"))
    return f'<span class="agent-status status-{cls}"><span class="dot"></span>{label}</span>'


# ── Sidebar rendering ─────────────────────────────────────────────────────────

def render_sidebar(meta: Optional[Dict[str, Any]], running: bool):
    with st.sidebar:
        st.markdown(
            '<div class="mp-logo-row">'
            '<div class="mp-logo-icon">📊</div>'
            '<div class="mp-logo-text">'
            '<div class="name">Market<span class="pulse">Pulse</span></div>'
            '<div class="sub">Competitive Intelligence</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size:0.74rem;color:var(--text-low);margin-bottom:0.4rem;line-height:1.5;">'
            'Coordinator → Researcher → Validator → Analyst → Writer<br>'
            '<span style="opacity:0.75">multi-agent crew · powered by LangGraph</span></div>',
            unsafe_allow_html=True,
        )

        # ── CREW RUN section ──────────────────────────────────────────────────
        st.markdown('<div class="sidebar-label">Crew Run</div>', unsafe_allow_html=True)

        agent_defs = [
            ("Coordinator", "Supervisor"),
            ("Researcher", "Source Discovery"),
            ("Validator", "Quality Check"),
            ("Analyst", "Signal Extraction"),
            ("Writer", "Briefing"),
        ]

        def _row(idx: int, label: str, subtitle: str, status: str, extra: str = ""):
            icon, grad = _AGENT_ICON_STYLE[idx % len(_AGENT_ICON_STYLE)]
            badge = _status_html(status)
            sub = f"{subtitle} · {extra}" if extra else subtitle
            st.markdown(
                f'<div class="agent-row">'
                f'<div class="agent-icon" style="background:{grad}">{icon}</div>'
                f'<div class="agent-meta"><div class="a-name">{label}</div>'
                f'<div class="a-sub">{sub}</div></div>'
                f'{badge}</div>',
                unsafe_allow_html=True,
            )

        if running:
            statuses = ["running", "pending", "pending", "pending", "pending"]
            for i, ((label, sub), status) in enumerate(zip(agent_defs, statuses)):
                _row(i, label, sub, status)
        elif meta:
            sources_label = (
                f"{meta.get('total_sources', 0)} sources" if meta.get("total_sources") else ""
            )
            statuses = [
                meta.get("coordinator_status", "pending"),
                meta.get("researcher_status", "pending"),
                meta.get("validator_status", "pending"),
                meta.get("analyst_status", "pending"),
                meta.get("writer_status", "pending"),
            ]
            extras = ["", sources_label, "", "", ""]
            for i, ((label, sub), status, extra) in enumerate(zip(agent_defs, statuses, extras)):
                _row(i, label, sub, status, extra)
        else:
            for i, (label, sub) in enumerate(agent_defs):
                _row(i, label, sub, "pending")

        # ── RELIABILITY section ───────────────────────────────────────────────
        st.markdown('<div class="sidebar-label">Reliability</div>', unsafe_allow_html=True)

        if meta:
            skipped = meta.get("sources_skipped", 0)
            skip_cls = "status-skipped" if skipped else "status-done"
            skip_txt = f"{skipped} source timed out" if skipped == 1 else (
                f"{skipped} sources timed out" if skipped else "All sources OK"
            )
            cited_cls = "status-pass" if meta.get("all_claims_cited", True) else "status-failed"
            cited_txt = "Pass" if meta.get("all_claims_cited", True) else "Fail"

            st.markdown(
                f'<div class="kv-row"><span class="k">Source reliability</span>'
                f'<span class="agent-status {skip_cls}"><span class="dot"></span>{skip_txt}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="kv-row"><span class="k">All claims cited</span>'
                f'<span class="agent-status {cited_cls}"><span class="dot"></span>{cited_txt}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="kv-row"><span class="k">All claims cited</span>'
                '<span class="agent-status status-pending"><span class="dot"></span>–</span></div>',
                unsafe_allow_html=True,
            )

        # ── RUN section ───────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-label">Run</div>', unsafe_allow_html=True)

        if meta:
            dur = meta.get("duration_seconds")
            dur_txt = f"{dur:.0f}s" if dur else "–"
            tokens = meta.get("total_tokens", 0)
            tok_txt = f"{tokens:,}" if tokens else "–"
            run_id = meta.get("run_id", "–")

            for label, value in [
                ("Run ID", run_id),
                ("Duration", dur_txt),
                ("Tokens", tok_txt),
                ("Steps", str(meta.get("steps_taken", "–"))),
            ]:
                st.markdown(
                    f'<div class="kv-row"><span class="k">{label}</span>'
                    f'<span class="v">{value}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="kv-row"><span class="k">Duration</span><span class="v">–</span></div>',
                unsafe_allow_html=True,
            )

        # ── Errors ───────────────────────────────────────────────────────────
        if meta and meta.get("errors"):
            st.markdown('<div class="sidebar-label">Errors</div>', unsafe_allow_html=True)
            for err in meta["errors"][:5]:
                st.markdown(f'<div class="err-box">⚠ {err}</div>', unsafe_allow_html=True)


# ── Briefing card helpers ─────────────────────────────────────────────────────

def _citation_badges(citations: List[Dict]) -> str:
    """Render inline source badge links from a list of Citation dicts."""
    badges = []
    for c in citations:
        for url in c.get("sources", []):
            if url:
                domain = url.split("/")[2] if url.startswith("http") else url[:30]
                badges.append(
                    f'<a href="{url}" target="_blank" class="cite-badge">{domain}</a>'
                )
    return " ".join(badges)


def _card(icon: str, grad: str, title: str, body_html: str, tag: str = "", extra_style: str = ""):
    tag_html = f'<span class="tag">[{tag}]</span>' if tag else ""
    st.markdown(
        f'<div class="brief-card" style="{extra_style}">'
        f'<div class="brief-card-head">'
        f'<div class="brief-icon" style="background:{grad}">{icon}</div>'
        f'<h3>{title}{tag_html}</h3>'
        f'</div>{body_html}</div>',
        unsafe_allow_html=True,
    )


def render_executive_summary(summary: str):
    if not summary:
        return
    _card("⭐", "var(--grad-brand)", "Executive Summary", f'<p>{summary}</p>')


def render_pricing_moves(moves: List[Dict]):
    if not moves:
        _card("💰", "var(--grad-blue)", "Competitor Pricing Moves",
              '<p>No pricing data available this week.</p>')
        return

    # ── Comparison table via st.dataframe (always visible) ───────────────────
    st.markdown("#### 💰 Competitor Pricing Moves")
    rows = []
    for pm in moves:
        sources = []
        for c in pm.get("citations", []):
            sources += c.get("sources", [])
        rows.append({
            "Competitor": pm.get("competitor", "Unknown"),
            "Pricing Change": pm.get("description", ""),
            "Sources": len(sources),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Chart + detail side by side ───────────────────────────────────────────
    if len(moves) >= 2:
        col_chart, col_detail = st.columns([1, 1], gap="large")
        with col_chart:
            labels = [m.get("competitor", f"#{i+1}") for i, m in enumerate(moves)]
            values = [len(m.get("description", "").split()) for m in moves]
            fig = go.Figure(go.Bar(
                x=values, y=labels, orientation="h",
                marker_color="#22d3ee",
                text=values, textposition="outside",
                textfont=dict(size=11, color="#f3f1fa"),
            ))
            fig.update_layout(
                **_CHART_LAYOUT, height=max(200, len(moves) * 55),
                title=dict(text="Coverage per Competitor", font=dict(size=13, color="#f3f1fa"), x=0),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#f3f1fa")),
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

        with col_detail:
            st.markdown("**Detail**")
            for pm in moves:
                badges = _citation_badges(pm.get("citations", []))
                _card(
                    "💰", "var(--grad-blue)",
                    pm.get("competitor", "Unknown"),
                    f'<p style="font-size:0.85rem">{pm.get("description", "")}</p>'
                    f'<div style="margin-top:0.5rem">{badges}</div>',
                )
    else:
        # single item — just show the card
        for pm in moves:
            badges = _citation_badges(pm.get("citations", []))
            _card(
                "💰", "var(--grad-blue)",
                f'{pm.get("competitor", "Unknown")} — Pricing Move',
                f'<p>{pm.get("description", "")}</p>'
                f'<div style="margin-top:0.6rem">{badges}</div>',
            )


def render_product_launches(launches: List[Dict]):
    if not launches:
        _card("🚀", "var(--grad-green)", "Product Launches",
              '<p>No product launches recorded this week.</p>')
        return

    # ── Summary dataframe ─────────────────────────────────────────────────────
    st.markdown("#### 🚀 Product Launches")
    rows = []
    for pl in launches:
        sources = []
        for c in pl.get("citations", []):
            sources += c.get("sources", [])
        rows.append({
            "Competitor": pl.get("competitor", "Unknown"),
            "Product": pl.get("product_name", "—"),
            "Description": pl.get("description", ""),
            "Sources": len(sources),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Chart + detail side by side ───────────────────────────────────────────
    col_chart, col_detail = st.columns([1, 1], gap="large")

    with col_chart:
        from collections import Counter
        counts = Counter(pl.get("competitor", "Unknown") for pl in launches)
        labels = list(counts.keys())
        values = list(counts.values())
        colours = _PALETTE[:len(labels)]
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker=dict(color=colours, line=dict(color="rgba(255,255,255,0.1)", width=1)),
            text=values, textposition="outside",
            textfont=dict(size=12, color="#f3f1fa"),
        ))
        fig.update_layout(
            **_CHART_LAYOUT, height=260,
            title=dict(text="Launches per Competitor", font=dict(size=13, color="#f3f1fa"), x=0),
            xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#f3f1fa")),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            bargap=0.35,
        )
        st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

        # Mini scatter timeline below chart
        if len(launches) >= 2:
            y_labels = [f'{pl.get("competitor","?")} · {pl.get("product_name","?")}' for pl in launches]
            fig2 = go.Figure()
            for i, label in enumerate(y_labels):
                fig2.add_trace(go.Scatter(
                    x=[i + 1], y=[label],
                    mode="markers",
                    marker=dict(size=14, color=_PALETTE[i % len(_PALETTE)],
                                line=dict(color="rgba(255,255,255,0.3)", width=2)),
                    showlegend=False,
                    hovertemplate=f"{label}<extra></extra>",
                ))
            fig2.update_layout(
                **_CHART_LAYOUT, height=max(180, len(launches) * 46),
                title=dict(text="Launch Sequence", font=dict(size=13, color="#f3f1fa"), x=0),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                           range=[0, len(launches) + 1]),
                yaxis=dict(showgrid=False, tickfont=dict(size=10, color="#f3f1fa"),
                           autorange="reversed"),
            )
            st.plotly_chart(fig2, use_container_width=True, config=_PLOTLY_CONFIG)

    with col_detail:
        st.markdown("**Detail**")
        for pl in launches:
            badges = _citation_badges(pl.get("citations", []))
            _card(
                "🚀", "var(--grad-green)",
                f'{pl.get("competitor", "Unknown")} — {pl.get("product_name", "")}',
                f'<p style="font-size:0.85rem">{pl.get("description", "")}</p>'
                f'<div style="margin-top:0.5rem">{badges}</div>',
            )


def render_market_signals(signals: List[Dict]):
    if not signals:
        _card("📡", "var(--grad-amber)", "Market Signals",
              '<p>No market signals detected this week.</p>')
        return

    # ── Summary table ─────────────────────────────────────────────────────────
    rows_html = ""
    for ms in signals:
        badges = _citation_badges(ms.get("citations", []))
        signal = ms.get("signal", "—")
        detail = ms.get("detail", "")
        # Truncate detail for table readability
        short = detail[:120] + ("…" if len(detail) > 120 else "")
        rows_html += (
            f"<tr><td><strong>{signal}</strong></td>"
            f"<td>{short}</td>"
            f"<td>{badges if badges else '—'}</td></tr>"
        )

    table_html = (
        '<table class="comp-table">'
        "<thead><tr>"
        "<th style='width:22%'>Signal</th>"
        "<th>Detail</th>"
        "<th style='width:22%'>Sources</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )
    _card("📡", "var(--grad-amber)", "Market Signals — Summary Table", table_html)

    # ── Horizontal bar: signal prominence (word count of detail) ──────────────
    if len(signals) >= 2:
        labels = [ms.get("signal", f"Signal {i+1}")[:40] for i, ms in enumerate(signals)]
        values = [len(ms.get("detail", "").split()) for ms in signals]
        fig = _bar_chart(labels, values, "Signal Coverage Depth", "#fbbf24")
        st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

    # ── Detail cards ──────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;'
        'color:var(--text-low);text-transform:uppercase;margin:1rem 0 0.5rem">Detail</div>',
        unsafe_allow_html=True,
    )
    for ms in signals:
        badges = _citation_badges(ms.get("citations", []))
        _card(
            "📡", "var(--grad-amber)",
            ms.get("signal", "Signal"),
            f'<p>{ms.get("detail", "")}</p><div style="margin-top:0.6rem">{badges}</div>',
        )


def render_insights(insights: List[Dict]):
    if not insights:
        return

    TYPE_ICONS = {
        "trend":       ("📈", "var(--grad-blue)"),
        "risk":        ("⚠️",  "var(--grad-rose)"),
        "opportunity": ("✨", "var(--grad-brand)"),
        "threat":      ("🔴", "var(--grad-rose)"),
        "observation": ("🔍", "var(--grad-cyan)"),
    }
    TYPE_COLOURS = {
        "trend": "#3b82f6", "risk": "#f43f5e",
        "opportunity": "#8b5cf6", "threat": "#f97316", "observation": "#22d3ee",
    }

    # ── Donut chart: breakdown by type ────────────────────────────────────────
    from collections import Counter
    type_counts = Counter(ins.get("type", "observation") for ins in insights)
    if len(type_counts) >= 2:
        col_chart, col_table = st.columns([1, 1], gap="medium")
        with col_chart:
            labels = [t.title() for t in type_counts.keys()]
            values = list(type_counts.values())
            colours = [TYPE_COLOURS.get(t, "#8b5cf6") for t in type_counts.keys()]
            fig = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.55,
                marker=dict(colors=colours, line=dict(color="rgba(0,0,0,0.4)", width=2)),
                textinfo="label+percent",
                textfont=dict(size=11, color="#f3f1fa"),
                hovertemplate="%{label}: %{value} insight(s)<extra></extra>",
            ))
            fig.update_layout(
                **_CHART_LAYOUT,
                title=dict(text="Insights by Type", font=dict(size=13, color="#f3f1fa"), x=0),
                showlegend=False, height=280,
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

        with col_table:
            st.markdown(
                '<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;'
                'color:var(--text-low);text-transform:uppercase;margin-bottom:0.5rem">Type breakdown</div>',
                unsafe_allow_html=True,
            )
            rows = ""
            for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
                colour = TYPE_COLOURS.get(t, "#8b5cf6")
                rows += (
                    f"<tr><td><span style='display:inline-block;width:10px;height:10px;"
                    f"border-radius:50%;background:{colour};margin-right:6px'></span>"
                    f"<strong>{t.title()}</strong></td>"
                    f"<td style='text-align:right;font-weight:700'>{cnt}</td></tr>"
                )
            st.markdown(
                '<table class="comp-table" style="margin-top:0.4rem">'
                "<thead><tr><th>Type</th><th>Count</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>",
                unsafe_allow_html=True,
            )

    # ── Cards grouped by type ─────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;'
        'color:var(--text-low);text-transform:uppercase;margin:1rem 0 0.5rem">All Insights</div>',
        unsafe_allow_html=True,
    )
    for ins in insights:
        itype = ins.get("type", "observation")
        icon, grad = TYPE_ICONS.get(itype, ("🔍", "var(--grad-cyan)"))
        colour = TYPE_COLOURS.get(itype, "#8b5cf6")
        badges = _citation_badges(ins.get("citations", []))
        type_badge = (
            f'<span style="display:inline-block;background:{colour}22;color:{colour};'
            f'border:1px solid {colour}44;border-radius:999px;padding:2px 10px;'
            f'font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
            f'text-transform:uppercase;margin-right:8px">{itype}</span>'
        )
        _card(
            icon, grad,
            ins.get("title", "Insight"),
            f'{type_badge}<p style="margin-top:0.5rem">{ins.get("detail", "")}</p>'
            f'<div style="margin-top:0.6rem">{badges}</div>',
        )


def render_recommendation(text: str):
    if not text:
        return
    _card("✅", "var(--grad-green)", "Strategic Recommendation", f'<p>{text}</p>')


def render_sources(sources: List[Dict], failed: List[Dict]):
    with st.expander(f"📚 Sources ({len(sources)} collected, {len(failed)} skipped)", expanded=False):
        for src in sources:
            url = src.get("url", "")
            title = src.get("title") or url
            st.markdown(
                f'<span class="source-pill">'
                f'<a href="{url}" target="_blank" style="color:var(--text-mid);text-decoration:none">'
                f'{title[:60]}</a></span>',
                unsafe_allow_html=True,
            )
        if failed:
            st.markdown("**Skipped sources:**")
            for fs in failed:
                reason = fs.get("failure_reason") or fs.get("title", "unknown")
                st.markdown(
                    f'<span class="source-pill source-pill-fail">✗ {reason[:60]}</span>',
                    unsafe_allow_html=True,
                )


# ── Main page header ──────────────────────────────────────────────────────────

def render_page_header(briefing: Optional[Dict]):
    meta = briefing.get("run_metadata", {}) if briefing else {}
    total_sources = meta.get("total_sources", 0)
    skipped = meta.get("sources_skipped", 0)

    badge_text = ""
    if total_sources:
        badge_text = f"{total_sources} sources"
        if skipped:
            badge_text += f" · {skipped} skipped"

    sub = 'Coordinator <span class="arrow">→</span> Researcher <span class="arrow">→</span> Validator <span class="arrow">→</span> Analyst <span class="arrow">→</span> Writer · multi-agent crew'

    badge_html = f'<div class="badge">{badge_text}</div>' if badge_text else ""

    st.markdown(
        f'<div class="mp-header">'
        f'<div><h1>MarketPulse — Weekly Competitive Brief</h1>'
        f'<div class="sub">{sub}</div></div>'
        f'{badge_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Decorative preview strip (purely visual, matches top overview cards) ──────

def render_preview_strip():
    cols = st.columns(4)
    cards = [
        ("📄", "var(--grad-brand)", "Executive Summary", "Top highlights and recommended actions."),
        ("🏷️", "var(--grad-blue)", "Competitor Pricing Moves", "Key pricing updates and promotions this week."),
        ("🚀", "var(--grad-green)", "Product Launches", "New features, products and announcements."),
        ("📡", "var(--grad-amber)", "Market Signals", "Trends, updates and market sentiment."),
    ]
    for col, (icon, grad, title, desc) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="preview-card">'
                f'<div class="preview-icon" style="background:{grad}">{icon}</div>'
                f'<h4>{title}</h4><p>{desc}</p></div>',
                unsafe_allow_html=True,
            )


# ── Decorative right-hand info panel (purely visual) ──────────────────────────

def render_info_panel(meta: Optional[Dict[str, Any]]):
    all_cited = meta.get("all_claims_cited", True) if meta else True
    st.markdown(
        f'<div class="info-panel">'
        f'<h4>🛡️ Verification Guard</h4>'
        f'<p class="desc">Every claim cross-verified across multiple trusted sources.</p>'
        f'<div class="shield-ring">✅</div>'
        f'<div class="check-row"><span>Cross-source verification</span><span class="yes">✓</span></div>'
        f'<div class="check-row"><span>Uncited claims</span><span class="yes">{"✓" if all_cited else "✗"}</span></div>'
        f'<div class="check-row"><span>Peer review</span><span class="yes">✓</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    flow = [
        ("🔍", "var(--grad-blue)", "Researcher", "Finds and validates sources"),
        ("📈", "var(--grad-green)", "Analyst", "Extracts and interprets signals"),
        ("✍️", "var(--grad-rose)", "Writer", "Creates structured briefing"),
    ]
    flow_html = "".join(
        f'<div class="flow-step"><div class="fs-icon" style="background:{grad}">{icon}</div>'
        f'<div><div class="fs-name">{name}</div><div class="fs-sub">{sub}</div></div></div>'
        for icon, grad, name, sub in flow
    )
    st.markdown(
        f'<div class="info-panel">'
        f'<h4>✨ How It Works</h4>'
        f'<p class="desc">AI agents collaborate in sequence to deliver trusted intelligence.</p>'
        f'{flow_html}</div>',
        unsafe_allow_html=True,
    )


# ── Decorative bottom feature strip (purely visual) ───────────────────────────

def render_feature_strip():
    cols = st.columns(3)
    cards = [
        ("🛡️", "var(--grad-brand)", "Fact-Check Agent", "Cross-verifies each claim across independent trusted sources."),
        ("👥", "var(--grad-blue)", "Peer Review", "Analyst peers review the draft before publication."),
        ("📅", "var(--grad-green)", "Scheduled Runs", "Automated intelligence delivered on your cadence."),
    ]
    for col, (icon, grad, title, desc) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="feature-card">'
                f'<div class="f-icon" style="background:{grad}">{icon}</div>'
                f'<h4>{title}</h4><p>{desc}</p></div>',
                unsafe_allow_html=True,
            )


# ── Settings expander ─────────────────────────────────────────────────────────

def render_settings_expander() -> tuple:
    """Returns (max_sources, max_steps) from the advanced settings panel."""
    with st.expander("⚙️ Advanced settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            max_sources = st.slider(
                "Max sources", min_value=5, max_value=40, value=20, step=5,
                help="Maximum number of web sources the Researcher will collect.",
            )
        with col2:
            max_steps = st.slider(
                "Max steps", min_value=10, max_value=100, value=50, step=10,
                help="Hard limit on total graph execution steps.",
            )
    return max_sources, max_steps


# ── Overview metrics dashboard row ───────────────────────────────────────────

def render_overview_metrics(briefing: Dict):
    """
    A top-level dashboard row showing headline numbers and a mini
    multi-series bar chart comparing section volumes at a glance.
    """
    pricing   = briefing.get("competitor_pricing", [])
    launches  = briefing.get("product_launches", [])
    signals   = briefing.get("market_signals", [])
    insights  = briefing.get("insights", [])
    sources   = briefing.get("all_sources", [])
    failed    = briefing.get("failed_sources", [])
    meta      = briefing.get("run_metadata", {})

    # ── Metric tiles ──────────────────────────────────────────────────────────
    tiles = [
        (len(pricing),  "Pricing Moves",    "#22d3ee"),
        (len(launches), "Product Launches",  "#34d399"),
        (len(signals),  "Market Signals",    "#fbbf24"),
        (len(insights), "Insights",          "#8b5cf6"),
        (len(sources),  "Sources Collected", "#6366f1"),
        (len(failed),   "Sources Skipped",   "#fb7185"),
    ]

    dur = meta.get("duration_seconds")
    if dur:
        tiles.append((f"{dur:.0f}s", "Run Duration", "#a78bfa"))

    cols = st.columns(len(tiles))
    for col, (val, label, colour) in zip(cols, tiles):
        with col:
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.035);border:1px solid '
                f'rgba(255,255,255,0.08);border-top:3px solid {colour};border-radius:12px;'
                f'padding:0.85rem 1rem;">'
                f'<div style="font-size:1.9rem;font-weight:800;color:#f3f1fa;line-height:1">'
                f'{val}</div>'
                f'<div style="font-size:0.68rem;font-weight:700;color:#7c7796;'
                f'text-transform:uppercase;letter-spacing:0.09em;margin-top:0.25rem">'
                f'{label}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Intelligence Coverage Overview — horizontal bar chart ─────────────────
    section_names  = ["Pricing Moves", "Launches", "Signals", "Insights"]
    section_counts = [len(pricing), len(launches), len(signals), len(insights)]
    section_colours = ["#22d3ee", "#34d399", "#fbbf24", "#8b5cf6"]

    # Always render the chart (show 0-counts as thin baseline bars so the
    # chart is never empty and layout stays consistent).
    # Reverse so the top of the chart shows "Pricing Moves" first.
    names_r   = list(reversed(section_names))
    counts_r  = list(reversed(section_counts))
    colours_r = list(reversed(section_colours))

    # Clamp all-zero counts so bars still render at a minimum visible width
    max_count   = max(section_counts) if any(c > 0 for c in section_counts) else 1
    display_counts = [max(c, max_count * 0.04) for c in counts_r]

    fig = go.Figure(go.Bar(
        x=display_counts,
        y=names_r,
        orientation="h",
        marker=dict(
            color=colours_r,
            line=dict(color="rgba(0,0,0,0)", width=0),
            opacity=0.88,
        ),
        text=[str(c) for c in counts_r],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(size=13, color="#ffffff", family="Manrope, Inter, sans-serif"),
        hovertemplate=[
            f"<b>{n}</b>: {c}<extra></extra>"
            for n, c in zip(names_r, counts_r)
        ],
        customdata=counts_r,
    ))

    fig.update_layout(
        **_CHART_LAYOUT,
        height=190,
        title=dict(
            text="Intelligence Coverage",
            font=dict(size=13, color="#f3f1fa", family="Manrope, Inter, sans-serif"),
            x=0,
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[0, max_count * 1.35],  # headroom so text isn't clipped
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=12, color="#b6b1cc", family="Inter, sans-serif"),
            automargin=True,
        ),
        bargap=0.28,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)


# ── PDF export ────────────────────────────────────────────────────────────────

def generate_pdf(briefing: Dict) -> bytes:
    """
    Build a clean, well-formatted A4 PDF from a BriefingOutput dict.
    White background with dark text — proper print typography.
    Uses fpdf2 (pure-Python, no system dependencies).
    """
    from fpdf import FPDF

    meta    = briefing.get("run_metadata", {})
    topic   = meta.get("topic", "Competitive Intelligence Briefing")
    run_id  = meta.get("run_id", "")
    dur     = meta.get("duration_seconds")
    sources = briefing.get("all_sources", [])
    failed  = briefing.get("failed_sources", [])

    # ── latin-1 sanitiser ─────────────────────────────────────────────────────
    def _s(v) -> str:
        return (str(v) if v is not None else "").encode("latin-1", errors="ignore").decode("latin-1")

    # ── Citation domains ──────────────────────────────────────────────────────
    def _cite(citations: list) -> str:
        urls: list = []
        for c in citations:
            urls += c.get("sources", [])
        if not urls:
            return ""
        parts = []
        for u in urls[:4]:
            try:
                parts.append(u.split("/")[2])
            except IndexError:
                parts.append(u[:35])
        return "Sources: " + "  |  ".join(parts)

    # ── Colour palette (dark ink on white paper) ──────────────────────────────
    BLACK  = (15,  15,  25)
    DARK   = (40,  35,  55)
    MID    = (90,  85, 110)
    LIGHT  = (145, 140, 160)
    WHITE  = (255, 255, 255)
    PURPLE = (90,  50, 190)
    BLUE   = (25,  90, 185)
    TEAL   = (15, 130, 120)
    AMBER  = (165, 110,   5)
    ROSE   = (170,  30,  50)
    GREEN  = (20,  130,  60)
    RULE   = (210, 205, 220)
    SHADE  = (248, 246, 252)

    # ── PDF subclass: header + footer ─────────────────────────────────────────
    class PDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            self.set_fill_color(*PURPLE)
            self.rect(0, 0, self.w, 11, style="F")
            self.set_y(2)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*WHITE)
            self.cell(self.w * 0.55, 7, _s("MarketPulse  |  Competitive Intelligence"))
            self.set_font("Helvetica", "", 8)
            self.set_text_color(220, 215, 240)
            self.cell(0, 7, _s(topic[:55]), align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(4)

        def footer(self):
            self.set_y(-12)
            self.set_draw_color(*RULE)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(1)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*LIGHT)
            self.cell(0, 5, _s(f"Page {self.page_no()}   |   Run {run_id}   |   MarketPulse"), align="C")

    pdf = PDF()
    pdf.set_margins(left=20, top=20, right=20)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    L = pdf.l_margin
    W = pdf.w - pdf.l_margin - pdf.r_margin   # usable width

    # ── Layout helpers ────────────────────────────────────────────────────────
    def sp(h: float = 3):
        pdf.ln(h)

    def hrule():
        pdf.set_draw_color(*RULE)
        pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
        sp(3)

    def section_heading(title: str, bg=PURPLE):
        sp(5)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(W, 8, _s("  " + title), fill=True, new_x="LMARGIN", new_y="NEXT")
        sp(3)

    def kv(key: str, value: str):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*MID)
        pdf.cell(38, 5.5, _s(key))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*BLACK)
        pdf.cell(W - 38, 5.5, _s(str(value)[:80]), new_x="LMARGIN", new_y="NEXT")

    def item_block(accent, label: str, title: str, detail: str, cite: str):
        """Renders one content item with a coloured left stripe."""
        top_y = pdf.get_y()
        # left stripe placeholder — will be filled after we know the height
        stripe_w = 3
        pdf.set_x(L + stripe_w + 4)

        # label badge + title
        if label:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*WHITE)
            pdf.set_fill_color(*accent)
            badge_w = pdf.get_string_width(_s(label)) + 6
            pdf.cell(badge_w, 5, _s(label), fill=True)
            pdf.set_x(L + stripe_w + 4 + badge_w + 2)

        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5.5, _s(title))

        # detail body
        pdf.set_x(L + stripe_w + 4)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(0, 5, _s(detail))

        # citation line
        if cite:
            pdf.set_x(L + stripe_w + 4)
            pdf.set_font("Helvetica", "I", 7.5)
            pdf.set_text_color(*LIGHT)
            pdf.multi_cell(0, 4, _s(cite))

        # draw the filled left stripe now we know the total height
        bot_y = pdf.get_y()
        pdf.set_fill_color(*accent)
        pdf.rect(L, top_y, stripe_w, bot_y - top_y, style="F")
        sp(4)

    # ═══════════════════════════════ TITLE BLOCK ══════════════════════════════
    pdf.set_fill_color(*PURPLE)
    pdf.rect(0, 0, pdf.w, 40, style="F")
    pdf.set_y(9)
    pdf.set_x(L)
    pdf.set_font("Helvetica", "B", 21)
    pdf.set_text_color(*WHITE)
    pdf.cell(W, 10, _s("Competitive Intelligence Briefing"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(L)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(210, 200, 240)
    pdf.multi_cell(W, 7, _s(topic[:90]))
    pdf.set_y(44)

    # Metadata grid
    dur_txt = f"{int(dur)}s" if dur else "n/a"
    tok_txt = f"{meta.get('total_tokens', 0):,}" if meta.get("total_tokens") else "n/a"
    kv("Run ID",    run_id or "n/a")
    kv("Duration",  dur_txt)
    kv("Sources",   f"{meta.get('total_sources', 0)} collected,  {meta.get('sources_skipped', 0)} skipped")
    kv("Tokens",    tok_txt)
    kv("Citations", "All cited" if meta.get("all_claims_cited", True) else "Partial")
    sp(4)
    hrule()

    # ═══════════════════════════ EXECUTIVE SUMMARY ════════════════════════════
    summary = briefing.get("executive_summary", "")
    if summary:
        section_heading("Executive Summary", PURPLE)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W, 6, _s(summary))
        sp(3)
        hrule()

    # ══════════════════════════ COMPETITOR PRICING ════════════════════════════
    pricing = briefing.get("competitor_pricing", [])
    if pricing:
        section_heading("Competitor Pricing Moves", BLUE)
        for pm in pricing:
            item_block(
                accent=BLUE,
                label="PRICING",
                title=pm.get("competitor", "Unknown"),
                detail=pm.get("description", ""),
                cite=_cite(pm.get("citations", [])),
            )
        hrule()

    # ═════════════════════════════ PRODUCT LAUNCHES ═══════════════════════════
    launches = briefing.get("product_launches", [])
    if launches:
        section_heading("Product Launches", TEAL)
        for pl in launches:
            item_block(
                accent=TEAL,
                label="LAUNCH",
                title=f'{pl.get("competitor","Unknown")}  -  {pl.get("product_name","")}',
                detail=pl.get("description", ""),
                cite=_cite(pl.get("citations", [])),
            )
        hrule()

    # ═══════════════════════════════ MARKET SIGNALS ═══════════════════════════
    signals = briefing.get("market_signals", [])
    if signals:
        section_heading("Market Signals", AMBER)
        for ms in signals:
            item_block(
                accent=AMBER,
                label="SIGNAL",
                title=ms.get("signal", "Signal"),
                detail=ms.get("detail", ""),
                cite=_cite(ms.get("citations", [])),
            )
        hrule()

    # ═══════════════════════════════════ INSIGHTS ═════════════════════════════
    insights = briefing.get("insights", [])
    if insights:
        section_heading("Key Insights", PURPLE)
        TYPE_ACCENT = {
            "trend":       BLUE,
            "opportunity": GREEN,
            "observation": TEAL,
            "risk":        ROSE,
            "threat":      ROSE,
        }
        for ins in insights:
            itype = ins.get("type", "observation")
            item_block(
                accent=TYPE_ACCENT.get(itype, PURPLE),
                label=itype.upper(),
                title=ins.get("title", ""),
                detail=ins.get("detail", ""),
                cite=_cite(ins.get("citations", [])),
            )
        hrule()

    # ══════════════════════════ STRATEGIC RECOMMENDATION ══════════════════════
    rec = briefing.get("recommendation", "")
    if rec:
        section_heading("Strategic Recommendation", GREEN)
        # shaded callout box
        box_y = pdf.get_y()
        pdf.set_fill_color(235, 248, 240)
        pdf.set_draw_color(*GREEN)
        # draw after writing so we know the height
        pdf.set_x(L + 4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*GREEN)
        pdf.cell(W - 4, 6, _s("Recommended Action"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(L + 4)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W - 4, 5.5, _s(rec))
        box_h = pdf.get_y() - box_y + 2
        pdf.set_fill_color(235, 248, 240)
        pdf.rect(L, box_y, W, box_h, style="FD")
        # re-write text on top of the filled box
        pdf.set_y(box_y)
        pdf.set_x(L + 4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*GREEN)
        pdf.cell(W - 4, 6, _s("Recommended Action"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(L + 4)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W - 4, 5.5, _s(rec))
        sp(4)
        hrule()

    # ═══════════════════════════════════ SOURCES ══════════════════════════════
    if sources or failed:
        section_heading("Sources", MID)
        for i, src in enumerate(sources, 1):
            title_t = _s((src.get("title") or src.get("url", ""))[:85])
            url_t   = _s(src.get("url", "")[:95])
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*DARK)
            pdf.cell(7, 5, _s(f"{i}."))
            pdf.multi_cell(0, 5, title_t)
            pdf.set_x(L + 7)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*LIGHT)
            pdf.multi_cell(0, 4, url_t)
            sp(1)

        if failed:
            sp(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*ROSE)
            pdf.cell(W, 5, _s(f"Skipped sources ({len(failed)}):"),
                     new_x="LMARGIN", new_y="NEXT")
            for fs in failed:
                reason = _s((fs.get("failure_reason") or fs.get("title", "unknown"))[:85])
                pdf.set_font("Helvetica", "", 8.5)
                pdf.set_text_color(*ROSE)
                pdf.cell(7, 5, _s("x"))
                pdf.multi_cell(0, 5, reason)

    return bytes(pdf.output())


# ── Full briefing renderer ────────────────────────────────────────────────────

def render_briefing(briefing: Dict):
    """Render all sections of a completed BriefingOutput dict."""
    meta = briefing.get("run_metadata", {})

    # ── Dashboard overview row ────────────────────────────────────────────────
    render_overview_metrics(briefing)
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    col_main, col_side = st.columns([2.6, 1], gap="medium")

    with col_main:
        render_executive_summary(briefing.get("executive_summary", ""))

        tabs = st.tabs([
            "💰 Pricing",
            "🚀 Launches",
            "📡 Signals",
            "🔍 Insights",
            "✅ Recommendation",
            "📝 Full Markdown",
        ])

        with tabs[0]:
            render_pricing_moves(briefing.get("competitor_pricing", []))

        with tabs[1]:
            render_product_launches(briefing.get("product_launches", []))

        with tabs[2]:
            render_market_signals(briefing.get("market_signals", []))

        with tabs[3]:
            render_insights(briefing.get("insights", []))

        with tabs[4]:
            render_recommendation(briefing.get("recommendation", ""))

        with tabs[5]:
            raw = briefing.get("raw_markdown", "")
            if raw:
                st.markdown(raw)
                col_md, col_pdf = st.columns(2, gap="small")
                with col_md:
                    st.download_button(
                        label="⬇️ Download Markdown",
                        data=raw,
                        file_name=f"briefing_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with col_pdf:
                    try:
                        pdf_bytes = generate_pdf(briefing)
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_bytes,
                            file_name=f"briefing_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as _pdf_err:
                        st.caption(f"PDF unavailable: {_pdf_err}")

        render_sources(
            briefing.get("all_sources", []),
            briefing.get("failed_sources", []),
        )

    with col_side:
        render_info_panel(meta)

    st.divider()
    render_feature_strip()


# ── Streaming progress display ────────────────────────────────────────────────

def run_with_progress(topic: str, max_sources: int, max_steps: int, container) -> Dict:
    """
    Run the briefing pipeline with a live progress display rendered
    inside the provided stable container (st.empty).

    Returns the final BriefingOutput dict.
    """
    from graph import stream_briefing

    NODE_LABELS = {
        "coordinator": ("🎯", "Coordinator", "Validating topic & initialising run…"),
        "researcher":  ("🔍", "Researcher",  "Searching the web for competitive data…"),
        "validator":   ("🛡️",  "Validator",   "Checking source quality & relevance…"),
        "analyst":     ("🧠", "Analyst",     "Extracting insights from research…"),
        "writer":      ("✍️",  "Writer",      "Composing your briefing…"),
    }
    NODE_ORDER = ["coordinator", "researcher", "validator", "analyst", "writer"]

    def _progress_html(completed: list, current: str) -> str:
        """Render a fixed-height progress card so the container never resizes."""
        steps_html = ""
        for node in NODE_ORDER:
            if node in completed:
                dot_cls  = "status-done";    dot_lbl = "Done"
            elif node == current:
                dot_cls  = "status-running"; dot_lbl = "Running"
            else:
                dot_cls  = "status-pending"; dot_lbl = "Pending"

            icon, name, sub = NODE_LABELS[node]
            steps_html += (
                f'<div style="display:flex;align-items:center;gap:10px;'
                f'padding:8px 10px;border-radius:10px;margin-bottom:6px;'
                f'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07)">'
                f'<span style="font-size:1.1rem;min-width:26px;text-align:center">{icon}</span>'
                f'<div style="flex:1;min-width:0">'
                f'<div style="font-size:0.84rem;font-weight:700;color:#f3f1fa">{name}</div>'
                f'<div style="font-size:0.72rem;color:#7c7796">{sub}</div>'
                f'</div>'
                f'<span class="agent-status {dot_cls}">'
                f'<span class="dot"></span>{dot_lbl}</span>'
                f'</div>'
            )
        pct = int(len(completed) / len(NODE_ORDER) * 100)
        bar_html = (
            f'<div style="background:rgba(255,255,255,0.08);border-radius:999px;'
            f'height:6px;margin-bottom:18px;overflow:hidden">'
            f'<div style="background:linear-gradient(90deg,#8b5cf6,#c026d3);'
            f'height:100%;width:{pct}%;border-radius:999px;'
            f'transition:width 0.4s ease"></div></div>'
        )
        return (
            '<div style="background:rgba(255,255,255,0.035);border:1px solid '
            'rgba(255,255,255,0.08);border-radius:20px;padding:1.6rem 1.8rem;'
            'max-width:680px;margin:0 auto">'
            '<div style="font-size:0.68rem;font-weight:800;letter-spacing:0.12em;'
            'color:#a78bfa;text-transform:uppercase;margin-bottom:12px">'
            '▶ Pipeline Running</div>'
            + bar_html + steps_html +
            '</div>'
        )

    completed_nodes: list = []
    final_state: Dict = {}

    try:
        for event in stream_briefing(topic, max_sources=max_sources, max_steps=max_steps):
            node = event.get("node", "")
            state = event.get("state", {})

            if node in NODE_ORDER:
                current = node
                # Show current node as running before marking done
                container.markdown(
                    _progress_html(completed_nodes, current),
                    unsafe_allow_html=True,
                )
                completed_nodes.append(node)
                # Re-render with node now marked done
                container.markdown(
                    _progress_html(completed_nodes, ""),
                    unsafe_allow_html=True,
                )

                if node == "writer" and state.get("briefing_output"):
                    final_state = state

    except Exception as exc:
        container.markdown(
            f'<div style="background:rgba(244,63,94,0.10);border:1px solid '
            f'rgba(244,63,94,0.35);border-radius:14px;padding:1rem 1.2rem;'
            f'color:#fda4af;font-size:0.86rem">⚠ Pipeline error: {exc}</div>',
            unsafe_allow_html=True,
        )
        return {}

    return final_state.get("briefing_output") or {}


# ── Main entrypoint ───────────────────────────────────────────────────────────

def main():
    init_session()

    briefing: Optional[Dict] = st.session_state.get("briefing")
    running: bool = st.session_state.get("running", False)
    meta = briefing.get("run_metadata", {}) if briefing else None

    render_page_header(briefing)
    render_sidebar(meta, running)

    # ── Input row — always rendered at the same position ─────────────────────
    with st.container():
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            topic = st.text_input(
                "Market / topic to brief",
                placeholder="e.g. CRM software market, AI coding assistants, fintech payments…",
                value=st.session_state.get("last_topic", ""),
                disabled=running,
                label_visibility="collapsed",
            )
        with col_btn:
            run_clicked = st.button(
                "▶ Run Brief",
                disabled=running,
                use_container_width=True,
            )

    max_sources, max_steps = render_settings_expander()

    # ── Single stable content slot — never changes position ──────────────────
    # All three states (welcome / running / briefing) render into this one
    # placeholder so nothing above or below it ever shifts.
    content_slot = st.empty()

    # ── Handle button click ───────────────────────────────────────────────────
    if run_clicked:
        topic = topic.strip()
        if not topic:
            st.warning("Please enter a topic before running.")
        else:
            st.session_state["running"] = True
            st.session_state["last_topic"] = topic
            st.session_state["briefing"] = None
            st.rerun()

    # ── Execute pipeline (running state) ─────────────────────────────────────
    if running and briefing is None:
        topic = st.session_state.get("last_topic", "")
        briefing_dict = run_with_progress(topic, max_sources, max_steps, content_slot)

        if briefing_dict:
            st.session_state["briefing"] = briefing_dict
        st.session_state["running"] = False
        st.rerun()

    # ── Render completed briefing ─────────────────────────────────────────────
    elif briefing:
        with content_slot.container():
            st.divider()
            render_briefing(briefing)

    # ── Welcome state ─────────────────────────────────────────────────────────
    else:
        with content_slot.container():
            render_preview_strip()
            st.markdown(
                """
                <div class="welcome-box">
                    <div class="w-icon">📊</div>
                    <h3>Enter a market topic above to generate your briefing</h3>
                    <p>
                        The AI crew will search the web, analyse competitors, and produce a
                        structured weekly briefing with inline citations — in under 3 minutes.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()