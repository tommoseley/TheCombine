# The Combine - AWS Secrets Manager
# Stores sensitive values securely, App Runner reads at runtime

# Database password
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.app_name}/db-password"
  description             = "PostgreSQL database password for The Combine"
  recovery_window_in_days = 7  # Allow recovery if accidentally deleted
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

# Anthropic API key
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "${var.app_name}/anthropic-api-key"
  description             = "Anthropic API key for Claude"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

# Application secret key
resource "aws_secretsmanager_secret" "secret_key" {
  name                    = "${var.app_name}/secret-key"
  description             = "Application secret key for sessions/tokens"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id     = aws_secretsmanager_secret.secret_key.id
  secret_string = var.secret_key
}

# Outputs - ARNs only, never the values
output "secret_arns" {
  description = "Secret ARNs (for reference only)"
  value = {
    db_password       = aws_secretsmanager_secret.db_password.arn
    anthropic_api_key = aws_secretsmanager_secret.anthropic_api_key.arn
    secret_key        = aws_secretsmanager_secret.secret_key.arn
  }
}
