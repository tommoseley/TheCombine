# The Combine - Route 53 DNS + ACM Certificate

# ACM Certificate for custom domain
resource "aws_acm_certificate" "main" {
  domain_name       = var.domain_name
  validation_method = "DNS"
  
  lifecycle {
    create_before_destroy = true
  }
  
  tags = {
    Name = "${var.app_name}-cert"
  }
}

# DNS validation records for ACM
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  
  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.route53_zone_id
}

# Wait for certificate validation
resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
  
  timeouts {
    create = "10m"
  }
}

# App Runner custom domain association
resource "aws_apprunner_custom_domain_association" "main" {
  domain_name = var.domain_name
  service_arn = aws_apprunner_service.main.arn
  
  # App Runner manages its own certificate, but we create one for validation
  # The certificate_validation_records output will have CNAME records to add
}

# Route 53 records for App Runner custom domain
# App Runner provides the target - we need to create CNAME/ALIAS records
resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "CNAME"
  ttl     = 300
  records = [aws_apprunner_service.main.service_url]
}

# Note: App Runner custom domains require additional CNAME validation records
# These are output below - you may need to add them manually or via a second apply

output "domain_name" {
  description = "Custom domain"
  value       = var.domain_name
}

output "apprunner_domain_validation_records" {
  description = "DNS validation records for App Runner custom domain (add these to Route 53)"
  value       = aws_apprunner_custom_domain_association.main.certificate_validation_records
}

output "certificate_arn" {
  description = "ACM certificate ARN"
  value       = aws_acm_certificate.main.arn
}
