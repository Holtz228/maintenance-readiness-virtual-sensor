from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


EXPECTED_OUTPUTS = {
    "sensor_readings": PROCESSED_DIR / "sensor_readings.parquet",
    "sensor_profile": PROCESSED_DIR / "sensor_profile.parquet",
    "predictions": PROCESSED_DIR / "virtual_sensor_predictions.parquet",
    "asset_health": PROCESSED_DIR / "asset_health.parquet",
    "recommendations": PROCESSED_DIR / "maintenance_recommendations.parquet",
    "metrics": PROCESSED_DIR / "virtual_sensor_metrics.json",
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


def read_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(EXPECTED_OUTPUTS[name])


def read_metrics() -> dict:
    with EXPECTED_OUTPUTS["metrics"].open("r", encoding="utf-8") as file:
        return json.load(file)


def assert_score_range(df: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column not in df.columns:
            continue

        values = pd.to_numeric(df[column], errors="coerce").dropna()

        assert not values.empty, f"{column} has no numeric values."
        assert values.between(0, 100).all(), f"{column} contains values outside 0-100."


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


def test_virtual_sensor_predictions_contract() -> None:
    predictions = read_parquet("predictions")

    required_columns = {
        "unit_number",
        "time_cycle",
        "actual_value",
        "predicted_value",
        "absolute_error",
        "confidence_score",
        "fallback_status",
        "evaluation_split",
    }

    assert required_columns.issubset(predictions.columns)

    assert_score_range(
        predictions,
        [
            "confidence_score",
        ],
    )

    observed_statuses = set(predictions["fallback_status"].dropna().unique())

    assert observed_statuses.issubset(ALLOWED_FALLBACK_STATUSES)
    assert "validation" in set(predictions["evaluation_split"].dropna().unique())


def test_asset_health_contract() -> None:
    asset_health = read_parquet("asset_health")

    required_columns = {
        "asset_id",
        "estimated_rul",
        "asset_health_score",
        "readiness_tier",
        "maintenance_priority",
    }

    assert required_columns.issubset(asset_health.columns)

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

    observed_tiers = set(asset_health["readiness_tier"].dropna().unique())

    assert observed_tiers.issubset(ALLOWED_READINESS_TIERS)
    assert asset_health["asset_id"].nunique() > 0


def test_recommendations_contract() -> None:
    recommendations = read_parquet("recommendations")

    required_columns = {
        "asset_id",
        "recommended_action",
        "priority_score",
        "readiness_tier",
        "estimated_rul",
    }

    assert required_columns.issubset(recommendations.columns)

    assert_score_range(
        recommendations,
        [
            "priority_score",
            "asset_health_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
        ],
    )

    observed_actions = set(recommendations["recommended_action"].dropna().unique())

    assert observed_actions.issubset(ALLOWED_RECOMMENDED_ACTIONS)
    assert len(recommendations) > 0


def test_model_quality_beats_baseline() -> None:
    metrics = read_metrics()

    assert metrics["model_mae"] < metrics["baseline_mae"]
    assert metrics["model_rmse"] < metrics["baseline_rmse"]
    assert metrics["model_r2"] > metrics["baseline_r2"]