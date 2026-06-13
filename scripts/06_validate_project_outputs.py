from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    ASSET_HEALTH_PATH,
    MAINTENANCE_RECOMMENDATIONS_PATH,
    SENSOR_PROFILE_PATH,
    SENSOR_READINGS_PATH,
    VIRTUAL_SENSOR_METRICS_PATH,
    VIRTUAL_SENSOR_MODEL_PATH,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    path: Path
    required_columns: list[str]
    score_columns: list[str]


DATASET_SPECS = [
    DatasetSpec(
        name="sensor_readings",
        path=SENSOR_READINGS_PATH,
        required_columns=[
            "unit_number",
            "time_cycle",
            "remaining_useful_life",
            "max_cycle",
        ],
        score_columns=[],
    ),
    DatasetSpec(
        name="sensor_profile",
        path=SENSOR_PROFILE_PATH,
        required_columns=[
            "sensor",
            "missing_rate",
            "std",
            "unique_value_count",
            "correlation_with_rul",
            "usable_for_virtual_sensor",
        ],
        score_columns=[
            "missing_rate",
        ],
    ),
    DatasetSpec(
        name="predictions",
        path=VIRTUAL_SENSOR_PREDICTIONS_PATH,
        required_columns=[
            "unit_number",
            "time_cycle",
            "actual_value",
            "predicted_value",
            "absolute_error",
            "relative_error",
            "confidence_score",
            "fallback_status",
            "sensor_failure_simulated",
            "evaluation_split",
        ],
        score_columns=[
            "confidence_score",
        ],
    ),
    DatasetSpec(
        name="asset_health",
        path=ASSET_HEALTH_PATH,
        required_columns=[
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
        ],
        score_columns=[
            "rul_risk_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
            "virtual_sensor_confidence_risk",
            "trend_risk_score",
            "asset_health_score",
            "maintenance_priority",
        ],
    ),
    DatasetSpec(
        name="recommendations",
        path=MAINTENANCE_RECOMMENDATIONS_PATH,
        required_columns=[
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
        ],
        score_columns=[
            "priority_score",
            "asset_health_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
        ],
    ),
]

EXPECTED_READINESS_TIERS = {
    "Ready",
    "Monitor",
    "Maintenance Planned",
    "Critical",
}

EXPECTED_FALLBACK_STATUSES = {
    "Reliable fallback",
    "Limited fallback",
    "Inspection required",
    "Fallback not recommended",
}

EXPECTED_RECOMMENDED_ACTIONS = {
    "Schedule maintenance",
    "Replace sensor",
    "Inspect sensor",
    "Review asset before next production window",
    "Continue limited monitoring",
    "No immediate action",
}


class ValidationReporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []

    def ok(self, message: str) -> None:
        self.passed.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def print_summary(self) -> None:
        print("\n=== Project Output Validation Summary ===")

        status = "FAILED" if self.errors else "PASSED"
        print(f"Status: {status}\n")

        if self.passed:
            print("Passed checks:")
            for message in self.passed:
                print(f"  [OK] {message}")

        if self.warnings:
            print("\nWarnings:")
            for message in self.warnings:
                print(f"  [WARN] {message}")

        if self.errors:
            print("\nErrors:")
            for message in self.errors:
                print(f"  [ERROR] {message}")

        print("\nValidation result:")
        print(f"  Passed:   {len(self.passed)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Errors:   {len(self.errors)}")


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported table format: {path.suffix}")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Metrics JSON must contain a JSON object.")

    return payload


def validate_file_exists(
    spec: DatasetSpec,
    reporter: ValidationReporter,
) -> bool:
    if not spec.path.exists():
        reporter.error(
            f"{spec.name}: expected output file not found: "
            f"{spec.path.relative_to(PROJECT_ROOT)}"
        )
        return False

    reporter.ok(f"{spec.name}: found {spec.path.relative_to(PROJECT_ROOT)}")
    return True


def validate_model_file(reporter: ValidationReporter) -> None:
    if not VIRTUAL_SENSOR_MODEL_PATH.exists():
        reporter.error(
            "model: expected virtual sensor model not found: "
            f"{VIRTUAL_SENSOR_MODEL_PATH.relative_to(PROJECT_ROOT)}"
        )
        return

    reporter.ok(
        "model: found "
        f"{VIRTUAL_SENSOR_MODEL_PATH.relative_to(PROJECT_ROOT)}"
    )


def validate_non_empty(
    dataset_name: str,
    df: pd.DataFrame,
    reporter: ValidationReporter,
) -> None:
    if df.empty:
        reporter.error(f"{dataset_name}: dataset is empty.")
        return

    reporter.ok(f"{dataset_name}: contains {len(df):,} rows.")


def validate_required_columns(
    dataset_name: str,
    df: pd.DataFrame,
    required_columns: list[str],
    reporter: ValidationReporter,
) -> None:
    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        reporter.error(
            f"{dataset_name}: missing required columns: "
            f"{', '.join(missing_columns)}"
        )
        return

    reporter.ok(f"{dataset_name}: all required columns are present.")


