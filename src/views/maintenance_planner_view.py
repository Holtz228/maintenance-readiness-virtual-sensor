from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui_style import (
    render_decision_summary_card,
    render_page_header,
)


ACTION_ORDER = [
    "Schedule maintenance",
    "Replace sensor",
    "Inspect sensor",
    "Review asset before next production window",
    "Continue limited monitoring",
    "No immediate action",
]

ACTION_COLOR_MAP = {
    "Schedule maintenance": "#60a5fa",
    "Replace sensor": "#f59e0b",
    "Inspect sensor": "#38bdf8",
    "Review asset before next production window": "#a78bfa",
    "Continue limited monitoring": "#14b8a6",
    "No immediate action": "#64748b",
}


def format_action_board_table(recommendations: pd.DataFrame) -> pd.DataFrame:
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


def format_technical_scoring_table(recommendations: pd.DataFrame) -> pd.DataFrame:
    available_columns = [
        column
        for column in [
            "asset_id",
            "priority_score",
            "readiness_tier",
            "recommended_action",
            "time_horizon",
            "estimated_rul",
            "asset_health_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
            "reason",
        ]
        if column in recommendations.columns
    ]

    display = recommendations[available_columns].copy()

    display = display.rename(
        columns={
            "asset_id": "Asset",
            "priority_score": "Priority",
            "readiness_tier": "Readiness Tier",
            "recommended_action": "Action",
            "time_horizon": "Time Horizon",
            "estimated_rul": "Estimated RUL",
            "asset_health_score": "Health Risk",
            "sensor_deviation_score": "Sensor Deviation",
            "virtual_sensor_confidence": "Fallback Confidence",
            "reason": "Reason",
        }
    )

    score_columns = [
        "Priority",
        "Health Risk",
        "Sensor Deviation",
        "Fallback Confidence",
    ]

    for column in score_columns:
        if column in display.columns:
            display[column] = display[column].clip(0, 100).round(1)

    if "Estimated RUL" in display.columns:
        display["Estimated RUL"] = display["Estimated RUL"].round(0).astype(int)

    return display


