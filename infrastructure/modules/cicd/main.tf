# CI/CD wiring:
#   PR -> main    : CodeBuild "pr_test" (webhook) runs pytest, reports status on the PR.
#   merge -> main : CodeBuild "build" (webhook on push) upserts the SageMaker pipeline
#                   and starts a training run (path-scoped) -> Model Registry.
#   approval      : EventBridge (model package -> Approved) -> CodeBuild "deploy" -> endpoint.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  sagemaker_pipeline_arn = "arn:aws:sagemaker:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:pipeline/${var.sagemaker_pipeline_name}"
  model_package_arns     = "arn:aws:sagemaker:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:model-package/${var.model_package_group}/*"
  sagemaker_model_arns   = "arn:aws:sagemaker:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:model/*"
  endpoint_config_arns   = "arn:aws:sagemaker:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:endpoint-config/*"
  endpoint_arn           = "arn:aws:sagemaker:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:endpoint/${var.serverless_endpoint_name}"
}

# CodeBuild authenticates to GitHub with a fine-grained PAT (via the github_pat
# variable) -- used to create the source webhooks, clone the repo, and report PR
# status. Account-level credential shared by all GITHUB-source CodeBuild projects.
resource "aws_codebuild_source_credential" "github" {
  auth_type   = "PERSONAL_ACCESS_TOKEN"
  server_type = "GITHUB"
  token       = var.github_pat
}

# ---------------------------------------------------------------------------
# CodeBuild
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "codebuild_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codebuild" {
  name               = "${var.project_name}-codebuild"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume.json
}

data "aws_iam_policy_document" "codebuild" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
  statement {
    # CodeBuild reads the raw dataset for data-validation tests, and writes the
    # pipeline code tarball to the bucket during `pipeline.upsert` (default bucket).
    sid       = "ReadWriteDataBucket"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = [var.data_bucket_arn, "${var.data_bucket_arn}/*"]
  }
  statement {
    # Register/refresh the SageMaker pipeline definition and start training runs.
    sid = "ManageSageMakerPipeline"
    actions = [
      "sagemaker:CreatePipeline",
      "sagemaker:UpdatePipeline",
      "sagemaker:DescribePipeline",
      "sagemaker:StartPipelineExecution",
      "sagemaker:ListPipelineExecutions",
      "sagemaker:AddTags",
      "sagemaker:ListTags",
    ]
    resources = ["${local.sagemaker_pipeline_arn}", "${local.sagemaker_pipeline_arn}/*"]
  }
  statement {
    # CreatePipeline embeds the execution role, which requires PassRole.
    sid       = "PassExecutionRole"
    actions   = ["iam:PassRole"]
    resources = [var.execution_role_arn]
  }
}

resource "aws_iam_role_policy" "codebuild" {
  name   = "${var.project_name}-codebuild"
  role   = aws_iam_role.codebuild.id
  policy = data.aws_iam_policy_document.codebuild.json
}

resource "aws_codebuild_project" "this" {
  name         = "${var.project_name}-build"
  service_role = aws_iam_role.codebuild.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL" # cheapest compute tier
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "DATA_BUCKET"
      value = var.data_bucket_name
    }
    environment_variable {
      name  = "SAGEMAKER_ROLE_ARN"
      value = var.execution_role_arn
    }
    environment_variable {
      name  = "PIPELINE_NAME"
      value = var.sagemaker_pipeline_name
    }
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/${var.github_owner}/${var.github_repo}.git"
    buildspec       = "buildspec.yml" # lives in the repo root
    git_clone_depth = 0               # full history for the path-scoped `git diff HEAD~1`
  }
  source_version = var.github_branch

  depends_on = [aws_codebuild_source_credential.github]
}

# Fire the merge build on every push to the main branch.
resource "aws_codebuild_webhook" "build" {
  project_name = aws_codebuild_project.this.name
  build_type   = "BUILD"

  filter_group {
    filter {
      type    = "EVENT"
      pattern = "PUSH"
    }
    filter {
      type    = "HEAD_REF"
      pattern = "^refs/heads/${var.github_branch}$"
    }
  }
}

# ---------------------------------------------------------------------------
# CodeBuild: PR gate (webhook) -- runs tests only, no SageMaker permissions
# ---------------------------------------------------------------------------
resource "aws_iam_role" "codebuild_pr" {
  name               = "${var.project_name}-codebuild-pr"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume.json
}

data "aws_iam_policy_document" "codebuild_pr" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
  statement {
    # Read-only: the PR gate only syncs the dataset in and runs pytest.
    sid       = "ReadDataBucket"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [var.data_bucket_arn, "${var.data_bucket_arn}/*"]
  }
}

resource "aws_iam_role_policy" "codebuild_pr" {
  name   = "${var.project_name}-codebuild-pr"
  role   = aws_iam_role.codebuild_pr.id
  policy = data.aws_iam_policy_document.codebuild_pr.json
}

