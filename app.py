import json
from dataclasses import asdict
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis_engine import (
    DriverAggregateStats,
    calculate_personalized_risk_score,
    get_risk_coaching,
    summarize_driver,
)


NAVY = "#1A2B3C"
GREEN = "#00A3AD"
YELLOW = "#F2C94C"
RED = "#E04F5F"
SIDEBAR_BG = "#1E3246"
SURFACE = "#FFFFFF"

SAMPLE_DATA_PATH = Path("driving_log.csv")

REQUIRED_COLUMNS = [
    "trip_id",
    "duration_minutes",
    "distance_miles",
    "hard_braking_events",
    "speeding_events",
    "night_driving_minutes",
    "distraction_score",
]

LOGO_SVG = f"""
<svg width="44" height="44" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="ClearClaim logo">
  <path d="M32 6C42 13 50 14 56 14V33C56 47 45 56 32 60C19 56 8 47 8 33V14C14 14 22 13 32 6Z"
        fill="rgba(255,255,255,0.0)" stroke="{NAVY}" stroke-width="3.2" stroke-linejoin="round"/>
  <path d="M32 14L36.2 25.8L48 30L36.2 34.2L32 46L27.8 34.2L16 30L27.8 25.8L32 14Z"
        fill="rgba(0,163,173,0.18)" stroke="{GREEN}" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M23.5 33.2L29.1 38.7L41.5 26.6" stroke="{NAVY}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

ICON_FILE = """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M7 3h7l3 3v15H7V3Z" stroke="rgba(255,255,255,0.92)" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M14 3v4h4" stroke="rgba(255,255,255,0.92)" stroke-width="1.8" stroke-linejoin="round"/>
</svg>
"""

ICON_GEAR = """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M12 15.2a3.2 3.2 0 1 0 0-6.4a3.2 3.2 0 0 0 0 6.4Z" stroke="rgba(255,255,255,0.92)" stroke-width="1.8"/>
  <path d="M19 12a7.2 7.2 0 0 0-.1-1.2l2-1.5l-2-3.5l-2.4 1a7.4 7.4 0 0 0-2-.9L14.2 3h-4.4L9.4 6.4a7.4 7.4 0 0 0-2 .9l-2.4-1l-2 3.5l2 1.5A7.2 7.2 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5l2 3.5l2.4-1c.6.4 1.3.7 2 .9L9.8 21h4.4l.4-3.4c.7-.2 1.4-.5 2-.9l2.4 1l2-3.5l-2-1.5c.1-.4.1-.8.1-1.2Z"
        stroke="rgba(255,255,255,0.65)" stroke-width="1.4" stroke-linejoin="round"/>
</svg>
"""

ICON_CHART = """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M4 20V5" stroke="rgba(255,255,255,0.65)" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M4 20h16" stroke="rgba(255,255,255,0.65)" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M7.5 18V11" stroke="rgba(255,255,255,0.92)" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M12 18V8" stroke="rgba(255,255,255,0.92)" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M16.5 18V13" stroke="rgba(255,255,255,0.92)" stroke-width="2.2" stroke-linecap="round"/>
</svg>
"""

ICON_SHIELD = """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M12 3c3.6 2.6 6.5 3 8 3v8.6c0 4.2-3.2 7.1-8 9.4c-4.8-2.3-8-5.2-8-9.4V6c1.5 0 4.4-.4 8-3Z"
        stroke="rgba(255,255,255,0.92)" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M8.6 13l2.1 2.1L15.6 10" stroke="rgba(0,163,173,0.95)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

ICON_WAND = """
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M5 20l9.5-9.5" stroke="rgba(255,255,255,0.92)" stroke-width="2.0" stroke-linecap="round"/>
  <path d="M14.5 10.5l4-4a2.1 2.1 0 0 0 0-3l-.1-.1a2.1 2.1 0 0 0-3 0l-4 4" stroke="rgba(0,163,173,0.95)" stroke-width="2.0" stroke-linecap="round"/>
  <path d="M16.8 2.8l4.4 4.4" stroke="rgba(255,255,255,0.55)" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M3 9h3M6 6V3M19 21v-3M21 19h-3" stroke="rgba(255,255,255,0.55)" stroke-width="1.4" stroke-linecap="round"/>
</svg>
"""


