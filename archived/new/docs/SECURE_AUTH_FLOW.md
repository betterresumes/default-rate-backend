# 🔐 Secure Authentication & Invitation Flow

## 🚨 **Current Issues**
1. ❌ Users can login without email verification 
2. ❌ No OTP verification on login
3. ❌ Invitation system allows non-registered users but no clear registration flow
4. ❌ Missing secure email verification process

## ✅ **Proper Authentication Flow**

### 1. 📝 **User Registration Flow**
```
1. User submits registration (email, password, etc.)
2. System creates user with is_active=FALSE, is_verified=FALSE
3. System generates OTP and sends verification email
4. User enters OTP from email
5. System verifies OTP → sets is_verified=TRUE, is_active=TRUE
6. User can now login
```

### 2. 🔐 **Login Flow (with OTP)**
```
1. User submits email/password
2. System validates credentials
3. If valid → generates OTP and sends to email
4. User enters OTP from email  
5. System verifies OTP → issues JWT token
6. User is authenticated
```

### 3. 📧 **Organization Invitation Flow**

#### Case A: Existing User (Already Registered)
```
1. Admin invites user@example.com to organization
2. System finds existing user in database
3. System creates invitation record with token
4. System sends invitation email with accept link
5. User clicks link → auto-login and joins organization
```

#### Case B: New User (Not Registered)
```
1. Admin invites newuser@example.com to organization  
2. System doesn't find user in database
3. System creates invitation record with token
4. System sends invitation email with registration link
5. User clicks link → goes to special registration page
6. User completes registration (password, profile)
7. System auto-verifies email (since invitation came via email)
8. User is created with is_verified=TRUE, is_active=TRUE
9. User auto-joins the organization
```

## 🛠 **Implementation Plan**

### Phase 1: Fix Registration & Email Verification
- [ ] Update registration to set is_active=FALSE
- [ ] Add email verification endpoint
- [ ] Send OTP email on registration
- [ ] Add OTP verification endpoint

### Phase 2: Add Login OTP
- [ ] Update login to require OTP after password
- [ ] Send OTP email on successful password check
- [ ] Add login OTP verification endpoint

### Phase 3: Fix Invitation System
- [ ] Update invitation endpoints to handle both cases
- [ ] Add special registration-via-invitation endpoint
- [ ] Update email templates for both scenarios

## 🎯 **Email Templates Needed**
1. **Registration Verification**: "Verify your email with OTP: 123456"
2. **Login OTP**: "Your login code: 123456"  
3. **Invitation (Existing User)**: "You've been invited to join Organization X"
4. **Invitation (New User)**: "You've been invited to join Organization X - Complete your registration"

## 🔒 **Security Benefits**
- ✅ Email ownership verification
- ✅ Two-factor authentication on login
- ✅ Secure invitation system  
- ✅ Prevents unauthorized access
- ✅ Audit trail of invitations

## 📧 **Example Email Flow**

### Registration Email:
```
Subject: Verify Your Email - Default Rate Prediction

Hi John,

Your verification code is: 123456

This code expires in 10 minutes.

If you didn't create an account, please ignore this email.
```

### Login OTP Email:
```  
Subject: Login Verification Code

Hi John,

Your login code is: 789012

This code expires in 5 minutes.

If you didn't try to login, please secure your account.
```

### Invitation Email (New User):
```
Subject: You've been invited to join TechCorp

Hi sarah@example.com,

John Doe has invited you to join TechCorp organization.

Complete your registration: https://app.com/accept-invitation/abc123

This invitation expires in 7 days.
```

Would you like me to implement this secure flow?
