# SageMaker Training Pipeline — Churn

SageMaker Pipeline that trains, evaluates, and registers the churn model.

```
Preprocess ──▶ Train ──▶ Evaluate ──▶ [ROC-AUC ≥ threshold?] ──▶ Register model
 (SKLearn      (SKLearn    (metrics →        gate                  (Model Registry,
  Processor)    estimator)  evaluation.json)                        PendingManualApproval)
```

Serving is handled separately: an **approved** model version is deployed to a
**Serverless Inference** endpoint via `deploy.py` (scales to zero → no idle cost).

## Files

| File | Role |
|------|------|
| `pipeline.py` | Pipeline (DAG) definition — `get_pipeline()` + `upsert` CLI |
| `config.py` | Names, instance types, ROC-AUC threshold, serverless config |
| `scripts/preprocess.py` | ProcessingStep: clean, encode, scale, 70/15/15 split |
| `scripts/train.py` | TrainingStep (script-mode) + inference handlers for serving |
| `scripts/evaluate.py` | ProcessingStep: metrics → `evaluation.json` |
| `deploy.py` | Deploy latest approved model to a serverless endpoint |

The three `scripts/` entry points run **both** inside SageMaker and locally, so
they can be tested without AWS.

## Local test (no AWS needed)

```bash
python pipeline/scripts/preprocess.py --input-data data/raw/telco_churn.csv --base-dir /tmp/churn-proc
python pipeline/scripts/train.py      --train /tmp/churn-proc/train --validation /tmp/churn-proc/validation --model-dir /tmp/churn-model
python pipeline/scripts/evaluate.py   --model-dir /tmp/churn-model --test-dir /tmp/churn-proc/test --output-dir /tmp/churn-eval
```

## Run on AWS (requires credentials + SageMaker execution role)

```bash
pip install -r pipeline/requirements.txt

# 1. Upload raw data to S3, then register the pipeline definition
python -m pipeline.pipeline --role arn:aws:iam::<acct>:role/<SageMakerRole>

# 2. Start an execution (console, or SDK: pipeline.start(parameters={"InputDataUrl": "s3://.../telco_churn.csv"}))

# 3. Approve the registered model version in the Model Registry (console or SDK)

# 4. Deploy the approved version to a serverless endpoint
python -m pipeline.deploy --role arn:aws:iam::<acct>:role/<SageMakerRole>
```

The execution role comes from the `iam` Terraform module (`infrastructure/`).
