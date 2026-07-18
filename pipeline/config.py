"""Centralized configuration for the SageMaker training pipeline."""

import os

# --- Naming ---
PIPELINE_NAME = os.environ.get("PIPELINE_NAME", "churn-training-pipeline")
MODEL_PACKAGE_GROUP = os.environ.get("MODEL_PACKAGE_GROUP", "churn-model-group")
BASE_JOB_PREFIX = "churn"

# --- SageMaker sklearn container version ---
FRAMEWORK_VERSION = "1.2-1"

# --- Instance types ---
PROCESSING_INSTANCE_TYPE = "ml.t3.medium"
TRAINING_INSTANCE_TYPE = "ml.m5.xlarge"

# --- Quality gate: register the model only if test ROC-AUC >= threshold ---
ROC_AUC_THRESHOLD = 0.75

# --- Serverless Inference ---
SERVERLESS_MEMORY_MB = 2048
SERVERLESS_MAX_CONCURRENCY = 5
