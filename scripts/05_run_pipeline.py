from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.asset_health import run_asset_health_calculation  # noqa: E402

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    asset_health = run_asset_health_calculation()

    print("\nAsset health calculation completed.")
    print(f"- Assets scored: {len(asset_health):,}")
    print("\nTop 10 assets by maintenance priority:")
    print(asset_health.head(10).to_string(index=False))


if __name__ == "__main__":
    main()