# Load Balancer Setup

Complete guide for configuring the AWS Application Load Balancer (ALB) for AccuNode.

## Overview

The AccuNode application uses an AWS Application Load Balancer to:
- Route HTTPS traffic to ECS Fargate containers
- Terminate SSL/TLS certificates
- Provide health checks and auto-scaling integration
- Enable high availability across multiple AZs

## Load Balancer Configuration

### 1. Application Load Balancer (ALB)

**Load Balancer Settings**:
```yaml
Name: accunode-alb
Scheme: Internet-facing
IP Address Type: IPv4
VPC: accunode-vpc
Availability Zones:
  - us-east-1a: accunode-public-subnet-1
  - us-east-1b: accunode-public-subnet-2
```

**Security Group**: `accunode-alb-sg`
- **Inbound Rules**:
  - HTTP (80): 0.0.0.0/0 → Redirect to HTTPS
  - HTTPS (443): 0.0.0.0/0 → Forward to targets
- **Outbound Rules**:
  - All traffic: 0.0.0.0/0

### 2. Target Group Configuration

**Target Group**: `accunode-tg`
```yaml
Target Type: IP addresses
Protocol: HTTP
Port: 8000
VPC: accunode-vpc

Health Check:
  Protocol: HTTP
  Path: /health
  Port: traffic-port
  Healthy Threshold: 2
  Unhealthy Threshold: 5
  Timeout: 5 seconds
  Interval: 30 seconds
  Success Codes: 200
```

**Target Registration**:
- Targets are automatically registered by ECS Service
- Dynamic port mapping with Fargate networking
- Cross-AZ load balancing enabled

### 3. SSL/TLS Configuration

**Certificate Manager**:
```yaml
Domain Names:
  - api.accunode.com
  - *.accunode.com
Validation Method: DNS
Certificate Authority: Amazon CA
Auto-renewal: Enabled
```

**SSL Policy**: `ELBSecurityPolicy-TLS-1-2-2017-01`
- Minimum TLS version: 1.2
- Supported cipher suites: Modern security standards

### 4. Listener Configuration

**HTTPS Listener (Port 443)**:
```yaml
Default Actions:
  - Type: forward
    Target Group: accunode-tg
    
Rules:
  - IF: Host header = api.accunode.com
    THEN: Forward to accunode-tg
  - IF: Path pattern = /api/v1/health
    THEN: Return fixed response (Health check bypass)
```

**HTTP Listener (Port 80)**:
```yaml
Default Actions:
  - Type: redirect
    Redirect Config:
      Protocol: HTTPS
      Port: 443
      Status Code: HTTP_301
```

## Terraform Configuration

### Load Balancer Resource

```hcl
resource "aws_lb" "accunode_alb" {
  name               = "accunode-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets           = [
    aws_subnet.public_subnet_1.id,
    aws_subnet.public_subnet_2.id
  ]

  enable_deletion_protection = false
  enable_http2              = true

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "accunode-alb"
    enabled = true
  }

  tags = {
    Name        = "AccuNode ALB"
    Environment = "production"
    Project     = "AccuNode"
  }
}
```

### Target Group

```hcl
resource "aws_lb_target_group" "accunode_tg" {
  name     = "accunode-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 5
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "AccuNode Target Group"
  }
}
```

### Listeners

```hcl
# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.accunode_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.accunode_cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.accunode_tg.arn
  }
}

# HTTP Listener (Redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.accunode_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

## Security Groups

### ALB Security Group

```hcl
resource "aws_security_group" "alb_sg" {
  name        = "accunode-alb-sg"
  description = "Security group for AccuNode ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "AccuNode ALB SG"
  }
}
```

## Health Check Configuration

The ALB performs health checks on the `/health` endpoint:

### Health Check Response Format

```json
{
  "status": "healthy",
  "service": "accunode-api",
  "version": "2.0.0",
  "timestamp": "2025-10-05T12:00:00Z",
  "checks": {
    "database": "connected",
    "redis": "connected",
    "ml_models": "loaded"
  }
}
```

### Health Check Implementation

The health endpoint is implemented in FastAPI:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "accunode-api",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Monitoring and Logging

### CloudWatch Metrics

The ALB automatically reports these metrics:
- `RequestCount`: Number of requests processed
- `TargetResponseTime`: Average response time from targets
- `HTTPCode_Target_2XX_Count`: Successful responses
- `HTTPCode_Target_4XX_Count`: Client errors
- `HTTPCode_Target_5XX_Count`: Server errors
- `HealthyHostCount`: Number of healthy targets
- `UnHealthyHostCount`: Number of unhealthy targets

### Access Logs

ALB access logs are stored in S3:
```
s3://accunode-alb-logs/
├── AWSLogs/
│   └── {account-id}/
│       └── elasticloadbalancing/
│           └── us-east-1/
│               └── 2025/10/05/
│                   └── access_logs
```

## Custom Domain Setup

### Route 53 Configuration

```hcl
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.accunode.zone_id
  name    = "api.accunode.com"
  type    = "A"

  alias {
    name                   = aws_lb.accunode_alb.dns_name
    zone_id                = aws_lb.accunode_alb.zone_id
    evaluate_target_health = true
  }
}
```

### SSL Certificate

```hcl
resource "aws_acm_certificate" "accunode_cert" {
  domain_name               = "api.accunode.com"
  subject_alternative_names = ["*.accunode.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "AccuNode SSL Certificate"
  }
}
```

## Deployment Commands

### Deploy Load Balancer

```bash
# Initialize Terraform
terraform init

# Plan ALB deployment
terraform plan -target=aws_lb.accunode_alb

# Apply ALB configuration
terraform apply -target=aws_lb.accunode_alb

# Verify deployment
aws elbv2 describe-load-balancers --names accunode-alb
```

### Update Target Group

```bash
# Modify target group settings
terraform plan -target=aws_lb_target_group.accunode_tg
terraform apply -target=aws_lb_target_group.accunode_tg

# Check target health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/accunode-tg/ID
```

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check ECS service health
   - Verify security group rules
   - Check target group health

2. **SSL Certificate Issues**
   - Verify DNS validation records
   - Check certificate status in ACM
   - Ensure correct listener configuration

3. **Health Check Failures**
   - Verify `/health` endpoint response
   - Check container logs
   - Review security group rules

### Debugging Commands

```bash
# Check ALB status
aws elbv2 describe-load-balancers --names accunode-alb

# View target health
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN

# Check SSL certificate
aws acm describe-certificate --certificate-arn CERT_ARN

# View access logs
aws s3 ls s3://accunode-alb-logs/ --recursive
```

---

*For additional support, refer to the [AWS Infrastructure Issues](../troubleshooting/aws-infrastructure-issues.md) troubleshooting guide.*
