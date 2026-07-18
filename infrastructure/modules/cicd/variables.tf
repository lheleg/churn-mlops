variable "project_name" {
  description = "Base name used as a prefix for CI/CD resource names."
  type        = string
}

variable "github_owner" {
  description = "GitHub user or organization that owns the repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name."
  type        = string
}

variable "github_branch" {
  description = "Branch that triggers the pipeline."
  type        = string
  default     = "main"
}

variable "data_bucket_name" {
  description = "Name of the data/artifact bucket -- exposed to CodeBuild as $DATA_BUCKET."
  type        = string
}

variable "data_bucket_arn" {
  description = "ARN of the data/artifact bucket, for scoping CodeBuild's read permission."
  type        = string
}

variable "execution_role_arn" {
  description = "SageMaker execution role ARN that CodeBuild passes to SageMaker (upsert/deploy) and EventBridge deploys use."
  type        = string
}

variable "github_pat" {
  description = "GitHub fine-grained PAT for CodeBuild to create the PR webhook and report build status. Pass via TF_VAR_github_pat."
  type        = string
  sensitive   = true
}

variable "sagemaker_pipeline_name" {
  description = "Name of the SageMaker (model) pipeline that CodeBuild upserts and executes."
  type        = string
  default     = "churn-training-pipeline"
}

variable "model_package_group" {
  description = "Model Registry package group whose approvals trigger auto-deploy."
  type        = string
  default     = "churn-model-group"
}

variable "serverless_endpoint_name" {
  description = "Name of the serverless inference endpoint created by the deploy stage."
  type        = string
  default     = "churn-serverless"
}
