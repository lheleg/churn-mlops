# Monitoring — Data Drift (C9 / P8)

Detects data drift: drift → trigger pipeline
retraining.

## Two paths (pick by serving mode)

| Path | Tool | When |
|------|------|------|
| **A. Scheduled (native)** | `baseline.py` + `schedule.py` | Real-time endpoint with Data Capture |
| **B. Batch (serverless-friendly)** | `baseline.py` + `local_drift.py` | Serverless endpoint (our default) |

## Files

| File | Role | Testable locally |
|------|------|:----------------:|
| `baseline.py` | SageMaker `suggest_baseline` → statistics.json + constraints.json | ✗ (managed job) |
| `schedule.py` | Scheduled Model Monitor on a real-time endpoint | ✗ (needs AWS) |
| `local_drift.py` | PSI drift check, no AWS; exits non-zero on drift | ✓ |
| `config.py` | Instance type, PSI thresholds | — |

## Path B — batch drift check (default)

Runs anywhere. Compare a batch of recent production inputs against the training
baseline:

```bash
python monitoring/local_drift.py \
    --baseline data/processed/train/train.csv \
    --current  <recent_production_batch>.csv \
    --report   drift_report.json
```

PSI thresholds: `< 0.10` none · `0.10–0.25` moderate · `≥ 0.25` drift.
Exit code `1` on drift → a scheduler (EventBridge / CI) triggers retraining:

```python
# on non-zero exit:
from pipeline.pipeline import get_pipeline
get_pipeline(role=ROLE).start(parameters={"InputDataUrl": NEW_DATA_S3_URI})
```

## Path A — scheduled Model Monitor (real-time endpoint)

```bash
# 1. Baseline from training data
python -m monitoring.baseline --role <ROLE> \
    --train-uri s3://<bucket>/processed/train/train.csv \
    --output-uri s3://<bucket>/monitoring/baseline

# 2. Deploy a REAL-TIME endpoint with data capture (not serverless), e.g.:
#    model.deploy(instance_type="ml.m5.large", initial_instance_count=1,
#                 data_capture_config=DataCaptureConfig(enable_capture=True,
#                     sampling_percentage=100, destination_s3_uri="s3://<bucket>/capture"))

# 3. Schedule the monitor
python -m monitoring.schedule --role <ROLE> --endpoint churn-realtime \
    --statistics s3://<bucket>/monitoring/baseline/statistics.json \
    --constraints s3://<bucket>/monitoring/baseline/constraints.json \
    --output-uri s3://<bucket>/monitoring/reports
```

Violations are published to CloudWatch → wire an EventBridge rule to trigger the
training pipeline.

## Feedback loop (thesis narrative)

```
Monitoring (drift) ──▶ EventBridge/CI ──▶ pipeline.start() ──▶ retrain ──▶ register ──▶ redeploy
```

## Dependencies

- `local_drift.py`: pandas + numpy (already in the base `requirements.txt`).
- `baseline.py` / `schedule.py`: `pip install -r pipeline/requirements.txt` (sagemaker, boto3).
