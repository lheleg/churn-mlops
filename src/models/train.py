"""Train baseline models: Logistic Regression and Random Forest."""

import logging

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from src.config import (
    LOGISTIC_REGRESSION_PATH,
    MODELS_DIR,
    RANDOM_STATE,
    TARGET_COLUMN,
    TRAIN_DATA_PATH,
    RANDOM_FOREST_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODELS = {
    "logistic_regression": {
        "estimator": LogisticRegression(random_state=RANDOM_STATE, max_iter=1000),
        "path": LOGISTIC_REGRESSION_PATH,
    },
    "random_forest": {
        "estimator": RandomForestClassifier(
            n_estimators=200, max_depth=10, random_state=RANDOM_STATE
        ),
        "path": RANDOM_FOREST_PATH,
    },
}


def train_models(train_path=TRAIN_DATA_PATH):
    train_df = pd.read_csv(train_path)
    X_train = train_df.drop(columns=[TARGET_COLUMN])
    y_train = train_df[TARGET_COLUMN]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    trained = {}

    for name, spec in MODELS.items():
        model = spec["estimator"]
        logger.info("Training %s with params: %s", name, model.get_params())
        model.fit(X_train, y_train)
        joblib.dump(model, spec["path"])
        logger.info("Saved %s to %s", name, spec["path"])
        trained[name] = model

    return trained


if __name__ == "__main__":
    train_models()
