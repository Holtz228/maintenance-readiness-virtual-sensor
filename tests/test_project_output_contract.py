from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    ASSET_HEALTH_PATH,
    MAINTENANCE_RECOMMENDATIONS_PATH,
    SENSOR_PROFILE_PATH,
    SENSOR_READINGS_PATH,
    TARGET_SENSOR,
    VIRTUAL_SENSOR_METRICS_PATH,
    VIRTUAL_SENSOR_MODEL_PATH,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)


# Contract tests validate the concrete pipeline artifacts used by the dashboard.
# Using config paths avoids validating stale files from older output folders by accident.
EXPECTED_OUTPUTS = {
    "sensor_readings": SENSOR_READINGS_PATH,
    "sensor_profile": SENSOR_PROFILE_PATH,
    "predictions": VIRTUAL_SENSOR_PREDICTIONS_PATH,
    "asset_health": ASSET_HEALTH_PATH,
    "recommendations": MAINTENANCE_RECOMMENDATIONS_PATH,
    "metrics": VIRTUAL_SENSOR_METRICS_PATH,
    "model": VIRTUAL_SENSOR_MODEL_PATH,
}


ALLOWED_FALLBACK_STATUSES = {
    "Reliable fallback",
    "Limited fallback",
    "Inspection required",
    "Fallback not recommended",
}


ALLOWED_READINESS_TIERS = {
    "Critical",
    "Maintenance Planned",
    "Monitor",
    "Ready",
}


ALLOWED_RECOMMENDED_ACTIONS = {
    "Schedule maintenance",
    "Replace sensor",
    "Inspect sensor",
    "Review asset before next production window",
    "Continue limited monitoring",
    "No immediate action",
}


FORBIDDEN_SAFETY_CLAIMS = {
    "safe operation",
    "continue safely",
    "certified fallback",
    "certified safety",
    "safety certified",
    "autonomous control",
    "fully automated maintenance",
    "production-ready safety system",
}


def read_parquet(name: str) -> pd.DataFrame:
    path = EXPECTED_OUTPUTS[name]
    assert isinstance(path, Path)
    return pd.read_parquet(path)


def read_metrics() -> dict[str, Any]:
    path = EXPECTED_OUTPUTS["metrics"]
    assert isinstance(path, Path)

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    assert isinstance(payload, dict), "Metrics output must be a JSON object."
    return payload


def assert_required_columns(df: pd.DataFrame, required_columns: set[str]) -> None:
    missing_columns = required_columns - set(df.columns)
    assert not missing_columns, f"Missing required columns: {sorted(missing_columns)}"


def assert_required_columns_not_empty(
    df: pd.DataFrame,
    required_columns: set[str],
) -> None:
    fully_empty_columns = [
        column
        for column in required_columns
        if column in df.columns and df[column].isna().all()
    ]

    assert not fully_empty_columns, (
        f"Required columns are fully empty: {fully_empty_columns}"
    )


def assert_score_range(df: pd.DataFrame, columns: list[str]) -> None:
    # All business-facing scores are normalized to 0-100 so that dashboard KPIs,
    # readiness tiers and recommendation priorities stay comparable.
    for column in columns:
        if column not in df.columns:
            continue

        values = pd.to_numeric(df[column], errors="coerce").dropna()

        assert not values.empty, f"{column} has no numeric values."
        assert values.between(0, 100).all(), (
            f"{column} contains values outside 0-100."
        )


def test_expected_pipeline_outputs_exist() -> None:
    for name, path in EXPECTED_OUTPUTS.items():
        assert path.exists(), f"Missing expected output: {name} at {path}"


def test_core_outputs_are_not_empty() -> None:
    for name in [
        "sensor_readings",
        "sensor_profile",
        "predictions",
        "asset_health",
        "recommendations",
    ]:
        df = read_parquet(name)
        assert not df.empty, f"{name} is empty."


