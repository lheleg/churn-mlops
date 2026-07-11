"""Local data-drift check using the Population Stability Index (PSI).

Runs anywhere (plain pandas/numpy) — no AWS needed. Two uses:

1. Fast local sanity check / thesis illustration of drift detection.
2. The serverless-compatible monitoring path: schedule this (EventBridge / CI)
   against a batch of recent production inputs logged to S3. On drift it exits
   non-zero, which a scheduler can use to trigger pipeline retraining (closing
   the P9 feedback loop -> P6 continuous training).

    python monitoring/local_drift.py \
        --baseline /tmp/churn-proc/train/train.csv \
        --current  /tmp/churn-proc/test/test.csv \
        --report   /tmp/drift_report.json

Exit code 0 = no drift, 1 = drift detected.
"""

import argparse
import json
import logging
import sys

import numpy as np
import pandas as pd

from monitoring.config import PSI_MODERATE, PSI_SIGNIFICANT, TARGET

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def psi_for_column(base: pd.Series, cur: pd.Series, bins: int = 10, eps: float = 1e-6) -> float:
    """PSI between a baseline and current distribution for one column."""
    base, cur = base.dropna(), cur.dropna()

    if base.nunique() <= bins:
        # Few distinct values (e.g. one-hot columns): compare category proportions.
        categories = sorted(set(base.unique()) | set(cur.unique()))
        base_pct = base.value_counts(normalize=True).reindex(categories).fillna(0.0)
        cur_pct = cur.value_counts(normalize=True).reindex(categories).fillna(0.0)
    else:
        # Continuous: bin by baseline deciles, then score current data in those bins.
        edges = np.unique(np.quantile(base, np.linspace(0, 1, bins + 1)))
        edges[0], edges[-1] = -np.inf, np.inf
        base_pct = pd.cut(base, edges).value_counts(normalize=True).sort_index()
        cur_pct = pd.cut(cur, edges).value_counts(normalize=True).reindex(base_pct.index).fillna(0.0)

    base_pct = base_pct.clip(lower=eps)
    cur_pct = cur_pct.clip(lower=eps)
    return float(((cur_pct - base_pct) * np.log(cur_pct / base_pct)).sum())


def classify(psi: float) -> str:
    if psi >= PSI_SIGNIFICANT:
        return "significant"
    if psi >= PSI_MODERATE:
        return "moderate"
    return "none"


def run_drift_check(baseline_path: str, current_path: str) -> dict:
    base_df = pd.read_csv(baseline_path)
    cur_df = pd.read_csv(current_path)

    features = [c for c in base_df.columns if c != TARGET and c in cur_df.columns]
    per_feature = {}
    for col in features:
        psi = psi_for_column(base_df[col], cur_df[col])
        per_feature[col] = {"psi": round(psi, 4), "shift": classify(psi)}

    drifted = [c for c, r in per_feature.items() if r["shift"] == "significant"]
    report = {
        "n_features": len(features),
        "drift_detected": bool(drifted),
        "drifted_features": drifted,
        "features": dict(sorted(per_feature.items(), key=lambda kv: kv[1]["psi"], reverse=True)),
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, help="Baseline (training) CSV")
    parser.add_argument("--current", required=True, help="Current / production batch CSV")
    parser.add_argument("--report", default=None, help="Optional path to write JSON report")
    args = parser.parse_args()

    report = run_drift_check(args.baseline, args.current)

    logger.info("Features checked: %d", report["n_features"])
    for col, r in list(report["features"].items())[:8]:
        logger.info("  PSI %.4f  [%s]  %s", r["psi"], r["shift"], col)
    if report["drift_detected"]:
        logger.warning("DRIFT DETECTED in: %s", ", ".join(report["drifted_features"]))
    else:
        logger.info("No significant drift.")

    if args.report:
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Wrote report to %s", args.report)

    sys.exit(1 if report["drift_detected"] else 0)


if __name__ == "__main__":
    main()
