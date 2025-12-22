# The Combine - Terraform Outputs

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

# Summary output for easy reference
output "deployment_info" {
  description = "Deployment summary"
  value = {
    app_url         = "https://${var.domain_name}"
    apprunner_url   = "https://${aws_apprunner_service.main.service_url}"
    ecr_repository  = aws_ecr_repository.app.repository_url
    database_host   = aws_db_instance.main.endpoint
    health_check    = "https://${var.domain_name}/health"
  }
}

# GitHub Actions secrets (for reference)
output "github_secrets_needed" {
  description = "Secrets to add to GitHub repository"
  value = {
    AWS_ACCESS_KEY_ID     = "(create IAM user for CI/CD)"
    AWS_SECRET_ACCESS_KEY = "(create IAM user for CI/CD)"
    AWS_REGION            = data.aws_region.current.name
    ECR_REPOSITORY        = aws_ecr_repository.app.name
    ECR_REGISTRY          = split("/", aws_ecr_repository.app.repository_url)[0]
  }
}
