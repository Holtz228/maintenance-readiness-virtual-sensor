from __future__ import annotations

import html

import streamlit as st


PLOTLY_TEMPLATE = "plotly_dark"


CUSTOM_CSS = """
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main {
        background: #070b14;
    }

    .block-container {
        max-width: none;
        width: 100%;
        padding-top: 1.25rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        padding-bottom: 2rem;
        background: #070b14;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stToolbar"] {
        opacity: 0.45;
        color: #94a3b8;
    }

    [data-testid="stToolbar"]:hover {
        opacity: 1;
    }

    section[data-testid="stSidebar"] {
        background: #07111f;
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }

    * {
        font-family: "Inter", "Segoe UI", sans-serif;
    }

    h1, h2, h3 {
        color: #f8fafc !important;
        opacity: 1 !important;
        letter-spacing: -0.035em;
        text-shadow: none !important;
    }

    h1 {
        font-size: 2.45rem;
        margin-bottom: 0.2rem;
        font-weight: 850;
    }

    h2 {
        font-size: 1.45rem;
        margin-top: 0.6rem;
        font-weight: 800;
    }

    h3 {
        font-size: 1.05rem;
        font-weight: 800;
    }

    p, li, span, div {
        color: inherit;
    }

    .main-header {
        color: #f8fafc !important;
        font-size: 2.25rem;
        font-weight: 850;
        letter-spacing: -0.035em;
        margin-bottom: 0.25rem;
    }

    .subtitle,
    .subtle {
        color: #d1d9e6 !important;
        font-size: 0.95rem;
        margin-bottom: 1rem;
        line-height: 1.45;
    }

    .subsection-divider {
        border-top: 1px solid rgba(148,163,184,0.14);
        margin: 1rem 0 1rem 0;
    }

    /* =========================================================
       Sidebar
       ========================================================= */

    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.35rem;
        padding: 0.4rem 0.2rem 0.85rem 0.2rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.14);
    }

    .sidebar-logo-mark {
        width: 2.3rem;
        height: 2.3rem;
        background: linear-gradient(135deg, #2563eb, #14b8a6);
        border-radius: 0.7rem;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 850;
        font-size: 0.78rem;
        letter-spacing: -0.03em;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.35);
        flex-shrink: 0;
    }

    .sidebar-title {
        color: #f8fafc;
        font-weight: 850;
        font-size: 0.9rem;
        line-height: 1.1;
    }

    .sidebar-subtitle {
        color: #d1d9e6 !important;
        font-size: 0.69rem;
        margin-top: 0.16rem;
        line-height: 1.25;
    }

    .sidebar-section-label {
        color: #94a3b8;
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-weight: 800;
        margin: 0.75rem 0 0.5rem 0.2rem;
    }

    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
        width: 100%;
        justify-content: flex-start;
        border-radius: 0.85rem;
        padding: 0.72rem 0.85rem;
        margin-bottom: 0.35rem;
        font-size: 0.88rem;
        font-weight: 750;
        border: 1px solid rgba(148, 163, 184, 0.16);
        background: #0f172a;
        color: #dbeafe;
        box-shadow: none;
        transition: all 0.15s ease-in-out;
    }

    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
        background: rgba(37, 99, 235, 0.18);
        border-color: rgba(96, 165, 250, 0.38);
        color: #f8fafc;
        transform: translateX(2px);
    }

    section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #ffffff !important;
        border-color: rgba(96, 165, 250, 0.72) !important;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.32) !important;
    }

    .active-page-card {
        background: rgba(37, 99, 235, 0.24);
        border: 1px solid rgba(56, 189, 248, 0.55);
        border-radius: 0.9rem;
        padding: 0.85rem;
        margin: 0.9rem 0 1rem 0;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.22);
    }

    .active-page-label {
        color: #93c5fd;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 850;
        margin-bottom: 0.25rem;
    }

    .active-page-title {
        color: #ffffff;
        font-size: 0.86rem;
        font-weight: 850;
    }

    .sidebar-status-card {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        background: rgba(20, 184, 166, 0.13);
        border: 1px solid rgba(20, 184, 166, 0.38);
        border-radius: 0.9rem;
        padding: 0.85rem;
        margin-top: 0.55rem;
    }

    .status-dot {
        width: 0.65rem;
        height: 0.65rem;
        background: #22c55e;
        border-radius: 999px;
        box-shadow: 0 0 12px rgba(34, 197, 94, 0.75);
        flex-shrink: 0;
    }

    .status-title-small {
        color: #dcfce7;
        font-size: 0.78rem;
        font-weight: 850;
    }

    .status-text-small {
        color: #d1d9e6 !important;
        font-size: 0.69rem;
        margin-top: 0.1rem;
        line-height: 1.35;
    }

    /* =========================================================
       Header / Cards
       ========================================================= */

    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1.05rem;
    }

    .hero-card {
        background: linear-gradient(135deg, #10233f, #123b45);
        padding: 1.25rem 1.45rem;
        border-radius: 1rem;
        border: 1px solid rgba(56, 189, 248, 0.35);
        box-shadow: 0 12px 34px rgba(0,0,0,0.30);
        margin-bottom: 1rem;
    }

    .hero-card h2 {
        margin: 0;
        color: #ffffff;
        font-size: 1.16rem;
        font-weight: 850;
        letter-spacing: -0.02em;
    }

    .hero-card p {
        color: #dbeafe;
        margin-top: 0.55rem;
        margin-bottom: 0;
        line-height: 1.56;
        font-size: 0.93rem;
        max-width: 1250px;
    }

    .decision-box {
        background: rgba(13, 148, 136, 0.18);
        border: 1px solid rgba(45, 212, 191, 0.48);
        border-radius: 0.95rem;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
        color: #ecfeff;
        font-size: 0.91rem;
        line-height: 1.5;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }

    .decision-box strong {
        color: #ffffff;
        font-weight: 850;
    }

    .decision-summary-card {
        background: rgba(13, 148, 136, 0.16);
        border: 1px solid rgba(45, 212, 191, 0.42);
        border-radius: 0.95rem;
        padding: 1rem 1.15rem;
        margin: 1rem 0;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }

    .decision-summary-title {
        color: #ffffff;
        font-weight: 850;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }

    .decision-summary-text {
        color: #d1fae5;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .decision-summary-text strong {
        color: #ffffff;
        font-weight: 900;
    }

    .warning-box,
    .safety-box {
        background: rgba(245, 158, 11, 0.16);
        border: 1px solid rgba(245, 158, 11, 0.48);
        border-left: 5px solid #f59e0b;
        border-radius: 0.95rem;
        padding: 1rem 1.1rem;
        margin: 0.8rem 0 1.2rem 0;
        color: #fff7ed;
        font-size: 0.91rem;
        line-height: 1.5;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }

    .warning-box strong,
    .safety-box b {
        color: #ffffff;
        font-weight: 850;
    }

    .executive-summary-card {
        background: #0f172a;
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 1rem;
        padding: 1.1rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 28px rgba(0,0,0,0.25);
    }

    .executive-summary-title {
        color: #ffffff;
        font-size: 1.05rem;
        font-weight: 850;
        margin-bottom: 0.85rem;
    }

    .executive-summary-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.9rem;
        margin-bottom: 0.9rem;
    }

    .summary-number {
        color: #38bdf8;
        font-size: 1.55rem;
        font-weight: 900;
        letter-spacing: -0.04em;
    }

    .summary-label {
        color: #d1d9e6;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .executive-summary-text {
        color: #e2e8f0;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* =========================================================
       KPI / Layer Cards
       ========================================================= */

    .kpi-card {
        background: #0f172a;
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 0.95rem;
        padding: 1rem 1.05rem;
        min-height: 122px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.24);
    }

    .kpi-icon {
        color: #60a5fa;
        font-size: 1.1rem;
        margin-bottom: 0.35rem;
        line-height: 1;
    }

    .kpi-label {
        color: #dbeafe;
        font-size: 0.82rem !important;
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .kpi-value {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 900;
        letter-spacing: -0.035em;
        margin-bottom: 0.25rem;
        line-height: 1.1;
    }

    .kpi-delta-positive {
        color: #5eead4;
        font-size: 0.76rem !important;
        font-weight: 700;
        line-height: 1.35;
    }

    .kpi-delta-negative {
        color: #fbbf24;
        font-size: 0.76rem !important;
        font-weight: 700;
        line-height: 1.35;
    }

    .module-shell {
        background: #0f172a;
        border: 1px solid rgba(148,163,184,0.20);
        border-radius: 1rem;
        padding: 1rem 1rem 0.85rem 1rem;
        box-shadow: 0 10px 28px rgba(0,0,0,0.25);
        margin-bottom: 1rem;
    }

    .module-eyebrow {
        color: #60a5fa !important;
        opacity: 1 !important;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-weight: 850;
        margin-bottom: 0.3rem;
    }

    .module-main-title {
        color: #ffffff;
        font-size: 1.05rem;
        font-weight: 850;
        margin-bottom: 0.25rem;
        line-height: 1.25;
    }

    .module-main-subtitle {
        color: #d1d9e6 !important;
        font-size: 0.82rem;
        line-height: 1.48;
    }

    .layer-card {
        background: #0f172a;
        border: 1px solid rgba(148,163,184,0.24);
        border-radius: 0.85rem;
        padding: 0.85rem 0.95rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 8px 22px rgba(0,0,0,0.22);
    }

    .layer-number {
        display: inline-block;
        background: #2563eb;
        color: white;
        border-radius: 999px;
        padding: 0.1rem 0.46rem;
        font-size: 0.72rem;
        font-weight: 850;
        margin-right: 0.45rem;
    }

    .layer-title {
        color: #ffffff;
        font-weight: 850;
        font-size: 0.9rem !important;
    }

    .layer-text {
        color: #d1d9e6 !important;
        margin-top: 0.3rem;
        font-size: 0.8rem !important;
        line-height: 1.48 !important;
    }

    /* =========================================================
       Dataframes / Tables
       ========================================================= */

    .stDataFrame {
        border-radius: 0.95rem !important;
        overflow: hidden !important;
        border: 1px solid rgba(148,163,184,0.22);
        background: #0b1220;
        box-shadow: 0 10px 28px rgba(0,0,0,0.24);
    }

    div[data-testid="stDataFrame"] {
        border-radius: 0.95rem !important;
        overflow: hidden !important;
    }

    div[data-testid="stDataFrame"] [role="grid"] {
        border-radius: 0.95rem !important;
    }

    .table-context-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.20);
        border-radius: 0.85rem;
        padding: 0.85rem 1rem;
        margin: 0.75rem 0;
        color: #cbd5e1;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* =========================================================
       Native Streamlit Elements
       ========================================================= */

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 23, 42, 0.88);
        border: 1px solid rgba(59, 130, 246, 0.20);
        border-radius: 0.75rem 0.75rem 0 0;
        color: #cbd5e1;
        padding: 0.6rem 1rem;
        font-weight: 750;
    }

    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: rgba(29, 78, 216, 0.30) !important;
        border-color: rgba(56, 189, 248, 0.48) !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 0.9rem;
        border-color: rgba(56, 189, 248, 0.35);
        background: rgba(14, 116, 144, 0.12);
        color: #e0f2fe;
    }

    div[data-testid="stMetric"] {
        background: #0f172a;
        border: 1px solid rgba(148,163,184,0.22);
        padding: 0.95rem;
        border-radius: 0.95rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.22);
    }

    div[data-testid="stMetricLabel"] {
        color: #cbd5e1;
    }

    div[data-testid="stMetricValue"] {
        color: #ffffff;
    }

    button[kind="secondary"] {
        background: #0f172a;
        color: #dbeafe;
        border: 1px solid rgba(148, 163, 184, 0.26);
        border-radius: 0.75rem;
    }

    button[kind="secondary"]:hover {
        background: rgba(37, 99, 235, 0.18);
        border-color: rgba(96, 165, 250, 0.38);
        color: #ffffff;
    }

    div[data-baseweb="select"] > div {
        background: #111827;
        border-color: rgba(148, 163, 184, 0.22);
        border-radius: 0.75rem;
    }

    .footer-status {
        color: #94a3b8;
        font-size: 0.78rem;
        margin-top: 1.5rem;
        border-top: 1px solid rgba(148,163,184,0.16);
        padding-top: 0.8rem;
        line-height: 1.4;
    }

    .sidebar-nav-link {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    width: 100%;
    border-radius: 0.85rem;
    padding: 0.72rem 0.85rem;
    margin-bottom: 0.35rem;
    font-size: 0.88rem;
    font-weight: 750;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: #0f172a;
    color: #dbeafe !important;
    box-shadow: none;
    transition: all 0.15s ease-in-out;
    text-decoration: none !important;
    }

    .sidebar-nav-link:hover {
        background: rgba(37, 99, 235, 0.18);
        border-color: rgba(96, 165, 250, 0.38);
        color: #ffffff !important;
        transform: translateX(2px);
        text-decoration: none !important;
    }

    .sidebar-nav-link.active {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important;
        border-color: rgba(96, 165, 250, 0.72);
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.32);
    }

    .sidebar-nav-icon {
        width: 1.2rem;
        text-align: center;
        display: inline-block;
    }
</style>
"""


