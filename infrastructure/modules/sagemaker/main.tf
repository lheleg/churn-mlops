# SageMaker Studio Domain — OPTIONAL, created only when enable_domain = true.
#
# Architectural decision:
# Terraform manages only "standing" infrastructure. Ephemeral resources
# (training jobs, model-registry entries, endpoints) are created/destroyed
# on demand via the SageMaker Python SDK, NOT Terraform, so they can be
# spun up and torn down cheaply from application code.

resource "aws_sagemaker_domain" "this" {
  count = var.enable_domain ? 1 : 0

  domain_name = "${var.project_name}-domain"
  auth_mode   = "IAM"
  vpc_id      = var.vpc_id
  subnet_ids  = var.subnet_ids

  default_user_settings {
    # Reuse the execution role created by the IAM module.
    execution_role = var.execution_role_arn
  }
}
