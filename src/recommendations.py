from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.config import (
    ASSET_HEALTH_PATH,
    MAINTENANCE_PRIORITY_WEIGHTS,
    MAINTENANCE_RECOMMENDATIONS_PATH,
)

LOGGER = logging.getLogger(__name__)


def _calculate_priority_score(row: pd.Series) -> float:
    missing_columns = [
        column for column in MAINTENANCE_PRIORITY_WEIGHTS if column not in row.index
    ]
    if missing_columns:
        raise ValueError(f"Missing priority score input columns: {missing_columns}")

    score = sum(
        float(row[column]) * weight
        for column, weight in MAINTENANCE_PRIORITY_WEIGHTS.items()
    )

    return float(np.clip(score, 0, 100))


def _build_action(row: pd.Series) -> tuple[str, str, str]:
    """Convert risk signals into a maintenance-oriented recommendation.

    The recommendation layer is intentionally rule-based. For this MVP, transparent
    decision rules are more credible than an opaque scheduling model because the output
    supports inspection and planning decisions, not automated maintenance execution.
    """
    if row["readiness_tier"] == "Critical":
        return (
            "Schedule maintenance",
            "Within 10 cycles",
            "Asset has critical readiness priority based on RUL risk, health score and sensor deviation.",
        )

    if row["sensor_deviation_score"] >= 85 and row["virtual_sensor_confidence"] < 50:
        return (
            "Replace sensor",
            "Before next production window",
            "Sensor deviation is very high and virtual-sensor confidence is weak, so the physical sensor should be treated as unreliable.",
        )

    if row["sensor_deviation_score"] >= 70 and row["virtual_sensor_confidence"] < 60:
        return (
            "Inspect sensor",
            "Before next production window",
            "Virtual sensor deviation is high and fallback confidence is limited.",
        )

    if row["readiness_tier"] == "Maintenance Planned":
        return (
            "Review asset before next production window",
            "Within 25 cycles",
            "Asset is not critical yet, but health score and maintenance priority suggest proactive planning.",
        )

    if row["readiness_tier"] == "Monitor":
        return (
            "Continue limited monitoring",
            "Next planned inspection",
            "MVP thresholds do not trigger immediate escalation, but the asset should remain under observation.",
        )

    return (
        "No immediate action",
        "Standard maintenance cycle",
        "Risk indicators are currently below action threshold.",
    )


def generate_recommendations(asset_health: pd.DataFrame | None = None) -> pd.DataFrame:
    if asset_health is None:
        asset_health = pd.read_parquet(ASSET_HEALTH_PATH)

    rows: list[dict[str, object]] = []

    for _, row in asset_health.iterrows():
        action, time_horizon, reason = _build_action(row)
        priority_score = _calculate_priority_score(row)

        rows.append(
            {
                "asset_id": int(row["asset_id"]),
                "priority_score": priority_score,
                "readiness_tier": row["readiness_tier"],
                "recommended_action": action,
                "time_horizon": time_horizon,
                "reason": reason,
                "estimated_rul": float(row["estimated_rul"]),
                "asset_health_score": float(row["asset_health_score"]),
                "sensor_deviation_score": float(row["sensor_deviation_score"]),
                "virtual_sensor_confidence": float(row["virtual_sensor_confidence"]),
            }
        )

    recommendations = pd.DataFrame(rows)
    recommendations = recommendations.sort_values("priority_score", ascending=False)

    return recommendations.reset_index(drop=True)


def run_recommendation_generation() -> pd.DataFrame:
    recommendations = generate_recommendations()

    MAINTENANCE_RECOMMENDATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_parquet(MAINTENANCE_RECOMMENDATIONS_PATH, index=False)

    LOGGER.info(
        "Saved maintenance recommendations to %s",
        MAINTENANCE_RECOMMENDATIONS_PATH,
    )

    return recommendations