# User Credentials Storage Guide

This document explains where and how usernames and passwords are stored in the HRSP AI Hub platform.

---

## 📍 Storage Location

### Database File Location

**Default (SQLite):**
- **File Path**: `backend/intranet.db` (or `backend/app.db` depending on configuration)
- **Location**: Relative to the backend directory where the application runs
- **Full Path Example**: `/home/ubuntu/apps/hrsp_ai_hub/backend/intranet.db`

**PostgreSQL (Production):**
- **Host**: Configured in `DATABASE_URL` environment variable
- **Database Name**: Specified in connection string
- **Default**: `hrsp_ai_hub` (if using PostgreSQL)

### Configuration

The database location is configured in `backend/.env`:

```env
# SQLite (Default - for development/prototype)
DATABASE_URL=sqlite:///./intranet.db

# PostgreSQL (Production)
DATABASE_URL=postgresql://username:password@localhost:5432/hrsp_ai_hub
```

---

## 🔐 Password Storage

### Security Implementation

**Passwords are NEVER stored in plain text!**

1. **Hashing Algorithm**: Bcrypt
2. **Salt**: Automatically generated (unique per password)
3. **Storage Format**: Hashed password string (bcrypt hash)

### How It Works

1. **Registration/Password Creation**:
   ```python
   # User provides: "myPassword123"
   # System hashes it using bcrypt
   hashed = bcrypt.hashpw(password, bcrypt.gensalt())
   # Stored in database: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY..."
   ```

2. **Login Verification**:
   ```python
   # User provides: "myPassword123"
   # System compares with stored hash
   bcrypt.checkpw(provided_password, stored_hash)
   # Returns: True or False
   ```

3. **Storage in Database**:
   - **Column**: `hashed_password` (String)
   - **Table**: `users`
   - **Example**: `$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY...`

---

## 👤 User Data Structure

### Database Schema

**Table**: `users`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key (auto-increment) |
| `email` | String | Username/email (unique, indexed) |
| `hashed_password` | String | Bcrypt hashed password |
| `full_name` | String | User's full name |
| `role` | Enum | User role (admin, employee, etc.) |
| `is_active` | Boolean | Account active status |
| `created_at` | DateTime | Account creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

### Example Record

```sql
id: 1
email: "thiachan@pseudo-ai.com"
hashed_password: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY..."
full_name: "Admin User"
role: "admin"
is_active: true
created_at: "2025-01-15 10:30:00"
updated_at: "2025-01-15 10:30:00"
```

---

## 🔍 How to Access User Data

### View Users (SQLite)

```bash
# Navigate to backend directory
cd backend

# Use SQLite command line
sqlite3 intranet.db

# View all users (passwords are hashed)
SELECT id, email, full_name, role, is_active FROM users;

# View specific user
SELECT * FROM users WHERE email = 'thiachan@pseudo-ai.com';

# Exit SQLite
.quit
```

### View Users (PostgreSQL)

```bash
# Connect to PostgreSQL
psql -U username -d hrsp_ai_hub

# View all users
SELECT id, email, full_name, role, is_active FROM users;

# View specific user
SELECT * FROM users WHERE email = 'thiachan@pseudo-ai.com';

# Exit
\q
```

### View Users via Python

```python
from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
users = db.query(User).all()

for user in users:
    print(f"Email: {user.email}")
    print(f"Name: {user.full_name}")
    print(f"Role: {user.role}")
    print(f"Password Hash: {user.hashed_password[:20]}...")  # First 20 chars only
    print("---")

db.close()
```

---

## 🔑 Default Admin Account

### Initial Setup

When you run `python init_db.py`, a default admin account is created:

- **Email**: `thiachan@pseudo-ai.com`
- **Password**: `password123`
- **Role**: `admin`
- **Status**: Active

**⚠️ IMPORTANT**: Change this password immediately in production!

### Change Default Admin Password

**Option 1: Via UI**
1. Login with default credentials
2. Go to profile/settings (if available)
3. Change password

**Option 2: Via Database**
```python
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
admin = db.query(User).filter(User.email == "thiachan@pseudo-ai.com").first()
if admin:
    admin.hashed_password = get_password_hash("new_secure_password")
    db.commit()
    print("Password updated!")
db.close()
```

**Option 3: Via Script**
```bash
cd backend
python create_admin.py
# Follow prompts to create/update admin user
```

---

## 🛡️ Security Best Practices

### Password Requirements

Currently, the system doesn't enforce password complexity, but you should:

1. **Minimum Length**: 8+ characters
2. **Complexity**: Mix of uppercase, lowercase, numbers, symbols
3. **Uniqueness**: Don't reuse passwords
4. **Regular Updates**: Change passwords periodically

### Database Security

1. **File Permissions** (SQLite):
   ```bash
   # Restrict access to database file
   chmod 600 backend/intranet.db
   ```

2. **PostgreSQL Security**:
   - Use strong database passwords
   - Restrict network access (firewall)
   - Use SSL connections
   - Regular backups

3. **Environment Variables**:
   - Never commit `.env` files to Git
   - Use strong `SECRET_KEY` for JWT tokens
   - Rotate secrets regularly

---

## 📊 User Management

### Create New User

**Via API**:
```bash
POST /api/auth/register
{
  "email": "user@company.com",
  "password": "secure_password",
  "full_name": "User Name",
  "role": "employee"
}
```

**Via Database**:
```python
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash

db = SessionLocal()
new_user = User(
    email="user@company.com",
    hashed_password=get_password_hash("secure_password"),
    full_name="User Name",
    role=UserRole.EMPLOYEE,
    is_active=True
)
db.add(new_user)
db.commit()
db.close()
```

### Reset Password

**Via Database**:
```python
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
user = db.query(User).filter(User.email == "user@company.com").first()
if user:
    user.hashed_password = get_password_hash("new_password")
    db.commit()
    print("Password reset!")
db.close()
```

### Deactivate User

```python
from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
user = db.query(User).filter(User.email == "user@company.com").first()
if user:
    user.is_active = False
    db.commit()
    print("User deactivated!")
db.close()
```

---

## 🔄 Database Migration

### Backup Database

**SQLite**:
```bash
# Backup database file
cp backend/intranet.db backend/intranet.db.backup

# Or create timestamped backup
cp backend/intranet.db backend/intranet.db.$(date +%Y%m%d_%H%M%S)
```

**PostgreSQL**:
```bash
# Backup database
pg_dump -U username hrsp_ai_hub > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U username hrsp_ai_hub < backup_20250115.sql
```

---

## 📝 Summary

- **Storage**: Database (SQLite file or PostgreSQL)
- **Location**: `backend/intranet.db` (SQLite) or PostgreSQL server
- **Password Format**: Bcrypt hashed (never plain text)
- **Default Admin**: `thiachan@pseudo-ai.com` / `password123` (change immediately!)
- **Security**: Passwords are hashed with bcrypt, never stored in plain text

---

## 🚨 Important Notes

1. **Never store passwords in plain text**
2. **Change default admin password immediately**
3. **Backup database regularly**
4. **Use strong passwords**
5. **Restrict database file access**
6. **Use PostgreSQL for production** (better security and performance)

---

For more information, see:
- `backend/app/models/user.py` - User model definition
- `backend/app/core/security.py` - Password hashing functions
- `backend/app/api/auth.py` - Authentication endpoints