def _coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["duration_minutes"] = pd.to_numeric(df["duration_minutes"], errors="coerce")
    df["distance_miles"] = pd.to_numeric(df["distance_miles"], errors="coerce")
    df["hard_braking_events"] = pd.to_numeric(df["hard_braking_events"], errors="coerce").astype("Int64")
    df["speeding_events"] = pd.to_numeric(df["speeding_events"], errors="coerce").astype("Int64")
    df["night_driving_minutes"] = pd.to_numeric(df["night_driving_minutes"], errors="coerce")
    df["distraction_score"] = pd.to_numeric(df["distraction_score"], errors="coerce")
    return df.dropna(subset=["trip_id"])


def risk_score_from_safety_score(safety_score: float) -> float:
    # The analysis engine computes a "safety score" where higher is better.
    # The dashboard shows a "risk score" where lower is better.
    return max(0.0, min(100.0, round(100.0 - float(safety_score), 1)))


def estimated_premium_savings(risk_score: float) -> float:
    # Hackathon-friendly estimate: compare to a mid-risk baseline.
    baseline = 55.0
    savings_per_point_per_year = 18.0
    return max(0.0, round((baseline - risk_score) * savings_per_point_per_year, 0))

def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))

def projected_risk_score(
    *,
    stats: DriverAggregateStats,
    reduce_hard_braking_pct: float,
    limit_night_driving_pct: float,
    improve_focus_pct: float,
) -> float:
    # Recompute using the same score formula for braking/speeding/distraction,
    # then apply a small adjustment for reduced night driving so that slider matters.
    hb = float(stats.avg_hard_braking_events) * (1.0 - reduce_hard_braking_pct / 100.0)
    sp = float(stats.avg_speeding_events)
    ds = float(stats.avg_distraction_score) * (1.0 - improve_focus_pct / 100.0)

    new_safety = calculate_personalized_risk_score(
        avg_hard_braking_events=hb,
        avg_speeding_events=sp,
        avg_distraction_score=ds,
    )
    base_risk = risk_score_from_safety_score(new_safety)

    # Night driving impact: reduce risk modestly if the driver meaningfully cuts night miles.
    if float(stats.avg_duration_minutes) > 0:
        night_ratio = clamp(float(stats.avg_night_driving_minutes) / float(stats.avg_duration_minutes), 0.0, 1.0)
    else:
        night_ratio = 0.0

    night_impact_points = min(12.0, night_ratio * 20.0)  # 0..12 points
    night_delta = (limit_night_driving_pct / 100.0) * night_impact_points

    return round(clamp(base_risk - night_delta, 0.0, 100.0), 1)


def gauge_figure(risk_score: float) -> go.Figure:
    if risk_score <= 30:
        bar_color = GREEN
    elif risk_score <= 60:
        bar_color = YELLOW
    else:
        bar_color = RED

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_score,
            number={"suffix": "/100", "font": {"color": NAVY, "size": 42}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": NAVY},
                "bar": {"color": bar_color},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "rgba(26,43,60,0.25)",
                "steps": [
                    {"range": [0, 30], "color": "rgba(0, 163, 173, 0.18)"},
                    {"range": [30, 60], "color": "rgba(242, 201, 76, 0.22)"},
                    {"range": [60, 100], "color": "rgba(224, 79, 95, 0.20)"},
                ],
                "threshold": {
                    "line": {"color": NAVY, "width": 3},
                    "thickness": 0.75,
                    "value": risk_score,
                },
            },
            title={"text": "Average Risk Score", "font": {"color": NAVY, "size": 18}},
        )
    )
    fig.update_layout(
        height=330,
        margin=dict(l=20, r=20, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY),
    )
    return fig


