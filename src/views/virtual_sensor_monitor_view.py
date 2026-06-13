from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import TARGET_SENSOR
from src.ui_style import render_page_header


FALLBACK_ORDER = [
    "Reliable fallback",
    "Limited fallback",
    "Inspection required",
    "Fallback not recommended",
]

FALLBACK_COLOR_MAP = {
    "Reliable fallback": "#14b8a6",
    "Limited fallback": "#f59e0b",
    "Inspection required": "#f97316",
    "Fallback not recommended": "#64748b",
}


def get_asset_options(predictions: pd.DataFrame) -> list[int]:
    # The monitor defaults to validation assets because they were not used for
    # model fitting. This makes the view more credible than showing training examples first.
    if "evaluation_split" in predictions.columns:
        validation_assets = predictions.loc[
            predictions["evaluation_split"] == "validation",
            "unit_number",
        ].dropna()

        if not validation_assets.empty:
            return sorted(validation_assets.astype(int).unique().tolist())

    return sorted(predictions["unit_number"].dropna().astype(int).unique().tolist())


def format_recent_events_table(asset_predictions: pd.DataFrame) -> pd.DataFrame:
    display = asset_predictions[
        [
            "time_cycle",
            "remaining_useful_life",
            "actual_value",
            "predicted_value",
            "absolute_error",
            "relative_error",
            "confidence_score",
            "fallback_status",
            "evaluation_split",
        ]
    ].copy()

    display = display.rename(
        columns={
            "time_cycle": "Cycle",
            "remaining_useful_life": "RUL",
            "actual_value": "Actual Value",
            "predicted_value": "Virtual Sensor",
            "absolute_error": "Absolute Error",
            "relative_error": "Relative Error",
            "confidence_score": "Confidence",
            "fallback_status": "Fallback Status",
            "evaluation_split": "Split",
        }
    )

    display["Actual Value"] = display["Actual Value"].round(3)
    display["Virtual Sensor"] = display["Virtual Sensor"].round(3)
    display["Absolute Error"] = display["Absolute Error"].round(4)
    display["Relative Error"] = display["Relative Error"].round(4)
    display["Confidence"] = display["Confidence"].clip(0, 100).round(1)
    display["Cycle"] = display["Cycle"].astype(int)
    display["RUL"] = display["RUL"].astype(int)

    return display.sort_values("Cycle", ascending=False)


