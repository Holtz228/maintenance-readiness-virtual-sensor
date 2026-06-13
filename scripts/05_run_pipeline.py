from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.asset_health import run_asset_health_calculation
from src.data_prep import run_data_preparation
from src.recommendations import run_recommendation_generation
from src.virtual_sensor import train_virtual_sensor

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

if __name__ == "__main__":
    run_data_preparation()
    result = train_virtual_sensor()
    run_asset_health_calculation()
    run_recommendation_generation()

    print("\nPipeline completed.")
    print("Key model metrics:")
    for key in ["baseline_mae", "model_mae", "model_rmse", "model_r2"]:
        print(f"- {key}: {result.metrics[key]}")
