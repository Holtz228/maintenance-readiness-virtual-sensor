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
    "Inspection required": "#ef4444",
    "Fallback not recommended": "#64748b",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False

    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y"}

    return bool(value)


def _format_metric_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    return str(value)


def get_target_sensor(metrics: dict) -> str:
    return str(metrics.get("target_sensor", TARGET_SENSOR))


def get_validation_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty or "evaluation_split" not in predictions.columns:
        return predictions

    validation_predictions = predictions[predictions["evaluation_split"] == "validation"]

    if validation_predictions.empty:
        return predictions

    return validation_predictions


def get_target_sensor_row(
    sensor_profile: pd.DataFrame,
    target_sensor: str,
) -> pd.Series:
    if sensor_profile.empty or "sensor" not in sensor_profile.columns:
        return pd.Series(dtype="object")

    target_rows = sensor_profile[
        sensor_profile["sensor"].astype(str) == str(target_sensor)
    ]

    if target_rows.empty:
        return pd.Series(dtype="object")

    return target_rows.iloc[0]


def calculate_mae_improvement(metrics: dict) -> float | None:
    baseline_mae = _safe_float(metrics.get("baseline_mae"), default=0.0)
    model_mae = _safe_float(metrics.get("model_mae"), default=0.0)

    if baseline_mae <= 0 or model_mae <= 0:
        return None

    return ((baseline_mae - model_mae) / baseline_mae) * 100


