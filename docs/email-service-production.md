# Email Service Production Deployment Guide

## Overview

This guide covers deploying the email service to production with proper security and configuration management.

## Production Configuration Methods

### Method 1: Environment Variables (Recommended for most deployments)

Set these environment variables in your production environment:

```bash
# GoDaddy Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-production-email@yourdomain.com
SMTP_PASSWORD=your-production-app-password
SMTP_TLS=true
SMTP_SSL=false

# Email Settings
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Your Company Name
EMAIL_TO=contact@yourdomain.com
EMAIL_SUBJECT_PREFIX=[Your Company Contact]

# Security
USE_PARAMETER_STORE=false
```

### Method 2: AWS Parameter Store (Recommended for AWS deployments)

1. **Store sensitive values in AWS Systems Manager Parameter Store:**

```bash
# Store SMTP credentials securely
aws ssm put-parameter \
  --name "/accunode/smtp-username" \
  --value "your-email@yourdomain.com" \
  --type "SecureString" \
  --region your-aws-region

aws ssm put-parameter \
  --name "/accunode/smtp-password" \
  --value "your-app-password" \
  --type "SecureString" \
  --region your-aws-region

aws ssm put-parameter \
  --name "/accunode/smtp-host" \
  --value "smtp.gmail.com" \
  --type "String" \
  --region your-aws-region
```

2. **Set these environment variables:**

```bash
USE_PARAMETER_STORE=true
AWS_REGION=your-aws-region
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME=Your Company Name
EMAIL_TO=contact@yourdomain.com
EMAIL_SUBJECT_PREFIX=[Your Company Contact]
```

3. **Ensure your ECS task role has the required permissions:**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters"
            ],
            "Resource": [
                "arn:aws:ssm:region:account:parameter/accunode/smtp-*"
            ]
        }
    ]
}
```

## Platform-Specific Deployment

### AWS ECS

1. **Update your task definition environment variables:**

```json
{
    "environment": [
        {
            "name": "SMTP_HOST",
            "value": "smtp.gmail.com"
        },
        {
            "name": "SMTP_PORT", 
            "value": "587"
        },
        {
            "name": "SMTP_TLS",
            "value": "true"
        },
        {
            "name": "EMAIL_FROM",
            "value": "noreply@yourdomain.com"
        },
        {
            "name": "EMAIL_TO",
            "value": "contact@yourdomain.com"
        },
        {
            "name": "USE_PARAMETER_STORE",
            "value": "true"
        }
    ],
    "secrets": [
        {
            "name": "SMTP_USERNAME",
            "valueFrom": "arn:aws:ssm:region:account:parameter/accunode/smtp-username"
        },
        {
            "name": "SMTP_PASSWORD", 
            "valueFrom": "arn:aws:ssm:region:account:parameter/accunode/smtp-password"
        }
    ]
}
```

### Docker Compose

```yaml
version: '3.8'
services:
  backend:
    build: .
    environment:
      - SMTP_HOST=smtp.gmail.com
      - SMTP_PORT=587
      - SMTP_TLS=true
      - EMAIL_FROM=noreply@yourdomain.com
      - EMAIL_TO=contact@yourdomain.com
    secrets:
      - smtp_username
      - smtp_password

secrets:
  smtp_username:
    external: true
  smtp_password:
    external: true
