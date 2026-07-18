"""Deploy an approved model package to a SageMaker Serverless Inference endpoint.

Run AFTER a model version has been approved in the Model Registry (either in the
console or via the SDK).

    python -m pipeline.deploy --role arn:aws:iam::<acct>:role/<SageMakerRole>
"""

import argparse

import boto3
import sagemaker
from sagemaker import ModelPackage
from sagemaker.serverless import ServerlessInferenceConfig

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
    boto_session = boto3.Session(region_name=region)
    sagemaker_session = sagemaker.Session(boto_session=boto_session)
    sm_client = boto_session.client("sagemaker")

    package_arn = latest_approved_package_arn(sm_client, MODEL_PACKAGE_GROUP)
    print(f"Deploying model package: {package_arn}")

    model = ModelPackage(
        role=args.role, model_package_arn=package_arn, sagemaker_session=sagemaker_session
    )
    already_exists = endpoint_exists(sm_client, args.endpoint_name)
    model.deploy(
        endpoint_name=args.endpoint_name,
        serverless_inference_config=ServerlessInferenceConfig(
            memory_size_in_mb=SERVERLESS_MEMORY_MB,
            max_concurrency=SERVERLESS_MAX_CONCURRENCY,
        ),
        update_endpoint=already_exists,
    )
    action = "Updated" if already_exists else "Deployed"
    print(f"{action} serverless endpoint: {args.endpoint_name}")


if __name__ == "__main__":
    main()