def radar_figure(stats: DriverAggregateStats) -> go.Figure:
    # 0-100 "performance" where higher is better, for readability in a radar chart.
    # These are heuristic mappings that stay stable for hackathon demos.
    speed_perf = 100.0 - (min(3.0, stats.avg_speeding_events) / 3.0) * 100.0
    braking_perf = 100.0 - (min(5.0, stats.avg_hard_braking_events) / 5.0) * 100.0
    distraction_perf = 100.0 - (min(1.0, stats.avg_distraction_score) / 1.0) * 100.0
    night_ratio = (
        0.0
        if stats.avg_duration_minutes <= 0
        else min(1.0, stats.avg_night_driving_minutes / stats.avg_duration_minutes)
    )
    night_perf = 100.0 - night_ratio * 100.0
    smoothness_perf = max(0.0, min(100.0, (0.55 * braking_perf) + (0.45 * speed_perf)))

    categories = ["Speed", "Braking", "Distraction", "Night Driving", "Smoothness"]
    values = [speed_perf, braking_perf, distraction_perf, night_perf, smoothness_perf]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Driver",
            line=dict(color=GREEN, width=3),
            fillcolor="rgba(0,163,173,0.18)",
        )
    )
    fig.update_layout(
        title=dict(text="Driver Performance Radar", font=dict(color=NAVY, size=18)),
        height=420,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY),
        polar=dict(
            bgcolor="white",
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color="rgba(26,43,60,0.65)")),
            angularaxis=dict(tickfont=dict(color=NAVY)),
        ),
        showlegend=False,
    )
    return fig