def test_sensor_readings_contract() -> None:
    sensor_readings = read_parquet("sensor_readings")

    required_columns = {
        "unit_number",
        "time_cycle",
        "remaining_useful_life",
        "max_cycle",
    }

    assert_required_columns(sensor_readings, required_columns)
    assert_required_columns_not_empty(sensor_readings, required_columns)

    assert sensor_readings["unit_number"].nunique() > 0
    assert pd.to_numeric(sensor_readings["time_cycle"], errors="coerce").min() >= 1
    assert pd.to_numeric(
        sensor_readings["remaining_useful_life"],
        errors="coerce",
    ).min() >= 0


def test_sensor_profile_contract() -> None:
    sensor_profile = read_parquet("sensor_profile")

    required_columns = {
        "sensor",
        "missing_rate",
        "std",
        "unique_value_count",
        "correlation_with_rul",
        "usable_for_virtual_sensor",
    }

    assert_required_columns(sensor_profile, required_columns)
    assert_required_columns_not_empty(sensor_profile, required_columns)

    assert_score_range(sensor_profile, ["missing_rate"])

    assert TARGET_SENSOR in set(sensor_profile["sensor"])
    assert sensor_profile["usable_for_virtual_sensor"].astype(bool).any(), (
        "At least one sensor should be usable for virtual-sensor modelling."
    )


def test_virtual_sensor_predictions_contract() -> None:
    predictions = read_parquet("predictions")

    required_columns = {
        "unit_number",
        "time_cycle",
        "remaining_useful_life",
        "target_sensor",
        "actual_value",
        "predicted_value",
        "absolute_error",
        "relative_error",
        "confidence_score",
        "fallback_status",
        "sensor_failure_simulated",
        "evaluation_split",
    }

    assert_required_columns(predictions, required_columns)
    assert_required_columns_not_empty(predictions, required_columns)

    assert_score_range(predictions, ["confidence_score"])

    observed_statuses = set(predictions["fallback_status"].dropna().astype(str).unique())
    observed_splits = set(predictions["evaluation_split"].dropna().astype(str).unique())

    assert observed_statuses.issubset(ALLOWED_FALLBACK_STATUSES)
    assert "validation" in observed_splits
    assert "train" in observed_splits
    assert set(predictions["target_sensor"].dropna().astype(str).unique()) == {
        TARGET_SENSOR
    }


def test_asset_health_contract() -> None:
    asset_health = read_parquet("asset_health")

    required_columns = {
        "asset_id",
        "current_cycle",
        "estimated_rul",
        "rul_risk_score",
        "sensor_deviation_score",
        "virtual_sensor_confidence",
        "virtual_sensor_confidence_risk",
        "trend_risk_score",
        "asset_health_score",
        "readiness_tier",
        "maintenance_priority",
        "fallback_status",
    }

    assert_required_columns(asset_health, required_columns)
    assert_required_columns_not_empty(asset_health, required_columns)

    assert_score_range(
        asset_health,
        [
            "asset_health_score",
            "maintenance_priority",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
            "virtual_sensor_confidence_risk",
            "trend_risk_score",
            "rul_risk_score",
        ],
    )

    observed_tiers = set(asset_health["readiness_tier"].dropna().astype(str).unique())
    observed_fallback_statuses = set(
        asset_health["fallback_status"].dropna().astype(str).unique()
    )

    assert observed_tiers.issubset(ALLOWED_READINESS_TIERS)
    assert observed_fallback_statuses.issubset(ALLOWED_FALLBACK_STATUSES)
    assert asset_health["asset_id"].nunique() > 0


