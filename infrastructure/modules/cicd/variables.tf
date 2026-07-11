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
