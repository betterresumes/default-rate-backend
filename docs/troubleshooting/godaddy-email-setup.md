# GoDaddy Email Configuration Guide

## 🎯 How to Get Email Variables from GoDaddy

This guide will walk you through getting the exact values needed for your `.env` file from your GoDaddy email account.

## 📧 Variables You Need to Get

From your `.env.test` file, you need to replace these placeholder values:

```bash
SMTP_USERNAME=your-godaddy-email@yourdomain.com     # ← Replace this
SMTP_PASSWORD=your-app-specific-password            # ← Replace this  
EMAIL_FROM=noreply@yourdomain.com                   # ← Replace this
EMAIL_TO=contact@yourdomain.com                     # ← Replace this
```

## 🔐 Step-by-Step GoDaddy Setup

### Step 1: Log into GoDaddy Email

1. Go to [https://www.godaddy.com](https://www.godaddy.com)
2. Sign in to your GoDaddy account
3. Go to **"Email & Office"** or **"Workspace Email"**
4. Click **"Manage"** next to your email plan
5. Click **"Webmail"** to access your email

### Step 2: Find Your Email Address (`SMTP_USERNAME`)

Your `SMTP_USERNAME` is simply your full GoDaddy email address.

**Examples:**
- If you own `yourdomain.com` and have an email `info@yourdomain.com`
- Then `SMTP_USERNAME=info@yourdomain.com`

**Common GoDaddy email patterns:**
```bash
# If you have a custom domain
SMTP_USERNAME=info@yourdomain.com
SMTP_USERNAME=contact@yourdomain.com  
SMTP_USERNAME=noreply@yourdomain.com

# If you're using GoDaddy's email hosting
SMTP_USERNAME=yourname@yourdomain.com
```

### Step 3: Generate App-Specific Password (`SMTP_PASSWORD`)

**⚠️ Important:** You CANNOT use your regular email password. You must create an "App Password".

#### Option A: If you have GoDaddy Workspace Email

1. Log into your GoDaddy Workspace Email
2. Click your profile icon (top right)
3. Go to **"Account Settings"**
4. Click **"Security"** tab
5. Look for **"App Passwords"** or **"Application-Specific Passwords"**
6. Click **"Generate New App Password"**
7. Enter description: `AccuNode Backend API`
8. Copy the generated password → This is your `SMTP_PASSWORD`

#### Option B: If you have Gmail through GoDaddy

Some GoDaddy plans use Gmail interface:

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Sign in with your GoDaddy email
3. Go to **"Security"** 
4. Enable **"2-Step Verification"** (required)
5. Go back to **"Security"**
6. Click **"App passwords"**
7. Select **"Mail"** and **"Other (custom name)"**
8. Enter: `AccuNode API`
9. Click **"Generate"**
10. Copy the 16-character password → This is your `SMTP_PASSWORD`

#### Option C: Check GoDaddy Email Settings

1. In GoDaddy account, go to **"Email & Office"**
2. Click **"Manage"** next to your email
3. Look for **"Email Settings"** or **"SMTP Settings"**
4. There might be an option to **"Generate App Password"**

### Step 4: Set EMAIL_FROM and EMAIL_TO

#### EMAIL_FROM (Sender Address)
This should be the same as your `SMTP_USERNAME` or a valid email from your domain:

```bash
# Use the same email as SMTP_USERNAME
EMAIL_FROM=info@yourdomain.com

# Or create a "noreply" address if you have it
EMAIL_FROM=noreply@yourdomain.com
```

#### EMAIL_TO (Where contact emails go)
This is where you want to receive the contact form submissions:

```bash
# Your main business email
EMAIL_TO=contact@yourdomain.com

# Or your personal email  
EMAIL_TO=yourname@yourdomain.com

# Or the same as SMTP_USERNAME
EMAIL_TO=info@yourdomain.com
```

## 🧪 Example Configuration

Here's what your `.env.test` might look like with real values:

```bash
# Example if your domain is "mycompany.com"
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=info@mycompany.com
SMTP_PASSWORD=abcd efgh ijkl mnop              # ← 16-char app password
SMTP_TLS=true
SMTP_SSL=false

EMAIL_FROM=noreply@mycompany.com               # ← Sender address
EMAIL_FROM_NAME=MyCompany Contact
EMAIL_TO=contact@mycompany.com                 # ← Where emails go
EMAIL_SUBJECT_PREFIX=[MyCompany Contact]
```

## 🔍 How to Find Your Domain and Email Options

### Check Your GoDaddy Products:

1. Log into GoDaddy
2. Go to **"My Products"**
3. Look for:
   - **Domain names** you own
   - **Email & Office** plans
   - **Workspace Email** subscriptions

### Common GoDaddy Email Plans:

- **Professional Email** - Uses GoDaddy interface
- **Workspace Email** - Uses Gmail/Outlook interface  
- **Email Essentials** - Basic email hosting

## 🚨 Troubleshooting Common Issues

### Issue 1: "Can't find App Passwords option"

**Solutions:**
- Make sure 2-Factor Authentication is enabled
- Try logging into the actual email interface (Webmail)
- Look in "Security" or "Advanced Settings"
- Contact GoDaddy support if the option is missing

### Issue 2: "Don't have a custom domain email"

**Solutions:**
- You might be using a free email (Gmail, Yahoo, etc.)
- Check if you have a GoDaddy domain with email included
- Consider upgrading to include email with your domain

### Issue 3: "Authentication Failed" when testing

**Possible causes:**
- Using regular password instead of app password
- Wrong email address format
- 2FA not enabled
- App password expired

## 📞 Getting Help from GoDaddy

If you're stuck, contact GoDaddy support:

1. **Phone:** Call the number on your GoDaddy account
2. **Chat:** Use the chat option in your GoDaddy dashboard
3. **Email:** Submit a support ticket

**Tell them:** "I need to set up SMTP access for my email account to send emails from my application. I need help generating an app-specific password."

## ✅ Testing Your Configuration

Once you have the values, update your `.env.test` file and run:

```bash
cd /Users/nikhil/Downloads/pranit/work/final/default-rate/backend
source venv/bin/activate
python test_email_service.py
```

This will test your email configuration and tell you if everything is working correctly.

## 🎯 Quick Checklist

- [ ] Found your GoDaddy email address (`SMTP_USERNAME`)
- [ ] Generated app-specific password (`SMTP_PASSWORD`)  
- [ ] Set sender email (`EMAIL_FROM`)
- [ ] Set recipient email (`EMAIL_TO`)
- [ ] Updated `.env.test` file
- [ ] Ran test script to verify everything works

## 💡 Pro Tips

1. **Use a dedicated email** like `noreply@yourdomain.com` for sending
2. **Keep app passwords secure** - treat them like regular passwords
3. **Test in development first** before deploying to production
4. **Set up email forwarding** so contact emails reach your main inbox

---

Need more help? The email service test script will give you detailed error messages to help troubleshoot any issues!
