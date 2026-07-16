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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

# ── History / Archive store ───────────────────────────────────────────────────
from history import store as _report_store

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

/* sidebar buttons — brand gradient (primary: Run Brief, Clear Chat, etc.) */
[data-testid="stSidebar"] [data-testid="baseButton-primary"],
[data-testid="stSidebar"] div.stButton > button:not([data-testid="baseButton-secondary"]) {
    background: var(--grad-brand) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    box-shadow: 0 8px 24px rgba(139,92,246,0.35);
}
[data-testid="stSidebar"] [data-testid="baseButton-primary"]:hover,
[data-testid="stSidebar"] div.stButton > button:not([data-testid="baseButton-secondary"]):hover {
    filter: brightness(1.08);
}

/* History "Open" buttons in sidebar — ghost style so they're visible on dark bg */
/* Streamlit 1.46 renders secondary buttons with data-testid="baseButton-secondary" */
[data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
    background: rgba(139,92,246,0.15) !important;
    color: #a78bfa !important;
    border: 1px solid rgba(139,92,246,0.4) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    box-shadow: none !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover {
    background: rgba(139,92,246,0.28) !important;
    border-color: rgba(139,92,246,0.65) !important;
    color: #c4b5fd !important;
    filter: none !important;
}

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
    margin-bottom: 1.2rem;
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
    max_val = max(values) if values else 1
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
        cliponaxis=False,
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        height=max(240, len(labels) * 52),
        title=dict(text=title, font=dict(size=13, color="#f3f1fa"), x=0),
        # 30 % headroom on the right so "outside" text labels are never clipped
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[0, max_val * 1.30],
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#f3f1fa"),
            automargin=True,
        ),
    )
    # Override the margin from _CHART_LAYOUT to add right-side space for labels
    fig.update_layout(margin=dict(l=0, r=40, t=32, b=0))
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
        # Tracks what is currently displayed in the text input widget.
        # Kept separately from last_topic so we can restore it after a
        # rerun without relying on the disabled-widget value quirk.
        "topic_input": "",
        # ── History / Archive ─────────────────────────────────────────────────
        # ID of the report currently open in the read-only viewer (None = closed)
        "history_view_id": None,
        # Current search query text in the History tab
        "history_search": "",
        # ID awaiting delete confirmation (None = no pending delete)
        "history_delete_id": None,
        # Flag to force a re-fetch of the history list after save/delete
        "history_stale": False,
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

        # ── HISTORY section ───────────────────────────────────────────────────
        _render_history_sidebar_section()


# ── History sidebar section ───────────────────────────────────────────────────

