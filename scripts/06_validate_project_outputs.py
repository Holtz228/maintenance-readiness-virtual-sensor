from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEARCH_ROOTS = [
    PROJECT_ROOT / "data" / "processed",
    PROJECT_ROOT / "data" / "output",
    PROJECT_ROOT / "outputs",
    PROJECT_ROOT / "output",
]


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    patterns: list[str]
    required_columns: list[str]
    score_columns: list[str]


DATASET_SPECS = [
    DatasetSpec(
        name="sensor_readings",
        patterns=[
            "*sensor_readings*.parquet",
            "*sensor_readings*.csv",
            "*readings*.parquet",
            "*readings*.csv",
        ],
        required_columns=[
            "unit_number",
            "time_cycle",
        ],
        score_columns=[],
    ),
    DatasetSpec(
        name="sensor_profile",
        patterns=[
            "*sensor_profile*.parquet",
            "*sensor_profile*.csv",
            "*profile*.parquet",
            "*profile*.csv",
        ],
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
        patterns=[
            "*prediction*.parquet",
            "*prediction*.csv",
            "*virtual_sensor*.parquet",
            "*virtual_sensor*.csv",
        ],
        required_columns=[
            "unit_number",
            "time_cycle",
            "actual_value",
            "predicted_value",
            "absolute_error",
            "confidence_score",
            "fallback_status",
            "evaluation_split",
        ],
        score_columns=[
            "confidence_score",
        ],
    ),
    DatasetSpec(
        name="asset_health",
        patterns=[
            "*asset_health*.parquet",
            "*asset_health*.csv",
            "*health*.parquet",
            "*health*.csv",
        ],
        required_columns=[
            "asset_id",
            "estimated_rul",
            "asset_health_score",
            "readiness_tier",
            "maintenance_priority",
        ],
        score_columns=[
            "asset_health_score",
            "maintenance_priority",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
            "virtual_sensor_confidence_risk",
            "trend_risk_score",
            "rul_risk_score",
        ],
    ),
    DatasetSpec(
        name="recommendations",
        patterns=[
            "*recommendation*.parquet",
            "*recommendation*.csv",
            "*maintenance_action*.parquet",
            "*maintenance_action*.csv",
        ],
        required_columns=[
            "asset_id",
            "recommended_action",
            "priority_score",
            "readiness_tier",
            "estimated_rul",
        ],
        score_columns=[
            "priority_score",
            "asset_health_score",
            "sensor_deviation_score",
            "virtual_sensor_confidence",
        ],
    ),
]


METRICS_PATTERNS = [
    "*metrics*.json",
    "*model_quality*.json",
    "*model_metrics*.json",
]


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


def existing_search_roots() -> list[Path]:
    return [path for path in SEARCH_ROOTS if path.exists()]


