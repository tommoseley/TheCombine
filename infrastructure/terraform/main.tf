# The Combine - AWS Infrastructure
# Terraform configuration for App Runner + RDS PostgreSQL

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Uncomment to use S3 backend for state (recommended for team use)
  # backend "s3" {
  #   bucket = "the-combine-terraform-state"
  #   key    = "infrastructure/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "the-combine"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# VPC for RDS (App Runner manages its own networking)
# Using default VPC for simplicity - production should use dedicated VPC
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Filter subnets to only those in App Runner supported AZs
data "aws_subnet" "default" {
  for_each = toset(data.aws_subnets.default.ids)
  id       = each.value
}

locals {
  # Exclude use1-az3 (doesn't support App Runner)
  apprunner_supported_subnets = [
    for s in data.aws_subnet.default : s.id
    if s.availability_zone_id != "use1-az3"
  ]
}
