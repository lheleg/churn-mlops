"""Create a scheduled SageMaker Model Monitor for data-quality drift.

    python -m monitoring.schedule \
        --role arn:aws:iam::<acct>:role/<SageMakerRole> \
        --endpoint churn-realtime \
        --statistics s3://<bucket>/monitoring/baseline/statistics.json \
        --constraints s3://<bucket>/monitoring/baseline/constraints.json \
        --output-uri s3://<bucket>/monitoring/reports
"""

import argparse

import boto3
import sagemaker
from sagemaker.model_monitor import CronExpressionGenerator, DefaultModelMonitor

from monitoring.config import (
    MONITOR_INSTANCE_TYPE,
    MONITOR_MAX_RUNTIME_S,
    MONITOR_SCHEDULE_NAME,
    MONITOR_VOLUME_GB,
)


def create_schedule(role, endpoint_name, statistics_uri, constraints_uri, output_uri, region=None):
    session = sagemaker.Session(boto3.Session(region_name=region))
    monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type=MONITOR_INSTANCE_TYPE,
        volume_size_in_gb=MONITOR_VOLUME_GB,
        max_runtime_in_seconds=MONITOR_MAX_RUNTIME_S,
        sagemaker_session=session,
    )
    monitor.create_monitoring_schedule(
        monitor_schedule_name=MONITOR_SCHEDULE_NAME,
        endpoint_input=endpoint_name,
        statistics=statistics_uri,
        constraints=constraints_uri,
        output_s3_uri=output_uri,
        schedule_cron_expression=CronExpressionGenerator.hourly(),
        enable_cloudwatch_metrics=True,
    )
    print(f"Created monitoring schedule: {MONITOR_SCHEDULE_NAME}")
    print("Violations are emitted to CloudWatch -> wire an EventBridge rule to trigger retraining.")
    return monitor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, help="SageMaker execution role ARN")
    parser.add_argument("--endpoint", required=True, help="Real-time endpoint name (with data capture)")
    parser.add_argument("--statistics", required=True, help="S3 URI of baseline statistics.json")
    parser.add_argument("--constraints", required=True, help="S3 URI of baseline constraints.json")
    parser.add_argument("--output-uri", required=True, help="S3 URI for monitoring reports")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()
    create_schedule(
        args.role, args.endpoint, args.statistics, args.constraints, args.output_uri, args.region
    )


if __name__ == "__main__":
    main()
