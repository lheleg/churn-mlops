output "domain_id" {
  description = "SageMaker Domain ID, or null when the Domain is disabled."
  value       = one(aws_sagemaker_domain.this[*].id)
}
