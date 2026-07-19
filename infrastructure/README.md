# Infrastructure (Terraform) — Churn MLOps on AWS

AWS infrastructure as code for the churn-mlops project. Terraform manages the
**standing** resources (S3, IAM, optional SageMaker Domain, CI/CD). Ephemeral
resources (training jobs, endpoints) are handled on demand via the SageMaker
SDK, not Terraform, so they can be spun up/down cheaply.

## Modules

| Module      | Creates                                                            |
|-------------|-------------------------------------------------------------------|
| `s3`        | Data/artifact bucket: versioned, encrypted, private, lifecycle rule |
| `iam`       | SageMaker execution role (S3 scoped to project bucket, logs)       |
| `sagemaker` | SageMaker Studio Domain — **optional**, off by default            |
| `cicd`      | CodeBuild projects (PR gate, merge build, deploy) + GitHub webhooks + EventBridge |

## Prerequisites

Install and configure both tools first — do not assume they are present.

**AWS CLI**
```bash
aws configure                 # enter Access Key, Secret, region, output format
aws sts get-caller-identity   # should return your account details
```

**Terraform**
```bash
terraform version             # verify install (>= 1.5)
```

## Usage

```bash
cd infrastructure

cp terraform.tfvars.example terraform.tfvars   # then edit real values (gitignored)

terraform init       # download providers
terraform validate   # check syntax
terraform plan       # preview changes (creates nothing)
terraform apply      # create resources
```

### GitHub access

All three CodeBuild projects authenticate to GitHub with a fine-grained PAT.
Provide it as `TF_VAR_github_pat` (or a `github_pat` entry in `terraform.tfvars`)
**before** `terraform apply` — the PAT is used to register the push/PR webhooks,
clone the repo, and report PR status. No console handshake is required.

### Manual step after apply

Add a branch-protection rule on `main` requiring the `churn-mlops-pr-test` check,
so the PR gate is blocking (via the GitHub UI or `gh api`).
