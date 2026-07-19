"""SageMaker script-mode training entry point.

Training: reads the `train` and `validation` channels, trains Logistic
Regression and Random Forest, selects the best by validation ROC-AUC, and saves
it to SM_MODEL_DIR as model.joblib (+ feature_columns.json for inference).

Runnable locally for testing:

    python pipeline/scripts/train.py \
        --train /tmp/churn-proc/train --validation /tmp/churn-proc/validation \
        --model-dir /tmp/churn-model
"""

import argparse
import json
import logging
import os

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TARGET = "Churn"
RANDOM_STATE = 42

# Raw feature groups.
NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL_FEATURES = [
    "gender",
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


def _build_preprocessor() -> ColumnTransformer:
    """Scale numerics, one-hot categoricals; everything else passes through.

    `handle_unknown="ignore"` makes the encoder robust to categories unseen at
    fit time, so a serving request with a novel value degrades gracefully
    instead of erroring.
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="passthrough",
    )


def _load_channel(channel_dir: str) -> pd.DataFrame:
    csvs = [f for f in os.listdir(channel_dir) if f.endswith(".csv")]
    if not csvs:
        raise FileNotFoundError(f"No CSV in channel {channel_dir}")
    return pd.read_csv(os.path.join(channel_dir, csvs[0]))


def train(args):
    train_df = _load_channel(args.train)
    val_df = _load_channel(args.validation)

    X_train, y_train = train_df.drop(columns=[TARGET]), train_df[TARGET]
    X_val, y_val = val_df.drop(columns=[TARGET]), val_df[TARGET]

    candidates = {
        "logistic_regression": LogisticRegression(
            C=args.C, random_state=RANDOM_STATE, max_iter=1000
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=args.n_estimators, max_depth=args.max_depth, random_state=RANDOM_STATE
        ),
    }

    # Each candidate is a full Pipeline: the same fitted preprocessor that
    # trains the model also serves it, so the saved artifact takes raw records
    # and training/serving skew is impossible by construction. Fitting only on
    # the train channel preserves the leakage-safe property from preprocessing.
    best_name, best_model, best_auc = None, None, -1.0
    for name, est in candidates.items():
        model = Pipeline([("prep", _build_preprocessor()), ("clf", est)])
        model.fit(X_train, y_train)
        auc = roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])
        logger.info("%s validation ROC-AUC: %.4f", name, auc)
        if auc > best_auc:
            best_name, best_model, best_auc = name, model, auc

    logger.info("Selected best model: %s (ROC-AUC=%.4f)", best_name, best_auc)

    os.makedirs(args.model_dir, exist_ok=True)
    joblib.dump(best_model, os.path.join(args.model_dir, "model.joblib"))
    with open(os.path.join(args.model_dir, "feature_columns.json"), "w") as f:
        json.dump(list(X_train.columns), f)
    with open(os.path.join(args.model_dir, "training_meta.json"), "w") as f:
        json.dump({"best_model": best_name, "validation_roc_auc": best_auc}, f, indent=2)


# --- Inference handlers (used when this script serves the deployed model) ---
def model_fn(model_dir):
    model = joblib.load(os.path.join(model_dir, "model.joblib"))
    with open(os.path.join(model_dir, "feature_columns.json")) as f:
        columns = json.load(f)
    return {"model": model, "columns": columns}


def input_fn(request_body, content_type="text/csv"):
    """Parse a header-less CSV of raw feature values into a named DataFrame.

    Column order must match feature_columns.json (the payload contract). Only
    the raw features are expected — no header, no target.
    """
    from io import StringIO

    if content_type != "text/csv":
        raise ValueError(f"Unsupported content type: {content_type}")
    return pd.read_csv(StringIO(request_body), header=None)


def predict_fn(input_data, model_bundle):
    model, columns = model_bundle["model"], model_bundle["columns"]
    input_data.columns = columns[: input_data.shape[1]]
    # TotalCharges arrives as text in the raw payload; the Pipeline's scaler
    # needs it numeric (mirrors the cleaning step's coercion).
    if "TotalCharges" in input_data.columns:
        input_data["TotalCharges"] = pd.to_numeric(
            input_data["TotalCharges"], errors="coerce"
        ).fillna(0)
    return model.predict_proba(input_data)[:, 1]


def output_fn(prediction, accept="text/csv"):
    return "\n".join(str(p) for p in prediction), accept


def _parse_args():
    parser = argparse.ArgumentParser()
    # Hyperparameters (passed by the estimator in the pipeline).
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("-C", "--C", dest="C", type=float, default=1.0)
    # SageMaker channels / paths (fall back to env vars, then local defaults).
    parser.add_argument("--model-dir", default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument(
        "--validation",
        default=os.environ.get("SM_CHANNEL_VALIDATION", "/opt/ml/input/data/validation"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    train(_parse_args())
