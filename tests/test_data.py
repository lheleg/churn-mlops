"""Basic validation tests for the raw data loading pipeline."""

from src.config import TARGET_COLUMN
from src.data.load_data import load_raw_data

EXPECTED_COLUMNS = {
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
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
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
}


def test_expected_columns_present():
    df = load_raw_data()
    assert EXPECTED_COLUMNS.issubset(set(df.columns))


def test_no_missing_values_after_cleaning():
    df = load_raw_data()
    assert df.isna().sum().sum() == 0


def test_target_is_binary():
    df = load_raw_data()
    assert set(df[TARGET_COLUMN].unique()) == {0, 1}
