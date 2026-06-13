from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    CMAPSS_COLUMNS,
    OPERATIONAL_SETTING_COLUMNS,
    PROCESSED_DATA_DIR,
    SENSOR_COLUMNS,
    SENSOR_PROFILE_PATH,
    SENSOR_READINGS_PATH,
    TRAIN_RAW_PATH,
)

LOGGER = logging.getLogger(__name__)


def ensure_project_directories() -> None:
    """Create output directories used by the local MVP pipeline."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_cmapss_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {path}. Place train_FD001.txt in data/raw first."
        )

    df = pd.read_csv(path, sep=r"\s+", header=None, names=CMAPSS_COLUMNS)

    expected_columns = len(CMAPSS_COLUMNS)
    if df.shape[1] != expected_columns:
        raise ValueError(
            f"Expected {expected_columns} columns for C-MAPSS FD001, got {df.shape[1]}."
        )

    return df


def add_remaining_useful_life(train_df: pd.DataFrame) -> pd.DataFrame:
    df = train_df.copy()
    max_cycles = df.groupby("unit_number")["time_cycle"].max().rename("max_cycle")
    df = df.merge(max_cycles, on="unit_number", how="left")
    df["remaining_useful_life"] = df["max_cycle"] - df["time_cycle"]
    return df


def build_sensor_profile(sensor_readings: pd.DataFrame) -> pd.DataFrame:
    profile_rows: list[dict[str, object]] = []

    for sensor in SENSOR_COLUMNS:
        values = sensor_readings[sensor]
        missing_rate = float(values.isna().mean())
        std = float(values.std())
        unique_value_count = int(values.nunique(dropna=True))

        if std <= 1e-9 or unique_value_count <= 1:
            correlation_with_rul = np.nan
        else:
            correlation_with_rul = float(values.corr(sensor_readings["remaining_useful_life"]))

        # A virtual sensor only makes sense if the target signal actually varies.
        # Constant or quasi-constant sensors would create impressive-looking but useless metrics.
        usable_for_virtual_sensor = (
            missing_rate <= 0.01
            and std > 1e-6
            and unique_value_count >= 20
            and not np.isnan(correlation_with_rul)
        )

        profile_rows.append(
            {
                "sensor": sensor,
                "missing_rate": missing_rate,
                "std": std,
                "unique_value_count": unique_value_count,
                "correlation_with_rul": correlation_with_rul,
                "usable_for_virtual_sensor": usable_for_virtual_sensor,
            }
        )

    profile = pd.DataFrame(profile_rows)
    profile["abs_correlation_with_rul"] = profile["correlation_with_rul"].abs()
    return profile.sort_values(
        ["usable_for_virtual_sensor", "abs_correlation_with_rul"],
        ascending=[False, False],
    ).reset_index(drop=True)


def prepare_sensor_readings(raw_train_path: Path = TRAIN_RAW_PATH) -> pd.DataFrame:
    LOGGER.info("Loading NASA C-MAPSS FD001 training data from %s", raw_train_path)
    train_df = load_cmapss_file(raw_train_path)
    train_df = add_remaining_useful_life(train_df)

    numeric_columns = OPERATIONAL_SETTING_COLUMNS + SENSOR_COLUMNS + [
        "max_cycle",
        "remaining_useful_life",
    ]
    train_df[numeric_columns] = train_df[numeric_columns].apply(pd.to_numeric, errors="raise")
    train_df[["unit_number", "time_cycle"]] = train_df[["unit_number", "time_cycle"]].astype(int)
    return train_df


def run_data_preparation() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_project_directories()
    sensor_readings = prepare_sensor_readings()
    sensor_profile = build_sensor_profile(sensor_readings)

    sensor_readings.to_parquet(SENSOR_READINGS_PATH, index=False)
    sensor_profile.to_parquet(SENSOR_PROFILE_PATH, index=False)

    LOGGER.info("Saved sensor readings to %s", SENSOR_READINGS_PATH)
    LOGGER.info("Saved sensor profile to %s", SENSOR_PROFILE_PATH)
    return sensor_readings, sensor_profile
