# Customer Churn Prediction — MLOps

MLOps implementation for a master's thesis on *"MLOps principles in developing
and delivering ML models"*. A churn model (binary classification) is used as the
vehicle to demonstrate an AWS-native MLOps stack built around **SageMaker**.

**Dataset:** [IBM Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) — churn / no churn.

## Repository structure

| Area | Path | What 
|------|------|------
| Baseline model | [`src/`](src/) | load → features → train (LR + RF) → evaluate; config, tests, EDA 
| Infrastructure | [`infrastructure/`](infrastructure/README.md) | Terraform IaC: S3, IAM, SageMaker domain (optional), CI/CD 
| Training pipeline | [`pipeline/`](pipeline/README.md) | SageMaker Pipeline: process → train → evaluate → gate → register; serverless deploy 
| Monitoring | [`monitoring/`](monitoring/README.md) | PSI drift check (local) + SageMaker Model Monitor 

Data, models, reports, and Terraform state are gitignored.

## Setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Place the raw dataset at `data/raw/telco_churn.csv` (Kaggle link above).

## Quickstart — local baseline (no AWS needed)

```bash
python -m src.features.build_features   # clean, engineer features, split train/test
python -m src.models.train              # train logistic regression + random forest
python -m src.models.evaluate           # metrics + confusion matrices
pytest                                  # data validation tests
```

Metrics → `reports/metrics.json`, plots → `reports/figures/`.

## Quickstart — SageMaker pipeline scripts (locally, no AWS)

The pipeline entry points run standalone, so the full DAG logic is verifiable
offline before it ever runs on AWS:

```bash
python pipeline/scripts/preprocess.py --input-data data/raw/telco_churn.csv --base-dir /tmp/churn-proc
python pipeline/scripts/train.py      --train /tmp/churn-proc/train --validation /tmp/churn-proc/validation --model-dir /tmp/churn-model
python pipeline/scripts/evaluate.py   --model-dir /tmp/churn-model --test-dir /tmp/churn-proc/test --output-dir /tmp/churn-eval
python -m monitoring.local_drift      --baseline /tmp/churn-proc/train/train.csv --current /tmp/churn-proc/test/test.csv
```

## Running on AWS

Requires AWS credentials + a SageMaker execution role. See the per-area guides:

- **Infrastructure** → [`infrastructure/README.md`](infrastructure/README.md) (`terraform init/plan/apply`)
- **Pipeline & serving** → [`pipeline/README.md`](pipeline/README.md) (upsert, execute, approve, deploy serverless)
- **Monitoring** → [`monitoring/README.md`](monitoring/README.md) (baseline, drift check, scheduled monitor)