```

### Heroku

```bash
# Set config vars
heroku config:set SMTP_HOST=smtp.gmail.com
heroku config:set SMTP_PORT=587
heroku config:set SMTP_TLS=true
heroku config:set SMTP_USERNAME=your-email@yourdomain.com
heroku config:set SMTP_PASSWORD=your-app-password
heroku config:set EMAIL_FROM=noreply@yourdomain.com
heroku config:set EMAIL_TO=contact@yourdomain.com
```

### Vercel

Add to `vercel.json`:

```json
{
  "env": {
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_TLS": "true",
    "EMAIL_FROM": "noreply@yourdomain.com",
    "EMAIL_TO": "contact@yourdomain.com"
  },
  "secrets": {
    "SMTP_USERNAME": "@smtp-username",
    "SMTP_PASSWORD": "@smtp-password"
  }
}
```

## GoDaddy Email Setup for Production

### 1. Create Dedicated Email Account

- Create a dedicated email account for your application (e.g., `noreply@yourdomain.com`)
- Don't use your personal email for production

### 2. Enable 2-Factor Authentication

- Log into your GoDaddy account
- Enable 2FA for security

### 3. Generate App-Specific Password

- Go to Account Settings → Security → App passwords
- Create a new app password with description "AccuNode Production API"
- Use this password as `SMTP_PASSWORD`

### 4. Configure Email Forwarding (Optional)

- Set up forwarding from your application email to your monitoring email
- This helps you receive contact form submissions

## Security Considerations

### 1. Email Rate Limiting

The service includes built-in rate limiting:
- 5 submissions per minute per IP
- Configurable in the API endpoint

### 2. Input Sanitization

All form inputs are validated and sanitized:
- Name: alphanumeric + basic punctuation only
- Email: validated email format
- Subject: printable characters only
- Message: printable characters + newlines

### 3. Secure Headers

Add security headers for the contact endpoint:

```python
# Already included in the middleware
Content-Security-Policy
X-Frame-Options
X-Content-Type-Options
```

## Monitoring and Logging

### 1. Application Logs

Monitor these log messages:
- `✅ Contact email sent successfully`
- `❌ Failed to send contact email`
- `📧 Contact form submission`

### 2. AWS CloudWatch (for AWS deployments)

Set up alerts for:
- Email send failures
- Rate limit violations
- SMTP authentication errors

### 3. Error Tracking

Common errors to monitor:
- SMTP authentication failures
- Network connectivity issues
- Invalid email addresses

## Testing Production Deployment

### 1. Health Check

```bash
curl https://your-domain.com/api/v1/contact/test-email
```

### 2. Send Test Email

```bash
curl -X POST https://your-domain.com/api/v1/contact/test-send?test_email=test@example.com
```

### 3. Full Contact Form Test

```bash
curl -X POST https://your-domain.com/api/v1/contact/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Production Test",
    "message": "Testing the contact form in production"
  }'
```

## Troubleshooting

### Common Issues

1. **"SMTP Authentication Failed"**
   - Check app-specific password is correct
   - Verify 2FA is enabled on GoDaddy account
   - Ensure username includes full email address

2. **"Connection Timeout"**
   - Check firewall allows outbound SMTP (port 587)
   - Verify SMTP host and port configuration

3. **"Rate Limited"**
   - Normal behavior for spam protection
   - Wait 1 minute between tests

4. **"Email not received"**
   - Check spam folder
   - Verify `EMAIL_TO` configuration
   - Check GoDaddy email account is active

### Debug Commands

```bash
# Check configuration
curl https://your-domain.com/api/v1/contact/test-email

# View logs
docker logs container-name
# or
kubectl logs deployment/app-name
# or
aws logs tail /aws/ecs/your-task
```

## Performance Optimization

### 1. Background Processing

Emails are sent asynchronously using FastAPI BackgroundTasks to avoid blocking the API response.

### 2. Connection Pooling

The email service creates new SMTP connections per email to ensure reliability.

### 3. Template Caching

Email templates are loaded once at startup and cached in memory.

## Backup and Recovery

### 1. Email Delivery Guarantees

- The service returns success immediately after queueing
- Background task handles actual sending
- Failed emails are logged but not retried

### 2. Contact Form Data

Consider storing contact form submissions in database for:
- Backup purposes
- Analytics
- Follow-up tracking

### 3. Configuration Backup

- Export Parameter Store values
- Document environment variable configurations
- Keep secure backups of app passwords

## Maintenance

### 1. Regular Tasks

- Monitor email delivery rates
- Check SMTP credentials validity
- Review and update rate limits
- Monitor for spam/abuse

### 2. Updates

- Keep email service dependencies updated
- Test email functionality after deployments
- Monitor for GoDaddy service changes

### 3. Scaling

- Email service scales with application instances
- No shared state or connection pools
- Stateless design for easy horizontal scaling
