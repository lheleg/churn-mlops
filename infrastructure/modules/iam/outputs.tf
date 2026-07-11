output "execution_role_arn" {
  description = "ARN of the SageMaker execution role."
  value       = aws_iam_role.sagemaker_execution.arn
}

output "execution_role_name" {
  description = "Name of the SageMaker execution role."
  value       = aws_iam_role.sagemaker_execution.name
}
