# The Combine - GitHub Actions OIDC Authentication
# Uses OpenID Connect instead of long-lived access keys

# GitHub OIDC provider (only need one per AWS account)
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  
  # GitHub's OIDC thumbprint - this is AWS's known thumbprint for GitHub
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
  
  tags = {
    Purpose = "GitHub Actions OIDC"
  }
}

# IAM role that GitHub Actions assumes
resource "aws_iam_role" "github_actions" {
  name = "${var.app_name}-github-actions"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Restrict to your specific repository
            # Format: repo:OWNER/REPO:*
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
          }
        }
      }
    ]
  })
  
  tags = {
    Purpose = "GitHub Actions CI/CD"
  }
}

# Policy with minimal permissions for CI/CD
resource "aws_iam_role_policy" "github_actions" {
  name = "${var.app_name}-github-actions-policy"
  role = aws_iam_role.github_actions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRLogin"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Resource = aws_ecr_repository.app.arn
      },
      {
        Sid    = "AppRunnerList"
        Effect = "Allow"
        Action = [
          "apprunner:ListServices",
          "apprunner:DescribeService"
        ]
        Resource = "*"
      },
      {
        Sid    = "AppRunnerDeploy"
        Effect = "Allow"
        Action = [
          "apprunner:StartDeployment",
          "apprunner:UpdateService"
        ]
        Resource = aws_apprunner_service.main.arn
      }
    ]
  })
}

# Output the role ARN for GitHub Actions configuration
output "github_actions_role_arn" {
  description = "IAM Role ARN for GitHub Actions (use in workflow)"
  value       = aws_iam_role.github_actions.arn
}

output "github_actions_setup_instructions" {
  description = "Instructions for GitHub Actions setup"
  value = <<-EOT
    
    ✅ GitHub OIDC configured! No access keys needed.
    
    Add this to your GitHub Actions workflow:
    
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${aws_iam_role.github_actions.arn}
        aws-region: ${var.aws_region}
    
    Required GitHub repository setting:
    - Settings → Actions → General → Workflow permissions
    - Enable "Allow GitHub Actions to create and approve pull requests"
    
  EOT
}