def build_signal_reconstruction_chart(asset_predictions: pd.DataFrame):
    plot_df = asset_predictions[
        [
            "time_cycle",
            "actual_value",
            "predicted_value",
        ]
    ].melt(
        id_vars="time_cycle",
        var_name="Signal",
        value_name="Sensor Value",
    )

    signal_name_map = {
        "actual_value": "Actual sensor value",
        "predicted_value": "Virtual sensor estimate",
    }
    plot_df["Signal"] = plot_df["Signal"].map(signal_name_map)

    fig = px.line(
        plot_df,
        x="time_cycle",
        y="Sensor Value",
        color="Signal",
        title="Actual vs. Virtual Sensor Signal",
        labels={
            "time_cycle": "Cycle",
            "Sensor Value": "Sensor Value",
            "Signal": "Signal",
        },
    )

    fig.update_layout(
        legend_title_text="Signal",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def build_confidence_chart(asset_predictions: pd.DataFrame):
    fig = px.line(
        asset_predictions,
        x="time_cycle",
        y="confidence_score",
        color="fallback_status",
        color_discrete_map=FALLBACK_COLOR_MAP,
        title="Fallback Confidence Over Time",
        labels={
            "time_cycle": "Cycle",
            "confidence_score": "Confidence Score",
            "fallback_status": "Fallback Status",
        },
    )

    fig.update_traces(mode="lines+markers")
    fig.update_layout(
        yaxis=dict(range=[0, 100]),
        legend_title_text="Fallback Status",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def build_error_chart(asset_predictions: pd.DataFrame):
    fig = px.line(
        asset_predictions,
        x="time_cycle",
        y="absolute_error",
        title="Absolute Prediction Error Over Time",
        labels={
            "time_cycle": "Cycle",
            "absolute_error": "Absolute Error",
        },
    )

    fig.update_traces(mode="lines+markers")
    fig.update_layout(
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def render_monitor_kpis(
    asset_predictions: pd.DataFrame,
    metrics: dict[str, Any],
) -> None:
    latest = asset_predictions.iloc[-1]

    avg_confidence = float(asset_predictions["confidence_score"].mean())
    latest_error = float(latest["absolute_error"])

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Target sensor", metrics.get("target_sensor", TARGET_SENSOR))
    col2.metric("Model MAE", f"{float(metrics.get('model_mae', 0.0)):.3f}")
    col3.metric("Model R²", f"{float(metrics.get('model_r2', 0.0)):.3f}")
    col4.metric("Avg. confidence", f"{avg_confidence:.1f}%")
    col5.metric("Latest error", f"{latest_error:.4f}")


def render_signal_reconstruction(asset_predictions: pd.DataFrame) -> None:
    st.plotly_chart(
        build_signal_reconstruction_chart(asset_predictions),
        use_container_width=True,
    )

    latest = asset_predictions.iloc[-1]
    latest_status = str(latest["fallback_status"])
    latest_error = float(latest["absolute_error"])
    latest_confidence = float(latest["confidence_score"])

    # The interpretation deliberately avoids any operational approval wording.
    # The virtual sensor supports monitoring judgement, not autonomous machine control.
    st.info(
        "Interpretation: The virtual sensor can support temporary monitoring analysis "
        "when confidence remains high and prediction error stays stable. "
        f"Latest status: {latest_status} | latest error: {latest_error:.4f} | "
        f"confidence: {latest_confidence:.1f}%."
    )


def render_fallback_confidence(asset_predictions: pd.DataFrame) -> None:
    st.plotly_chart(
        build_confidence_chart(asset_predictions),
        use_container_width=True,
    )

    st.plotly_chart(
        build_error_chart(asset_predictions),
        use_container_width=True,
    )

    st.warning(
        "Important: Confidence and absolute error are shown separately because they use different scales. "
        "The virtual sensor supports monitoring decisions, but it is not a certified replacement for the physical sensor."
    )


def render_recent_events(asset_predictions: pd.DataFrame) -> None:
    st.subheader("Recent Sensor Events")

    # The page shows the latest records only. This keeps the monitor focused on
    # decision support instead of turning it into a raw prediction export.
    st.markdown(
        """
        This table shows the latest validation events for the selected asset.
        It focuses on operational monitoring signals instead of exposing the full raw prediction dataset.
        """
    )

    display_df = format_recent_events_table(asset_predictions.tail(25))

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_order=[
            "Cycle",
            "RUL",
            "Actual Value",
            "Virtual Sensor",
            "Absolute Error",
            "Relative Error",
            "Confidence",
            "Fallback Status",
            "Split",
        ],
        column_config={
            "Cycle": st.column_config.NumberColumn(
                "Cycle",
                format="%d",
                width="small",
            ),
            "RUL": st.column_config.NumberColumn(
                "RUL",
                format="%d",
                width="small",
            ),
            "Actual Value": st.column_config.NumberColumn(
                "Actual Value",
                format="%.3f",
                width="medium",
            ),
            "Virtual Sensor": st.column_config.NumberColumn(
                "Virtual Sensor",
                format="%.3f",
                width="medium",
            ),
            "Absolute Error": st.column_config.NumberColumn(
                "Absolute Error",
                format="%.4f",
                width="medium",
            ),
            "Relative Error": st.column_config.NumberColumn(
                "Relative Error",
                format="%.4f",
                width="medium",
            ),
            "Confidence": st.column_config.ProgressColumn(
                "Confidence",
                min_value=0,
                max_value=100,
                format="%.1f",
                width="medium",
            ),
            "Fallback Status": st.column_config.TextColumn(
                "Fallback Status",
                width="medium",
            ),
            "Split": st.column_config.TextColumn(
                "Split",
                width="small",
            ),
        },
    )


def render_virtual_sensor_monitor(
    sensor_readings: pd.DataFrame,
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    asset_health: pd.DataFrame,
    recommendations: pd.DataFrame,
    metrics: dict[str, Any],
) -> None:
    render_page_header(
        title="Virtual Sensor Monitor",
        subtitle="Actual-vs-predicted monitoring view for temporary sensor fallback assessment.",
        eyebrow="Sensor Reliability",
    )

    st.info(
        "Decision question: Is the virtual sensor plausible as a temporary monitoring fallback?"
    )

    if predictions.empty:
        st.warning("No prediction data available for the virtual sensor monitor.")
        return

    asset_options = get_asset_options(predictions)

    if not asset_options:
        st.warning("No assets available for virtual sensor monitoring.")
        return

    selected_asset = st.selectbox(
        "Asset",
        options=asset_options,
        index=0,
    )

    asset_predictions = predictions[
        predictions["unit_number"] == selected_asset
    ].sort_values("time_cycle")

    if asset_predictions.empty:
        st.warning("No prediction records available for the selected asset.")
        return

    latest = asset_predictions.iloc[-1]

    render_monitor_kpis(asset_predictions, metrics)

    st.success(
        f"Latest fallback status for asset {selected_asset}: {latest['fallback_status']}"
    )

    signal_tab, confidence_tab, events_tab = st.tabs(
        [
            "Signal Reconstruction",
            "Fallback Confidence",
            "Recent Sensor Events",
        ]
    )

    with signal_tab:
        render_signal_reconstruction(asset_predictions)

    with confidence_tab:
        render_fallback_confidence(asset_predictions)

    with events_tab:
        render_recent_events(asset_predictions)