def find_latest_file(patterns: list[str]) -> Path | None:
    candidates: list[Path] = []

    for root in existing_search_roots():
        for pattern in patterns:
            candidates.extend(root.rglob(pattern))

    candidates = [
        path
        for path in candidates
        if path.is_file() and path.suffix.lower() in {".parquet", ".csv", ".json"}
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


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
) -> Path | None:
    path = find_latest_file(spec.patterns)

    if path is None:
        reporter.error(
            f"{spec.name}: expected output file not found. "
            f"Checked patterns: {', '.join(spec.patterns)}"
        )
        return None

    relative_path = path.relative_to(PROJECT_ROOT)
    reporter.ok(f"{spec.name}: found {relative_path}")

    return path


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
        column
        for column in required_columns
        if column not in df.columns
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
    for column in required_columns:
        if column not in df.columns:
            continue

        if df[column].isna().all():
            reporter.error(f"{dataset_name}: required column '{column}' is fully empty.")


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
            reporter.warn(
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
        reporter.ok(f"{dataset_name}: {checked_columns} score columns are within 0-100.")


def validate_recommendations(
    recommendations: pd.DataFrame,
    reporter: ValidationReporter,
) -> None:
    if recommendations.empty:
        reporter.error("recommendations: no maintenance recommendations available.")
        return

    if "recommended_action" in recommendations.columns:
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

    if "priority_score" in recommendations.columns:
        top_priority = pd.to_numeric(
            recommendations["priority_score"],
            errors="coerce",
        ).max()

        if pd.isna(top_priority):
            reporter.error("recommendations: priority_score contains no numeric values.")
        else:
            reporter.ok(f"recommendations: highest priority score is {top_priority:.1f}.")


def validate_predictions(
    predictions: pd.DataFrame,
    reporter: ValidationReporter,
) -> None:
    if predictions.empty:
        reporter.error("predictions: no prediction records available.")
        return

    if "evaluation_split" in predictions.columns:
        split_counts = predictions["evaluation_split"].value_counts().to_dict()

        if "validation" not in split_counts:
            reporter.warn("predictions: no validation split found.")
        else:
            reporter.ok(
                f"predictions: validation split contains {split_counts['validation']:,} rows."
            )

    if "fallback_status" in predictions.columns:
        status_counts = predictions["fallback_status"].value_counts().to_dict()

        if not status_counts:
            reporter.error("predictions: fallback_status has no values.")
        else:
            reporter.ok(
                "predictions: fallback statuses found: "
                + ", ".join(f"{key}={value:,}" for key, value in status_counts.items())
            )

    if "absolute_error" in predictions.columns:
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

    if "readiness_tier" in asset_health.columns:
        tier_counts = asset_health["readiness_tier"].value_counts().to_dict()

        if not tier_counts:
            reporter.error("asset_health: readiness_tier has no values.")
        else:
            reporter.ok(
                "asset_health: readiness tiers found: "
                + ", ".join(f"{key}={value:,}" for key, value in tier_counts.items())
            )

    if "asset_id" in asset_health.columns:
        asset_count = int(asset_health["asset_id"].nunique())
        reporter.ok(f"asset_health: contains {asset_count:,} unique assets.")


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
    metrics_path = find_latest_file(METRICS_PATTERNS)

    if metrics_path is None:
        reporter.warn(
            "metrics: no metrics JSON file found. "
            "This is acceptable if metrics are generated in memory, but a saved metrics file is better for reproducibility."
        )
        return

    try:
        metrics = read_json(metrics_path)
    except Exception as exc:
        reporter.error(f"metrics: could not read metrics file: {exc}")
        return

    relative_path = metrics_path.relative_to(PROJECT_ROOT)
    reporter.ok(f"metrics: found {relative_path}")

    expected_keys = [
        "target_sensor",
        "model_mae",
        "model_r2",
    ]

    missing_keys = [
        key
        for key in expected_keys
        if key not in metrics
    ]

    if missing_keys:
        reporter.warn(
            "metrics: missing recommended keys: "
            + ", ".join(missing_keys)
        )
    else:
        reporter.ok("metrics: required model quality keys are present.")

    for key in ["model_mae", "model_rmse", "baseline_mae", "baseline_rmse"]:
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
    path = validate_file_exists(spec, reporter)

    if path is None:
        return None

    try:
        df = read_table(path)
    except Exception as exc:
        reporter.error(f"{spec.name}: could not read file '{path.name}': {exc}")
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

    if not existing_search_roots():
        reporter.error(
            "No output folders found. Expected one of: "
            + ", ".join(str(path.relative_to(PROJECT_ROOT)) for path in SEARCH_ROOTS)
        )
        reporter.print_summary()
        return 1

    loaded_datasets: dict[str, pd.DataFrame] = {}

    for spec in DATASET_SPECS:
        df = validate_dataset(spec, reporter)

        if df is not None:
            loaded_datasets[spec.name] = df

    if "asset_health" in loaded_datasets:
        validate_asset_health(loaded_datasets["asset_health"], reporter)

    if "recommendations" in loaded_datasets:
        validate_recommendations(loaded_datasets["recommendations"], reporter)

    if "predictions" in loaded_datasets:
        validate_predictions(loaded_datasets["predictions"], reporter)

    validate_dashboard_core_data(loaded_datasets, reporter)
    validate_metrics(reporter)

    reporter.print_summary()

    return 1 if reporter.errors else 0


if __name__ == "__main__":
    sys.exit(main())