resource "aws_codebuild_project" "pr_test" {
  name         = "${var.project_name}-pr-test"
  service_role = aws_iam_role.codebuild_pr.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "DATA_BUCKET"
      value = var.data_bucket_name
    }
  }

  source {
    type                = "GITHUB"
    location            = "https://github.com/${var.github_owner}/${var.github_repo}.git"
    buildspec           = "buildspec.pr.yml"
    git_clone_depth     = 1
    report_build_status = true # posts pass/fail back onto the PR
  }

  depends_on = [aws_codebuild_source_credential.github]
}

# Fire the PR gate on pull requests targeting the main branch.
resource "aws_codebuild_webhook" "pr_test" {
  project_name = aws_codebuild_project.pr_test.name
  build_type   = "BUILD"

  filter_group {
    filter {
      type    = "EVENT"
      pattern = "PULL_REQUEST_CREATED, PULL_REQUEST_UPDATED, PULL_REQUEST_REOPENED"
    }
    filter {
      type    = "BASE_REF"
      pattern = "^refs/heads/${var.github_branch}$"
    }
  }
}

# ---------------------------------------------------------------------------
# CodeBuild: deploy -- reuses pipeline/deploy.py to stand up / update the endpoint
# ---------------------------------------------------------------------------
resource "aws_iam_role" "codebuild_deploy" {
  name               = "${var.project_name}-codebuild-deploy"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume.json
}

data "aws_iam_policy_document" "codebuild_deploy" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
  statement {
    # Read the model artifacts (model.tar.gz) referenced by the model package.
    sid       = "ReadDataBucket"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [var.data_bucket_arn, "${var.data_bucket_arn}/*"]
  }
  statement {
    # Find the latest Approved package in the group.
    sid       = "ReadModelPackages"
    actions   = ["sagemaker:ListModelPackages", "sagemaker:DescribeModelPackage"]
    resources = ["${local.model_package_arns}", "arn:aws:sagemaker:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:model-package-group/${var.model_package_group}"]
  }
  statement {
    # Create/refresh the model, endpoint config, and serverless endpoint.
    sid = "ManageEndpoint"
    actions = [
      "sagemaker:CreateModel",
      "sagemaker:CreateEndpointConfig",
      "sagemaker:CreateEndpoint",
      "sagemaker:UpdateEndpoint",
      "sagemaker:DescribeEndpoint",
      "sagemaker:DescribeEndpointConfig",
      "sagemaker:DescribeModel",
      "sagemaker:AddTags",
    ]
    resources = [local.sagemaker_model_arns, local.endpoint_config_arns, local.endpoint_arn]
  }
  statement {
    # CreateModel embeds the execution role, which requires PassRole.
    sid       = "PassExecutionRole"
    actions   = ["iam:PassRole"]
    resources = [var.execution_role_arn]
  }
}

resource "aws_iam_role_policy" "codebuild_deploy" {
  name   = "${var.project_name}-codebuild-deploy"
  role   = aws_iam_role.codebuild_deploy.id
  policy = data.aws_iam_policy_document.codebuild_deploy.json
}

resource "aws_codebuild_project" "deploy" {
  name         = "${var.project_name}-deploy"
  service_role = aws_iam_role.codebuild_deploy.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "SAGEMAKER_ROLE_ARN"
      value = var.execution_role_arn
    }
    environment_variable {
      name  = "ENDPOINT_NAME"
      value = var.serverless_endpoint_name
    }
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/${var.github_owner}/${var.github_repo}.git"
    buildspec       = "buildspec.deploy.yml"
    git_clone_depth = 1
  }
  source_version = var.github_branch

  depends_on = [aws_codebuild_source_credential.github]
}

# ---------------------------------------------------------------------------
# EventBridge: Model Registry approval -> trigger the deploy build
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "model_approved" {
  name        = "${var.project_name}-model-approved"
  description = "Fire when a churn model package is Approved in the registry."

  event_pattern = jsonencode({
    source      = ["aws.sagemaker"]
    detail-type = ["SageMaker Model Package State Change"]
    detail = {
      ModelApprovalStatus   = ["Approved"]
      ModelPackageGroupName = [var.model_package_group]
    }
  })
}

resource "aws_iam_role" "events_deploy" {
  name = "${var.project_name}-events-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "events_deploy" {
  name = "${var.project_name}-events-deploy"
  role = aws_iam_role.events_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "codebuild:StartBuild"
      Resource = aws_codebuild_project.deploy.arn
    }]
  })
}

resource "aws_cloudwatch_event_target" "deploy" {
  rule     = aws_cloudwatch_event_rule.model_approved.name
  arn      = aws_codebuild_project.deploy.arn
  role_arn = aws_iam_role.events_deploy.arn
}