def _render_history_sidebar_section() -> None:
    """
    Renders the collapsible History section at the bottom of the sidebar.
    Shows a compact list of the 10 most recent reports.  Each row is a
    button that opens the full report in the read-only viewer.
    """
    count = _report_store.count()
    count_badge = (
        f'<span style="display:inline-block;background:rgba(139,92,246,0.25);'
        f'color:#a78bfa;border:1px solid rgba(139,92,246,0.35);border-radius:999px;'
        f'padding:1px 8px;font-size:0.65rem;font-weight:700;margin-left:6px">'
        f'{count}</span>'
    )
    st.markdown(
        f'<div class="sidebar-label" style="margin-top:1.4rem">'
        f'History {count_badge}</div>',
        unsafe_allow_html=True,
    )

    if count == 0:
        st.markdown(
            '<div style="font-size:0.76rem;color:var(--text-low);'
            'padding:0.4rem 0.2rem">No reports saved yet.</div>',
            unsafe_allow_html=True,
        )
        return

    # Load the 10 most-recent summaries for the sidebar preview
    recent = _report_store.list_reports(limit=10)

    for row in recent:
        rid        = row["id"]
        title      = row["title"] or "Untitled Report"
        competitors = row.get("competitors") or ""
        created_raw = row.get("created_at", "")

        # Format the timestamp for display
        try:
            dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            ts = dt.strftime("%b %d, %H:%M")
        except Exception:
            ts = created_raw[:16] if created_raw else "–"

        is_active = (st.session_state.get("history_view_id") == rid)
        active_style = (
            "border-color:rgba(139,92,246,0.5);background:rgba(139,92,246,0.08);"
            if is_active else ""
        )

        # Competitor sub-label (truncate to keep sidebar compact)
        sub_label = (competitors[:38] + "…") if len(competitors) > 38 else competitors
        sub_html = (
            f'<div style="font-size:0.66rem;color:var(--text-low);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{sub_label or "—"}</div>'
        ) if sub_label else ""

        st.markdown(
            f'<div class="agent-row" style="cursor:pointer;{active_style}">'
            f'<div class="agent-icon" style="background:var(--grad-brand);'
            f'font-size:0.85rem">📄</div>'
            f'<div class="agent-meta" style="min-width:0">'
            f'<div class="a-name" style="white-space:nowrap;overflow:hidden;'
            f'text-overflow:ellipsis;max-width:140px" title="{title}">'
            f'{title[:36]}{"…" if len(title) > 36 else ""}</div>'
            f'{sub_html}'
            f'</div>'
            f'<div style="font-size:0.64rem;color:var(--text-low);'
            f'white-space:nowrap;text-align:right">{ts}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Open →",
            key=f"hist_open_{rid}",
            use_container_width=True,
            help=f"Open: {title}",
            type="primary",
        ):
            st.session_state["history_view_id"] = rid
            st.rerun()
        st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

    if count > 10:
        st.markdown(
            f'<div style="font-size:0.72rem;color:var(--text-low);'
            f'text-align:center;padding:0.3rem 0">'
            f'+ {count - 10} more — see History tab</div>',
            unsafe_allow_html=True,
        )


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
            max_val = max(values) if values else 1
            fig = go.Figure(go.Bar(
                x=values, y=labels, orientation="h",
                marker_color="#22d3ee",
                text=values, textposition="outside",
                textfont=dict(size=11, color="#f3f1fa"),
                cliponaxis=False,
            ))
            fig.update_layout(
                **_CHART_LAYOUT, height=max(200, len(moves) * 55),
                title=dict(text="Coverage per Competitor", font=dict(size=13, color="#f3f1fa"), x=0),
                xaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    range=[0, max_val * 1.30],
                ),
                yaxis=dict(
                    showgrid=False, tickfont=dict(size=12, color="#f3f1fa"),
                    automargin=True,
                ),
            )
            fig.update_layout(margin=dict(l=0, r=40, t=32, b=0))
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
        max_val = max(values) if values else 1
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker=dict(color=colours, line=dict(color="rgba(255,255,255,0.1)", width=1)),
            text=values, textposition="outside",
            textfont=dict(size=12, color="#f3f1fa"),
            cliponaxis=False,
        ))
        fig.update_layout(
            **_CHART_LAYOUT,
            # Extra top headroom so "outside" count labels above bars are never clipped
            height=max(280, len(labels) * 80),
            title=dict(text="Launches per Competitor", font=dict(size=13, color="#f3f1fa"), x=0),
            xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#f3f1fa"), automargin=True),
            yaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=[0, max_val * 1.30],
            ),
            bargap=0.35,
        )
        fig.update_layout(margin=dict(l=0, r=10, t=48, b=0))
        st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

        # ── Launch Sequence: fixed-column dot plot ────────────────────────────
        # All dots share x=0 so they form a clean vertical list aligned with
        # the y-axis labels. Text is rendered to the right of each dot.
        if len(launches) >= 2:
            y_labels = [
                f'{pl.get("competitor", "?")} · {pl.get("product_name", "?")}'
                for pl in launches
            ]
            fig2 = go.Figure(go.Scatter(
                x=[0] * len(y_labels),
                y=y_labels,
                mode="markers+text",
                marker=dict(
                    size=14,
                    color=_PALETTE[:len(y_labels)],
                    line=dict(color="rgba(255,255,255,0.3)", width=2),
                ),
                text=y_labels,
                textposition="middle right",
                textfont=dict(size=10, color="#b6b1cc"),
                showlegend=False,
                hovertemplate="%{y}<extra></extra>",
            ))
            # Right margin wide enough for the longest label; hide x-axis entirely
            max_label_len = max(len(lbl) for lbl in y_labels) if y_labels else 20
            fig2.update_layout(
                **_CHART_LAYOUT,
                height=max(180, len(launches) * 52),
                title=dict(text="Launch Sequence", font=dict(size=13, color="#f3f1fa"), x=0),
                xaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    range=[-0.5, max_label_len * 0.065 + 0.5],
                ),
                yaxis=dict(
                    showgrid=False,
                    showticklabels=False,   # labels are the dot text, not tick labels
                    autorange="reversed",
                    automargin=True,
                ),
            )
            fig2.update_layout(margin=dict(l=10, r=10, t=40, b=0))
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
    Build a professional A4 executive report PDF from a BriefingOutput dict.
    Layout: branded cover page -> KPI dashboard -> sections with tables/cards
    -> recommendation callout -> numbered references.
    Uses fpdf2 (pure-Python, no system dependencies).
    """
    from fpdf import FPDF
    from datetime import datetime as _dt, timezone as _tz

    meta    = briefing.get("run_metadata", {})
    topic   = meta.get("topic", "Competitive Intelligence Briefing")
    run_id  = meta.get("run_id", "")
    dur     = meta.get("duration_seconds")
    sources = briefing.get("all_sources", [])
    failed  = briefing.get("failed_sources", [])
    pricing   = briefing.get("competitor_pricing", [])
    launches  = briefing.get("product_launches", [])
    signals   = briefing.get("market_signals", [])
    insights  = briefing.get("insights", [])
    summary   = briefing.get("executive_summary", "")
    rec       = briefing.get("recommendation", "")

    # ── latin-1 sanitiser ────────────────────────────────────────────────────
    def _s(v) -> str:
        return (str(v) if v is not None else "").encode("latin-1", errors="ignore").decode("latin-1")

    # ── Build a global citation index: url -> [N]  ───────────────────────────
    _url_index: dict = {}
    _ref_list: list = []          # (N, title, url)

    def _register_url(url: str, title: str = "") -> int:
        """Register url and return its 1-based citation number."""
        if not url:
            return 0
        if url not in _url_index:
            n = len(_ref_list) + 1
            _url_index[url] = n
            _ref_list.append((n, title or url, url))
        return _url_index[url]

    def _cite_nums(citations: list) -> str:
        """Return compact inline citation string like '[1][3]' from citations list."""
        nums = []
        for c in citations:
            for url in c.get("sources", []):
                n = _register_url(url)
                if n and n not in nums:
                    nums.append(n)
        if not nums:
            return ""
        return "  " + "".join(f"[{n}]" for n in sorted(nums))

    # Pre-register all sources in order so numbering is deterministic
    for src in sources:
        if not src.get("failed"):
            _register_url(src.get("url", ""), src.get("title", ""))

    # Pre-pass: register citations from all sections so numbers are stable
    for pm in pricing:
        _cite_nums(pm.get("citations", []))
    for pl in launches:
        _cite_nums(pl.get("citations", []))
    for ms in signals:
        _cite_nums(ms.get("citations", []))
    for ins in insights:
        _cite_nums(ins.get("citations", []))

    # ── Colour palette ───────────────────────────────────────────────────────
    BLACK   = (20,  20,  30)
    DARK    = (45,  40,  60)
    MID     = (95,  90, 115)
    LIGHT   = (150, 145, 165)
    WHITE   = (255, 255, 255)
    NAVY    = (18,  42,  88)       # primary brand colour
    INDIGO  = (63,  81, 181)       # section headers
    TEAL    = (0,  128, 128)       # launches
    AMBER   = (158, 104,   0)      # signals
    ROSE    = (160,  30,  50)      # risk / failed
    GREEN   = (20,  120,  60)      # recommendation / opportunity
    BLUE    = (25,  90,  185)      # pricing
    RULE    = (215, 210, 225)      # horizontal rules
    SHADE_L = (247, 246, 252)      # light section background
    SHADE_G = (235, 248, 240)      # green tint for recommendation
    SHADE_B = (235, 242, 255)      # blue tint for KPI
    COVER_BG= (18,  42,  88)       # cover background = NAVY
    COVER_AC= (99, 102, 241)       # cover accent stripe

    # ── PDF class with header / footer ───────────────────────────────────────
    class PDF(FPDF):
        def header(self):
            if self.page_no() <= 2:          # cover + TOC/KPI page: no header
                return
            # Slim navy bar
            self.set_fill_color(*NAVY)
            self.rect(0, 0, self.w, 10, style="F")
            self.set_y(1.5)
            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*WHITE)
            self.set_x(self.l_margin)
            self.cell(self.w * 0.55, 7, _s("MarketPulse  |  Competitive Intelligence"))
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(190, 200, 230)
            self.cell(0, 7, _s(topic[:60]), align="R",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(3)

        def footer(self):
            if self.page_no() == 1:          # no footer on cover
                return
            self.set_y(-13)
            self.set_draw_color(*RULE)
            self.line(self.l_margin, self.get_y(),
                      self.w - self.r_margin, self.get_y())
            self.ln(1)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*LIGHT)
            date_str = _dt.now(_tz.utc).strftime("%B %Y")
            self.cell(self.w * 0.45, 5,
                      _s(f"Confidential  |  {date_str}  |  Run {run_id}"))
            self.cell(0, 5, _s(f"Page {self.page_no() - 1}"), align="R")

    pdf = PDF()
    pdf.set_margins(left=18, top=18, right=18)
    pdf.set_auto_page_break(auto=True, margin=20)

    L = 18
    W = 210 - 36          # A4 width minus both margins = 174 mm

    # ── Shared layout helpers ────────────────────────────────────────────────
    def sp(h: float = 4):
        pdf.ln(h)

    def hrule(colour=RULE, thickness: float = 0.3):
        pdf.set_draw_color(*colour)
        pdf.set_line_width(thickness)
        pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
        pdf.set_line_width(0.2)
        sp(3)

    def section_heading(title: str, colour=INDIGO, icon: str = ""):
        sp(6)
        # Accent bar left of heading
        bar_h = 8
        pdf.set_fill_color(*colour)
        pdf.rect(L, pdf.get_y(), 4, bar_h, style="F")
        pdf.set_x(L + 7)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*colour)
        label = f"{icon}  {title}" if icon else title
        pdf.cell(W - 7, bar_h, _s(label), new_x="LMARGIN", new_y="NEXT")
        sp(2)
        hrule(colour, 0.4)

    def label_pill(text: str, colour):
        """Inline coloured badge rendered as filled rectangle + white text."""
        pdf.set_font("Helvetica", "B", 7)
        tw = pdf.get_string_width(_s(text)) + 4
        x, y = pdf.get_x(), pdf.get_y()
        pdf.set_fill_color(*colour)
        pdf.rect(x, y + 0.5, tw, 4.5, style="F")
        pdf.set_text_color(*WHITE)
        pdf.cell(tw, 5.5, _s(text), align="C")
        pdf.set_text_color(*BLACK)

    # ════════════════════════════ PAGE 1 — COVER ═════════════════════════════
    pdf.add_page()

    # Full-page navy background
    pdf.set_fill_color(*COVER_BG)
    pdf.rect(0, 0, 210, 297, style="F")

    # Decorative accent stripe (bottom-left triangle simulation via thick rect)
    pdf.set_fill_color(*COVER_AC)
    pdf.rect(0, 240, 60, 57, style="F")
    pdf.rect(0, 240, 120, 12, style="F")

    # Logo / brand wordmark
    pdf.set_xy(L, 38)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(160, 170, 230)
    pdf.cell(W, 8, _s("MARKETPULSE"), new_x="LMARGIN", new_y="NEXT")

    # Thin horizontal accent rule under brand
    pdf.set_draw_color(*COVER_AC)
    pdf.set_line_width(0.8)
    pdf.line(L, pdf.get_y(), L + 30, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(10)

    # Main title
    pdf.set_x(L)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(W, 13, _s("Competitive\nIntelligence\nBriefing"), align="L")
    pdf.ln(6)

    # Topic subtitle
    pdf.set_x(L)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(190, 200, 235)
    pdf.multi_cell(W, 8, _s(topic[:100]), align="L")
    pdf.ln(14)

    # Divider
    pdf.set_draw_color(90, 100, 160)
    pdf.set_line_width(0.5)
    pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(8)

    # Metadata grid on cover (2-col key/value)
    dur_txt = f"{int(dur)}s" if dur else "n/a"
    tok_txt = f"{meta.get('total_tokens', 0):,}" if meta.get("total_tokens") else "n/a"
    date_cover = _dt.now(_tz.utc).strftime("%d %B %Y")
    cover_meta = [
        ("Date",        date_cover),
        ("Run ID",      run_id or "n/a"),
        ("Duration",    dur_txt),
        ("Sources",     f"{meta.get('total_sources', 0)} collected"),
        ("Citations",   "All cited" if meta.get("all_claims_cited", True) else "Partial"),
        ("Tokens",      tok_txt),
    ]
    col_w = W / 2
    for i, (k, v) in enumerate(cover_meta):
        if i % 2 == 0:
            pdf.set_x(L)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(140, 155, 210)
        pdf.cell(22, 6, _s(k.upper()))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*WHITE)
        if i % 2 == 0:
            pdf.cell(col_w - 22, 6, _s(v), new_x="CONTIGUOUS")
        else:
            pdf.cell(col_w - 22, 6, _s(v), new_x="LMARGIN", new_y="NEXT")

    # "CONFIDENTIAL" watermark strip at bottom
    pdf.set_xy(L, 270)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(80, 95, 150)
    pdf.cell(W, 5,
             _s("CONFIDENTIAL — For internal use only. Generated by MarketPulse AI Crew."),
             align="C")


    # ════════════════════════ PAGE 2 — KPI DASHBOARD + EXEC SUMMARY ══════════
    pdf.add_page()

    # ── KPI cards row ────────────────────────────────────────────────────────
    # Five equal-width cards in a single row across the full usable width
    kpi_items = [
        ("Pricing Moves",   len(pricing),   BLUE),
        ("Product Launches",len(launches),  TEAL),
        ("Market Signals",  len(signals),   AMBER),
        ("Key Insights",    len(insights),  INDIGO),
        ("Sources",         len(sources),   NAVY),
    ]
    card_w   = W / len(kpi_items)
    card_h   = 22
    card_top = pdf.get_y()

    for idx, (label, count, colour) in enumerate(kpi_items):
        cx = L + idx * card_w
        # Card background
        pdf.set_fill_color(SHADE_L[0], SHADE_L[1], SHADE_L[2])
        pdf.rect(cx, card_top, card_w - 1.5, card_h, style="F")
        # Top accent strip
        pdf.set_fill_color(*colour)
        pdf.rect(cx, card_top, card_w - 1.5, 2.5, style="F")
        # Count number
        pdf.set_xy(cx, card_top + 4)
        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(*colour)
        pdf.cell(card_w - 1.5, 9, _s(str(count)), align="C",
                 new_x="RIGHT", new_y="TOP")
        # Label text
        pdf.set_xy(cx, card_top + 13)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(*MID)
        pdf.cell(card_w - 1.5, 5, _s(label), align="C",
                 new_x="RIGHT", new_y="TOP")

    pdf.set_y(card_top + card_h + 6)

    # ── Section: Executive Summary ───────────────────────────────────────────
    if summary:
        section_heading("Executive Summary", NAVY, "")

        # Shaded callout box
        box_top = pdf.get_y()
        # Measure height first by writing off-page, then draw box, then re-write
        # fpdf2 does not support look-ahead, so we use a two-pass approach:
        # pass 1 — write to get ending Y, pass 2 — draw rect then re-write.
        pdf.set_x(L + 6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W - 12, 6, _s(summary))
        box_bot = pdf.get_y()
        box_h   = box_bot - box_top + 3

        # Draw shaded rect behind the text (overdraw then re-write)
        pdf.set_fill_color(SHADE_L[0], SHADE_L[1], SHADE_L[2])
        pdf.set_draw_color(*INDIGO)
        pdf.set_line_width(0.3)
        pdf.rect(L, box_top - 1, W, box_h, style="FD")
        pdf.set_line_width(0.2)
        # Left accent bar
        pdf.set_fill_color(*NAVY)
        pdf.rect(L, box_top - 1, 3, box_h, style="F")
        # Re-write text on top
        pdf.set_xy(L + 6, box_top)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W - 12, 6, _s(summary))
        sp(5)


    # ════════════════════ SECTION: COMPETITOR PRICING MOVES ══════════════════
    if pricing:
        section_heading("Competitor Pricing Moves", BLUE, "")

        # Table header
        col_comp  = 42
        col_desc  = W - col_comp - 18
        col_cite  = 18
        row_h     = 6

        def table_header_pricing():
            pdf.set_fill_color(*BLUE)
            pdf.set_text_color(*WHITE)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_x(L)
            pdf.cell(col_comp, row_h, _s("  Competitor"),  fill=True)
            pdf.cell(col_desc, row_h, _s("  Change Detail"), fill=True)
            pdf.cell(col_cite, row_h, _s("Ref"), fill=True, align="C",
                     new_x="LMARGIN", new_y="NEXT")

        table_header_pricing()
        for i, pm in enumerate(pricing):
            cite_str = _cite_nums(pm.get("citations", []))
            desc     = pm.get("description", "")
            comp     = pm.get("competitor", "Unknown")
            fill_col = SHADE_L if i % 2 == 0 else WHITE
            pdf.set_fill_color(*fill_col)
            pdf.set_text_color(*DARK)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_x(L)
            # Measure wrapped height for description
            pdf.set_font("Helvetica", "", 8)
            lines_needed = max(1, len(desc) // 70 + 1)
            cell_h = max(row_h + 2, lines_needed * 5)
            start_y = pdf.get_y()
            # Competitor name cell (vertically centred via manual offset)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_fill_color(*fill_col)
            pdf.rect(L, start_y, col_comp, cell_h, style="F")
            pdf.set_xy(L + 2, start_y + 1)
            pdf.multi_cell(col_comp - 2, 5, _s(comp[:28]))
            # Description cell
            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_comp, start_y, col_desc, cell_h, style="F")
            pdf.set_xy(L + col_comp + 2, start_y + 1)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(col_desc - 4, 5, _s(desc))
            # Citation cell
            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_comp + col_desc, start_y, col_cite, cell_h, style="F")
            pdf.set_xy(L + col_comp + col_desc + 1, start_y + 1)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*BLUE)
            pdf.multi_cell(col_cite - 2, 5, _s(cite_str))
            # Advance cursor
            pdf.set_y(start_y + cell_h)
            # Row border line
            pdf.set_draw_color(*RULE)
            pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
        sp(6)

    # ═════════════════════════ SECTION: PRODUCT LAUNCHES ═════════════════════
    if launches:
        section_heading("Product Launches", TEAL, "")

        col_comp  = 38
        col_prod  = 44
        col_desc  = W - col_comp - col_prod - 16
        col_cite  = 16
        row_h     = 6

        def table_header_launches():
            pdf.set_fill_color(*TEAL)
            pdf.set_text_color(*WHITE)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_x(L)
            pdf.cell(col_comp, row_h, _s("  Competitor"),   fill=True)
            pdf.cell(col_prod, row_h, _s("  Product"),      fill=True)
            pdf.cell(col_desc, row_h, _s("  Description"),  fill=True)
            pdf.cell(col_cite, row_h, _s("Ref"), fill=True, align="C",
                     new_x="LMARGIN", new_y="NEXT")

        table_header_launches()
        for i, pl in enumerate(launches):
            cite_str = _cite_nums(pl.get("citations", []))
            desc     = pl.get("description", "")
            comp     = pl.get("competitor", "Unknown")
            prod     = pl.get("product_name", "")
            fill_col = SHADE_L if i % 2 == 0 else WHITE
            start_y  = pdf.get_y()
            lines_needed = max(1, len(desc) // 58 + 1)
            cell_h   = max(row_h + 2, lines_needed * 5)

            pdf.set_fill_color(*fill_col)
            pdf.rect(L, start_y, col_comp, cell_h, style="F")
            pdf.set_xy(L + 2, start_y + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(col_comp - 2, 5, _s(comp[:24]))

            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_comp, start_y, col_prod, cell_h, style="F")
            pdf.set_xy(L + col_comp + 2, start_y + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*TEAL)
            pdf.multi_cell(col_prod - 2, 5, _s(prod[:30]))

            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_comp + col_prod, start_y, col_desc, cell_h, style="F")
            pdf.set_xy(L + col_comp + col_prod + 2, start_y + 1)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(col_desc - 4, 5, _s(desc))

            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_comp + col_prod + col_desc, start_y, col_cite, cell_h, style="F")
            pdf.set_xy(L + col_comp + col_prod + col_desc + 1, start_y + 1)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*TEAL)
            pdf.multi_cell(col_cite - 2, 5, _s(cite_str))

            pdf.set_y(start_y + cell_h)
            pdf.set_draw_color(*RULE)
            pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
        sp(6)

    # ══════════════════════════ SECTION: MARKET SIGNALS ══════════════════════
    if signals:
        section_heading("Market Signals", AMBER, "")

        col_sig  = 52
        col_det  = W - col_sig - 16
        col_cite = 16
        row_h    = 6

        def table_header_signals():
            pdf.set_fill_color(*AMBER)
            pdf.set_text_color(*WHITE)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_x(L)
            pdf.cell(col_sig,  row_h, _s("  Signal"),  fill=True)
            pdf.cell(col_det,  row_h, _s("  Detail"),  fill=True)
            pdf.cell(col_cite, row_h, _s("Ref"), fill=True, align="C",
                     new_x="LMARGIN", new_y="NEXT")

        table_header_signals()
        for i, ms in enumerate(signals):
            cite_str = _cite_nums(ms.get("citations", []))
            sig      = ms.get("signal", "")
            det      = ms.get("detail", "")
            fill_col = SHADE_L if i % 2 == 0 else WHITE
            start_y  = pdf.get_y()
            lines_needed = max(1, len(det) // 72 + 1)
            cell_h   = max(row_h + 2, lines_needed * 5)

            pdf.set_fill_color(*fill_col)
            pdf.rect(L, start_y, col_sig, cell_h, style="F")
            pdf.set_xy(L + 2, start_y + 1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*AMBER)
            pdf.multi_cell(col_sig - 2, 5, _s(sig[:40]))

            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_sig, start_y, col_det, cell_h, style="F")
            pdf.set_xy(L + col_sig + 2, start_y + 1)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(col_det - 4, 5, _s(det))

            pdf.set_fill_color(*fill_col)
            pdf.rect(L + col_sig + col_det, start_y, col_cite, cell_h, style="F")
            pdf.set_xy(L + col_sig + col_det + 1, start_y + 1)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*AMBER)
            pdf.multi_cell(col_cite - 2, 5, _s(cite_str))

            pdf.set_y(start_y + cell_h)
            pdf.set_draw_color(*RULE)
            pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
        sp(6)


    # ════════════════════════════ SECTION: KEY INSIGHTS ══════════════════════
    if insights:
        section_heading("Key Insights", INDIGO, "")

        TYPE_COLOUR = {
            "trend":       BLUE,
            "opportunity": GREEN,
            "observation": TEAL,
            "risk":        ROSE,
            "threat":      ROSE,
        }

        for ins in insights:
            itype    = ins.get("type", "observation")
            colour   = TYPE_COLOUR.get(itype, INDIGO)
            title_t  = ins.get("title", "")
            detail_t = ins.get("detail", "")
            cite_str = _cite_nums(ins.get("citations", []))

            top_y  = pdf.get_y()
            stripe = 3          # left accent stripe width

            # Write content first to measure height
            pdf.set_x(L + stripe + 5)
            # Type badge
            badge_txt = itype.upper()
            pdf.set_font("Helvetica", "B", 7)
            bw = pdf.get_string_width(_s(badge_txt)) + 4
            pdf.set_fill_color(*colour)
            pdf.set_text_color(*WHITE)
            pdf.rect(L + stripe + 5, top_y + 1, bw, 4.5, style="F")
            pdf.set_xy(L + stripe + 5, top_y + 1)
            pdf.cell(bw, 4.5, _s(badge_txt), align="C")

            # Title
            pdf.set_xy(L + stripe + 5 + bw + 2, top_y + 1)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(W - stripe - 5 - bw - 2, 5.5, _s(title_t))

            # Detail body
            pdf.set_x(L + stripe + 5)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(W - stripe - 5, 5, _s(detail_t))

            # Citation footnote
            if cite_str:
                pdf.set_x(L + stripe + 5)
                pdf.set_font("Helvetica", "I", 7)
                pdf.set_text_color(*LIGHT)
                pdf.multi_cell(W - stripe - 5, 4, _s(cite_str))

            bot_y = pdf.get_y()
            # Draw the coloured left stripe over the full card height
            pdf.set_fill_color(*colour)
            pdf.rect(L, top_y, stripe, bot_y - top_y, style="F")
            # Subtle card background
            pdf.set_fill_color(SHADE_L[0], SHADE_L[1], SHADE_L[2])
            # (already drawn inline content — background drawn before text next iteration)
            sp(4)

    # ══════════════════════ SECTION: STRATEGIC RECOMMENDATION ════════════════
    if rec:
        section_heading("Strategic Recommendation", GREEN, "")

        box_top = pdf.get_y()
        pad     = 5

        # First pass — write text to measure height
        pdf.set_x(L + pad + 3)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GREEN)
        pdf.cell(W - pad - 3, 6, _s("Recommended Action"))
        pdf.ln(6)
        pdf.set_x(L + pad + 3)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W - pad - 3, 5.5, _s(rec))
        box_bot = pdf.get_y()
        box_h   = box_bot - box_top + pad

        # Draw green-tinted box + left bar
        pdf.set_fill_color(*SHADE_G)
        pdf.set_draw_color(*GREEN)
        pdf.set_line_width(0.4)
        pdf.rect(L, box_top - 1, W, box_h, style="FD")
        pdf.set_line_width(0.2)
        pdf.set_fill_color(*GREEN)
        pdf.rect(L, box_top - 1, 4, box_h, style="F")

        # Second pass — re-write text on top of the filled box
        pdf.set_xy(L + pad + 3, box_top)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GREEN)
        pdf.cell(W - pad - 3, 6, _s("Recommended Action"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(L + pad + 3)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(W - pad - 3, 5.5, _s(rec))
        sp(8)

    # ════════════════════════════ REFERENCES PAGE ════════════════════════════
    if _ref_list:
        pdf.add_page()
        section_heading("References", NAVY, "")

        pdf.set_font("Helvetica", "", 8)
        for n, title_r, url_r in _ref_list:
            # Row background alternating
            fill_col = SHADE_L if n % 2 == 1 else WHITE
            row_top  = pdf.get_y()

            # Number
            pdf.set_fill_color(*fill_col)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*NAVY)
            pdf.set_x(L)
            pdf.cell(8, 5, _s(f"[{n}]"))

            # Title (bold)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*DARK)
            title_disp = _s(title_r[:90]) if title_r != url_r else ""
            if title_disp:
                pdf.multi_cell(W - 8, 5, title_disp)
            else:
                pdf.ln(5)

            # URL (lighter, smaller)
            pdf.set_x(L + 8)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*LIGHT)
            pdf.multi_cell(W - 8, 4, _s(url_r[:110]))

            # Row separator
            pdf.set_draw_color(*RULE)
            pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
            pdf.ln(1)

        # Failed sources note
        if failed:
            sp(5)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*ROSE)
            pdf.cell(W, 5, _s(f"Skipped / Failed Sources ({len(failed)})"),
                     new_x="LMARGIN", new_y="NEXT")
            sp(2)
            for fs in failed:
                reason = (fs.get("failure_reason") or fs.get("title") or "unknown")[:90]
                pdf.set_x(L + 3)
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*ROSE)
                pdf.cell(4, 5, _s("-"))
                pdf.multi_cell(W - 4, 5, _s(reason))

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
                        file_name=f"briefing_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with col_pdf:
                    try:
                        pdf_bytes = generate_pdf(briefing)
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_bytes,
                            file_name=f"briefing_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf",
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


# ── History: full-screen read-only report viewer ──────────────────────────────

def render_history_page(report_id: str) -> None:
    """
    Renders a stored report in read-only mode, filling the full content area.
    A Back button at the top clears history_view_id and returns to the main view.
    """
    # ── Back button row ───────────────────────────────────────────────────────
    col_back, col_title = st.columns([1, 7])
    with col_back:
        if st.button("← Back", use_container_width=True, key="hist_back_btn"):
            st.session_state["history_view_id"] = None
            st.rerun()

    # ── Load the briefing ─────────────────────────────────────────────────────
    briefing = _report_store.get(report_id)
    if briefing is None:
        st.error(f"Report `{report_id}` not found in the archive.")
        return

    meta = briefing.get("run_metadata") or {}
    topic = meta.get("topic") or "Untitled Report"
    created_raw = ""
    # Try to get the timestamp from the DB summary instead
    summary_rows = _report_store.search(report_id, limit=1)
    if summary_rows:
        created_raw = summary_rows[0].get("created_at", "")
    if not created_raw:
        created_raw = meta.get("completed_at") or meta.get("started_at") or ""

    try:
        dt = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
        ts = dt.strftime("%A, %B %d %Y · %H:%M UTC")
    except Exception:
        ts = str(created_raw)[:19] if created_raw else "–"

    with col_title:
        st.markdown(
            f'<div style="padding:0.25rem 0">'
            f'<span style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;'
            f'color:var(--violet-2);text-transform:uppercase">Archived Report</span><br>'
            f'<span style="font-size:1.05rem;font-weight:700;color:var(--text-hi)">'
            f'{topic}</span> '
            f'<span style="font-size:0.78rem;color:var(--text-low)">{ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Read-only badge ───────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:inline-flex;align-items:center;gap:6px;'
        'background:rgba(251,191,36,0.10);border:1px solid rgba(251,191,36,0.3);'
        'border-radius:999px;padding:3px 12px;font-size:0.74rem;font-weight:700;'
        'color:#fbbf24;margin-bottom:1rem">🔒 Read-only archive view</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Reuse the existing full briefing renderer ─────────────────────────────
    render_briefing(briefing)


# ── History: main tab (table + search + delete) ───────────────────────────────

def render_history_tab() -> None:
    """
    Renders the full History & Archive tab inside the main content area.

    Layout
    ------
    • Search box (filters by title / topic / competitors)
    • Summary metrics: total reports, date range
    • Sortable results table (newest first)
    • Per-row: Open button + Delete button with inline confirmation
    """
    st.markdown(
        '<div style="font-size:0.7rem;font-weight:800;letter-spacing:0.12em;'
        'color:var(--violet-2);text-transform:uppercase;margin-bottom:0.8rem">'
        '📚 Report History &amp; Archive</div>',
        unsafe_allow_html=True,
    )

    # ── Search bar ────────────────────────────────────────────────────────────
    search_query = st.text_input(
        "Search reports",
        value=st.session_state.get("history_search", ""),
        placeholder="Filter by topic, title, or competitor name…",
        key="history_search_input",
        label_visibility="collapsed",
    )
    st.session_state["history_search"] = search_query

    # ── Load rows ─────────────────────────────────────────────────────────────
    if search_query.strip():
        rows = _report_store.search(search_query.strip())
    else:
        rows = _report_store.list_reports()

    total_db = _report_store.count()

    # ── Summary metrics strip ─────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.035);border:1px solid '
            f'rgba(255,255,255,0.08);border-top:3px solid #8b5cf6;border-radius:12px;'
            f'padding:0.75rem 1rem;">'
            f'<div style="font-size:1.6rem;font-weight:800;color:#f3f1fa">{total_db}</div>'
            f'<div style="font-size:0.66rem;font-weight:700;color:#7c7796;'
            f'text-transform:uppercase;letter-spacing:0.09em">Total Reports</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with m2:
        match_count = len(rows)
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.035);border:1px solid '
            f'rgba(255,255,255,0.08);border-top:3px solid #22d3ee;border-radius:12px;'
            f'padding:0.75rem 1rem;">'
            f'<div style="font-size:1.6rem;font-weight:800;color:#f3f1fa">{match_count}</div>'
            f'<div style="font-size:0.66rem;font-weight:700;color:#7c7796;'
            f'text-transform:uppercase;letter-spacing:0.09em">Showing</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with m3:
        if rows:
            try:
                newest = datetime.fromisoformat(
                    rows[0]["created_at"].replace("Z", "+00:00")
                ).strftime("%b %d, %Y")
            except Exception:
                newest = "–"
        else:
            newest = "–"
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.035);border:1px solid '
            f'rgba(255,255,255,0.08);border-top:3px solid #34d399;border-radius:12px;'
            f'padding:0.75rem 1rem;">'
            f'<div style="font-size:1.0rem;font-weight:800;color:#f3f1fa;line-height:1.3">'
            f'{newest}</div>'
            f'<div style="font-size:0.66rem;font-weight:700;color:#7c7796;'
            f'text-transform:uppercase;letter-spacing:0.09em">Latest Report</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # ── Empty state ───────────────────────────────────────────────────────────
    if not rows:
        st.markdown(
            '<div class="welcome-box" style="padding:2.5rem 1.5rem">'
            '<div class="w-icon" style="width:52px;height:52px;font-size:1.4rem">📭</div>'
            + (
                '<h3>No reports match your search</h3>'
                f'<p>Try a different keyword — {total_db} report(s) are stored.</p>'
                if search_query else
                '<h3>No reports saved yet</h3>'
                '<p>Run a brief to start building your archive.</p>'
            )
            + '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Table header ──────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:grid;grid-template-columns:1fr 2fr 1.4fr 1fr 90px 90px;'
        'gap:0.5rem;padding:0.45rem 0.9rem;'
        'font-size:0.64rem;font-weight:800;letter-spacing:0.1em;'
        'color:var(--text-low);text-transform:uppercase;'
        'border-bottom:1px solid var(--border-soft);margin-bottom:0.3rem">'
        '<span>Report ID</span>'
        '<span>Title / Topic</span>'
        '<span>Competitors</span>'
        '<span>Date &amp; Time</span>'
        '<span style="text-align:center">Open</span>'
        '<span style="text-align:center">Delete</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Pending delete confirmation state ─────────────────────────────────────
    delete_pending_id = st.session_state.get("history_delete_id")

    for row in rows:
        rid         = row["id"]
        title       = row["title"] or "Untitled Report"
        topic       = row["topic"] or "–"
        competitors = row.get("competitors") or "–"
        created_raw = row.get("created_at", "")
        duration    = row.get("duration_sec")

        try:
            dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            ts = dt.strftime("%b %d %Y, %H:%M")
        except Exception:
            ts = created_raw[:16] if created_raw else "–"

        dur_label = f"{int(duration)}s" if duration else "–"
        is_viewing = (st.session_state.get("history_view_id") == rid)
        is_deleting = (delete_pending_id == rid)

        # Highlight row that is currently open in the viewer
        row_style = (
            "background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.3);"
            if is_viewing else
            "background:var(--glass);border:1px solid var(--border-soft);"
        )
        if is_deleting:
            row_style = "background:rgba(244,63,94,0.07);border:1px solid rgba(244,63,94,0.35);"

        st.markdown(
            f'<div style="display:grid;grid-template-columns:1fr 2fr 1.4fr 1fr 90px 90px;'
            f'gap:0.5rem;padding:0.55rem 0.9rem;border-radius:10px;{row_style}'
            f'margin-bottom:0.35rem;align-items:center">'
            # Run ID
            f'<code style="font-size:0.72rem;color:var(--text-low)">{rid}</code>'
            # Title + topic
            f'<div><div style="font-size:0.84rem;font-weight:700;color:var(--text-hi);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:320px"'
            f' title="{title}">{title[:55]}{"…" if len(title)>55 else ""}</div>'
            f'<div style="font-size:0.70rem;color:var(--text-low)">{topic[:60]}</div></div>'
            # Competitors
            f'<div style="font-size:0.76rem;color:var(--text-mid);white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis" title="{competitors}">'
            f'{competitors[:42]}{"…" if len(competitors)>42 else ""}</div>'
            # Date + duration
            f'<div><div style="font-size:0.78rem;color:var(--text-mid)">{ts}</div>'
            f'<div style="font-size:0.68rem;color:var(--text-low)">{dur_label}</div></div>'
            # Button placeholders (rendered below as real Streamlit buttons)
            f'<div></div><div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Render actual Streamlit buttons in a tight column pair below the row
        # (Streamlit cannot place buttons inside raw HTML; we overlap them with CSS offsets)
        btn_col_open, btn_col_del = st.columns([1, 1])

        with btn_col_open:
            open_label = "✓ Open" if is_viewing else "Open →"
            if st.button(open_label, key=f"tab_open_{rid}", use_container_width=True):
                st.session_state["history_view_id"] = rid
                st.session_state["history_delete_id"] = None
                st.rerun()

        with btn_col_del:
            if is_deleting:
                # ── Confirmation row ──────────────────────────────────────────
                st.markdown(
                    '<div style="background:rgba(244,63,94,0.12);border:1px solid '
                    'rgba(244,63,94,0.4);border-radius:9px;padding:0.45rem 0.7rem;'
                    'font-size:0.76rem;color:#fda4af;margin-bottom:0.3rem">'
                    '⚠ Delete this report permanently?</div>',
                    unsafe_allow_html=True,
                )
                conf_col, cancel_col = st.columns(2)
                with conf_col:
                    if st.button("✓ Confirm", key=f"del_confirm_{rid}", use_container_width=True):
                        _report_store.delete(rid)
                        st.session_state["history_delete_id"] = None
                        st.session_state["history_stale"] = True
                        # If user was viewing this report, close the viewer
                        if st.session_state.get("history_view_id") == rid:
                            st.session_state["history_view_id"] = None
                        st.rerun()
                with cancel_col:
                    if st.button("✗ Cancel", key=f"del_cancel_{rid}", use_container_width=True):
                        st.session_state["history_delete_id"] = None
                        st.rerun()
            else:
                if st.button("🗑 Delete", key=f"tab_del_{rid}", use_container_width=True):
                    st.session_state["history_delete_id"] = rid
                    st.rerun()

        st.markdown("<div style='height:0.1rem'></div>", unsafe_allow_html=True)


# ── Main entrypoint ───────────────────────────────────────────────────────────

def main():
    init_session()

    briefing: Optional[Dict] = st.session_state.get("briefing")
    running: bool = st.session_state.get("running", False)
    meta = briefing.get("run_metadata", {}) if briefing else None

    render_page_header(briefing)
    render_sidebar(meta, running)

    # ── Input row — always rendered at the same position ─────────────────────
    # During execution the input is read-only (disabled) but its VALUE is
    # explicitly set from session state so the topic stays visible.
    # The "Clear Chat" button is ALWAYS shown (enabled once there is a topic
    # or a completed briefing; disabled only when there is nothing to clear).
    with st.container():
        col_input, col_run, col_clear = st.columns([4, 1, 1])

        with col_input:
            # When running: widget is disabled, show the saved topic via value=.
            # When idle: let Streamlit own the widget via its key so typing is
            # never overridden on rerun. Read the current value from session_state.
            if running:
                topic = st.text_input(
                    "Market / topic to brief",
                    placeholder="e.g. CRM software market, AI coding assistants, fintech payments…",
                    value=st.session_state.get("last_topic", ""),
                    disabled=True,
                    key="topic_widget",
                    label_visibility="collapsed",
                )
            else:
                topic = st.text_input(
                    "Market / topic to brief",
                    placeholder="e.g. CRM software market, AI coding assistants, fintech payments…",
                    key="topic_widget",
                    label_visibility="collapsed",
                )
                # Mirror into topic_input so the rest of the code can read it
                st.session_state["topic_input"] = topic

        with col_run:
            run_clicked = st.button(
                "▶ Run Brief",
                disabled=running,
                use_container_width=True,
            )

        with col_clear:
            # Clear Chat is always visible. Disabled only when there is
            # genuinely nothing to clear (no topic typed, no briefing).
            has_content = bool(
                st.session_state.get("last_topic")
                or st.session_state.get("topic_input")
                or briefing
            )
            clear_clicked = st.button(
                "🗑 Clear Chat",
                disabled=(not has_content) or running,
                use_container_width=True,
                help="Clear the current briefing and topic. Available after a run completes.",
            )

    max_sources, max_steps = render_settings_expander()

    # ── Single stable content slot — never changes position ──────────────────
    # All three states (welcome / running / briefing) render into this one
    # placeholder so nothing above or below it ever shifts.
    content_slot = st.empty()

    # ── Handle Clear Chat ─────────────────────────────────────────────────────
    if clear_clicked and not running:
        st.session_state["briefing"]    = None
        st.session_state["last_topic"]  = ""
        st.session_state["topic_input"] = ""
        st.session_state["running"]     = False
        st.rerun()

    # ── Handle Run button click ───────────────────────────────────────────────
    if run_clicked and not running:
        topic_value = topic.strip()
        if not topic_value:
            st.warning("Please enter a topic before running.")
        else:
            # Save the topic BEFORE setting running=True so it survives the
            # rerun and the disabled text_input still shows it.
            st.session_state["last_topic"]  = topic_value
            st.session_state["topic_input"] = topic_value
            st.session_state["running"]     = True
            # Do NOT clear briefing here — keep the previous result visible
            # in session state until the new one arrives. The content_slot
            # will show the progress UI instead regardless.
            st.rerun()

    # ── Execute pipeline (running state) ─────────────────────────────────────
    if running:
        topic_value = st.session_state.get("last_topic", "")

        # Render a stable wrapper inside content_slot that contains:
        #   1. A topic banner (always visible so the user knows what's running)
        #   2. A live-updating progress card
        # We use a single st.empty so run_with_progress can overwrite it on
        # each pipeline step without shifting the surrounding layout.
        with content_slot.container():
            st.markdown(
                f'<div style="background:rgba(139,92,246,0.10);border:1px solid '
                f'rgba(139,92,246,0.3);border-radius:12px;padding:0.55rem 1rem;'
                f'font-size:0.86rem;color:#a78bfa;margin-bottom:0.8rem;">'
                f'🔄 <strong>Running brief for:</strong> {topic_value}</div>',
                unsafe_allow_html=True,
            )
            progress_placeholder = st.empty()

        briefing_dict = run_with_progress(topic_value, max_sources, max_steps, progress_placeholder)

        if briefing_dict:
            st.session_state["briefing"] = briefing_dict
            # ── Auto-save to history archive ──────────────────────────────────
            try:
                _report_store.save(briefing_dict)
                st.session_state["history_stale"] = True
            except Exception:
                pass  # never block the UI on a storage failure
        st.session_state["running"] = False
        st.rerun()

    # ── Render completed briefing ─────────────────────────────────────────────
    elif briefing:
        with content_slot.container():
            # ── History viewer takes over the full content area ───────────────
            history_view_id = st.session_state.get("history_view_id")
            if history_view_id:
                render_history_page(history_view_id)
            else:
                # Normal current-briefing view with an extra History tab
                tabs = st.tabs(["📊 Current Brief", "📚 History"])
                with tabs[0]:
                    st.divider()
                    render_briefing(briefing)
                with tabs[1]:
                    render_history_tab()

    # ── Welcome state ─────────────────────────────────────────────────────────
    else:
        # Check if the user navigated to a history entry from the sidebar
        history_view_id = st.session_state.get("history_view_id")
        with content_slot.container():
            if history_view_id:
                render_history_page(history_view_id)
            else:
                tabs = st.tabs(["📊 New Brief", "📚 History"])
                with tabs[0]:
                    render_preview_strip()
                    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
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
                with tabs[1]:
                    render_history_tab()


if __name__ == "__main__":
    main()