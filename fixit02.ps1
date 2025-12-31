# Set variables
$DB_PASSWORD = "Gamecocks4896!"  # CHANGE THIS!
$REGION = "us-east-1"

# Create database
aws rds create-db-instance `
  --db-instance-identifier the-combine-db `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --engine-version 15.3 `
  --master-username combine_admin `
  --master-user-password "$DB_PASSWORD" `
  --allocated-storage 20 `
  --db-name combine `
  --publicly-accessible `
  --backup-retention-period 7 `
  --region $REGION

Write-Host "Creating database... (5-10 minutes)"

# Wait for database
aws rds wait db-instance-available `
  --db-instance-identifier the-combine-db `
  --region $REGION

Write-Host "✅ Database created!"

# Get endpoint
$DB_ENDPOINT = aws rds describe-db-instances `
  --db-instance-identifier the-combine-db `
  --query 'DBInstances[0].Endpoint.Address' `
  --output text `
  --region $REGION

Write-Host "Database endpoint: $DB_ENDPOINT"

# Get security group
$DB_SG = aws rds describe-db-instances `
  --db-instance-identifier the-combine-db `
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' `
  --output text `
  --region $REGION

# Open to all IPs (development only!)
aws ec2 authorize-security-group-ingress `
  --group-id $DB_SG `
  --protocol tcp `
  --port 5432 `
  --cidr 0.0.0.0/0 `
  --region $REGION

Write-Host "✅ Database accessible from anywhere"

# Build DATABASE_URL
$DATABASE_URL = "postgresql://combine_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/combine"
Write-Host ""
Write-Host "=========================================="
Write-Host "DATABASE_URL: $DATABASE_URL"
Write-Host "=========================================="
Write-Host "SAVE THIS!"