def coaching_box(payload: dict) -> None:
    st.markdown(
        f"""
<div class="coach-box">
  <div class="coach-title">AI Coaching Advice</div>
  <div class="coach-row"><span class="coach-pill">Risk Category</span> {payload.get("risk_category", "—")}</div>
  <div class="coach-row"><span class="coach-pill">Top Risk Factor</span> {payload.get("top_risk_factor", "—")}</div>
  <div class="coach-advice">{payload.get("coaching_advice", "—")}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def sidebar_section(title: str, icon_svg: str) -> None:
    st.markdown(
        f"""
<div class="side-title">{icon_svg}<span>{title}</span></div>
""",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Telematics Risk Dashboard", layout="wide")

    st.markdown(
        f"""
<style>
  :root {{
    --navy: {NAVY};
    --green: {GREEN};
    --yellow: {YELLOW};
    --red: {RED};
    --sidebar: {SIDEBAR_BG};
    --surface: {SURFACE};
    --header-border: #F0F2F6;
    --pill-bg: #F0F2F6;
    --muted: rgba(26,43,60,0.65);
    --card: rgba(255,255,255,0.92);
    --border: rgba(26,43,60,0.14);
  }}

  /* Hide Streamlit chrome so custom header is truly top-aligned */
  header[data-testid="stHeader"] {{
    display: none;
  }}
  [data-testid="stToolbar"] {{
    display: none;
  }}
  [data-testid="stDecoration"] {{
    display: none;
  }}
  #MainMenu {{
    visibility: hidden;
  }}

  html, body, [class*="css"] {{
    font-family: Inter, "Open Sans", Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }}

  .block-container {{
    padding-top: 0rem;
    padding-left: 1.6rem;
    padding-right: 1.6rem;
    background: var(--surface);
  }}

  h1, h2, h3, h4 {{
    color: var(--navy);
    letter-spacing: 0.2px;
  }}

  .stMarkdown p, .stMarkdown li {{
    color: var(--muted);
  }}

  /* Sidebar */
  [data-testid="stSidebar"] > div:first-child {{
    background: var(--sidebar);
  }}
  [data-testid="stSidebar"] * {{
    color: rgba(255,255,255,0.92);
  }}
  [data-testid="stSidebar"] a {{
    color: rgba(255,255,255,0.92);
  }}
  [data-testid="stSidebar"] .stCaption {{
    color: rgba(255,255,255,0.72);
  }}
  [data-testid="stSidebar"] hr {{
    border: none;
    height: 1px;
    background: rgba(255,255,255,0.12);
    margin: 10px 0;
  }}
  [data-testid="stSidebar"] label {{
    font-size: 12px !important;
    color: rgba(255,255,255,0.80) !important;
    font-weight: 700 !important;
  }}
  .side-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 900;
    letter-spacing: 0.2px;
    font-size: 13px;
    color: rgba(255,255,255,0.92);
    margin: 6px 0 8px 0;
  }}
  .side-title span {{
    transform: translateY(-0.5px);
  }}

  /* Slider accent (best-effort across Streamlit versions) */
  [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
    background-color: var(--green) !important;
    box-shadow: 0 0 0 6px rgba(0,163,173,0.18) !important;
  }}
  [data-testid="stSlider"] [data-baseweb="slider"] div[aria-valuemin] ~ div {{
    background: var(--green) !important;
  }}

  /* File uploader button accent */
  [data-testid="stFileUploader"] button {{
    background: rgba(0,163,173,0.16) !important;
    border: 1px solid rgba(0,163,173,0.35) !important;
  }}
  [data-testid="stFileUploader"] button:hover {{
    filter: brightness(1.02);
  }}

  /* Buttons */
  .stButton > button {{
    border-radius: 12px;
    border: 1px solid rgba(0,163,173,0.35);
  }}
  [data-testid="baseButton-primary"] > button {{
    background: var(--green) !important;
    color: white !important;
    border: 1px solid rgba(0,163,173,0.55) !important;
  }}
  [data-testid="baseButton-primary"] > button:hover {{
    filter: brightness(0.96);
  }}
  /* Make download button match primary accent consistently */
  .stDownloadButton > button {{
    background: var(--green) !important;
    color: white !important;
    border: 1px solid rgba(0,163,173,0.55) !important;
    border-radius: 12px !important;
  }}

  /* Metric cards */
  [data-testid="stMetric"] {{
    background: rgba(255,255,255,0.92);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 14px 12px 14px;
  }}
  [data-testid="stMetricLabel"] p {{
    color: rgba(26,43,60,0.72) !important;
    font-weight: 700 !important;
  }}
  [data-testid="stMetricValue"] {{
    color: var(--green) !important;
    font-weight: 900 !important;
  }}

  .coach-box {{
    border: 1px solid var(--border);
    background: var(--card);
    border-left: 6px solid var(--green);
    border-radius: 14px;
    padding: 16px 16px 14px 16px;
  }}
  .coach-title {{
    font-weight: 800;
    color: var(--navy);
    margin-bottom: 10px;
    font-size: 16px;
  }}
  .coach-row {{
    margin: 6px 0;
    color: var(--navy);
    font-weight: 650;
  }}
  .coach-pill {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    background: rgba(0,163,173,0.12);
    border: 1px solid rgba(0,163,173,0.25);
    margin-right: 10px;
    color: var(--navy);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2px;
  }}
  .coach-advice {{
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 12px;
    background: rgba(26,43,60,0.06);
    border: 1px dashed rgba(26,43,60,0.18);
    color: var(--navy);
    font-weight: 600;
    line-height: 1.45;
  }}

  [data-testid="stMetricValue"] {{
    color: var(--green);
  }}

  .hero {{
    max-width: 900px;
    margin: 72px auto 10px auto;
    background: rgba(255,255,255,0.98);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 28px 26px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.10);
  }}
  .hero-title {{
    font-size: 30px;
    font-weight: 900;
    color: var(--navy);
    margin: 0 0 10px 0;
    letter-spacing: 0.2px;
  }}
  .hero-sub {{
    color: rgba(26,43,60,0.72);
    font-weight: 600;
    line-height: 1.55;
    margin: 0 0 16px 0;
  }}
  .status {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.14);
  }}
  .dot {{
    width: 7px;
    height: 7px;
    border-radius: 999px;
    display: inline-block;
    background: rgba(255,255,255,0.35);
    box-shadow: 0 0 0 3px rgba(255,255,255,0.07);
  }}
  .dot.active {{
    background: var(--green);
  }}

  /* Top bar styling: target the horizontal block immediately after the anchor */
  #topbar-anchor + div[data-testid="stHorizontalBlock"] {{
    background: #FFFFFF !important;
    border: 1px solid var(--header-border) !important;
    border-bottom: 1px solid var(--header-border) !important;
    border-radius: 18px;
    padding: 14px 14px;
    box-shadow: 0 10px 28px rgba(26,43,60,0.07);
    margin-top: 14px;
    margin-bottom: 18px;
  }}
  #topbar-anchor + div[data-testid="stHorizontalBlock"] * {{
    color: var(--navy) !important;
  }}
  #topbar-anchor + div[data-testid="stHorizontalBlock"] div {{
    background: transparent !important;
  }}
  .topbar-title {{
    font-size: 26px;
    font-weight: 950;
    color: var(--navy) !important;
    line-height: 1.1;
    margin-top: 2px;
  }}
  .topbar-sub {{
    color: var(--navy) !important;
    opacity: 0.72;
    font-weight: 650;
    margin-top: 6px;
  }}
  .cluster {{
    display: flex;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 6px;
  }}
  .pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 999px;
    padding: 6px 10px;
    background: var(--pill-bg) !important;
    border: 1px solid #E6E9EF !important;
    color: var(--navy) !important;
    font-size: 12px;
    font-weight: 750;
  }}
  .pill b {{
    color: rgba(26,43,60,0.65) !important;
    font-weight: 800;
  }}
