variable "project_name" {
  description = "Base name used as a prefix for IAM resource names."
  type        = string
}

variable "data_bucket_arn" {
  description = "ARN of the project S3 bucket the role is granted access to."
  type        = string
}
