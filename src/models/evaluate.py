"""Evaluate trained models on the held-out test set."""

import json
import logging

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.config import (
    CONFUSION_MATRIX_PATH,
    FIGURES_DIR,
    LOGISTIC_REGRESSION_PATH,
    METRICS_PATH,
    RANDOM_FOREST_PATH,
    REPORTS_DIR,
    TARGET_COLUMN,
    TEST_DATA_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATHS = {
    "logistic_regression": LOGISTIC_REGRESSION_PATH,
    "random_forest": RANDOM_FOREST_PATH,
}


def evaluate_model(model, X_test, y_test, model_name: str) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }
    logger.info("%s metrics: %s", model_name, metrics)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_path = str(CONFUSION_MATRIX_PATH).format(model_name=model_name)
    ConfusionMatrixDisplay.from_predictions(y_test, y_pred, display_labels=["No Churn", "Churn"])
    plt.title(f"Confusion Matrix - {model_name}")
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    logger.info("Saved confusion matrix to %s", fig_path)

    return metrics


def evaluate_all(test_path=TEST_DATA_PATH):
    test_df = pd.read_csv(test_path)
    X_test = test_df.drop(columns=[TARGET_COLUMN])
    y_test = test_df[TARGET_COLUMN]

    all_metrics = {}
    for name, path in MODEL_PATHS.items():
        model = joblib.load(path)
        all_metrics[name] = evaluate_model(model, X_test, y_test, name)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(all_metrics, f, indent=2)
    logger.info("Saved metrics to %s", METRICS_PATH)

    return all_metrics


if __name__ == "__main__":
    evaluate_all()
