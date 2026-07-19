"""Deploy an approved model package to a SageMaker Serverless Inference endpoint.

Run AFTER a model version has been approved in the Model Registry (either in the
console or via the SDK).

    python -m pipeline.deploy --role arn:aws:iam::<acct>:role/<SageMakerRole>
"""

import argparse
import time

import boto3

from pipeline.config import (
    MODEL_PACKAGE_GROUP,
    SERVERLESS_MAX_CONCURRENCY,
    SERVERLESS_MEMORY_MB,
)


def latest_approved_package_arn(sm_client, group_name: str) -> str:
    resp = sm_client.list_model_packages(
        ModelPackageGroupName=group_name,
        ModelApprovalStatus="Approved",
        SortBy="CreationTime",
        SortOrder="Descending",
        MaxResults=1,
    )
    packages = resp.get("ModelPackageSummaryList", [])
    if not packages:
        raise RuntimeError(f"No approved model package in group '{group_name}'.")
    return packages[0]["ModelPackageArn"]


def endpoint_exists(sm_client, endpoint_name: str) -> bool:
    """True if the endpoint already exists (so we update in place vs. create)."""
    try:
        sm_client.describe_endpoint(EndpointName=endpoint_name)
        return True
    except sm_client.exceptions.ClientError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, help="SageMaker execution role ARN")
    parser.add_argument("--region", default=None)
    parser.add_argument("--endpoint-name", default="churn-serverless")
    args = parser.parse_args()

    region = args.region or boto3.Session().region_name
    sm_client = boto3.Session(region_name=region).client("sagemaker")

    package_arn = latest_approved_package_arn(sm_client, MODEL_PACKAGE_GROUP)
    print(f"Deploying model package: {package_arn}")

    # Fresh, immutable model + endpoint config per deploy (timestamped names).
    suffix = time.strftime("%Y%m%d-%H%M%S")
    model_name = f"{args.endpoint_name}-{suffix}"
    config_name = f"{args.endpoint_name}-{suffix}"

    sm_client.create_model(
        ModelName=model_name,
        ExecutionRoleArn=args.role,
        Containers=[{"ModelPackageName": package_arn}],
    )
    sm_client.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": model_name,
                "ServerlessConfig": {
                    "MemorySizeInMB": SERVERLESS_MEMORY_MB,
                    "MaxConcurrency": SERVERLESS_MAX_CONCURRENCY,
                },
            }
        ],
    )

    # Idempotent: create the endpoint the first time, roll it to the new config
    # on subsequent runs. update_endpoint is a zero-downtime
    # swap; both paths are serverless-safe.
    if endpoint_exists(sm_client, args.endpoint_name):
        sm_client.update_endpoint(
            EndpointName=args.endpoint_name, EndpointConfigName=config_name
        )
        action = "Updated"
    else:
        sm_client.create_endpoint(
            EndpointName=args.endpoint_name, EndpointConfigName=config_name
        )
        action = "Created"

    print(f"{action} endpoint {args.endpoint_name}; waiting for InService...")
    sm_client.get_waiter("endpoint_in_service").wait(EndpointName=args.endpoint_name)
    print(f"Endpoint {args.endpoint_name} is InService serving {package_arn}")


if __name__ == "__main__":
    main()