def render_quality_kpis(
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: dict,
) -> None:
    target_sensor = get_target_sensor(metrics)
    validation_predictions = get_validation_predictions(predictions)

    model_mae = _safe_float(metrics.get("model_mae"))
    model_r2 = _safe_float(metrics.get("model_r2"))
    mae_improvement = calculate_mae_improvement(metrics)

    validated_assets = 0
    if not validation_predictions.empty and "unit_number" in validation_predictions.columns:
        validated_assets = int(validation_predictions["unit_number"].nunique())

    avg_confidence = 0.0
    if not validation_predictions.empty and "confidence_score" in validation_predictions.columns:
        avg_confidence = float(validation_predictions["confidence_score"].mean())

    improvement_label = (
        f"{mae_improvement:.1f}%"
        if mae_improvement is not None
        else "n/a"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Target sensor", target_sensor)
    col2.metric("Model MAE", f"{model_mae:.3f}")
    col3.metric("Model R²", f"{model_r2:.3f}")
    col4.metric("MAE improvement", improvement_label)
    col5.metric("Avg. confidence", f"{avg_confidence:.1f}%")


def build_quality_gates(
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: dict,
) -> pd.DataFrame:
    target_sensor = get_target_sensor(metrics)
    target_row = get_target_sensor_row(sensor_profile, target_sensor)
    validation_predictions = get_validation_predictions(predictions)

    missing_rate = _safe_float(target_row.get("missing_rate"), default=1.0)
    abs_correlation = _safe_float(
        target_row.get(
            "abs_correlation_with_rul",
            abs(_safe_float(target_row.get("correlation_with_rul"))),
        )
    )
    usable_for_virtual_sensor = _safe_bool(
        target_row.get("usable_for_virtual_sensor")
    )

    sensor_gate_passed = (
        not target_row.empty
        and usable_for_virtual_sensor
        and missing_rate <= 0.05
        and abs_correlation >= 0.30
    )

    baseline_mae = _safe_float(metrics.get("baseline_mae"))
    model_mae = _safe_float(metrics.get("model_mae"))
    model_r2 = _safe_float(metrics.get("model_r2"))

    model_gate_passed = (
        model_mae > 0
        and model_r2 >= 0.50
        and (baseline_mae <= 0 or model_mae < baseline_mae)
    )

    validation_records = len(validation_predictions)
    validation_assets = 0

    if not validation_predictions.empty and "unit_number" in validation_predictions.columns:
        validation_assets = int(validation_predictions["unit_number"].nunique())

    validation_gate_passed = validation_records >= 500 and validation_assets >= 10

    avg_confidence = 0.0
    if not validation_predictions.empty and "confidence_score" in validation_predictions.columns:
        avg_confidence = float(validation_predictions["confidence_score"].mean())

    confidence_gate_passed = avg_confidence >= 50

    gate_rows = [
        {
            "Gate": "Sensor usability",
            "Status": "Passed" if sensor_gate_passed else "Review required",
            "Evidence": (
                f"Missing rate {missing_rate:.2%}, "
                f"abs. RUL correlation {abs_correlation:.3f}, "
                f"usable flag {usable_for_virtual_sensor}"
            ),
            "Decision Impact": "Confirms whether the selected signal is suitable as virtual-sensor target.",
        },
        {
            "Gate": "Model performance",
            "Status": "Passed" if model_gate_passed else "Review required",
            "Evidence": (
                f"Model MAE {model_mae:.4f}, "
                f"baseline MAE {baseline_mae:.4f}, "
                f"model R² {model_r2:.3f}"
            ),
            "Decision Impact": "Checks whether the model improves over baseline and explains enough variance.",
        },
        {
            "Gate": "Validation coverage",
            "Status": "Passed" if validation_gate_passed else "Review required",
            "Evidence": (
                f"{validation_records:,} validation records across "
                f"{validation_assets:,} assets"
            ),
            "Decision Impact": "Checks whether the validation set is broad enough for an MVP claim.",
        },
        {
            "Gate": "Fallback confidence",
            "Status": "Passed" if confidence_gate_passed else "Review required",
            "Evidence": f"Average confidence {avg_confidence:.1f}%",
            "Decision Impact": "Checks whether fallback estimates are stable enough for monitoring support.",
        },
    ]

    return pd.DataFrame(gate_rows)


def render_quality_decision(
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: dict,
) -> None:
    quality_gates = build_quality_gates(
        sensor_profile=sensor_profile,
        predictions=predictions,
        metrics=metrics,
    )

    passed_gates = int((quality_gates["Status"] == "Passed").sum())
    total_gates = len(quality_gates)

    if passed_gates == total_gates:
        st.success(
            "Quality decision: The virtual-sensor MVP is defensible for monitoring and maintenance-planning support."
        )
    else:
        st.warning(
            f"Quality decision: {passed_gates}/{total_gates} gates passed. "
            "The MVP is useful for analysis, but the limitations should stay visible."
        )

    st.caption(
        "Scope boundary: This validates a portfolio-grade decision-support MVP. "
        "It does not certify the model for automated machine control or safety-critical operation."
    )

    left, right = st.columns([1.4, 1])

    with left:
        st.dataframe(
            quality_gates,
            use_container_width=True,
            hide_index=True,
            height=250,
            column_config={
                "Gate": st.column_config.TextColumn("Gate", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Evidence": st.column_config.TextColumn("Evidence", width="large"),
                "Decision Impact": st.column_config.TextColumn(
                    "Decision Impact",
                    width="large",
                ),
            },
        )

    with right:
        validation_predictions = get_validation_predictions(predictions)
        render_fallback_distribution(validation_predictions)


def render_fallback_distribution(predictions: pd.DataFrame) -> None:
    if predictions.empty or "fallback_status" not in predictions.columns:
        st.info("No fallback-status distribution available.")
        return

    fallback_counts = (
        predictions["fallback_status"]
        .value_counts()
        .reindex(FALLBACK_ORDER, fill_value=0)
        .reset_index()
    )
    fallback_counts.columns = ["Fallback Status", "Records"]
    fallback_counts = fallback_counts[fallback_counts["Records"] > 0]

    fig = px.pie(
        fallback_counts,
        names="Fallback Status",
        values="Records",
        hole=0.58,
        color="Fallback Status",
        color_discrete_map=FALLBACK_COLOR_MAP,
        title="Validation Fallback Mix",
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Records: %{value}<br>Share: %{percent}<extra></extra>",
    )

    fig.update_layout(
        legend_title_text="Fallback Status",
        margin=dict(t=60, l=20, r=20, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def build_model_error_chart(metrics: dict):
    rows = []

    for metric_name, baseline_key, model_key in [
        ("MAE", "baseline_mae", "model_mae"),
        ("RMSE", "baseline_rmse", "model_rmse"),
    ]:
        baseline_value = metrics.get(baseline_key)
        model_value = metrics.get(model_key)

        if baseline_value is None or model_value is None:
            continue

        rows.extend(
            [
                {
                    "Metric": metric_name,
                    "Model": "Baseline",
                    "Value": _safe_float(baseline_value),
                },
                {
                    "Metric": metric_name,
                    "Model": "Virtual Sensor",
                    "Value": _safe_float(model_value),
                },
            ]
        )

    chart_df = pd.DataFrame(rows)

    if chart_df.empty:
        return None

    fig = px.bar(
        chart_df,
        x="Metric",
        y="Value",
        color="Model",
        barmode="group",
        title="Error Metrics: Baseline vs. Virtual Sensor",
        labels={
            "Value": "Error Value",
            "Model": "Model",
        },
    )

    fig.update_layout(
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def build_model_r2_chart(metrics: dict):
    rows = []

    if "baseline_r2" in metrics:
        rows.append(
            {
                "Model": "Baseline",
                "R²": _safe_float(metrics.get("baseline_r2")),
            }
        )

    if "model_r2" in metrics:
        rows.append(
            {
                "Model": "Virtual Sensor",
                "R²": _safe_float(metrics.get("model_r2")),
            }
        )

    chart_df = pd.DataFrame(rows)

    if chart_df.empty:
        return None

    fig = px.bar(
        chart_df,
        x="Model",
        y="R²",
        title="Explained Variance: Baseline vs. Virtual Sensor",
        labels={
            "R²": "R² Score",
        },
    )

    fig.update_layout(
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def format_model_benchmark_table(metrics: dict) -> pd.DataFrame:
    rows = []

    metric_pairs = [
        ("MAE", "baseline_mae", "model_mae", "Lower is better"),
        ("RMSE", "baseline_rmse", "model_rmse", "Lower is better"),
        ("R²", "baseline_r2", "model_r2", "Higher is better"),
    ]

    for metric_name, baseline_key, model_key, direction in metric_pairs:
        if baseline_key not in metrics and model_key not in metrics:
            continue

        baseline_value = _safe_float(metrics.get(baseline_key))
        model_value = _safe_float(metrics.get(model_key))

        if metric_name in {"MAE", "RMSE"} and baseline_value > 0:
            delta = ((baseline_value - model_value) / baseline_value) * 100
            delta_label = f"{delta:.1f}% reduction"
        elif metric_name == "R²":
            delta = model_value - baseline_value
            delta_label = f"{delta:+.3f}"
        else:
            delta_label = "n/a"

        rows.append(
            {
                "Metric": metric_name,
                "Baseline": baseline_value,
                "Virtual Sensor": model_value,
                "Delta": delta_label,
                "Direction": direction,
            }
        )

    return pd.DataFrame(rows)


def format_model_metrics_table(metrics: dict) -> pd.DataFrame:
    metric_order = [
        "target_sensor",
        "feature_count",
        "train_units",
        "validation_units",
        "baseline_mae",
        "baseline_rmse",
        "baseline_r2",
        "model_mae",
        "model_rmse",
        "model_r2",
    ]

    rows = []

    for key in metric_order:
        if key in metrics:
            rows.append(
                {
                    "Metric": key.replace("_", " ").title(),
                    "Value": _format_metric_value(metrics[key]),
                }
            )

    for key in sorted(set(metrics.keys()) - set(metric_order)):
        rows.append(
            {
                "Metric": key.replace("_", " ").title(),
                "Value": _format_metric_value(metrics[key]),
            }
        )

    return pd.DataFrame(rows)


def render_model_benchmark(metrics: dict) -> None:
    st.subheader("Model Benchmark")
    st.markdown(
        """
        This view compares the virtual-sensor model against the baseline.
        The key question is whether the model creates analytical value beyond a simple benchmark.
        """
    )

    benchmark_df = format_model_benchmark_table(metrics)

    if not benchmark_df.empty:
        st.dataframe(
            benchmark_df,
            use_container_width=True,
            hide_index=True,
            height=170,
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="small"),
                "Baseline": st.column_config.NumberColumn(
                    "Baseline",
                    format="%.4f",
                    width="medium",
                ),
                "Virtual Sensor": st.column_config.NumberColumn(
                    "Virtual Sensor",
                    format="%.4f",
                    width="medium",
                ),
                "Delta": st.column_config.TextColumn("Delta", width="medium"),
                "Direction": st.column_config.TextColumn("Direction", width="medium"),
            },
        )

    left, right = st.columns(2)

    with left:
        error_fig = build_model_error_chart(metrics)
        if error_fig is not None:
            st.plotly_chart(error_fig, use_container_width=True)
        else:
            st.info("No baseline error metrics available.")

    with right:
        r2_fig = build_model_r2_chart(metrics)
        if r2_fig is not None:
            st.plotly_chart(r2_fig, use_container_width=True)
        else:
            st.info("No R² benchmark metrics available.")

    with st.expander("Show raw model metrics"):
        metric_rows = format_model_metrics_table(metrics)

        st.dataframe(
            metric_rows,
            use_container_width=True,
            hide_index=True,
            height=360,
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="medium"),
                "Value": st.column_config.TextColumn("Value", width="medium"),
            },
        )


def format_target_sensor_profile(
    sensor_profile: pd.DataFrame,
    metrics: dict,
) -> pd.DataFrame:
    target_sensor = get_target_sensor(metrics)
    target_row = get_target_sensor_row(sensor_profile, target_sensor)

    if target_row.empty:
        return pd.DataFrame()

    display = pd.DataFrame([target_row])

    display = display.rename(
        columns={
            "sensor": "Sensor",
            "missing_rate": "Missing Rate",
            "std": "Std. Dev.",
            "unique_value_count": "Unique Values",
            "correlation_with_rul": "RUL Correlation",
            "usable_for_virtual_sensor": "Usable",
            "abs_correlation_with_rul": "Abs. RUL Correlation",
        }
    )

    for column in [
        "Missing Rate",
        "Std. Dev.",
        "RUL Correlation",
        "Abs. RUL Correlation",
    ]:
        if column in display.columns:
            display[column] = display[column].round(4)

    if "Unique Values" in display.columns:
        display["Unique Values"] = display["Unique Values"].astype(int)

    return display


def format_sensor_candidates(sensor_profile: pd.DataFrame) -> pd.DataFrame:
    if sensor_profile.empty:
        return pd.DataFrame()

    available_columns = [
        column
        for column in [
            "sensor",
            "missing_rate",
            "std",
            "unique_value_count",
            "correlation_with_rul",
            "usable_for_virtual_sensor",
            "abs_correlation_with_rul",
        ]
        if column in sensor_profile.columns
    ]

    display = sensor_profile[available_columns].copy()

    display = display.rename(
        columns={
            "sensor": "Sensor",
            "missing_rate": "Missing Rate",
            "std": "Std. Dev.",
            "unique_value_count": "Unique Values",
            "correlation_with_rul": "RUL Correlation",
            "usable_for_virtual_sensor": "Usable",
            "abs_correlation_with_rul": "Abs. RUL Correlation",
        }
    )

    for column in [
        "Missing Rate",
        "Std. Dev.",
        "RUL Correlation",
        "Abs. RUL Correlation",
    ]:
        if column in display.columns:
            display[column] = display[column].round(4)

    if "Unique Values" in display.columns:
        display["Unique Values"] = display["Unique Values"].astype(int)

    if "Abs. RUL Correlation" in display.columns:
        display = display.sort_values("Abs. RUL Correlation", ascending=False)

    return display


def build_sensor_candidate_chart(sensor_profile: pd.DataFrame):
    candidate_df = format_sensor_candidates(sensor_profile)

    if candidate_df.empty or "Abs. RUL Correlation" not in candidate_df.columns:
        return None

    chart_df = candidate_df.head(12).sort_values("Abs. RUL Correlation")

    fig = px.bar(
        chart_df,
        x="Abs. RUL Correlation",
        y="Sensor",
        orientation="h",
        color="Usable" if "Usable" in chart_df.columns else None,
        title="Top Sensor Candidates by RUL Correlation",
        labels={
            "Abs. RUL Correlation": "Absolute Correlation with RUL",
            "Sensor": "Sensor",
            "Usable": "Usable",
        },
    )

    fig.update_layout(
        margin=dict(t=60, l=20, r=20, b=20),
    )

    return fig


def render_sensor_evidence(sensor_profile: pd.DataFrame, metrics: dict) -> None:
    st.subheader("Sensor Evidence")
    st.markdown(
        """
        This view explains why the selected target sensor is technically plausible.
        The strongest evidence is low missingness, sufficient signal variation and a meaningful relationship with RUL.
        """
    )

    target_profile = format_target_sensor_profile(sensor_profile, metrics)

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("**Selected target sensor**")

        if target_profile.empty:
            st.warning("Target sensor not found in the sensor profile.")
        else:
            st.dataframe(
                target_profile,
                use_container_width=True,
                hide_index=True,
                height=95,
            )

    with right:
        candidate_fig = build_sensor_candidate_chart(sensor_profile)

        if candidate_fig is not None:
            st.plotly_chart(candidate_fig, use_container_width=True)
        else:
            st.info("No sensor candidate chart available.")

    with st.expander("Show sensor candidate table"):
        candidate_df = format_sensor_candidates(sensor_profile)

        if candidate_df.empty:
            st.warning("No sensor profile data available.")
        else:
            st.dataframe(
                candidate_df.head(25),
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config={
                    "Sensor": st.column_config.TextColumn("Sensor", width="medium"),
                    "Missing Rate": st.column_config.NumberColumn(
                        "Missing Rate",
                        format="%.4f",
                        width="medium",
                    ),
                    "Std. Dev.": st.column_config.NumberColumn(
                        "Std. Dev.",
                        format="%.4f",
                        width="medium",
                    ),
                    "Unique Values": st.column_config.NumberColumn(
                        "Unique Values",
                        format="%d",
                        width="medium",
                    ),
                    "RUL Correlation": st.column_config.NumberColumn(
                        "RUL Correlation",
                        format="%.4f",
                        width="medium",
                    ),
                    "Usable": st.column_config.CheckboxColumn(
                        "Usable",
                        width="small",
                    ),
                    "Abs. RUL Correlation": st.column_config.NumberColumn(
                        "Abs. RUL Correlation",
                        format="%.4f",
                        width="medium",
                    ),
                },
            )


def format_validation_records(predictions: pd.DataFrame) -> pd.DataFrame:
    available_columns = [
        column
        for column in [
            "unit_number",
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
        if column in predictions.columns
    ]

    display = predictions[available_columns].copy()

    display = display.rename(
        columns={
            "unit_number": "Asset",
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

    for column in [
        "Actual Value",
        "Virtual Sensor",
        "Absolute Error",
        "Relative Error",
        "Confidence",
    ]:
        if column in display.columns:
            display[column] = display[column].round(4)

    for column in ["Asset", "Cycle", "RUL"]:
        if column in display.columns:
            display[column] = display[column].round(0).astype(int)

    if "Cycle" in display.columns:
        display = display.sort_values("Cycle", ascending=False)

    return display


def render_validation_records(predictions: pd.DataFrame) -> None:
    st.subheader("Validation Records")
    st.markdown(
        """
        This view shows a filtered sample of prediction records.
        It is kept intentionally compact so the page remains a validation view, not a raw-data dump.
        """
    )

    if predictions.empty:
        st.warning("No prediction records available.")
        return

    filtered = predictions.copy()

    filter_left, filter_right = st.columns(2)

    with filter_left:
        if "evaluation_split" in filtered.columns:
            split_options = sorted(filtered["evaluation_split"].dropna().unique())

            default_split_index = (
                split_options.index("validation")
                if "validation" in split_options
                else 0
            )

            selected_split = st.selectbox(
                "Evaluation split",
                options=split_options,
                index=default_split_index,
            )

            filtered = filtered[filtered["evaluation_split"] == selected_split]

    with filter_right:
        if "fallback_status" in filtered.columns:
            status_options = sorted(filtered["fallback_status"].dropna().unique())

            selected_status = st.multiselect(
                "Fallback status",
                options=status_options,
                default=status_options,
            )

            filtered = filtered[filtered["fallback_status"].isin(selected_status)]

    if filtered.empty:
        st.warning("No validation records match the selected filters.")
        return

    display_df = format_validation_records(filtered).head(50)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_order=[
            column
            for column in [
                "Asset",
                "Cycle",
                "RUL",
                "Actual Value",
                "Virtual Sensor",
                "Absolute Error",
                "Relative Error",
                "Confidence",
                "Fallback Status",
                "Split",
            ]
            if column in display_df.columns
        ],
        column_config={
            "Asset": st.column_config.NumberColumn(
                "Asset",
                format="%d",
                width="small",
            ),
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
                format="%.4f",
                width="medium",
            ),
            "Virtual Sensor": st.column_config.NumberColumn(
                "Virtual Sensor",
                format="%.4f",
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


def render_data_quality(
    sensor_readings: pd.DataFrame,
    sensor_profile: pd.DataFrame,
    predictions: pd.DataFrame,
    asset_health: pd.DataFrame,
    recommendations: pd.DataFrame,
    metrics: dict,
) -> None:
    render_page_header(
        title="Data & Model Quality",
        subtitle="Validation view for sensor suitability, model benchmark quality and fallback reliability.",
        eyebrow="Quality Assurance",
    )

    st.markdown(
        "**Decision question:** Is the selected sensor technically defensible for a virtual-sensor MVP?"
    )

    render_quality_kpis(
        sensor_profile=sensor_profile,
        predictions=predictions,
        metrics=metrics,
    )

    quality_tab, model_tab, sensor_tab, validation_tab = st.tabs(
        [
            "QA Decision",
            "Model Benchmark",
            "Sensor Evidence",
            "Validation Records",
        ]
    )

    with quality_tab:
        render_quality_decision(
            sensor_profile=sensor_profile,
            predictions=predictions,
            metrics=metrics,
        )

    with model_tab:
        render_model_benchmark(metrics)

    with sensor_tab:
        render_sensor_evidence(
            sensor_profile=sensor_profile,
            metrics=metrics,
        )

    with validation_tab:
        render_validation_records(predictions)