"""SageMaker Pipeline definition for the churn model.

DAG: Preprocess -> Train -> Evaluate -> (ROC-AUC gate) -> Register model.

Build and register the pipeline:

    python -m pipeline.pipeline --role arn:aws:iam::<acct>:role/<SageMakerRole>
"""

import argparse
import os

import boto3
import sagemaker
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.sklearn.model import SKLearnModel
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.functions import Join, JsonGet
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.parameters import ParameterFloat, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

from pipeline.config import (
    BASE_JOB_PREFIX,
    FRAMEWORK_VERSION,
    MODEL_PACKAGE_GROUP,
    PIPELINE_NAME,
    PROCESSING_INSTANCE_TYPE,
    ROC_AUC_THRESHOLD,
    TRAINING_INSTANCE_TYPE,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")


def get_pipeline(region=None, role=None, default_bucket=None) -> Pipeline:
    region = region or boto3.Session().region_name
    boto_session = boto3.Session(region_name=region)
    pipeline_session = PipelineSession(boto_session=boto_session, default_bucket=default_bucket)
    if role is None:
        role = sagemaker.session.get_execution_role(pipeline_session)

    # --- Pipeline parameters (overridable per execution) ---
    input_data = ParameterString(name="InputDataUrl")
    model_approval_status = ParameterString(
        name="ModelApprovalStatus", default_value="PendingManualApproval"
    )
    roc_auc_threshold = ParameterFloat(name="RocAucThreshold", default_value=ROC_AUC_THRESHOLD)

    # --- Step 1: Preprocess ---
    sklearn_processor = SKLearnProcessor(
        framework_version=FRAMEWORK_VERSION,
        instance_type=PROCESSING_INSTANCE_TYPE,
        instance_count=1,
        base_job_name=f"{BASE_JOB_PREFIX}-preprocess",
        role=role,
        sagemaker_session=pipeline_session,
    )
    process_args = sklearn_processor.run(
        code=os.path.join(SCRIPTS_DIR, "preprocess.py"),
        inputs=[ProcessingInput(source=input_data, destination="/opt/ml/processing/input")],
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
            ProcessingOutput(output_name="validation", source="/opt/ml/processing/validation"),
            ProcessingOutput(output_name="test", source="/opt/ml/processing/test"),
        ],
    )
    step_process = ProcessingStep(name="PreprocessChurnData", step_args=process_args)

    # --- Step 2: Train ---
    sklearn_estimator = SKLearn(
        entry_point="train.py",
        source_dir=SCRIPTS_DIR,
        framework_version=FRAMEWORK_VERSION,
        instance_type=TRAINING_INSTANCE_TYPE,
        instance_count=1,
        base_job_name=f"{BASE_JOB_PREFIX}-train",
        role=role,
        sagemaker_session=pipeline_session,
        hyperparameters={"n-estimators": 200, "max-depth": 10, "C": 1.0},
    )
    train_args = sklearn_estimator.fit(
        inputs={
            "train": sagemaker.inputs.TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs[
                    "train"
                ].S3Output.S3Uri,
                content_type="text/csv",
            ),
            "validation": sagemaker.inputs.TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs[
                    "validation"
                ].S3Output.S3Uri,
                content_type="text/csv",
            ),
        }
    )
    step_train = TrainingStep(name="TrainChurnModel", step_args=train_args)

    # --- Step 3: Evaluate ---
    evaluation_report = PropertyFile(
        name="EvaluationReport", output_name="evaluation", path="evaluation.json"
    )
    eval_args = sklearn_processor.run(
        code=os.path.join(SCRIPTS_DIR, "evaluate.py"),
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source=step_process.properties.ProcessingOutputConfig.Outputs[
                    "test"
                ].S3Output.S3Uri,
                destination="/opt/ml/processing/test",
            ),
        ],
        outputs=[ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")],
    )
    step_eval = ProcessingStep(
        name="EvaluateChurnModel", step_args=eval_args, property_files=[evaluation_report]
    )

    # --- Step 4: Register (gated on ROC-AUC) ---
    model = SKLearnModel(
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        entry_point="train.py",
        source_dir=SCRIPTS_DIR,
        framework_version=FRAMEWORK_VERSION,
        role=role,
        sagemaker_session=pipeline_session,
    )
    eval_s3_uri = Join(
        on="/",
        values=[
            step_eval.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
            "evaluation.json",
        ],
    )
    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(s3_uri=eval_s3_uri, content_type="application/json")
    )
    register_args = model.register(
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=MODEL_PACKAGE_GROUP,
        approval_status=model_approval_status,
        model_metrics=model_metrics,
    )
    step_register = ModelStep(name="RegisterChurnModel", step_args=register_args)

    condition = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=step_eval.name,
            property_file=evaluation_report,
            json_path="binary_classification_metrics.roc_auc.value",
        ),
        right=roc_auc_threshold,
    )
    step_condition = ConditionStep(
        name="CheckRocAuc", conditions=[condition], if_steps=[step_register], else_steps=[]
    )

    return Pipeline(
        name=PIPELINE_NAME,
        parameters=[input_data, model_approval_status, roc_auc_threshold],
        steps=[step_process, step_train, step_eval, step_condition],
        sagemaker_session=pipeline_session,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", default=None, help="SageMaker execution role ARN")
    parser.add_argument("--region", default=None)
    parser.add_argument("--default-bucket", default=None)
    args = parser.parse_args()

    pipeline = get_pipeline(region=args.region, role=args.role, default_bucket=args.default_bucket)
    pipeline.upsert(role_arn=args.role)
    print(f"Upserted pipeline: {pipeline.name}")


if __name__ == "__main__":
    main()
