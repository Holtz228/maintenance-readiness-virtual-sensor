from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_prep import run_data_preparation  # noqa: E402

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    sensor_readings, sensor_profile = run_data_preparation()

    print("\nData preparation completed.")
    print(f"- Sensor readings: {len(sensor_readings):,} rows")
    print(f"- Sensor profile:   {len(sensor_profile):,} sensors")


if __name__ == "__main__":
    main()