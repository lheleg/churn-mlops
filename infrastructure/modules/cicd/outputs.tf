output "pipeline_name" {
  description = "Name of the CodePipeline."
  value       = aws_codepipeline.this.name
}

output "connection_arn" {
  description = "ARN of the GitHub connection."
  value       = aws_codestarconnections_connection.github.arn
}

output "artifacts_bucket_name" {
  description = "Name of the CodePipeline artifact bucket."
  value       = aws_s3_bucket.artifacts.bucket
}
