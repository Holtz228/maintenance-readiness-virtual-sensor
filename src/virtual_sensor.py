from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.config import (
    OPERATIONAL_SETTING_COLUMNS,
    RANDOM_STATE,
    SENSOR_COLUMNS,
    SENSOR_READINGS_PATH,
    TARGET_SENSOR,
    VIRTUAL_SENSOR_METRICS_PATH,
    VIRTUAL_SENSOR_MODEL_PATH,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class VirtualSensorResult:
    predictions: pd.DataFrame
    metrics: dict[str, float | str | int]


def _rmse(y_true: pd.Series, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _mape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    denominator = y_true.abs().replace(0, np.nan)
    return float(((y_true - y_pred).abs() / denominator).mean() * 100)


def _build_feature_columns(df: pd.DataFrame, target_sensor: str) -> list[str]:
    feature_columns: list[str] = []
    for column in OPERATIONAL_SETTING_COLUMNS + SENSOR_COLUMNS:
        if column == target_sensor:
            continue
        if df[column].nunique(dropna=True) > 1 and df[column].std() > 1e-9:
            feature_columns.append(column)
    return feature_columns


def _split_units_by_engine(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    units = np.array(sorted(df["unit_number"].unique()))
    rng = np.random.default_rng(RANDOM_STATE)
    rng.shuffle(units)
    split_index = int(len(units) * 0.8)
    return units[:split_index], units[split_index:]


def _calculate_fallback_status(confidence_score: pd.Series) -> pd.Series:
    return pd.cut(
        confidence_score,
        bins=[-0.01, 35, 55, 75, 100.01],
        labels=[
            "Fallback not recommended",
            "Inspection required",
            "Limited fallback",
            "Reliable fallback",
        ],
    ).astype(str)


def train_virtual_sensor(
    sensor_readings: pd.DataFrame | None = None,
    target_sensor: str = TARGET_SENSOR,
) -> VirtualSensorResult:
    if sensor_readings is None:
        sensor_readings = pd.read_parquet(SENSOR_READINGS_PATH)

    if target_sensor not in sensor_readings.columns:
        raise ValueError(f"Target sensor {target_sensor!r} not found in sensor readings.")

    feature_columns = _build_feature_columns(sensor_readings, target_sensor)
    if not feature_columns:
        raise ValueError("No usable feature columns available for virtual sensor training.")

    train_units, validation_units = _split_units_by_engine(sensor_readings)
    train_mask = sensor_readings["unit_number"].isin(train_units)
    validation_mask = sensor_readings["unit_number"].isin(validation_units)

    x_train = sensor_readings.loc[train_mask, feature_columns]
    y_train = sensor_readings.loc[train_mask, target_sensor]
    x_validation = sensor_readings.loc[validation_mask, feature_columns]
    y_validation = sensor_readings.loc[validation_mask, target_sensor]

    baseline = DummyRegressor(strategy="median")
    baseline.fit(x_train, y_train)
    baseline_pred = baseline.predict(x_validation)

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=14,
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    validation_pred = model.predict(x_validation)
    all_predictions = model.predict(sensor_readings[feature_columns])

    mae = float(mean_absolute_error(y_validation, validation_pred))
    typical_error = max(mae, 1e-6)

    predictions = sensor_readings[
        ["unit_number", "time_cycle", "remaining_useful_life", target_sensor]
    ].copy()
    predictions = predictions.rename(columns={target_sensor: "actual_value"})
    predictions["target_sensor"] = target_sensor
    predictions["predicted_value"] = all_predictions
    predictions["absolute_error"] = (
        predictions["actual_value"] - predictions["predicted_value"]
    ).abs()
    predictions["relative_error"] = predictions["absolute_error"] / predictions[
        "actual_value"
    ].abs().replace(0, np.nan)

    # Confidence is a decision-support signal, not a safety certificate. Exponential decay avoids
    # overreacting to small errors while still penalizing large deviations clearly.
    predictions["confidence_score"] = (
        100 * np.exp(-predictions["absolute_error"] / (2 * typical_error))
    ).clip(0, 100)
    predictions["fallback_status"] = _calculate_fallback_status(
        predictions["confidence_score"]
    )
    predictions["sensor_failure_simulated"] = True
    predictions["evaluation_split"] = np.where(
        predictions["unit_number"].isin(validation_units), "validation", "train"
    )

    metrics: dict[str, float | str | int] = {
        "target_sensor": target_sensor,
        "feature_count": len(feature_columns),
        "train_units": int(len(train_units)),
        "validation_units": int(len(validation_units)),
        "baseline_mae": float(mean_absolute_error(y_validation, baseline_pred)),
        "baseline_rmse": _rmse(y_validation, baseline_pred),
        "baseline_r2": float(r2_score(y_validation, baseline_pred)),
        "model_mae": mae,
        "model_rmse": _rmse(y_validation, validation_pred),
        "model_mape": _mape(y_validation, validation_pred),
        "model_r2": float(r2_score(y_validation, validation_pred)),
    }

    VIRTUAL_SENSOR_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    VIRTUAL_SENSOR_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "target_sensor": target_sensor,
            "feature_columns": feature_columns,
            "typical_error": typical_error,
        },
        VIRTUAL_SENSOR_MODEL_PATH,
    )
    predictions.to_parquet(VIRTUAL_SENSOR_PREDICTIONS_PATH, index=False)
    VIRTUAL_SENSOR_METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    LOGGER.info("Saved virtual sensor model to %s", VIRTUAL_SENSOR_MODEL_PATH)
    LOGGER.info("Saved virtual sensor predictions to %s", VIRTUAL_SENSOR_PREDICTIONS_PATH)
    return VirtualSensorResult(predictions=predictions, metrics=metrics)
