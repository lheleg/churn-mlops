variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Base name used as a prefix for resource names."
  type        = string
  default     = "churn-mlops"
}

variable "github_owner" {
  description = "GitHub user or organization that owns the repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name."
  type        = string
  default     = "churn-mlops"
}

variable "github_branch" {
  description = "Branch that triggers the CI/CD pipeline."
  type        = string
  default     = "main"
}

variable "github_pat" {
  description = "GitHub fine-grained PAT for CodeBuild PR webhooks. Pass via TF_VAR_github_pat; never commit."
  type        = string
  sensitive   = true
}

# --- SageMaker Studio Domain (optional, cost-bearing) ---
# The baseline sklearn model trains locally / in CodeBuild, so the Domain is
# OFF by default. Should be turned on only when using SageMaker Studio.
variable "enable_sagemaker_domain" {
  description = "Whether to create a SageMaker Studio Domain."
  type        = bool
  default     = false
}

variable "sagemaker_vpc_id" {
  description = "VPC ID for the SageMaker Domain (required only if enable_sagemaker_domain = true)."
  type        = string
  default     = ""
}

variable "sagemaker_subnet_ids" {
  description = "Subnet IDs for the SageMaker Domain (required only if enable_sagemaker_domain = true)."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default = {
    Project   = "churn-mlops-thesis"
    ManagedBy = "terraform"
  }
}
