"""SageMaker Processing entry point: clean, encode, scale, split.

Runs inside an SKLearnProcessor container in the pipeline, but is also runnable
locally for testing:

    python pipeline/scripts/preprocess.py \
        --input-data data/raw/telco_churn.csv \
        --base-dir /tmp/churn-proc

Outputs train.csv / validation.csv / test.csv (target `Churn` as first column,
with header) under {base-dir}/{train,validation,test}/.
"""

import argparse
import logging
import os

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TARGET = "Churn"
ID_COLUMN = "customerID"
NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]
RANDOM_STATE = 42


def _resolve_input_csv(input_data: str) -> str:
    """Accept either a CSV file path or a directory containing one CSV."""
    if os.path.isdir(input_data):
        csvs = [f for f in os.listdir(input_data) if f.endswith(".csv")]
        if not csvs:
            raise FileNotFoundError(f"No CSV found in {input_data}")
        return os.path.join(input_data, csvs[0])
    return input_data


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Same deterministic cleaning as the local baseline."""
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
    if ID_COLUMN in df.columns:
        df = df.drop(columns=[ID_COLUMN])
    df[TARGET] = df[TARGET].map({"Yes": 1, "No": 0})
    return df


def build_features(train_df, val_df, test_df):
    """Fit encoders/scaler on TRAIN only, then apply to val/test (no leakage)."""
    y_train, y_val, y_test = train_df[TARGET], val_df[TARGET], test_df[TARGET]
    X_train = train_df.drop(columns=[TARGET])
    X_val = val_df.drop(columns=[TARGET])
    X_test = test_df.drop(columns=[TARGET])

    # One-hot encode categoricals, then align val/test to the train columns.
    X_train = pd.get_dummies(X_train, drop_first=True)
    X_val = pd.get_dummies(X_val, drop_first=True).reindex(columns=X_train.columns, fill_value=0)
    X_test = pd.get_dummies(X_test, drop_first=True).reindex(columns=X_train.columns, fill_value=0)

    # Scale numeric features with a scaler fit on the training set only.
    scaler = StandardScaler()
    X_train[NUMERIC_FEATURES] = scaler.fit_transform(X_train[NUMERIC_FEATURES])
    X_val[NUMERIC_FEATURES] = scaler.transform(X_val[NUMERIC_FEATURES])
    X_test[NUMERIC_FEATURES] = scaler.transform(X_test[NUMERIC_FEATURES])

    def reassemble(X, y):
        out = X.copy()
        out.insert(0, TARGET, y.values)
        return out

    return reassemble(X_train, y_train), reassemble(X_val, y_val), reassemble(X_test, y_test)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-data", default="/opt/ml/processing/input")
    parser.add_argument("--base-dir", default="/opt/ml/processing")
    args = parser.parse_args()

    csv_path = _resolve_input_csv(args.input_data)
    logger.info("Reading raw data from %s", csv_path)
    df = clean(pd.read_csv(csv_path))
    logger.info("Cleaned data: %d rows, %d columns", *df.shape)

    # Stratified 70 / 15 / 15 split.
    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=RANDOM_STATE, stratify=df[TARGET]
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=RANDOM_STATE, stratify=temp_df[TARGET]
    )

    train_out, val_out, test_out = build_features(train_df, val_df, test_df)

    for name, frame in [("train", train_out), ("validation", val_out), ("test", test_out)]:
        out_dir = os.path.join(args.base_dir, name)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{name}.csv")
        frame.to_csv(path, index=False)
        logger.info("Wrote %s (%d rows, %d cols)", path, frame.shape[0], frame.shape[1])


if __name__ == "__main__":
    main()
