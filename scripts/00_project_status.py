from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    ASSET_HEALTH_PATH,
    MAINTENANCE_RECOMMENDATIONS_PATH,
    SENSOR_PROFILE_PATH,
    SENSOR_READINGS_PATH,
    TRAIN_RAW_PATH,
    VIRTUAL_SENSOR_METRICS_PATH,
    VIRTUAL_SENSOR_MODEL_PATH,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)

CHECKS = [
    ("Raw FD001 training file", TRAIN_RAW_PATH),
    ("Sensor readings", SENSOR_READINGS_PATH),
    ("Sensor profile", SENSOR_PROFILE_PATH),
    ("Virtual sensor model", VIRTUAL_SENSOR_MODEL_PATH),
    ("Virtual sensor predictions", VIRTUAL_SENSOR_PREDICTIONS_PATH),
    ("Virtual sensor metrics", VIRTUAL_SENSOR_METRICS_PATH),
    ("Asset health", ASSET_HEALTH_PATH),
    ("Maintenance recommendations", MAINTENANCE_RECOMMENDATIONS_PATH),
]


def main() -> None:
    print("\n=== Maintenance Readiness Project Status ===")

    for label, path in CHECKS:
        status = "OK" if path.exists() else "MISSING"
        relative_path = path.relative_to(PROJECT_ROOT)
        print(f"{status:8} | {label:32} | {relative_path}")


if __name__ == "__main__":
    main()