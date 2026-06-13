from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui_style import (
    render_decision_summary_card,
    render_page_header,
)


READINESS_ORDER = [
    "Critical",
    "Maintenance Planned",
    "Monitor",
    "Ready",
]

READINESS_COLOR_MAP = {
    "Critical": "#60a5fa",
    "Maintenance Planned": "#f59e0b",
    "Monitor": "#14b8a6",
    "Ready": "#8b5cf6",
}


def _get_available_readiness_tiers(asset_health: pd.DataFrame) -> list[str]:
    available_tiers = set(asset_health["readiness_tier"].dropna().unique())

    ordered_tiers = [
        tier
        for tier in READINESS_ORDER
        if tier in available_tiers
    ]

    additional_tiers = sorted(available_tiers - set(ordered_tiers))

    return ordered_tiers + additional_tiers


def render_asset_health_kpis(asset_health: pd.DataFrame) -> None:
    critical_count = int((asset_health["readiness_tier"] == "Critical").sum())
    maintenance_count = int(
        (asset_health["readiness_tier"] == "Maintenance Planned").sum()
    )

    avg_health_risk = float(asset_health["asset_health_score"].mean())
    avg_fallback_confidence = float(asset_health["virtual_sensor_confidence"].mean())

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Critical assets", f"{critical_count:,}")
    col2.metric("Maintenance planned", f"{maintenance_count:,}")
    col3.metric("Avg. health risk", f"{avg_health_risk:.1f}")
    col4.metric("Avg. fallback confidence", f"{avg_fallback_confidence:.1f}")


def build_asset_health_scatter(filtered: pd.DataFrame):
    fig = px.scatter(
        filtered,
        x="estimated_rul",
        y="asset_health_score",
        size="sensor_deviation_score",
        color="readiness_tier",
        color_discrete_map=READINESS_COLOR_MAP,
        hover_data={
            "asset_id": True,
            "estimated_rul": ":.0f",
            "asset_health_score": ":.1f",
            "sensor_deviation_score": ":.1f",
            "virtual_sensor_confidence": ":.1f",
            "maintenance_priority": ":.1f",
            "fallback_status": True,
        },
        title="Asset Health vs. Estimated RUL",
        labels={
            "estimated_rul": "Estimated RUL",
            "asset_health_score": "Asset Health Risk Score",
            "sensor_deviation_score": "Sensor Deviation",
            "readiness_tier": "Readiness Tier",
            "asset_id": "Asset",
            "virtual_sensor_confidence": "Fallback Confidence",
            "maintenance_priority": "Maintenance Priority",
            "fallback_status": "Fallback Status",
        },
    )

    fig.update_traces(
        marker=dict(
            line=dict(width=1),
            opacity=0.86,
        )
    )

    fig.update_layout(
        legend_title_text="Readiness Tier",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def format_readiness_board_table(asset_health: pd.DataFrame) -> pd.DataFrame:
    display = asset_health[
        [
            "asset_id",
            "readiness_tier",
            "maintenance_priority",
            "estimated_rul",
            "asset_health_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
            "fallback_status",
        ]
    ].copy()

    display = display.rename(
        columns={
            "asset_id": "Asset",
            "readiness_tier": "Readiness Tier",
            "maintenance_priority": "Maintenance Priority",
            "estimated_rul": "Estimated RUL",
            "asset_health_score": "Health Risk",
            "sensor_deviation_score": "Sensor Deviation",
            "virtual_sensor_confidence": "Fallback Confidence",
            "fallback_status": "Fallback Status",
        }
    )

    display["Maintenance Priority"] = (
        display["Maintenance Priority"].clip(0, 100).round(1)
    )
    display["Estimated RUL"] = display["Estimated RUL"].round(0).astype(int)
    display["Health Risk"] = display["Health Risk"].clip(0, 100).round(1)
    display["Sensor Deviation"] = display["Sensor Deviation"].clip(0, 100).round(1)
    display["Fallback Confidence"] = (
        display["Fallback Confidence"].clip(0, 100).round(1)
    )

    return display


def format_technical_scoring_table(asset_health: pd.DataFrame) -> pd.DataFrame:
    display = asset_health[
        [
            "asset_id",
            "current_cycle",
            "rul_risk_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence_risk",
            "trend_risk_score",
            "asset_health_score",
            "maintenance_priority",
            "fallback_status",
        ]
    ].copy()

    display = display.rename(
        columns={
            "asset_id": "Asset",
            "current_cycle": "Current Cycle",
            "rul_risk_score": "RUL Risk",
            "sensor_deviation_score": "Deviation Risk",
            "virtual_sensor_confidence_risk": "Confidence Risk",
            "trend_risk_score": "Trend Risk",
            "asset_health_score": "Health Score",
            "maintenance_priority": "Maintenance Priority",
            "fallback_status": "Fallback Status",
        }
    )

    score_columns = [
        "RUL Risk",
        "Deviation Risk",
        "Confidence Risk",
        "Trend Risk",
        "Health Score",
        "Maintenance Priority",
    ]

    for column in score_columns:
        display[column] = display[column].clip(0, 100).round(1)

    display["Current Cycle"] = display["Current Cycle"].round(0).astype(int)

    return display


def render_readiness_board_table(display_df: pd.DataFrame) -> None:
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=460,
        column_order=[
            "Asset",
            "Readiness Tier",
            "Maintenance Priority",
            "Estimated RUL",
            "Health Risk",
            "Sensor Deviation",
            "Fallback Confidence",
            "Fallback Status",
        ],
        column_config={
            "Asset": st.column_config.NumberColumn(
                "Asset",
                format="%d",
                width="small",
            ),
            "Readiness Tier": st.column_config.TextColumn(
                "Readiness Tier",
                width="medium",
            ),
            "Maintenance Priority": st.column_config.ProgressColumn(
                "Maintenance Priority",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Estimated RUL": st.column_config.NumberColumn(
                "Estimated RUL",
                format="%d",
                width="small",
            ),
            "Health Risk": st.column_config.ProgressColumn(
                "Health Risk",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Sensor Deviation": st.column_config.ProgressColumn(
                "Sensor Deviation",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Fallback Confidence": st.column_config.ProgressColumn(
                "Fallback Confidence",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Fallback Status": st.column_config.TextColumn(
                "Fallback Status",
                width="medium",
            ),
        },
    )


