output "build_project_name" {
  description = "Name of the merge-build CodeBuild project."
  value       = aws_codebuild_project.this.name
}

output "pr_test_project_name" {
  description = "Name of the PR-gate CodeBuild project."
  value       = aws_codebuild_project.pr_test.name
}

output "deploy_project_name" {
  description = "Name of the deploy CodeBuild project."
  value       = aws_codebuild_project.deploy.name
}
