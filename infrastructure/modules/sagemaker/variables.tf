variable "project_name" {
  description = "Base name used as a prefix for SageMaker resource names."
  type        = string
}

variable "enable_domain" {
  description = "Whether to create the SageMaker Studio Domain."
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "VPC ID for the Domain (required only when enable_domain = true)."
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for the Domain (required only when enable_domain = true)."
  type        = list(string)
  default     = []
}

variable "execution_role_arn" {
  description = "ARN of the SageMaker execution role (from the IAM module)."
  type        = string
}
