from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui_style import (
    render_decision_summary_card,
    render_page_header,
)


TIER_ORDER = ["Critical", "Maintenance Planned", "Monitor", "Ready"]

TIER_COLOR_MAP = {
    "Critical": "#ef4444",
    "Maintenance Planned": "#f59e0b",
    "Monitor": "#14b8a6",
    "Ready": "#60a5fa",
}


def render_kpis(asset_health: pd.DataFrame, recommendations: pd.DataFrame) -> None:
    critical_assets = int((asset_health["readiness_tier"] == "Critical").sum())
    average_health = float(asset_health["asset_health_score"].mean())
    average_confidence = float(asset_health["virtual_sensor_confidence"].mean())
    open_actions = int(
        (recommendations["recommended_action"] != "No immediate action").sum()
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Assets monitored", f"{len(asset_health):,}")
    col2.metric("Critical assets", f"{critical_assets:,}")
    col3.metric("Avg. health risk", f"{average_health:.1f}/100")
    col4.metric("Virtual sensor confidence", f"{average_confidence:.1f}%")
    col5.metric("Open recommendations", f"{open_actions:,}")


def format_top_recommendations(recommendations: pd.DataFrame) -> pd.DataFrame:
    display = recommendations[
        [
            "asset_id",
            "recommended_action",
            "time_horizon",
            "priority_score",
            "readiness_tier",
            "estimated_rul",
            "reason",
        ]
    ].copy()

    display = display.rename(
        columns={
            "asset_id": "Asset",
            "recommended_action": "Recommended Action",
            "time_horizon": "Time Horizon",
            "priority_score": "Priority",
            "readiness_tier": "Readiness Tier",
            "estimated_rul": "Estimated RUL",
            "reason": "Reason",
        }
    )

    display["Priority"] = display["Priority"].clip(0, 100).round(1)
    display["Estimated RUL"] = display["Estimated RUL"].round(0).astype(int)

    return display


def render_recommendations_table(display_df: pd.DataFrame) -> None:
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=430,
        column_order=[
            "Asset",
            "Recommended Action",
            "Time Horizon",
            "Priority",
            "Readiness Tier",
            "Estimated RUL",
            "Reason",
        ],
        column_config={
            "Asset": st.column_config.NumberColumn(
                "Asset",
                format="%d",
                width="small",
            ),
            "Recommended Action": st.column_config.TextColumn(
                "Recommended Action",
                width="medium",
            ),
            "Time Horizon": st.column_config.TextColumn(
                "Time Horizon",
                width="medium",
            ),
            "Priority": st.column_config.ProgressColumn(
                "Priority",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Readiness Tier": st.column_config.TextColumn(
                "Readiness Tier",
                width="medium",
            ),
            "Estimated RUL": st.column_config.NumberColumn(
                "Estimated RUL",
                format="%d",
                width="small",
            ),
            "Reason": st.column_config.TextColumn(
                "Reason",
                width="large",
            ),
        },
    )


def build_readiness_chart(asset_health: pd.DataFrame):
    tier_counts = asset_health["readiness_tier"].value_counts().reindex(
        TIER_ORDER,
        fill_value=0,
    )

    chart_df = tier_counts.reset_index()
    chart_df.columns = ["Readiness Tier", "Assets"]

    fig = px.pie(
        chart_df,
        names="Readiness Tier",
        values="Assets",
        hole=0.58,
        color="Readiness Tier",
        color_discrete_map=TIER_COLOR_MAP,
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Assets: %{value}<br>Share: %{percent}<extra></extra>",
    )

    fig.update_layout(
        title="Readiness Tier Distribution",
        showlegend=True,
        legend_title_text="Readiness Tier",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def build_priority_scatter(asset_health: pd.DataFrame):
    top_assets = asset_health.sort_values(
        "maintenance_priority",
        ascending=False,
    ).head(15).copy()

    top_assets["asset_label"] = top_assets["asset_id"].astype(str)

    fig = px.scatter(
        top_assets,
        x="estimated_rul",
        y="maintenance_priority",
        color="readiness_tier",
        size="sensor_deviation_score",
        text="asset_label",
        color_discrete_map=TIER_COLOR_MAP,
        hover_data={
            "asset_id": True,
            "estimated_rul": ":.0f",
            "maintenance_priority": ":.1f",
            "asset_health_score": ":.1f",
            "sensor_deviation_score": ":.1f",
            "virtual_sensor_confidence": ":.1f",
            "readiness_tier": True,
        },
        labels={
            "estimated_rul": "Estimated RUL",
            "maintenance_priority": "Maintenance Priority",
            "readiness_tier": "Readiness Tier",
            "sensor_deviation_score": "Sensor Deviation",
        },
        title="Top Priority Assets: Priority vs. Estimated RUL",
    )

    fig.update_traces(
        textposition="top center",
        marker=dict(line=dict(width=1)),
    )

    fig.update_layout(
        legend_title_text="Readiness Tier",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def render_executive_overview(
    sensor_readings: pd.DataFrame,
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    asset_health: pd.DataFrame,
    recommendations: pd.DataFrame,
    metrics: dict,
) -> None:
    render_page_header(
        title="Executive Overview",
        subtitle="Management view on asset readiness, risk concentration and open maintenance actions.",
        eyebrow="Decision Layer",
    )

    st.info("Decision question: Which assets need management attention first?")

    render_kpis(asset_health, recommendations)

    critical_count = int((asset_health["readiness_tier"] == "Critical").sum())
    maintenance_count = int(
        (asset_health["readiness_tier"] == "Maintenance Planned").sum()
    )
    schedule_count = int(
        (recommendations["recommended_action"] == "Schedule maintenance").sum()
    )
    inspect_count = int(
        (recommendations["recommended_action"] == "Inspect sensor").sum()
    )
    replace_count = int(
        (recommendations["recommended_action"] == "Replace sensor").sum()
    )

    render_decision_summary_card(
        title="Current Decision Summary",
        text=(
            f"{critical_count} assets are critical, "
            f"{maintenance_count} require maintenance planning and "
            f"{schedule_count} should be scheduled for maintenance within the next 10 cycles. "
            f"Additionally, {inspect_count} sensors require inspection and "
            f"{replace_count} sensors should be reviewed for replacement."
        ),
    )

    left, right = st.columns([1, 1.25])

    with left:
        st.plotly_chart(
            build_readiness_chart(asset_health),
            use_container_width=True,
        )

    with right:
        st.plotly_chart(
            build_priority_scatter(asset_health),
            use_container_width=True,
        )

    st.subheader("Top Maintenance Recommendations")
    st.markdown(
        """
        This table focuses on the highest-priority actions only.
        It is intentionally simplified for management review and hides most technical scoring detail.
        """
    )

    top_recommendations = recommendations.sort_values(
        "priority_score",
        ascending=False,
    ).head(10)

    display_df = format_top_recommendations(top_recommendations)

    render_recommendations_table(display_df)