"""Centralized configuration: paths and parameters."""

from pathlib import Path

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"
REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RAW_DATA_PATH = DATA_RAW_DIR / "telco_churn.csv"
TRAIN_DATA_PATH = DATA_PROCESSED_DIR / "train.csv"
TEST_DATA_PATH = DATA_PROCESSED_DIR / "test.csv"

LOGISTIC_REGRESSION_PATH = MODELS_DIR / "logistic_regression.pkl"
RANDOM_FOREST_PATH = MODELS_DIR / "random_forest.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"

METRICS_PATH = REPORTS_DIR / "metrics.json"
CONFUSION_MATRIX_PATH = FIGURES_DIR / "confusion_matrix_{model_name}.png"

# --- Data schema ---
TARGET_COLUMN = "Churn"
ID_COLUMN = "customerID"

NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL_FEATURES = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
]

# --- Reproducibility ---
RANDOM_STATE = 42

# --- Train/test split ---
TEST_SIZE = 0.2