def render_action_kpis(recommendations: pd.DataFrame) -> None:
    schedule_count = int(
        (recommendations["recommended_action"] == "Schedule maintenance").sum()
    )
    replace_count = int(
        (recommendations["recommended_action"] == "Replace sensor").sum()
    )
    inspect_count = int(
        (recommendations["recommended_action"] == "Inspect sensor").sum()
    )
    review_count = int(
        (
            recommendations["recommended_action"]
            == "Review asset before next production window"
        ).sum()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Schedule maintenance", f"{schedule_count:,}")
    col2.metric("Replace sensor", f"{replace_count:,}")
    col3.metric("Inspect sensor", f"{inspect_count:,}")
    col4.metric("Review asset", f"{review_count:,}")


def build_action_distribution_chart(recommendations: pd.DataFrame):
    action_counts = (
        recommendations["recommended_action"]
        .value_counts()
        .reindex(ACTION_ORDER, fill_value=0)
        .reset_index()
    )

    action_counts.columns = ["Recommended Action", "Assets"]
    action_counts = action_counts[action_counts["Assets"] > 0]

    fig = px.pie(
        action_counts,
        names="Recommended Action",
        values="Assets",
        hole=0.58,
        color="Recommended Action",
        color_discrete_map=ACTION_COLOR_MAP,
        title="Action Mix",
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Assets: %{value}<br>"
            "Share: %{percent}<extra></extra>"
        ),
    )

    fig.update_layout(
        legend_title_text="Recommended Action",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def build_priority_scatter(recommendations: pd.DataFrame):
    top_recommendations = recommendations.sort_values(
        "priority_score",
        ascending=False,
    ).head(20).copy()

    top_recommendations["asset_label"] = top_recommendations["asset_id"].astype(str)

    fig = px.scatter(
        top_recommendations,
        x="estimated_rul",
        y="priority_score",
        color="recommended_action",
        size="asset_health_score",
        text="asset_label",
        color_discrete_map=ACTION_COLOR_MAP,
        title="Top Actions: Priority vs. Estimated RUL",
        labels={
            "estimated_rul": "Estimated RUL",
            "priority_score": "Priority Score",
            "recommended_action": "Recommended Action",
            "asset_health_score": "Health Risk",
        },
        hover_data={
            "asset_id": True,
            "readiness_tier": True,
            "time_horizon": True,
            "sensor_deviation_score": ":.1f",
            "virtual_sensor_confidence": ":.1f",
            "reason": True,
        },
    )

    fig.update_traces(
        textposition="top center",
        marker=dict(line=dict(width=1)),
    )

    fig.update_layout(
        legend_title_text="Recommended Action",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def render_action_board_table(display_df: pd.DataFrame) -> None:
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=460,
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


def render_technical_scoring_table(display_df: pd.DataFrame) -> None:
    column_config = {
        "Asset": st.column_config.NumberColumn(
            "Asset",
            format="%d",
            width="small",
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
        "Action": st.column_config.TextColumn(
            "Action",
            width="medium",
        ),
        "Time Horizon": st.column_config.TextColumn(
            "Time Horizon",
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
        "Reason": st.column_config.TextColumn(
            "Reason",
            width="large",
        ),
    }

    preferred_order = [
        "Asset",
        "Priority",
        "Readiness Tier",
        "Action",
        "Time Horizon",
        "Estimated RUL",
        "Health Risk",
        "Sensor Deviation",
        "Fallback Confidence",
        "Reason",
    ]

    column_order = [
        column
        for column in preferred_order
        if column in display_df.columns
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=560,
        column_order=column_order,
        column_config={
            column: config
            for column, config in column_config.items()
            if column in display_df.columns
        },
    )


def render_action_board(filtered: pd.DataFrame) -> None:
    left, right = st.columns([1, 1.25])

    with left:
        st.plotly_chart(
            build_action_distribution_chart(filtered),
            use_container_width=True,
        )

    with right:
        st.plotly_chart(
            build_priority_scatter(filtered),
            use_container_width=True,
        )

    st.subheader("Recommended Actions")

    # The action board is the business output of the project. It should answer
    # what to do next before explaining every scoring component.
    st.markdown(
        """
        This board shows the highest-priority maintenance actions in a business-friendly format.
        It focuses on the next decision, not on raw scoring internals.
        """
    )

    top_actions = filtered.sort_values("priority_score", ascending=False).head(12)
    display_df = format_action_board_table(top_actions)

    render_action_board_table(display_df)


def render_technical_scoring(filtered: pd.DataFrame) -> None:
    st.subheader("Technical Scoring Details")

    # Technical scoring remains available for credibility and reviewability.
    # The recommendation layer is rule-based, so the underlying score inputs should stay visible.
    st.markdown(
        """
        This view explains why the recommendation layer produced its actions.
        It keeps the key score components visible without turning the page into a raw data dump.
        """
    )

    technical_df = format_technical_scoring_table(
        filtered.sort_values("priority_score", ascending=False)
    )

    render_technical_scoring_table(technical_df)


def render_maintenance_planner(
    sensor_readings: pd.DataFrame,
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    asset_health: pd.DataFrame,
    recommendations: pd.DataFrame,
    metrics: dict[str, Any],
) -> None:
    render_page_header(
        title="Maintenance Planner",
        subtitle="Action-oriented recommendation layer for maintenance prioritization.",
        eyebrow="Recommendation Layer",
    )

    st.info("Decision question: What should the maintenance team do next?")

    render_action_kpis(recommendations)

    schedule_count = int(
        (recommendations["recommended_action"] == "Schedule maintenance").sum()
    )
    replace_count = int(
        (recommendations["recommended_action"] == "Replace sensor").sum()
    )
    inspect_count = int(
        (recommendations["recommended_action"] == "Inspect sensor").sum()
    )

    render_decision_summary_card(
        title="Maintenance Action Summary",
        text=(
            f"The decision layer identifies <strong>{schedule_count}</strong> assets for scheduled maintenance, "
            f"<strong>{replace_count}</strong> sensors for replacement review and "
            f"<strong>{inspect_count}</strong> sensors for inspection before the next production window."
        ),
    )

    action_options = [
        action
        for action in ACTION_ORDER
        if action in set(recommendations["recommended_action"].unique())
    ]

    action_filter = st.multiselect(
        "Filter recommended actions",
        options=action_options,
        default=action_options,
    )

    filtered = recommendations[recommendations["recommended_action"].isin(action_filter)]

    if filtered.empty:
        st.warning("No recommendations match the selected filters.")
        return

    action_tab, technical_tab = st.tabs(
        [
            "Action Board",
            "Technical Scoring",
        ]
    )

    with action_tab:
        render_action_board(filtered)

    with technical_tab:
        render_technical_scoring(filtered)