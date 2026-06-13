from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.config import (
    ASSET_HEALTH_PATH,
    ASSET_HEALTH_WEIGHTS,
    MAINTENANCE_PRIORITY_WEIGHTS,
    RUL_RISK_CAP_CYCLES,
    SENSOR_READINGS_PATH,
    TARGET_SENSOR,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)

LOGGER = logging.getLogger(__name__)


def _clip_score(value: float | pd.Series) -> float | pd.Series:
    return np.clip(value, 0, 100)


def _weighted_score(frame: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    missing_columns = [column for column in weights if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing score input columns: {missing_columns}")

    score = pd.Series(0.0, index=frame.index)
    for column, weight in weights.items():
        score += frame[column].fillna(0) * weight

    return _clip_score(score)


def _snapshot_cycle(unit_number: int, max_cycle: int) -> int:
    # C-MAPSS training data contains complete run-to-failure histories. For a dashboard
    # snapshot, every asset is intentionally observed before the final failure cycle.
    # Otherwise all assets would collapse into the same RUL=0 state, which is true for
    # the raw training data but useless for maintenance decision support.
    observation_fraction = min(0.94, 0.55 + ((unit_number % 40) / 100))
    return max(1, int(max_cycle * observation_fraction))


def _calculate_trend_risk(
    sensor_readings: pd.DataFrame,
    unit_number: int,
    current_cycle: int,
    target_sensor: str,
) -> float:
    unit_history = sensor_readings[
        (sensor_readings["unit_number"] == unit_number)
        & (sensor_readings["time_cycle"] <= current_cycle)
    ].sort_values("time_cycle")

    if len(unit_history) < 16:
        return 0.0

    current_value = float(unit_history[target_sensor].iloc[-1])
    previous_value = float(unit_history[target_sensor].iloc[-16])
    global_std = max(float(sensor_readings[target_sensor].std()), 1e-6)

    normalized_delta = abs(current_value - previous_value) / global_std
    return float(_clip_score(normalized_delta * 30))


def _assign_readiness_tier(row: pd.Series) -> str:
    """Translate technical risk signals into a business-facing readiness tier.

    Higher scores mean higher maintenance attention, not better condition. The tier
    helps prioritize inspection and planning work; it is not a safety certification
    and does not authorize continued operation.
    """
    if (
        row["maintenance_priority"] >= 75
        or row["asset_health_score"] >= 70
        or (
            row["rul_risk_score"] >= 85
            and row["sensor_deviation_score"] >= 60
        )
    ):
        return "Critical"

    if row["maintenance_priority"] >= 55 or row["asset_health_score"] >= 50:
        return "Maintenance Planned"

    if row["maintenance_priority"] >= 25 or row["asset_health_score"] >= 25:
        return "Monitor"

    return "Ready"


def build_asset_health(
    sensor_readings: pd.DataFrame | None = None,
    virtual_predictions: pd.DataFrame | None = None,
    target_sensor: str = TARGET_SENSOR,
) -> pd.DataFrame:
    if sensor_readings is None:
        sensor_readings = pd.read_parquet(SENSOR_READINGS_PATH)

    if virtual_predictions is None:
        virtual_predictions = pd.read_parquet(VIRTUAL_SENSOR_PREDICTIONS_PATH)

    latest_cycles = sensor_readings.groupby("unit_number")["max_cycle"].max().to_dict()
    snapshot_rows: list[pd.Series] = []

    for unit_number, max_cycle in latest_cycles.items():
        cycle = _snapshot_cycle(int(unit_number), int(max_cycle))

        unit_rows = sensor_readings[
            (sensor_readings["unit_number"] == unit_number)
            & (sensor_readings["time_cycle"] <= cycle)
        ].sort_values("time_cycle")

        if unit_rows.empty:
            continue

        snapshot_rows.append(unit_rows.iloc[-1])

    snapshot = pd.DataFrame(snapshot_rows)
    snapshot = snapshot[["unit_number", "time_cycle", "remaining_useful_life", "max_cycle"]]

    virtual_subset = virtual_predictions[
        [
            "unit_number",
            "time_cycle",
            "absolute_error",
            "relative_error",
            "confidence_score",
            "fallback_status",
        ]
    ]

    asset_health = snapshot.merge(
        virtual_subset,
        on=["unit_number", "time_cycle"],
        how="left",
    )

    p95_error = max(float(virtual_predictions["absolute_error"].quantile(0.95)), 1e-6)

    # RUL is capped because the MVP should compare maintenance urgency across assets,
    # not pretend to produce a certified failure-time forecast.
    asset_health["rul_risk_score"] = _clip_score(
        100 * (1 - (asset_health["remaining_useful_life"] / RUL_RISK_CAP_CYCLES))
    )

    asset_health["sensor_deviation_score"] = _clip_score(
        (asset_health["absolute_error"].fillna(0) / p95_error) * 100
    )

    asset_health["virtual_sensor_confidence"] = asset_health["confidence_score"].fillna(0)
    asset_health["virtual_sensor_confidence_risk"] = (
        100 - asset_health["virtual_sensor_confidence"]
    )

    trend_risks: list[float] = []
    for row in asset_health.itertuples(index=False):
        trend_risks.append(
            _calculate_trend_risk(
                sensor_readings=sensor_readings,
                unit_number=int(row.unit_number),
                current_cycle=int(row.time_cycle),
                target_sensor=target_sensor,
            )
        )

    asset_health["trend_risk_score"] = trend_risks

    # The Asset Health Score combines multiple weak signals into one planning KPI:
    # RUL risk drives urgency, deviation shows physical-vs-virtual sensor mismatch,
    # confidence risk prevents overtrusting the fallback, and trend risk adds recent drift.
    asset_health["asset_health_score"] = _weighted_score(
        asset_health,
        ASSET_HEALTH_WEIGHTS,
    )

    asset_health["maintenance_priority"] = _weighted_score(
        asset_health,
        MAINTENANCE_PRIORITY_WEIGHTS,
    )

    asset_health["readiness_tier"] = asset_health.apply(_assign_readiness_tier, axis=1)

    asset_health = asset_health.rename(
        columns={
            "unit_number": "asset_id",
            "time_cycle": "current_cycle",
            "remaining_useful_life": "estimated_rul",
        }
    )

    ordered_columns = [
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
    ]

    asset_health = asset_health[ordered_columns].sort_values(
        "maintenance_priority",
        ascending=False,
    )

    return asset_health.reset_index(drop=True)


def run_asset_health_calculation() -> pd.DataFrame:
    asset_health = build_asset_health()
    ASSET_HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    asset_health.to_parquet(ASSET_HEALTH_PATH, index=False)
    LOGGER.info("Saved asset health output to %s", ASSET_HEALTH_PATH)
    return asset_health