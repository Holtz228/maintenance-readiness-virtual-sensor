from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.virtual_sensor import train_virtual_sensor  # noqa: E402

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    result = train_virtual_sensor()

    print("\n=== Virtual Sensor Metrics ===")
    for key, value in result.metrics.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()