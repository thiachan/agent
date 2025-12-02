# Email Verification & Password Reset Setup Guide

This guide explains how to configure email functionality for user verification and password reset.

---

## 📧 Email Configuration

### Environment Variables

Add these to your `backend/.env` file:

```env
# Email Configuration (SMTP)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@hrsp-ai-hub.com
MAIL_FROM_NAME=HRSP AI Hub
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000
# For production:
# FRONTEND_URL=https://yourdomain.com
```

---

## 🔧 Email Provider Setup

### Option 1: Gmail (Recommended for Development)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Enter "HRSP AI Hub"
   - Copy the 16-character password
3. **Use in .env**:
   ```env
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=xxxx xxxx xxxx xxxx  # The 16-char app password
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_STARTTLS=true
   ```

### Option 2: AWS SES (Recommended for Production)

1. **Verify Email Domain** in AWS SES
2. **Get SMTP Credentials** from AWS SES
3. **Use in .env**:
   ```env
   MAIL_USERNAME=your-ses-smtp-username
   MAIL_PASSWORD=your-ses-smtp-password
   MAIL_SERVER=email-smtp.us-east-1.amazonaws.com
   MAIL_PORT=587
   MAIL_STARTTLS=true
   ```

### Option 3: SendGrid

1. **Create API Key** in SendGrid
2. **Use in .env**:
   ```env
   MAIL_USERNAME=apikey
   MAIL_PASSWORD=your-sendgrid-api-key
   MAIL_SERVER=smtp.sendgrid.net
   MAIL_PORT=587
   MAIL_STARTTLS=true
   ```

### Option 4: Mailgun

1. **Get SMTP Credentials** from Mailgun
2. **Use in .env**:
   ```env
   MAIL_USERNAME=postmaster@your-domain.mailgun.org
   MAIL_PASSWORD=your-mailgun-password
   MAIL_SERVER=smtp.mailgun.org
   MAIL_PORT=587
   MAIL_STARTTLS=true
   ```

---

## 🚀 Features Implemented

### 1. Email Verification

**Flow:**
1. User registers → Account created with `is_verified=False`
2. Verification email sent with unique token
3. User clicks link → Email verified → `is_verified=True`
4. User can now login

**Endpoints:**
- `POST /api/auth/register` - Register (sends verification email)
- `POST /api/auth/verify-email` - Verify email with token
- `POST /api/auth/resend-verification` - Resend verification email

**Frontend Pages:**
- `/verify-email?token=...` - Email verification page

### 2. Password Reset

**Flow:**
1. User clicks "Forgot Password"
2. Enters email → Reset token generated
3. Reset email sent with token (expires in 1 hour)
4. User clicks link → Enters new password
5. Password updated → User can login

**Endpoints:**
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password with token

**Frontend Pages:**
- `/reset-password?token=...` - Password reset page

---

## 🔒 Security Features

1. **Token Expiration**:
   - Verification tokens: 24 hours
   - Reset tokens: 1 hour

2. **Secure Tokens**:
   - Generated using `secrets.token_urlsafe(32)`
   - Cryptographically secure random tokens

3. **Email Privacy**:
   - "If email exists" messages prevent email enumeration
   - Don't reveal if email is registered or not

4. **Password Requirements**:
   - Minimum 8 characters
   - Validated on reset

---

## 🧪 Testing Without Email (Development)

If email is not configured, the system will:
- Log verification/reset tokens to console
- Log verification/reset URLs to console
- Still function, but emails won't be sent

**Example Console Output:**
```
WARNING: Email service disabled - verification email not sent to user@example.com
WARNING: Verification token for user@example.com: abc123...
WARNING: Verification URL: http://localhost:3000/verify-email?token=abc123...
```

You can manually copy the URL from logs and test the flow.

---

## 📝 Database Migration

If you have an existing database, you need to add the new columns:

**SQLite:**
```sql
ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_token TEXT;
ALTER TABLE users ADD COLUMN verification_token_expires DATETIME;
ALTER TABLE users ADD COLUMN reset_token TEXT;
ALTER TABLE users ADD COLUMN reset_token_expires DATETIME;
```

**PostgreSQL:**
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token_expires TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;
```

**Or recreate database:**
```bash
# Backup existing database
cp backend/intranet.db backend/intranet.db.backup

# Delete and recreate
rm backend/intranet.db
python backend/init_db.py
```

---

## ✅ Verification Checklist

- [ ] Email credentials configured in `.env`
- [ ] `FRONTEND_URL` set correctly
- [ ] Test registration → Check email received
- [ ] Test verification link → User can login
- [ ] Test forgot password → Check email received
- [ ] Test reset password → User can login with new password
- [ ] Test expired token handling
- [ ] Test resend verification

---

## 🐛 Troubleshooting

### Emails Not Sending

1. **Check credentials**:
   ```bash
   # Test SMTP connection
   python -c "from app.services.email_service import email_service; print('Enabled:', email_service.enabled)"
   ```

2. **Check logs**:
   - Look for email service warnings/errors
   - Check SMTP connection errors

3. **Test SMTP manually**:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-app-password')
   server.quit()
   ```

### Verification Link Not Working

1. **Check token in URL** - Should be long random string
2. **Check expiration** - Token expires after 24 hours
3. **Check frontend URL** - Must match `FRONTEND_URL` in `.env`
4. **Check database** - Verify token exists and not expired

### Password Reset Link Not Working

1. **Check token expiration** - Only valid for 1 hour
2. **Check if user is verified** - Must verify email before password reset
3. **Check token in database** - Should match URL token

---

## 📚 API Reference

### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "User Name",
  "role": "employee"
}
```

**Response:**
```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "email_sent": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "User Name",
    "is_verified": false
  }
}
```

### Verify Email
```http
POST /api/auth/verify-email
Content-Type: application/json

{
  "token": "verification-token-from-email"
}
```

### Forgot Password
```http
POST /api/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

### Reset Password
```http
POST /api/auth/reset-password
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "newSecurePassword123"
}
```

---

For more details, see the implementation in:
- `backend/app/services/email_service.py` - Email sending service
- `backend/app/api/auth.py` - Authentication endpoints
- `src/app/verify-email/page.tsx` - Verification page
- `src/app/reset-password/page.tsx` - Reset password page


