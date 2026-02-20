# Complete Onboarding & Deployment Guide - AGENT Platform

**Status**: ✅ Production-Ready  
**Last Updated**: January 13, 2026  
**Version**: 1.0.0 (VSCode Optimized v1)

---

## 📋 Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Full Onboarding Process](#full-onboarding-process)
3. [Deployment Checklist](#deployment-checklist)
4. [Troubleshooting](#troubleshooting)
5. [Verification Steps](#verification-steps)

---

## Quick Start

### For Development (Local Machine)

```bash
# 1. Clone repository and checkout latest stable branch
git clone https://github.com/thiachan/agent.git
cd agent
git checkout vscode-optimized-v1  # ⭐ Latest stable version with all improvements

# 2. Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup frontend (in new terminal)
cd ..
npm install

# 4. Create environment files
cd backend
nano .env  # Copy template from "Environment Configuration" section below
cd ..
nano .env.local
# Add: NEXT_PUBLIC_API_URL=http://localhost:8000

# 5. Initialize database
cd backend
python init_db.py

# 6. Start backend (terminal 1)
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 7. Start frontend (terminal 2)
cd ..
npm run dev

# 8. Access application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Default login: thiachan@pseudo-ai.com / password123
```

⭐ **Important Notes**:
- Always checkout `vscode-optimized-v1` branch for latest stable version
- There is no `.env.example` - copy the template from the Environment Configuration section
- Create `.env` in `backend/` and `.env.local` in project root
- Change default admin password before production use


### For Production (AWS EC2)

```bash
ssh -i "your-key.pem" ubuntu@<EC2_PUBLIC_IP>

# 1. Run setup script
chmod +x setup-ubuntu.sh
./setup-ubuntu.sh

# 2. Clone repository and checkout latest stable branch
git clone https://github.com/thiachan/agent.git
cd agent
git checkout vscode-optimized-v1  # ⭐ Latest stable version with all improvements

# 3. Create environment configuration (see template in Environment Configuration section)
nano backend/.env
# Copy all required variables from the template below

# 4. Initialize database and build frontend
cd backend
source venv/bin/activate
python init_db.py
cd ..
npm run build

# 5. Start services
./start-services.sh

# 6. Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/agent.alexcty.com
# Copy configuration from Nginx Configuration section

# 7. Enable and reload Nginx
sudo ln -s /etc/nginx/sites-available/agent.alexcty.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 8. Test and verify
curl http://localhost:8000/health
curl http://localhost:3000
curl https://yourdomain.com/api/health  # After Nginx is configured
```

⭐ **Critical for Production**:
- Checkout `vscode-optimized-v1` branch for all improvements
- Configure all required `.env` variables before starting services
- Set up Nginx reverse proxy for SSL/HTTPS
- Change default admin password from "password123"
- Use AWS Secrets Manager for storing sensitive credentials


---

## Full Onboarding Process

### Phase 1: Prerequisites & Environment Setup

#### 1.1 System Requirements

**Minimum for Development:**
- Python 3.10+
- Node.js 18.x+
- 4GB RAM
- 10GB disk space

**Minimum for Production (AWS EC2):**
- Instance Type: `t3.large` or larger (2+ vCPU, 8GB+ RAM)
- OS: Ubuntu 22.04 LTS
- Storage: 30GB (scalable)
- Security Group: SSH (22), HTTP (80), HTTPS (443), TCP 8000 (backend), TCP 3000 (frontend)

#### 1.2 Environment Variables Configuration

Create `backend/.env` with the following essential variables (see template below):

```bash
cd backend
nano .env  # Or use your preferred editor
```

Add the following content to `backend/.env`:
# ==============================================================================
# ESSENTIAL ENVIRONMENT VARIABLES (Minimal Production Config)
# ==============================================================================

# Core API
SECRET_KEY=your-secure-random-key-here-min-32-chars

# Database
DATABASE_URL=sqlite:///./intranet.db
# For PostgreSQL (production): DATABASE_URL=postgresql://user:password@localhost:5432/agent

# OpenAI API (for TTS/embeddings and RAG)
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_TTS_VOICE_HOST=nova      # Options: alloy, echo, fable, onyx, nova, shimmer
OPENAI_TTS_VOICE_GUEST=onyx     # Options: alloy, echo, fable, onyx, nova, shimmer

# Cisco OpenAI (GPT-4.1 via OAuth2)
CISCO_CLIENT_ID=your-client-id
CISCO_CLIENT_SECRET=your-client-secret
CISCO_ENDPOINT=https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions
CISCO_APPKEY=your-app-key

# Presenton PowerPoint Generation
PRESENTON_API_URL=https://api.presenton.ai  # Or internal ECS: http://172.31.10.166:80
PRESENTON_REQUIRE_AUTH=false
PRESENTON_MAX_SLIDES=12

# Email Configuration (Gmail example - see EMAIL_VERIFICATION_SETUP.md for other providers)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password  # Not your regular password - use App Password
MAIL_FROM=noreply@agent.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000
# Production: FRONTEND_URL=https://yourdomain.com
```

**⚠️ Critical Security Notes:**
- Change `SECRET_KEY` to a random secure value (min 32 characters)
- Never commit `.env` to git (already in `.gitignore`)
- For production, use secure secret management (AWS Secrets Manager)
- Use environment-specific `.env` files or configuration management

### 1.3 Git Setup

```bash
# Clone the repository
git clone https://github.com/thiachan/agent.git
cd agent

# Checkout vscode-optimized-v1 branch (latest stable with all improvements)
git checkout vscode-optimized-v1

# Verify you're on the correct branch
git branch -v  # Should show: * vscode-optimized-v1
```

---

### Phase 2: Backend Setup

#### 2.1 Create Python Virtual Environment

```bash
cd backend

# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate              # Linux/Mac
# OR
venv\Scripts\activate                 # Windows
```

#### 2.2 Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(fastapi|uvicorn|chromadb|langchain|sqlalchemy)"
```

#### 2.3 Initialize Database

```bash
# Create database and tables
python init_db.py

# Output should show:
# Database initialized successfully!
# Default admin user created!
#    Email: thiachan@pseudo-ai.com
#    Password: password123

# Verify SQLite database was created
ls -lh intranet.db
```

#### 2.4 Verify Backend Configuration

```bash
# Check that all imports work
python -c "from app.main import app; print('✅ Backend imports successful')"

# Check critical packages
python -c "import chromadb; import langchain; import fastapi; print('✅ All packages available')"
```

---

### Phase 3: Frontend Setup

#### 3.1 Install Node.js Dependencies

```bash
cd /path/to/AGENT  # Back to root directory

# Install npm packages
npm install

# Verify installation
npm list next react typescript
```

#### 3.2 Create Frontend Environment File

Create `.env.local` in the project root:

```env
# Frontend API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
# Production: NEXT_PUBLIC_API_URL=https://yourdomain.com/api
```

#### 3.3 Build Frontend (Production)

```bash
# Build optimized production bundle
npm run build

# Output should show:
# ✓ Compiled successfully
# ✓ Generating static pages (6/6)

# Check build output
ls -la .next/
```

---

### Phase 4: Service Startup & Verification

#### 4.1 Start Backend Service

**Development:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Production:**
```bash
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

**Using Systemd (Recommended for Production):**
```bash
# Create service file
sudo tee /etc/systemd/system/agent-backend.service > /dev/null << EOF
[Unit]
Description=AGENT AI Platform Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AGENT/backend
ExecStart=/home/ubuntu/AGENT/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable agent-backend
sudo systemctl start agent-backend
sudo systemctl status agent-backend
```

#### 4.2 Start Frontend Service

**Development:**
```bash
npm run dev
```

**Production:**
```bash
# Build first
npm run build

# Start production server
npm start

# Or using nohup
nohup npm start > frontend.log 2>&1 &
```

#### 4.3 Verify Services are Running

```bash
# Check backend health
curl -s http://localhost:8000/health
# Expected: {"status":"healthy"}

# Check frontend is accessible
curl -s http://localhost:3000 | head -20
# Expected: HTML content with "AI Intranet" title

# View API documentation
# Open browser: http://localhost:8000/docs
```

---

### Phase 5: Production Nginx Configuration

#### 5.1 Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/agent.alexcty.com`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name agent.alexcty.com www.agent.alexcty.com;
    return 301 https://$server_name$request_uri;
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    server_name agent.alexcty.com www.agent.alexcty.com;

    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/agent.alexcty.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/agent.alexcty.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # File upload limits (100MB)
    client_max_body_size 100M;

    # Frontend - Next.js on port 3000
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Backend API - FastAPI on port 8000
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;  # Important for large uploads
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # Static files caching
    location /_next/static {
        expires 365d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 5.2 Enable Nginx Configuration

```bash
# Create symlink to enable site
sudo ln -s /etc/nginx/sites-available/agent.alexcty.com \
           /etc/nginx/sites-enabled/agent.alexcty.com

# Test Nginx syntax
sudo nginx -t
# Expected: nginx: configuration file syntax is ok

# Reload Nginx
sudo systemctl reload nginx

# Verify status
sudo systemctl status nginx
```

#### 5.3 Setup SSL Certificate (Let's Encrypt)

```bash
# Get SSL certificate
sudo certbot certonly --nginx -d agent.alexcty.com -d www.agent.alexcty.com

# Renew automatically
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

### Phase 6: Email Configuration (Optional)

See [EMAIL_VERIFICATION_SETUP.md](docs/EMAIL_VERIFICATION_SETUP.md) for complete setup.

**Quick Setup (Gmail):**
1. Enable 2-Factor Authentication: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Add to `.env`:
```env
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All `.env` variables configured correctly
- [ ] Database initialized with `python init_db.py`
- [ ] Backend dependencies installed: `pip install -r requirements.txt`
- [ ] Frontend dependencies installed: `npm install`
- [ ] Frontend built: `npm run build`
- [ ] Backend health check passes: `curl http://localhost:8000/health`
- [ ] Frontend loads: `curl http://localhost:3000`
- [ ] API documentation accessible: `curl http://localhost:8000/docs`

### AWS EC2 Deployment

- [ ] EC2 instance created (t3.large or larger)
- [ ] Security groups configured (ports 22, 80, 443, 8000, 3000)
- [ ] Ubuntu 22.04 LTS installed
- [ ] SSH key pair secured
- [ ] Setup script executed: `./setup-ubuntu.sh`
- [ ] Repository cloned
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Services started (backend + frontend)
- [ ] Systemd services created and enabled
- [ ] Nginx configured and reloaded
- [ ] SSL certificate configured
- [ ] Domain DNS records pointing to EC2 IP

### Post-Deployment

- [ ] HTTPS working: `curl https://yourdomain.com`
- [ ] Backend API responding: `curl https://yourdomain.com/api/health`
- [ ] Frontend loading: `curl https://yourdomain.com`
- [ ] Chat functionality working (test with login)
- [ ] File upload working (< 100MB)
- [ ] Generation features working (PowerPoint, PDF, Speech, Podcast)
- [ ] Email verification working (if configured)
- [ ] Error logs monitored: `tail -f backend.log`
- [ ] Nginx logs monitored: `sudo tail -f /var/log/nginx/access.log`

### Monitoring & Maintenance

- [ ] Set up log rotation for backend.log
- [ ] Configure backup for SQLite database (or migrate to PostgreSQL)
- [ ] Set up monitoring/alerting (CloudWatch, Prometheus, etc.)
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`
- [ ] SSL certificate auto-renewal enabled

---

## Troubleshooting

### Backend Issues

#### Backend not starting
```bash
# Check logs
tail -f /home/ubuntu/AGENT/backend/backend.log

# Verify venv activated
source /home/ubuntu/AGENT/backend/venv/bin/activate

# Verify port 8000 is free
lsof -i :8000

# Check Python packages
pip list | grep fastapi
```

#### Database errors
```bash
# Reinitialize database
cd /home/ubuntu/AGENT/backend
python init_db.py

# Check database exists
ls -lh intranet.db
```

#### Import errors
```bash
# Verify all packages installed
pip install -r requirements.txt --force-reinstall

# Check specific packages
python -c "import chromadb; import langchain; print('OK')"
```

### Frontend Issues

#### Frontend not building
```bash
# Clear build cache
rm -rf .next node_modules

# Reinstall dependencies
npm install

# Build again
npm run build
```

#### Frontend not loading
```bash
# Check if port 3000 is in use
lsof -i :3000

# Check build output
ls -la .next/
```

### Nginx Issues

#### 413 Request Entity Too Large
```bash
# Verify client_max_body_size set correctly
grep client_max_body_size /etc/nginx/sites-available/agent.alexcty.com
# Should show: client_max_body_size 100M;

# Reload Nginx
sudo systemctl reload nginx
```

#### Nginx configuration error
```bash
# Test configuration
sudo nginx -t

# View full config
sudo cat /etc/nginx/sites-available/agent.alexcty.com

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

### Database Issues

#### SQLite "database is locked"
```bash
# Check for stale processes
ps aux | grep uvicorn

# Kill stale processes if needed
pkill -f uvicorn

# Restart backend
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Migrate to PostgreSQL (for production)
```bash
# Install PostgreSQL client
sudo apt install -y postgresql-client

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost:5432/agent_db

# Restart backend
sudo systemctl restart agent-backend
```

---

## Verification Steps

### Quick Verification (1 minute)

```bash
# Backend health
curl -s http://localhost:8000/health | grep healthy && echo "✅ Backend OK"

# Frontend responsive
curl -s http://localhost:3000 | grep "AI Intranet" && echo "✅ Frontend OK"

# Database accessible
[ -f /home/ubuntu/AGENT/backend/intranet.db ] && echo "✅ Database OK"
```

### Full Verification (5 minutes)

```bash
# 1. Test backend endpoints
curl -X GET http://localhost:8000/api/models | head -20

# 2. Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"thiachan@pseudo-ai.com","password":"password123"}'

# 3. Test frontend page load
curl -s http://localhost:3000 | grep -c "Next.js" > /dev/null && echo "✅ Frontend rendering"

# 4. Test API documentation
curl -s http://localhost:8000/docs | grep -c "Swagger" && echo "✅ API docs available"

# 5. Check services running
ps aux | grep uvicorn | grep -v grep && echo "✅ Backend running"
ps aux | grep next | grep -v grep && echo "✅ Frontend running"
```

### Production Verification (10 minutes)

```bash
# 1. HTTPS working
curl -I https://yourdomain.com | grep "HTTP/2"

# 2. Backend via Nginx
curl https://yourdomain.com/api/health

# 3. Frontend via Nginx
curl -I https://yourdomain.com | grep "200 OK"

# 4. Monitor logs
sudo tail -20 /var/log/nginx/access.log
tail -20 /home/ubuntu/AGENT/backend/backend.log

# 5. Systemd service status
sudo systemctl status agent-backend
sudo systemctl status agent-frontend  # If using systemd for frontend
```

---

## Quick Reference

### Common Commands

```bash
# View backend logs
tail -f /home/ubuntu/AGENT/backend/backend.log

# View frontend logs
tail -f /home/ubuntu/AGENT/frontend.log

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Stop services
pkill -f uvicorn
pkill -f "next"

# Restart services
sudo systemctl restart agent-backend
sudo systemctl restart nginx

# Check open ports
sudo netstat -tulpn | grep LISTEN

# Restart everything
./stop-services.sh
./start-services.sh
```

### File Locations

```
Project Root:        /home/ubuntu/AGENT
Backend:             /home/ubuntu/AGENT/backend
Frontend:            /home/ubuntu/AGENT
Database:            /home/ubuntu/AGENT/backend/intranet.db
Vector DB:           /home/ubuntu/AGENT/backend/vector_db
Uploads:             /home/ubuntu/AGENT/backend/uploads
Nginx Config:        /etc/nginx/sites-available/agent.alexcty.com
SSL Certificates:    /etc/letsencrypt/live/agent.alexcty.com/
Logs:                /var/log/nginx/
```

---

## Support & Documentation

- **Main Documentation**: [README.md](README.md)
- **Technical Details**: [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)
- **Deployment Guide**: [docs/AWS_EC2_DEPLOYMENT_GUIDE.md](docs/AWS_EC2_DEPLOYMENT_GUIDE.md)
- **Email Setup**: [docs/EMAIL_VERIFICATION_SETUP.md](docs/EMAIL_VERIFICATION_SETUP.md)
- **Troubleshooting**: [docs/WHY_IT_WASNT_WORKING.md](docs/WHY_IT_WASNT_WORKING.md)

---

**End of Onboarding Guide**
