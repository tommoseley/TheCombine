# The Combine - AWS App Runner (Hardened)
# Reads secrets from Secrets Manager, not environment variables

# IAM role for App Runner to access ECR
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${var.app_name}-apprunner-ecr-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# IAM role for App Runner instance (runtime)
resource "aws_iam_role" "apprunner_instance" {
  name = "${var.app_name}-apprunner-instance-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# Policy for App Runner to read secrets
resource "aws_iam_role_policy" "apprunner_secrets_access" {
  name = "${var.app_name}-secrets-access"
  role = aws_iam_role.apprunner_instance.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadSecrets"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn,
          aws_secretsmanager_secret.anthropic_api_key.arn,
          aws_secretsmanager_secret.secret_key.arn
        ]
      }
    ]
  })
}

# VPC Connector for App Runner to access RDS
resource "aws_security_group" "apprunner_vpc_connector" {
  name        = "${var.app_name}-apprunner-vpc-sg"
  description = "Security group for App Runner VPC connector"
  vpc_id      = data.aws_vpc.default.id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${var.app_name}-vpc-connector"
  subnets            = local.apprunner_supported_subnets
  security_groups    = [aws_security_group.apprunner_vpc_connector.id]
}

# App Runner service
resource "aws_apprunner_service" "main" {
  service_name = var.app_name
  
  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }
    
    image_repository {
      image_identifier      = "${aws_ecr_repository.app.repository_url}:latest"
      image_repository_type = "ECR"
      
      image_configuration {
        port = "8000"
        
        runtime_environment_variables = {
          # Non-sensitive config only
          ENVIRONMENT = var.environment
          DB_HOST     = aws_db_instance.main.address
          DB_PORT     = "5432"
          DB_NAME     = var.db_name
          DB_USERNAME = var.db_username
        }
        
        runtime_environment_secrets = {
          # App Runner injects these as env vars automatically
          DB_PASSWORD       = aws_secretsmanager_secret.db_password.arn
          ANTHROPIC_API_KEY = aws_secretsmanager_secret.anthropic_api_key.arn
          SECRET_KEY        = aws_secretsmanager_secret.secret_key.arn
        }
      }
    }
    
    auto_deployments_enabled = true  # Auto-deploy when ECR image updates
  }
  
  instance_configuration {
    cpu               = var.app_runner_cpu
    memory            = var.app_runner_memory
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }
  
  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
    }
  }
  
  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }
  
  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.main.arn
  
  tags = {
    Name = var.app_name
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.apprunner_ecr_access,
    aws_iam_role_policy.apprunner_secrets_access,
    aws_db_instance.main
  ]
}

# Auto-scaling configuration (minimal for cost savings)
resource "aws_apprunner_auto_scaling_configuration_version" "main" {
  auto_scaling_configuration_name = "${var.app_name}-autoscaling"
  
  max_concurrency = 100   # Requests per instance before scaling
  max_size        = 2     # Max instances
  min_size        = 1     # Min instances (set to 0 to scale to zero)
}

output "apprunner_service_url" {
  description = "App Runner service URL"
  value       = aws_apprunner_service.main.service_url
}

output "apprunner_service_arn" {
  description = "App Runner service ARN"
  value       = aws_apprunner_service.main.arn
}
