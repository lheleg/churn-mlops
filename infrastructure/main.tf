# Root module: wires the four sub-modules and passes outputs between them.

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
}

module "iam" {
  source          = "./modules/iam"
  project_name    = var.project_name
  data_bucket_arn = module.s3.bucket_arn # scope role access to the project bucket
}

module "sagemaker" {
  source             = "./modules/sagemaker"
  project_name       = var.project_name
  enable_domain      = var.enable_sagemaker_domain
  vpc_id             = var.sagemaker_vpc_id
  subnet_ids         = var.sagemaker_subnet_ids
  execution_role_arn = module.iam.execution_role_arn
}

module "cicd" {
  source             = "./modules/cicd"
  project_name       = var.project_name
  github_owner       = var.github_owner
  github_repo        = var.github_repo
  github_branch      = var.github_branch
  data_bucket_name   = module.s3.bucket_name
  data_bucket_arn    = module.s3.bucket_arn
  execution_role_arn = module.iam.execution_role_arn
  github_pat         = var.github_pat
}
