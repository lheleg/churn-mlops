# Aggregated key outputs, shown after `terraform apply`.

output "data_bucket_name" {
  description = "Data / artifact S3 bucket."
  value       = module.s3.bucket_name
}

output "data_bucket_arn" {
  description = "ARN of the data / artifact bucket."
  value       = module.s3.bucket_arn
}

output "sagemaker_execution_role_arn" {
  description = "SageMaker execution role ARN."
  value       = module.iam.execution_role_arn
}

output "sagemaker_domain_id" {
  description = "SageMaker Domain ID (null when the Domain is disabled)."
  value       = module.sagemaker.domain_id
}

output "pipeline_name" {
  description = "CodePipeline name."
  value       = module.cicd.pipeline_name
}

output "github_connection_arn" {
  description = "GitHub connection ARN."
  value       = module.cicd.connection_arn
}