def validate_no_fully_empty_required_columns(
    dataset_name: str,
    df: pd.DataFrame,
    required_columns: list[str],
    reporter: ValidationReporter,
) -> None:
    empty_columns = [
        column
        for column in required_columns
        if column in df.columns and df[column].isna().all()
    ]

    if empty_columns:
        reporter.error(
            f"{dataset_name}: required columns are fully empty: "
            f"{', '.join(empty_columns)}"
        )
        return

    reporter.ok(f"{dataset_name}: required columns are not fully empty.")


def validate_score_ranges(
    dataset_name: str,
    df: pd.DataFrame,
    score_columns: list[str],
    reporter: ValidationReporter,
) -> None:
    checked_columns = 0

    for column in score_columns:
        if column not in df.columns:
            continue

        numeric_values = pd.to_numeric(df[column], errors="coerce")
        non_null_values = numeric_values.dropna()

        if non_null_values.empty:
            reporter.error(
                f"{dataset_name}: score column '{column}' has no numeric values."
            )
            continue

        below_zero = int((non_null_values < 0).sum())
        above_hundred = int((non_null_values > 100).sum())

        if below_zero or above_hundred:
            reporter.error(
                f"{dataset_name}: score column '{column}' contains values outside 0-100 "
                f"({below_zero} below 0, {above_hundred} above 100)."
            )
        else:
            checked_columns += 1

    if checked_columns:
        reporter.ok(
            f"{dataset_name}: {checked_columns} score columns are within 0-100."
        )


def validate_allowed_values(
    dataset_name: str,
    df: pd.DataFrame,
    column: str,
    allowed_values: set[str],
    reporter: ValidationReporter,
) -> None:
    if column not in df.columns:
        return

    observed_values = set(df[column].dropna().astype(str).unique())
    unexpected_values = observed_values - allowed_values

    if unexpected_values:
        reporter.error(
            f"{dataset_name}: unexpected values in '{column}': "
            f"{', '.join(sorted(unexpected_values))}"
        )
        return

    reporter.ok(f"{dataset_name}: '{column}' values are valid.")


def validate_predictions(
    predictions: pd.DataFrame,
    reporter: ValidationReporter,
) -> None:
    if predictions.empty:
        reporter.error("predictions: no prediction records available.")
        return

    split_counts = predictions["evaluation_split"].value_counts().to_dict()

    if "validation" not in split_counts:
        reporter.error("predictions: no validation split found.")
    else:
        reporter.ok(
            f"predictions: validation split contains "
            f"{split_counts['validation']:,} rows."
        )

    status_counts = predictions["fallback_status"].value_counts().to_dict()
    reporter.ok(
        "predictions: fallback statuses found: "
        + ", ".join(f"{key}={value:,}" for key, value in status_counts.items())
    )

    absolute_error = pd.to_numeric(predictions["absolute_error"], errors="coerce")
    if absolute_error.dropna().empty:
        reporter.error("predictions: absolute_error contains no numeric values.")
    else:
        reporter.ok(
            f"predictions: average absolute error is {absolute_error.mean():.4f}."
        )


def validate_asset_health(
    asset_health: pd.DataFrame,
    reporter: ValidationReporter,
) -> None:
    if asset_health.empty:
        reporter.error("asset_health: no asset health records available.")
        return

    tier_counts = asset_health["readiness_tier"].value_counts().to_dict()
    reporter.ok(
        "asset_health: readiness tiers found: "
        + ", ".join(f"{key}={value:,}" for key, value in tier_counts.items())
    )

    asset_count = int(asset_health["asset_id"].nunique())
    reporter.ok(f"asset_health: contains {asset_count:,} unique assets.")


def validate_recommendations(
    recommendations: pd.DataFrame,
    reporter: ValidationReporter,
) -> None:
    if recommendations.empty:
        reporter.error("recommendations: no maintenance recommendations available.")
        return

    actionable = recommendations[
        recommendations["recommended_action"].astype(str) != "No immediate action"
    ]

    if actionable.empty:
        reporter.warn(
            "recommendations: dataset exists, but no actionable recommendation was found."
        )
    else:
        reporter.ok(
            f"recommendations: {len(actionable):,} actionable recommendations found."
        )

    priority_score = pd.to_numeric(
        recommendations["priority_score"],
        errors="coerce",
    )

    if priority_score.dropna().empty:
        reporter.error("recommendations: priority_score contains no numeric values.")
    else:
        reporter.ok(
            f"recommendations: highest priority score is {priority_score.max():.1f}."
        )


