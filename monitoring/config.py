"""Configuration for model/data monitoring (SageMaker Model Monitor + local drift)."""

import os

# --- SageMaker Model Monitor ---
MONITOR_INSTANCE_TYPE = "ml.m5.large"
MONITOR_VOLUME_GB = 20
MONITOR_MAX_RUNTIME_S = 1800
MONITOR_SCHEDULE_NAME = os.environ.get("MONITOR_SCHEDULE_NAME", "churn-data-quality-schedule")

# --- PSI drift thresholds (Population Stability Index, industry convention) ---
# < 0.10 : no significant shift
# 0.10 - 0.25 : moderate shift, worth watching
# >= 0.25 : significant shift -> treat as drift
PSI_MODERATE = 0.10
PSI_SIGNIFICANT = 0.25

TARGET = "Churn"