def render_technical_scoring_table(display_df: pd.DataFrame) -> None:
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=560,
        column_order=[
            "Asset",
            "Current Cycle",
            "RUL Risk",
            "Deviation Risk",
            "Confidence Risk",
            "Trend Risk",
            "Health Score",
            "Maintenance Priority",
            "Fallback Status",
        ],
        column_config={
            "Asset": st.column_config.NumberColumn(
                "Asset",
                format="%d",
                width="small",
            ),
            "Current Cycle": st.column_config.NumberColumn(
                "Current Cycle",
                format="%d",
                width="small",
            ),
            "RUL Risk": st.column_config.ProgressColumn(
                "RUL Risk",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Deviation Risk": st.column_config.ProgressColumn(
                "Deviation Risk",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Confidence Risk": st.column_config.ProgressColumn(
                "Confidence Risk",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Trend Risk": st.column_config.ProgressColumn(
                "Trend Risk",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Health Score": st.column_config.ProgressColumn(
                "Health Score",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Maintenance Priority": st.column_config.ProgressColumn(
                "Maintenance Priority",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Fallback Status": st.column_config.TextColumn(
                "Fallback Status",
                width="medium",
            ),
        },
    )


def render_readiness_map(filtered: pd.DataFrame) -> None:
    st.plotly_chart(
        build_asset_health_scatter(filtered),
        use_container_width=True,
    )

    st.subheader("Most Exposed Assets")
    st.markdown(
        """
        This board focuses on the assets with the highest maintenance priority.
        It keeps the operational decision visible and avoids exposing the full raw scoring table.
        """
    )

    top_assets = filtered.sort_values(
        "maintenance_priority",
        ascending=False,
    ).head(12)

    display_df = format_readiness_board_table(top_assets)

    render_readiness_board_table(display_df)


def render_scoring_details(filtered: pd.DataFrame) -> None:
    st.subheader("Technical Scoring Details")
    st.markdown(
        """
        This view explains how the readiness score is built from RUL risk,
        deviation exposure, fallback confidence risk and trend risk.
        """
    )

    technical_df = format_technical_scoring_table(
        filtered.sort_values("maintenance_priority", ascending=False)
    )

    render_technical_scoring_table(technical_df)


def render_asset_health(
    sensor_readings: pd.DataFrame,
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    asset_health: pd.DataFrame,
    recommendations: pd.DataFrame,
    metrics: dict,
) -> None:
    render_page_header(
        title="Asset Health",
        subtitle="Risk scoring view for estimated RUL, deviation exposure and readiness tiers.",
        eyebrow="Readiness Analytics",
    )

    st.markdown(
        '<div class="decision-box"><strong>Decision question:</strong><br>'
        "Which machines are most exposed from a readiness perspective?</div>",
        unsafe_allow_html=True,
    )

    render_asset_health_kpis(asset_health)

    critical_count = int((asset_health["readiness_tier"] == "Critical").sum())
    maintenance_count = int(
        (asset_health["readiness_tier"] == "Maintenance Planned").sum()
    )

    render_decision_summary_card(
        title="Readiness Exposure Summary",
        text=(
            f"The readiness layer identifies <strong>{critical_count}</strong> critical assets "
            f"and <strong>{maintenance_count}</strong> assets that should be planned for maintenance. "
            "The highest-priority assets combine low estimated RUL, high deviation exposure "
            "and limited fallback confidence."
        ),
    )

    tier_options = _get_available_readiness_tiers(asset_health)

    tier_filter = st.multiselect(
        "Readiness tier",
        options=tier_options,
        default=tier_options,
    )

    filtered = asset_health[asset_health["readiness_tier"].isin(tier_filter)]

    if filtered.empty:
        st.warning("No assets match the selected readiness tiers.")
        return

    readiness_tab, scoring_tab = st.tabs(
        [
            "Readiness Map",
            "Scoring Details",
        ]
    )

    with readiness_tab:
        render_readiness_map(filtered)

    with scoring_tab:
        render_scoring_details(filtered)