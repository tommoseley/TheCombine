# The Combine - RDS PostgreSQL

# Security group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.app_name}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = data.aws_vpc.default.id
  
  # Allow PostgreSQL from anywhere in VPC (App Runner uses VPC connector)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
    description = "PostgreSQL from VPC"
  }
  
  # Also allow from your IP for direct access during setup
  # You can add your IP here or use AWS console
  # ingress {
  #   from_port   = 5432
  #   to_port     = 5432
  #   protocol    = "tcp"
  #   cidr_blocks = ["YOUR.IP.ADDRESS/32"]
  #   description = "PostgreSQL from admin IP"
  # }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Subnet group for RDS
resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-db-subnet"
  subnet_ids = data.aws_subnets.default.ids
  
  tags = {
    Name = "${var.app_name}-db-subnet"
  }
}

# RDS PostgreSQL instance
resource "aws_db_instance" "main" {
  identifier = "${var.app_name}-db"
  
  # Engine
  engine               = "postgres"
  engine_version       = "18.1"  # Use latest 15.x
  instance_class       = var.db_instance_class
  
  # Storage
  allocated_storage     = 20      # GB - minimum for gp2
  max_allocated_storage = 100     # Enable autoscaling up to 100GB
  storage_type          = "gp2"
  storage_encrypted     = true
  
  # Database
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432
  
  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false  # Only accessible from VPC
  
  # Backup
  backup_retention_period = 7
  backup_window          = "03:00-04:00"  # UTC
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  # Performance
  performance_insights_enabled = false  # Extra cost
  
  # Deletion protection (disable for dev)
  deletion_protection = var.environment == "prod" ? true : false
  skip_final_snapshot = var.environment == "prod" ? false : true
  final_snapshot_identifier = var.environment == "prod" ? "${var.app_name}-final-snapshot" : null
  
  # Allow minor version upgrades
  auto_minor_version_upgrade = true
  
  tags = {
    Name = "${var.app_name}-db"
  }
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_database_url" {
  description = "Full database URL (without password)"
  value       = "postgresql://${var.db_username}:PASSWORD@${aws_db_instance.main.endpoint}/${var.db_name}"
  sensitive   = true
}
