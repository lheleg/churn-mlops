"""Create a SageMaker Model Monitor data-quality baseline from the training set.

`suggest_baseline` runs a managed processing job that profiles the training data
and writes two artifacts to S3:
  - statistics.json  (per-feature distribution statistics)
  - constraints.json (inferred constraints used to detect violations later)

These feed both the scheduled monitor (schedule.py) and on-demand checks.

    python -m monitoring.baseline \
        --role arn:aws:iam::<acct>:role/<SageMakerRole> \
        --train-uri s3://<bucket>/processed/train/train.csv \
        --output-uri s3://<bucket>/monitoring/baseline
"""

import argparse

import boto3
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

from monitoring.config import (
    MONITOR_INSTANCE_TYPE,
    MONITOR_MAX_RUNTIME_S,
    MONITOR_VOLUME_GB,
)


def create_baseline(role, train_uri, output_uri, region=None):
    session = sagemaker.Session(boto3.Session(region_name=region))
    monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type=MONITOR_INSTANCE_TYPE,
        volume_size_in_gb=MONITOR_VOLUME_GB,
        max_runtime_in_seconds=MONITOR_MAX_RUNTIME_S,
        sagemaker_session=session,
    )
    monitor.suggest_baseline(
        baseline_dataset=train_uri,
        dataset_format=DatasetFormat.csv(header=True),
        output_s3_uri=output_uri,
        wait=True,
    )
    print(f"Baseline written to: {output_uri}")
    return monitor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, help="SageMaker execution role ARN")
    parser.add_argument("--train-uri", required=True, help="S3 URI of the training CSV")
    parser.add_argument("--output-uri", required=True, help="S3 URI for baseline artifacts")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()
    create_baseline(args.role, args.train_uri, args.output_uri, args.region)


if __name__ == "__main__":
    main()
