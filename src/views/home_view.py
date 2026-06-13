from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.config import TARGET_SENSOR
from src.ui_style import (
    render_executive_summary_card,
    render_hero_card,
    render_layer_card,
    render_page_header,
    render_warning_box,
)


def render_home(
    sensor_readings: pd.DataFrame,
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    asset_health: pd.DataFrame,
    recommendations: pd.DataFrame,
    metrics: dict[str, Any],
) -> None:
    render_page_header(
        title="Maintenance Readiness & Virtual Sensor Decision Support",
        subtitle=(
            "Industrial analytics MVP for asset health, virtual sensor fallback confidence "
            "and maintenance prioritization."
        ),
        eyebrow="Portfolio Project",
    )

    render_hero_card(
        title="Business Problem",
        text=(
            "Maintenance teams need to understand which assets are becoming risky, which sensor signals "
            "are unreliable, and whether a virtual sensor can provide temporary monitoring support until "
            "the next inspection or maintenance window."
        ),
    )

    critical_assets = int((asset_health["readiness_tier"] == "Critical").sum())
    maintenance_escalations = int(
        (recommendations["recommended_action"] == "Schedule maintenance").sum()
    )
    model_r2 = float(metrics.get("model_r2", 0.0))

    # The home page is the recruiter-facing entry point. It compresses the full
    # pipeline into a few business KPIs instead of exposing technical detail too early.
    render_executive_summary_card(
        assets_monitored=len(asset_health),
        critical_assets=critical_assets,
        model_r2=model_r2,
        maintenance_escalations=maintenance_escalations,
        text=(
            "The system turns raw industrial sensor data into asset readiness tiers, "
            "virtual-sensor fallback confidence and concrete maintenance recommendations."
        ),
    )

    render_warning_box(
        title="Safety Boundary",
        text=(
            "The virtual sensor is a decision-support fallback for monitoring and maintenance planning. "
            "It is not a certified replacement for safety-critical instrumentation or machine control."
        ),
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        render_layer_card(
            1,
            "Sensor Data",
            f"{len(sensor_readings):,} sensor rows processed from NASA C-MAPSS FD001.",
        )

    with col2:
        render_layer_card(
            2,
            "Virtual Sensor",
            (
                f"Target sensor: {metrics.get('target_sensor', TARGET_SENSOR)} "
                f"with R² {float(metrics.get('model_r2', 0.0)):.3f}."
            ),
        )

    with col3:
        render_layer_card(
            3,
            "Maintenance Decision",
            (
                f"{len(recommendations):,} asset-level recommendations generated "
                "from health and deviation scores."
            ),
        )

    st.markdown('<div class="subsection-divider"></div>', unsafe_allow_html=True)

    st.subheader("MVP Data Flow")

    # This is intentionally shown as a simple business flow, not as a technical
    # architecture diagram. The page should make the decision-support chain obvious.
    st.markdown(
        """
        Sensor readings → Sensor profile → Virtual sensor prediction → Deviation monitoring → 
        Asset health score → Maintenance recommendation → Dashboard decision support
        """
    )