</style>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        sidebar_section("Upload", ICON_FILE)
        file = st.file_uploader("Driving log CSV", type=["csv"])
        st.sidebar.divider()

        sidebar_section("AI Settings", ICON_GEAR)
        openai_key = st.text_input("OpenAI API Key (optional)", type="password")
        model = st.text_input("Model", value="gpt-4o")
        st.caption("Uses Structured Outputs for valid JSON.")
        st.sidebar.divider()

        sidebar_section("Display", ICON_CHART)
        max_trips = st.slider("Trips shown in table", min_value=10, max_value=200, value=80, step=10)

        st.sidebar.divider()
        sidebar_section("Impact Simulator", ICON_WAND)
        base_premium = st.number_input("Base Premium (per year)", min_value=0, value=1800, step=50)
        reduce_hb = st.slider("Reduce Hard Braking (%)", min_value=0, max_value=80, value=20, step=5)
        limit_night = st.slider("Limit Night Driving (%)", min_value=0, max_value=80, value=15, step=5)
        improve_focus = st.slider("Improve Focus (%)", min_value=0, max_value=80, value=25, step=5)
        if not file:
            st.caption("Upload data to enable projected premium.")
        st.sidebar.divider()

        sidebar_section("System Status", ICON_SHIELD)
        api_active = bool(openai_key) or bool(os.getenv("OPENAI_API_KEY"))
        try:
            api_active = api_active or bool(st.secrets["OPENAI_API_KEY"])
        except Exception:
            pass
        st.markdown(
            f"""
<div class="status" style="margin-top: 6px; padding-top: 0; border-top: 0;">
  <span class="dot {'active' if api_active else ''}"></span>
  <div style="font-weight:800;">API Connection: {'Active' if api_active else 'Inactive'}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    data_status = "Ready" if file else "Awaiting Data"
    ai_level = "standard"
    credits = "Active" if api_active else "Inactive"

    st.markdown('<div id="topbar-anchor"></div>', unsafe_allow_html=True)
    top_left, top_mid, top_right = st.columns([1, 4, 3], vertical_alignment="center")
    with top_left:
        st.markdown(LOGO_SVG, unsafe_allow_html=True)
    with top_mid:
        st.markdown(
            """
<div class="topbar-title">ClearClaim: Driver Insights Pro</div>
<div class="topbar-sub">Enterprise telematics scoring for underwriting, fleet risk, and driver coaching.</div>
""",
            unsafe_allow_html=True,
        )
    with top_right:
        st.markdown(
            f"""
<div class="cluster">
  <span class="pill"><b>Data Status:</b> {data_status}</span>
  <span class="pill"><b>AI Level:</b> {ai_level}</span>
  <span class="pill"><b>Credits:</b> {credits}</span>
</div>
""",
            unsafe_allow_html=True,
        )

    if not file:
        st.markdown(
            """
<div class="hero">
  <div class="hero-title">Instant Driver Risk Insights</div>
  <div class="hero-sub">
    Upload a telematics driving log to generate an underwriting-ready risk score, performance radar,
    and AI coaching advice tailored to the driver’s behavior. Built to be fast, explainable, and demo-friendly.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        c_left, c_mid, c_right = st.columns([1, 2, 1])
        with c_mid:
            if SAMPLE_DATA_PATH.exists():
                st.download_button(
                    "Sample Data Download",
                    data=SAMPLE_DATA_PATH.read_bytes(),
                    file_name="driving_log.csv",
                    mime="text/csv",
                    type="primary",
                )
                st.caption("Tip: download, then upload it from the sidebar to see the full dashboard.")
            else:
                st.warning("Sample data is not available in this workspace.")
        return

    df = pd.read_csv(file)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    df = _coerce_schema(df)
    tmp_path = Path(".uploaded_driving_log.csv")
    df.to_csv(tmp_path, index=False)
    stats = summarize_driver(tmp_path)

    risk_score = risk_score_from_safety_score(stats.personalized_risk_score)
    savings = estimated_premium_savings(risk_score)

    # Impact simulator: compute projected premium based on what-if sliders.
    proj_risk = projected_risk_score(
        stats=stats,
        reduce_hard_braking_pct=float(reduce_hb),
        limit_night_driving_pct=float(limit_night),
        improve_focus_pct=float(improve_focus),
    )
    current_premium = float(base_premium) * (risk_score / 100.0)
    projected_premium = float(base_premium) * (proj_risk / 100.0)
    yearly_savings = max(0.0, round(current_premium - projected_premium, 2))

    with st.sidebar:
        st.metric("Projected Premium", f"${projected_premium:,.0f}/yr")
        st.metric("Potential Savings", f"${yearly_savings:,.0f}/yr")

    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("Average Risk Score", f"{risk_score}")
        m2.metric("Total Trips Analyzed", f"{stats.trip_count}")
        m3.metric("Estimated Premium Savings", f"${int(savings):,}/yr")

    st.write("")

    with st.container(border=True):
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Current Premium", f"${current_premium:,.0f}/yr")
        s2.metric("Projected Premium", f"${projected_premium:,.0f}/yr")
        s3.metric("Savings If You Improve", f"${yearly_savings:,.0f}/yr")
        s4.metric("Projected Risk Score", f"{proj_risk}")

    left, right = st.columns(2, gap="large")
    with left:
        st.plotly_chart(gauge_figure(risk_score), use_container_width=True)
    with right:
        st.plotly_chart(radar_figure(stats), use_container_width=True)

    st.markdown("### AI Coaching")
    if "llm_summary" not in st.session_state:
        st.session_state["llm_summary"] = None
        st.session_state["llm_error"] = None

    generate = st.button("Generate Coaching Advice", type="primary")
    if generate:
        st.session_state["llm_error"] = None
        try:
            summary = get_risk_coaching(stats, model=model, api_key=openai_key or None, mode="auto")
            st.session_state["llm_summary"] = summary
        except Exception as exc:  # keep the UI resilient for hackathon demos
            st.session_state["llm_error"] = str(exc)
            st.session_state["llm_summary"] = None

    if st.session_state["llm_error"]:
        st.warning(f"AI coaching unavailable: {st.session_state['llm_error']}")
        st.caption("Tip: provide an API key to enable OpenAI coaching. Offline coaching is available without a key.")

    if st.session_state["llm_summary"]:
        coaching_box(st.session_state["llm_summary"])
        with st.expander("Raw JSON"):
            st.code(json.dumps(st.session_state["llm_summary"], indent=2), language="json")
    else:
        st.caption("Click the button to generate coaching advice (offline deterministic if no API key is set).")

    st.markdown("### Trips (Preview)")
    st.dataframe(df.head(max_trips), use_container_width=True, height=320)

if __name__ == "__main__":
    main()