def test_recommendations_contract() -> None:
    recommendations = read_parquet("recommendations")

    required_columns = {
        "asset_id",
        "priority_score",
        "readiness_tier",
        "recommended_action",
        "time_horizon",
        "reason",
        "estimated_rul",
        "asset_health_score",
        "sensor_deviation_score",
        "virtual_sensor_confidence",
    }

    assert_required_columns(recommendations, required_columns)
    assert_required_columns_not_empty(recommendations, required_columns)

    assert_score_range(
        recommendations,
        [
            "priority_score",
            "asset_health_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
        ],
    )

    observed_actions = set(
        recommendations["recommended_action"].dropna().astype(str).unique()
    )
    observed_tiers = set(recommendations["readiness_tier"].dropna().astype(str).unique())

    assert observed_actions.issubset(ALLOWED_RECOMMENDED_ACTIONS)
    assert observed_tiers.issubset(ALLOWED_READINESS_TIERS)
    assert len(recommendations) > 0


def test_cross_output_row_consistency() -> None:
    # The project story depends on one consistent decision-support chain:
    # prepared sensor readings -> virtual sensor predictions -> asset health -> recommendations.
    # This test catches broken joins, missing assets or stale outputs between pipeline stages.
    sensor_readings = read_parquet("sensor_readings")
    predictions = read_parquet("predictions")
    asset_health = read_parquet("asset_health")
    recommendations = read_parquet("recommendations")

    assert len(predictions) == len(sensor_readings), (
        "Virtual sensor predictions should cover all prepared sensor readings."
    )

    sensor_asset_count = sensor_readings["unit_number"].nunique()
    health_asset_count = asset_health["asset_id"].nunique()
    recommendation_asset_count = recommendations["asset_id"].nunique()

    assert health_asset_count == sensor_asset_count
    assert recommendation_asset_count == health_asset_count

    assert set(recommendations["asset_id"]) == set(asset_health["asset_id"])


def test_recommendations_are_sorted_by_priority() -> None:
    # The Maintenance Planner should surface the most urgent assets first.
    # This is a business contract, not just a formatting preference.
    recommendations = read_parquet("recommendations")

    priority_scores = pd.to_numeric(
        recommendations["priority_score"],
        errors="coerce",
    ).dropna()

    assert priority_scores.is_monotonic_decreasing, (
        "Recommendations should be sorted by descending priority score."
    )


def test_model_quality_beats_baseline() -> None:
    # The virtual sensor is only credible if it beats a simple baseline.
    # Otherwise the ML layer would add complexity without decision-support value.
    metrics = read_metrics()

    required_keys = {
        "target_sensor",
        "feature_count",
        "train_units",
        "validation_units",
        "baseline_mae",
        "baseline_rmse",
        "baseline_r2",
        "model_mae",
        "model_rmse",
        "model_mape",
        "model_r2",
    }

    missing_keys = required_keys - set(metrics)
    assert not missing_keys, f"Missing model metric keys: {sorted(missing_keys)}"

    assert metrics["target_sensor"] == TARGET_SENSOR
    assert metrics["feature_count"] > 0
    assert metrics["train_units"] > 0
    assert metrics["validation_units"] > 0

    assert metrics["model_mae"] < metrics["baseline_mae"]
    assert metrics["model_rmse"] < metrics["baseline_rmse"]
    assert metrics["model_r2"] > metrics["baseline_r2"]


def test_recommendation_text_respects_safety_boundary() -> None:
    # The project is a monitoring and maintenance planning MVP.
    # Recommendation text must not imply certified safety, autonomous control or safe continued operation.
    recommendations = read_parquet("recommendations")

    text_columns = [
        "recommended_action",
        "time_horizon",
        "reason",
    ]

    combined_text = " ".join(
        recommendations[column].astype(str).str.lower().str.cat(sep=" ")
        for column in text_columns
        if column in recommendations.columns
    )

    forbidden_hits = [
        phrase
        for phrase in FORBIDDEN_SAFETY_CLAIMS
        if phrase in combined_text
    ]

    assert not forbidden_hits, (
        "Recommendation text contains forbidden safety claims: "
        f"{forbidden_hits}"
    )