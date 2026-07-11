"""SageMaker Processing entry point: evaluate the trained model on the test set.

Writes evaluation.json in the SageMaker binary-classification-metrics schema,
which the pipeline uses both for the quality gate (ConditionStep) and as the
model metrics attached in the Model Registry.

Runnable locally for testing:

    python pipeline/scripts/evaluate.py \
        --model-dir /tmp/churn-model --test-dir /tmp/churn-proc/test \
        --output-dir /tmp/churn-eval
"""

import argparse
import json
import logging
import os
import tarfile

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TARGET = "Churn"


def _load_model(model_dir: str):
    """In the pipeline the model arrives as model.tar.gz; locally it may be raw."""
    tar_path = os.path.join(model_dir, "model.tar.gz")
    if os.path.exists(tar_path):
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=model_dir)
    return joblib.load(os.path.join(model_dir, "model.joblib"))


def _load_test(test_dir: str) -> pd.DataFrame:
    csvs = [f for f in os.listdir(test_dir) if f.endswith(".csv")]
    if not csvs:
        raise FileNotFoundError(f"No CSV in {test_dir}")
    return pd.read_csv(os.path.join(test_dir, csvs[0]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="/opt/ml/processing/model")
    parser.add_argument("--test-dir", default="/opt/ml/processing/test")
    parser.add_argument("--output-dir", default="/opt/ml/processing/evaluation")
    args = parser.parse_args()

    model = _load_model(args.model_dir)
    test_df = _load_test(args.test_dir)
    X_test, y_test = test_df.drop(columns=[TARGET]), test_df[TARGET]

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    report = {
        "binary_classification_metrics": {
            "accuracy": {"value": accuracy_score(y_test, y_pred)},
            "precision": {"value": precision_score(y_test, y_pred)},
            "recall": {"value": recall_score(y_test, y_pred)},
            "f1": {"value": f1_score(y_test, y_pred)},
            "roc_auc": {"value": roc_auc_score(y_test, y_proba)},
        }
    }
    logger.info("Evaluation: %s", report["binary_classification_metrics"])

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "evaluation.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    main()
