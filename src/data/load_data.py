"""Loading and basic cleaning of the raw Telco Customer Churn dataset."""

import logging

import pandas as pd

from src.config import RAW_DATA_PATH, TARGET_COLUMN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_raw_data(path=RAW_DATA_PATH) -> pd.DataFrame:
    """Load the raw CSV and apply minimal, deterministic cleaning.

    Cleaning performed:
    - ``TotalCharges`` is stored as a string with blank values for customers
      with 0 tenure; coerce to numeric and fill resulting NaNs with 0.
    - ``customerID`` is dropped (identifier, not a feature).
    - ``Churn`` is mapped from Yes/No to 1/0.
    """
    df = pd.read_csv(path)
    logger.info("Loaded raw data: %d rows, %d columns", *df.shape)

    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    n_missing = df["TotalCharges"].isna().sum()
    if n_missing:
        logger.info("Filling %d missing TotalCharges values with 0", n_missing)
    df["TotalCharges"] = df["TotalCharges"].fillna(0)

    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])

    df[TARGET_COLUMN] = df[TARGET_COLUMN].map({"Yes": 1, "No": 0})

    logger.info("Cleaned data: %d rows, %d columns", *df.shape)
    return df


if __name__ == "__main__":
    data = load_raw_data()
    print(data.head())
