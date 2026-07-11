# SageMaker execution role: the identity SageMaker assumes to reach other services.

# Trust policy: allow the SageMaker service to assume this role.
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sagemaker_execution" {
  name               = "${var.project_name}-sagemaker-execution"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

# S3 access scoped to the PROJECT bucket only (least privilege), not all buckets.
data "aws_iam_policy_document" "s3_access" {
  statement {
    sid       = "ListProjectBucket"
    actions   = ["s3:ListBucket"]
    resources = [var.data_bucket_arn]
  }
  statement {
    sid       = "ReadWriteProjectObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${var.data_bucket_arn}/*"]
  }
}

resource "aws_iam_role_policy" "s3_access" {
  name   = "${var.project_name}-s3-access"
  role   = aws_iam_role.sagemaker_execution.id
  policy = data.aws_iam_policy_document.s3_access.json
}

# CloudWatch Logs access for job/endpoint logging.
data "aws_iam_policy_document" "logs" {
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "logs" {
  name   = "${var.project_name}-logs"
  role   = aws_iam_role.sagemaker_execution.id
  policy = data.aws_iam_policy_document.logs.json
}

resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}