def validate_dashboard_core_data(
    loaded_datasets: dict[str, pd.DataFrame],
    reporter: ValidationReporter,
) -> None:
    required_dashboard_inputs = {
        "Executive Overview": ["asset_health", "recommendations"],
        "Asset Health": ["asset_health"],
        "Virtual Sensor Monitor": ["predictions"],
        "Maintenance Planner": ["recommendations"],
        "Data & Model Quality": ["sensor_profile", "predictions"],
    }

    for page_name, dataset_names in required_dashboard_inputs.items():
        missing_or_empty = [
            dataset_name
            for dataset_name in dataset_names
            if dataset_name not in loaded_datasets or loaded_datasets[dataset_name].empty
        ]

        if missing_or_empty:
            reporter.error(
                f"{page_name}: missing or empty dashboard inputs: "
                f"{', '.join(missing_or_empty)}"
            )
        else:
            reporter.ok(f"{page_name}: dashboard core data is available.")


def validate_metrics(reporter: ValidationReporter) -> None:
    if not VIRTUAL_SENSOR_METRICS_PATH.exists():
        reporter.error(
            "metrics: expected metrics JSON not found: "
            f"{VIRTUAL_SENSOR_METRICS_PATH.relative_to(PROJECT_ROOT)}"
        )
        return

    try:
        metrics = read_json(VIRTUAL_SENSOR_METRICS_PATH)
    except Exception as exc:
        reporter.error(f"metrics: could not read metrics file: {exc}")
        return

    reporter.ok(
        "metrics: found "
        f"{VIRTUAL_SENSOR_METRICS_PATH.relative_to(PROJECT_ROOT)}"
    )

    expected_keys = [
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
    ]

    missing_keys = [key for key in expected_keys if key not in metrics]
    if missing_keys:
        reporter.error(
            "metrics: missing required keys: "
            + ", ".join(missing_keys)
        )
    else:
        reporter.ok("metrics: required model quality keys are present.")

    for key in ["model_mae", "model_rmse", "model_mape", "baseline_mae", "baseline_rmse"]:
        if key not in metrics:
            continue

        value = pd.to_numeric(pd.Series([metrics[key]]), errors="coerce").iloc[0]

        if pd.isna(value):
            reporter.error(f"metrics: '{key}' is not numeric.")
        elif value < 0:
            reporter.error(f"metrics: '{key}' is negative.")
        else:
            reporter.ok(f"metrics: '{key}' is valid.")

    for key in ["model_r2", "baseline_r2"]:
        if key not in metrics:
            continue

        value = pd.to_numeric(pd.Series([metrics[key]]), errors="coerce").iloc[0]

        if pd.isna(value):
            reporter.error(f"metrics: '{key}' is not numeric.")
        else:
            reporter.ok(f"metrics: '{key}' is valid.")


def validate_dataset(
    spec: DatasetSpec,
    reporter: ValidationReporter,
) -> pd.DataFrame | None:
    if not validate_file_exists(spec, reporter):
        return None

    try:
        df = read_table(spec.path)
    except Exception as exc:
        reporter.error(f"{spec.name}: could not read file '{spec.path.name}': {exc}")
        return None

    validate_non_empty(spec.name, df, reporter)
    validate_required_columns(spec.name, df, spec.required_columns, reporter)
    validate_no_fully_empty_required_columns(
        spec.name,
        df,
        spec.required_columns,
        reporter,
    )
    validate_score_ranges(spec.name, df, spec.score_columns, reporter)

    return df


def main() -> int:
    reporter = ValidationReporter()
    loaded_datasets: dict[str, pd.DataFrame] = {}

    validate_model_file(reporter)

    for spec in DATASET_SPECS:
        df = validate_dataset(spec, reporter)

        if df is not None:
            loaded_datasets[spec.name] = df

    if "predictions" in loaded_datasets:
        validate_allowed_values(
            "predictions",
            loaded_datasets["predictions"],
            "fallback_status",
            EXPECTED_FALLBACK_STATUSES,
            reporter,
        )
        validate_predictions(loaded_datasets["predictions"], reporter)

    if "asset_health" in loaded_datasets:
        validate_allowed_values(
            "asset_health",
            loaded_datasets["asset_health"],
            "readiness_tier",
            EXPECTED_READINESS_TIERS,
            reporter,
        )
        validate_allowed_values(
            "asset_health",
            loaded_datasets["asset_health"],
            "fallback_status",
            EXPECTED_FALLBACK_STATUSES,
            reporter,
        )
        validate_asset_health(loaded_datasets["asset_health"], reporter)

    if "recommendations" in loaded_datasets:
        validate_allowed_values(
            "recommendations",
            loaded_datasets["recommendations"],
            "readiness_tier",
            EXPECTED_READINESS_TIERS,
            reporter,
        )
        validate_allowed_values(
            "recommendations",
            loaded_datasets["recommendations"],
            "recommended_action",
            EXPECTED_RECOMMENDED_ACTIONS,
            reporter,
        )
        validate_recommendations(loaded_datasets["recommendations"], reporter)

    validate_dashboard_core_data(loaded_datasets, reporter)
    validate_metrics(reporter)

    reporter.print_summary()

    return 1 if reporter.errors else 0


if __name__ == "__main__":
    sys.exit(main())