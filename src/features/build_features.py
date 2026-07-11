"""Feature engineering: train/test split, encoding, and scaling."""

import logging

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.config import (
    CATEGORICAL_FEATURES,
    DATA_PROCESSED_DIR,
    MODELS_DIR,
    NUMERIC_FEATURES,
    RANDOM_STATE,
    SCALER_PATH,
    TARGET_COLUMN,
    TEST_DATA_PATH,
    TEST_SIZE,
    TRAIN_DATA_PATH,
)
from src.data.load_data import load_raw_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def split_raw(df: pd.DataFrame):
    """Stratified train/test split on the cleaned, pre-encoding data."""
    return train_test_split(
        df, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=df[TARGET_COLUMN]
    )


def build_features(train_df: pd.DataFrame, test_df: pd.DataFrame):
    """One-hot encode and scale, fitting exclusively on the training set."""
    train_df = pd.get_dummies(train_df, columns=CATEGORICAL_FEATURES, drop_first=True)
    test_df = pd.get_dummies(test_df, columns=CATEGORICAL_FEATURES, drop_first=True)
    test_df = test_df.reindex(columns=train_df.columns, fill_value=0)

    scaler = StandardScaler()
    train_df[NUMERIC_FEATURES] = scaler.fit_transform(train_df[NUMERIC_FEATURES])
    test_df[NUMERIC_FEATURES] = scaler.transform(test_df[NUMERIC_FEATURES])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, SCALER_PATH)
    logger.info("Saved fitted scaler to %s", SCALER_PATH)

    return train_df, test_df


def save(train_df: pd.DataFrame, test_df: pd.DataFrame):
    """Persist the featurized train/test sets to data/processed/."""
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(TRAIN_DATA_PATH, index=False)
    test_df.to_csv(TEST_DATA_PATH, index=False)

    logger.info("Saved train set: %s (%d rows)", TRAIN_DATA_PATH, len(train_df))
    logger.info("Saved test set: %s (%d rows)", TEST_DATA_PATH, len(test_df))


if __name__ == "__main__":
    raw_df = load_raw_data()
    train_raw, test_raw = split_raw(raw_df)
    train_featurized, test_featurized = build_features(train_raw, test_raw)
    save(train_featurized, test_featurized)
