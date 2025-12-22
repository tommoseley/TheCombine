# The Combine - Terraform Variables

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "the-combine"
}

# Database
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"  # Free tier eligible
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "combine"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "combine_admin"
}

variable "db_password" {
  description = "Database master password (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

# App Runner
variable "app_runner_cpu" {
  description = "App Runner CPU units (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "256"  # 0.25 vCPU - smallest/cheapest
}

variable "app_runner_memory" {
  description = "App Runner memory in MB (512, 1024, 2048, 3072, 4096, ...)"
  type        = string
  default     = "512"  # 0.5 GB - smallest/cheapest
}

# Domain
variable "domain_name" {
  description = "Custom domain name"
  type        = string
  default     = "thecombine.ui"
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for the domain"
  type        = string
}

# Secrets (will be stored in Secrets Manager, not plain env vars)
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Application secret key for sessions/tokens (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

# GitHub OIDC
variable "github_repository" {
  description = "GitHub repository in format 'owner/repo' (e.g., 'tmoseley/the-combine')"
  type        = string
}