def apply_global_style() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def apply_dashboard_style() -> None:
    """Compatibility wrapper for this project."""
    apply_global_style()


def render_sidebar_brand(
    title: str = "Maintenance Readiness",
    subtitle: str = "Virtual Sensor Decision Support",
    logo_text: str = "MR",
) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-logo">
            <div class="sidebar-logo-mark">{html.escape(logo_text)}</div>
            <div>
                <div class="sidebar-title">{html.escape(title)}</div>
                <div class="sidebar-subtitle">{html.escape(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_section_label(label: str) -> None:
    st.sidebar.markdown(
        f'<div class="sidebar-section-label">{html.escape(label)}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_status(
    title: str = "Portfolio MVP",
    text: str = "NASA C-MAPSS sensor data + virtual sensor fallback analytics",
) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-status-card">
            <div class="status-dot"></div>
            <div>
                <div class="status-title-small">{html.escape(title)}</div>
                <div class="status-text-small">{html.escape(text)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(
    title: str,
    subtitle: str,
    eyebrow: str | None = None,
) -> None:
    eyebrow_html = ""
    if eyebrow:
        eyebrow_html = f'<div class="module-eyebrow">{html.escape(eyebrow)}</div>'

    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                {eyebrow_html}
                <h1>{html.escape(title)}</h1>
                <div class="subtitle">{html.escape(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero_card(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <h2>{html.escape(title)}</h2>
            <p>{html.escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_executive_summary_card(
    assets_monitored: int,
    critical_assets: int,
    model_r2: float,
    maintenance_escalations: int,
    text: str,
) -> None:
    st.markdown(
        f"""
        <div class="executive-summary-card">
            <div class="executive-summary-title">What this dashboard does</div>
            <div class="executive-summary-grid">
                <div>
                    <div class="summary-number">{assets_monitored:,}</div>
                    <div class="summary-label">Assets monitored</div>
                </div>
                <div>
                    <div class="summary-number">{critical_assets:,}</div>
                    <div class="summary-label">Critical assets</div>
                </div>
                <div>
                    <div class="summary-number">{model_r2:.3f}</div>
                    <div class="summary-label">Virtual sensor R²</div>
                </div>
                <div>
                    <div class="summary-number">{maintenance_escalations:,}</div>
                    <div class="summary-label">Maintenance escalations</div>
                </div>
            </div>
            <div class="executive-summary-text">{html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decision_summary_card(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="decision-summary-card">
            <div class="decision-summary-title">{html.escape(title)}</div>
            <div class="decision-summary-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_table_context(text: str) -> None:
    st.markdown(
        f'<div class="table-context-card">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def render_module_header(
    eyebrow: str,
    title: str,
    subtitle: str,
) -> None:
    st.markdown(
        f"""
        <div class="module-header">
            <div class="module-eyebrow">{html.escape(eyebrow)}</div>
            <div class="module-main-title">{html.escape(title)}</div>
            <div class="module-main-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: str | int | float,
    delta: str | None = None,
    icon: str = "●",
    positive: bool = True,
) -> None:
    delta_html = ""
    if delta:
        delta_class = "kpi-delta-positive" if positive else "kpi-delta-negative"
        delta_html = f'<div class="{delta_class}">{html.escape(delta)}</div>'

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-icon">{html.escape(icon)}</div>
            <div class="kpi-label">{html.escape(label)}</div>
            <div class="kpi-value">{html.escape(str(value))}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decision_box(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="decision-box">
            <strong>{html.escape(title)}</strong><br>
            {html.escape(text)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_warning_box(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="warning-box">
            <strong>{html.escape(title)}</strong><br>
            {html.escape(text)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_layer_card(number: int, title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="layer-card">
            <span class="layer-number">{number}</span>
            <span class="layer-title">{html.escape(title)}</span>
            <div class="layer-text">{html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer_status(text: str) -> None:
    st.markdown(
        f'<div class="footer-status">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )