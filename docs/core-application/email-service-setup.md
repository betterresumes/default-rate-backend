# Email Service Setup Guide

This guide explains how to set up the email service for handling contact form submissions from your frontend.

## Overview

The email service enables your application to:
- Receive contact form submissions from the frontend
- Send formatted emails to your designated email address
- Handle rate limiting to prevent spam
- Work with GoDaddy Gmail SMTP configuration

## API Endpoints

### 1. Submit Contact Form
```
POST /api/v1/contact/submit
```

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com", 
  "subject": "Question about your services",
  "message": "Hi, I'm interested in learning more about your platform..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Your message has been sent successfully! We'll get back to you soon.",
  "reference_id": "cf_20241006_123456_abc123de"
}
```

**Rate Limiting:** 5 submissions per minute per IP address

### 2. Test Email Configuration (Development)
```
GET /api/v1/contact/test-email
```

### 3. Send Test Email (Development)
```
POST /api/v1/contact/test-send?test_email=test@example.com
```

## Setup Instructions

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   
   Copy `.env.example` to `.env` and update the email settings:
   ```bash
   cp .env.example .env
   ```

   Update these variables in your `.env` file:
   ```bash
   # Email Configuration (GoDaddy Gmail SMTP)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@yourdomain.com
   SMTP_PASSWORD=your-app-password
   SMTP_TLS=true
   SMTP_SSL=false
   
   # Email Settings
   EMAIL_FROM=noreply@yourdomain.com
   EMAIL_FROM_NAME=Your Company Name
   EMAIL_TO=contact@yourdomain.com
   EMAIL_SUBJECT_PREFIX=[Your Company Contact]
   ```

3. **GoDaddy Gmail Setup**
   
   a) Log into your GoDaddy email account
   b) Enable 2-factor authentication if not already enabled
   c) Generate an app-specific password:
      - Go to Account Settings → Security → App passwords
      - Create a new app password for "FastAPI Application"
      - Use this app password as `SMTP_PASSWORD` (not your regular password)

4. **Test the Configuration**
   ```bash
   # Start the application
   python main.py
   
   # Test email configuration
   curl http://localhost:8000/api/v1/contact/test-email
   
   # Send a test email
   curl -X POST "http://localhost:8000/api/v1/contact/test-send?test_email=your-email@example.com"
   ```

### Production Deployment

For production, use environment variables or AWS Parameter Store:

1. **Environment Variables Method**
   Set these environment variables in your deployment platform:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-production-email@yourdomain.com
   SMTP_PASSWORD=your-production-app-password
   EMAIL_FROM=noreply@yourdomain.com
   EMAIL_FROM_NAME=Your Company Name
   EMAIL_TO=contact@yourdomain.com
   EMAIL_SUBJECT_PREFIX=[Your Company Contact]
   ```

2. **AWS Parameter Store Method**
   
   Store sensitive values in AWS Systems Manager Parameter Store:
   ```bash
   aws ssm put-parameter --name "/accunode/smtp-username" --value "your-email@yourdomain.com" --type "SecureString"
   aws ssm put-parameter --name "/accunode/smtp-password" --value "your-app-password" --type "SecureString"
   ```

   Set these environment variables:
   ```bash
   USE_PARAMETER_STORE=true
   AWS_REGION=your-aws-region
   ```

## Frontend Integration

### React/Next.js Example

```javascript
async function submitContactForm(formData) {
  try {
    const response = await fetch('/api/v1/contact/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData),
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert('Message sent successfully!');
      // Clear form or show success message
    } else {
      alert('Failed to send message. Please try again.');
    }
  } catch (error) {
    console.error('Error submitting form:', error);
    alert('An error occurred. Please try again.');
  }
}

// Usage
const formData = {
  name: 'John Doe',
  email: 'john@example.com',
  subject: 'Question about services',
  message: 'Your message here...'
};

submitContactForm(formData);
```

### HTML Form Example

```html
<form id="contactForm">
  <input type="text" name="name" placeholder="Your Name" required>
  <input type="email" name="email" placeholder="Your Email" required>
  <input type="text" name="subject" placeholder="Subject" required>
  <textarea name="message" placeholder="Your Message" required></textarea>
  <button type="submit">Send Message</button>
</form>

<script>
document.getElementById('contactForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());
  
  try {
    const response = await fetch('/api/v1/contact/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert('Message sent successfully!');
      e.target.reset();
    } else {
      alert('Failed to send message.');
    }
  } catch (error) {
    alert('An error occurred.');
  }
});
</script>
```

## Security Features

- **Rate Limiting**: 5 submissions per minute per IP address
- **Input Validation**: All form fields are validated and sanitized
- **Email Validation**: Email addresses are validated using proper regex
- **CORS Protection**: Configured through FastAPI CORS middleware
- **Async Processing**: Email sending happens in background to prevent blocking

## Troubleshooting

### Common Issues

1. **"SMTP credentials not configured"**
   - Check that `SMTP_USERNAME` and `SMTP_PASSWORD` are set
   - Verify the app password is correct (not your regular password)

2. **"Authentication failed"**
   - Ensure 2FA is enabled on your GoDaddy account
   - Generate a new app-specific password
   - Check that the username includes the full email address

3. **"Rate limit exceeded"**
   - Wait 1 minute between submissions from the same IP
   - This is normal spam protection

4. **Emails not being received**
   - Check spam folder
   - Verify `EMAIL_TO` is set correctly
   - Test with the `/test-email` endpoint first

### Logs

Check application logs for detailed error messages:
```bash
# View logs in development
python main.py

# View logs in production (Docker)
docker logs container-name

# View logs in AWS ECS
aws logs tail /aws/ecs/your-task-definition
```

## Email Template Customization

The email template is located at:
`app/templates/email/contact_form.html`

You can customize the HTML template to match your branding. The template uses Jinja2 templating with these variables:
- `{{ name }}` - Sender's name
- `{{ email }}` - Sender's email
- `{{ subject }}` - Email subject
- `{{ message }}` - Message content
- `{{ timestamp }}` - Submission timestamp
- `{{ user_ip }}` - Sender's IP (optional)
- `{{ user_agent }}` - Browser user agent (optional)

## API Documentation

Once the application is running, you can view the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The contact endpoints will be listed under the "Contact" section.
