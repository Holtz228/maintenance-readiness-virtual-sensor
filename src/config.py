from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SCREENSHOTS_DIR = OUTPUTS_DIR / "screenshots"

TRAIN_RAW_PATH = RAW_DATA_DIR / "train_FD001.txt"
TEST_RAW_PATH = RAW_DATA_DIR / "test_FD001.txt"
RUL_RAW_PATH = RAW_DATA_DIR / "RUL_FD001.txt"

SENSOR_READINGS_PATH = PROCESSED_DATA_DIR / "sensor_readings.parquet"
SENSOR_PROFILE_PATH = PROCESSED_DATA_DIR / "sensor_profile.parquet"
VIRTUAL_SENSOR_PREDICTIONS_PATH = PROCESSED_DATA_DIR / "virtual_sensor_predictions.parquet"
VIRTUAL_SENSOR_METRICS_PATH = PROCESSED_DATA_DIR / "virtual_sensor_metrics.json"
ASSET_HEALTH_PATH = PROCESSED_DATA_DIR / "asset_health.parquet"
MAINTENANCE_RECOMMENDATIONS_PATH = PROCESSED_DATA_DIR / "maintenance_recommendations.parquet"

VIRTUAL_SENSOR_MODEL_PATH = MODELS_DIR / "virtual_sensor_model.pkl"

ID_COLUMNS = ["unit_number", "time_cycle"]

OPERATIONAL_SETTING_COLUMNS = [
    "operational_setting_1",
    "operational_setting_2",
    "operational_setting_3",
]

SENSOR_COLUMNS = [f"sensor_{sensor_id}" for sensor_id in range(1, 22)]

CMAPSS_COLUMNS = ID_COLUMNS + OPERATIONAL_SETTING_COLUMNS + SENSOR_COLUMNS

TARGET_SENSOR = "sensor_11"
RANDOM_STATE = 42

# The NASA training data runs assets to failure. Capping RUL risk keeps the score
# useful for maintenance prioritization instead of turning it into a false failure timer.
RUL_RISK_CAP_CYCLES = 120

# Higher scores mean higher maintenance attention, not better asset condition.
# The weighting reflects the MVP logic: RUL drives urgency, deviation and confidence
# qualify the virtual-sensor signal, and trend risk adds short-term movement.
ASSET_HEALTH_WEIGHTS = {
    "rul_risk_score": 0.45,
    "sensor_deviation_score": 0.25,
    "virtual_sensor_confidence_risk": 0.20,
    "trend_risk_score": 0.10,
}

# Maintenance priority reuses the health score but keeps direct sensor deviation
# and RUL risk visible for action ranking in the recommendation layer.
MAINTENANCE_PRIORITY_WEIGHTS = {
    "asset_health_score": 0.50,
    "sensor_deviation_score": 0.30,
    "rul_risk_score": 0.20,
}