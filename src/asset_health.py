from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.config import (
    ASSET_HEALTH_PATH,
    RUL_RISK_CAP_CYCLES,
    SENSOR_READINGS_PATH,
    TARGET_SENSOR,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)

LOGGER = logging.getLogger(__name__)


def _clip_score(value: float | pd.Series) -> float | pd.Series:
    return np.clip(value, 0, 100)


def _snapshot_cycle(unit_number: int, max_cycle: int) -> int:
    # The training set runs engines to failure. For a dashboard snapshot, we intentionally
    # observe each asset before end-of-life. Otherwise every engine would appear at RUL 0,
    # which would be technically true for training data but misleading for decision support.
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
    """Translate technical scores into a business-facing readiness tier.

    The tiering is calibrated for a portfolio MVP: the highest-priority assets should
    surface as Critical when both overall health risk and maintenance priority are high.
    This does not mean the asset is unsafe; it means the asset needs decision attention.
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

    asset_health["rul_risk_score"] = _clip_score(
        100 * (1 - (asset_health["remaining_useful_life"] / RUL_RISK_CAP_CYCLES))
    )

    asset_health["sensor_deviation_score"] = _clip_score(
        (asset_health["absolute_error"] / p95_error) * 100
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

    # Business weighting:
    # - RUL risk drives maintenance urgency.
    # - Sensor deviation indicates whether the measured signal is drifting from the fallback model.
    # - Confidence risk prevents overtrusting a weak virtual-sensor estimate.
    # - Trend risk adds short-term signal movement without dominating the decision.
    asset_health["asset_health_score"] = _clip_score(
        0.45 * asset_health["rul_risk_score"]
        + 0.25 * asset_health["sensor_deviation_score"]
        + 0.20 * asset_health["virtual_sensor_confidence_risk"]
        + 0.10 * asset_health["trend_risk_score"]
    )

    asset_health["maintenance_priority"] = _clip_score(
        0.50 * asset_health["asset_health_score"]
        + 0.30 * asset_health["sensor_deviation_score"]
        + 0.20 * asset_health["rul_risk_score"]
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