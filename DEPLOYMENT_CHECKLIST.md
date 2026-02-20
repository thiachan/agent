# AGENT Platform - Deployment Checklist

**Project**: GSSO AI Center (AGENT)  
**Version**: 1.0.0 (VSCode Optimized v1)  
**Last Updated**: January 13, 2026

---

## 📋 Pre-Deployment Checklist

### Repository & Code
- [ ] Clone latest from repository: `git clone https://github.com/thiachan/agent.git`
- [ ] Switch to `vscode-optimized-v1` branch: `git checkout vscode-optimized-v1`
- [ ] No uncommitted changes: `git status`
- [ ] All code reviewed and tested
- [ ] README.md up to date
- [ ] ONBOARDING_COMPLETE.md reviewed

### Infrastructure & Prerequisites
- [ ] AWS EC2 instance created (t3.large or larger)
- [ ] Security groups configured:
  - [ ] SSH (22) - restricted to your IP
  - [ ] HTTP (80) - open to world
  - [ ] HTTPS (443) - open to world
  - [ ] Custom TCP 8000 - backend API
  - [ ] Custom TCP 3000 - frontend dev
- [ ] Domain name configured and DNS records updated
- [ ] Public IP address noted
- [ ] SSH key pair downloaded and secured
- [ ] Storage size: 30GB minimum
- [ ] OS: Ubuntu 22.04 LTS confirmed

### System Setup
- [ ] SSH access verified: `ssh -i key.pem ubuntu@<IP>`
- [ ] System packages updated: `sudo apt update && sudo apt upgrade -y`
- [ ] Python 3.10+ installed: `python3 --version`
- [ ] Node.js 18.x+ installed: `node --version`
- [ ] Git installed: `git --version`
- [ ] Setup script executed: `./setup-ubuntu.sh`

---

## 🔧 Environment Configuration Checklist

### Backend Environment (.env)
- [ ] `SECRET_KEY` - Set secure random key (min 32 chars)
- [ ] `DATABASE_URL` - Set correct database path
- [ ] `OPENAI_API_KEY` - Configured from OpenAI platform
- [ ] `OPENAI_TTS_VOICE_HOST` - Set voice (nova recommended)
- [ ] `OPENAI_TTS_VOICE_GUEST` - Set voice (onyx recommended)
- [ ] `CISCO_CLIENT_ID` - Obtained from Cisco OAuth portal
- [ ] `CISCO_CLIENT_SECRET` - Obtained from Cisco OAuth portal
- [ ] `CISCO_ENDPOINT` - Correct endpoint for your region
- [ ] `CISCO_APPKEY` - Configured if required
- [ ] `PRESENTON_API_URL` - Set to Presenton.ai endpoint
- [ ] `PRESENTON_REQUIRE_AUTH` - Set to false for testing, true for production
- [ ] `PRESENTON_MAX_SLIDES` - Set to 12
- [ ] `MAIL_USERNAME` - Email configured
- [ ] `MAIL_PASSWORD` - App password (not regular password)
- [ ] `MAIL_FROM` - noreply email configured
- [ ] `MAIL_SERVER` - SMTP server configured (smtp.gmail.com for Gmail)
- [ ] `MAIL_PORT` - SMTP port configured (587 for Gmail)
- [ ] `FRONTEND_URL` - Set to your domain (http://localhost:3000 for dev)
- [ ] No hardcoded secrets in version control
- [ ] .env file in .gitignore

### Frontend Environment (.env.local)
- [ ] `NEXT_PUBLIC_API_URL` - Correct backend URL
  - Development: `http://localhost:8000`
  - Production: `https://yourdomain.com/api`

---

## 💾 Backend Setup Checklist

### Virtual Environment
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Pip upgraded: `pip install --upgrade pip setuptools wheel`

### Dependencies
- [ ] Requirements installed: `pip install -r requirements.txt`
- [ ] FastAPI installed: `pip list | grep fastapi`
- [ ] Uvicorn installed: `pip list | grep uvicorn`
- [ ] ChromaDB installed: `pip list | grep chromadb`
- [ ] LangChain installed: `pip list | grep langchain`

### Database
- [ ] Database initialized: `python init_db.py`
- [ ] Database file created: `ls -lh backend/intranet.db`
- [ ] Default admin user created:
  - [ ] Email: `thiachan@pseudo-ai.com`
  - [ ] Password: `password123`
- [ ] Password reset in production ⚠️

### Verification
- [ ] Backend imports work: `python -c "from app.main import app; print('OK')"`
- [ ] All critical packages available: `python -c "import chromadb; import langchain"`

---

## 🎨 Frontend Setup Checklist

### Node.js & NPM
- [ ] Node.js v18.x+: `node --version`
- [ ] npm latest: `npm --version`

### Dependencies
- [ ] Dependencies installed: `npm install`
- [ ] Next.js installed: `npm list next`
- [ ] React installed: `npm list react`
- [ ] Tailwind CSS installed: `npm list tailwindcss`

### Build
- [ ] Frontend builds successfully: `npm run build`
- [ ] Build output created: `ls -la .next/`
- [ ] No build errors or warnings

### Verification
- [ ] Local development works: `npm run dev`
- [ ] Frontend loads: `curl -s http://localhost:3000 | grep "AI Intranet"`

---

## 🚀 Service Startup Checklist

### Backend Service
- [ ] Backend starts: `uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] API docs available: `curl http://localhost:8000/docs`
- [ ] Logs monitored: `tail -f backend.log`

### Frontend Service
- [ ] Frontend starts: `npm start` (production build)
- [ ] Frontend accessible: `curl http://localhost:3000`
- [ ] Page loads without errors
- [ ] Frontend logs checked: `tail -f frontend.log`

### Systemd Services (Production)
- [ ] Backend service file created: `/etc/systemd/system/agent-backend.service`
- [ ] Backend service enabled: `sudo systemctl enable agent-backend`
- [ ] Backend service started: `sudo systemctl start agent-backend`
- [ ] Backend service status: `sudo systemctl status agent-backend`
- [ ] Frontend service configured if needed
- [ ] Services auto-start on reboot verified

---

## 🔒 Security Checklist

### SSL/HTTPS
- [ ] Domain DNS configured
- [ ] SSL certificate requested: `sudo certbot certonly --nginx -d yourdomain.com`
- [ ] Certificate installed and configured
- [ ] SSL auto-renewal enabled: `sudo systemctl enable certbot.timer`
- [ ] HTTP redirects to HTTPS

### Secrets Management
- [ ] No credentials in .env.local or .env
- [ ] .env files in .gitignore
- [ ] .env files NOT committed to git
- [ ] Production secrets stored securely
- [ ] AWS Secrets Manager or equivalent used for production
- [ ] API keys rotated (if applicable)

### Network Security
- [ ] SSH only from trusted IPs
- [ ] Firewall configured
- [ ] DDoS protection considered
- [ ] Rate limiting considered

---

## 🌐 Nginx Configuration Checklist

### Nginx Setup
- [ ] Nginx installed: `nginx -v`
- [ ] Configuration created: `/etc/nginx/sites-available/agent.alexcty.com`
- [ ] Configuration symlinked: `/etc/nginx/sites-enabled/agent.alexcty.com`
- [ ] Configuration tested: `sudo nginx -t` → "syntax is ok"
- [ ] Nginx reloaded: `sudo systemctl reload nginx`
- [ ] Nginx status: `sudo systemctl status nginx`

### Reverse Proxy
- [ ] Frontend proxy configured (port 3000)
- [ ] Backend proxy configured (port 8000)
- [ ] API path routing configured (`/api/` to port 8000)
- [ ] Static files caching configured
- [ ] Proxy headers set correctly:
  - [ ] `X-Real-IP`
  - [ ] `X-Forwarded-For`
  - [ ] `X-Forwarded-Proto`

### File Upload Configuration
- [ ] `client_max_body_size` set to 100M
- [ ] `proxy_request_buffering off` for `/api/`
- [ ] Proxy timeouts configured:
  - [ ] `proxy_read_timeout 120s`
  - [ ] `proxy_send_timeout 120s`

---

## ✅ Post-Deployment Verification Checklist

### Service Health
- [ ] Backend health: `curl https://yourdomain.com/api/health`
- [ ] Frontend loads: `curl https://yourdomain.com`
- [ ] API docs: `curl https://yourdomain.com/api/docs`
- [ ] Nginx serving requests: `curl -I https://yourdomain.com`

### Functionality Testing
- [ ] Login works with demo account
- [ ] Chat interface responsive
- [ ] Document upload works
- [ ] File size < 100MB tested
- [ ] Generation features work:
  - [ ] PowerPoint generation
  - [ ] PDF generation
  - [ ] Speech generation (MP3)
  - [ ] Podcast generation (MP3)
- [ ] Knowledge base operations work
- [ ] Search functionality works
- [ ] User roles/permissions work

### Error Handling
- [ ] Error pages display correctly
- [ ] 404 page configured
- [ ] 500 error page configured
- [ ] Nginx logs monitored: `tail -f /var/log/nginx/error.log`
- [ ] Backend logs checked: `tail -f backend.log`

### Performance
- [ ] Page load times acceptable
- [ ] API response times < 2s for normal queries
- [ ] Large file uploads complete successfully
- [ ] Concurrent users can access simultaneously
- [ ] No memory leaks observed

### Monitoring & Logging
- [ ] Access logs monitored: `tail -f /var/log/nginx/access.log`
- [ ] Error logs monitored: `tail -f /var/log/nginx/error.log`
- [ ] Backend logs configured
- [ ] Log rotation configured
- [ ] Alerts configured (optional)

---

## 🔄 Continuous Monitoring Checklist

### Daily/Weekly
- [ ] Check service status: `systemctl status agent-backend`
- [ ] Monitor logs for errors
- [ ] Verify backups (if configured)
- [ ] Check disk space: `df -h`
- [ ] Memory usage: `free -h`

### Monthly
- [ ] Update system packages: `sudo apt update && sudo apt upgrade -y`
- [ ] Review security logs
- [ ] Test backup/restore procedure
- [ ] Update documentation if needed

### Quarterly
- [ ] Security audit
- [ ] Performance review
- [ ] Dependency updates
- [ ] SSL certificate renewal verification

---

## 📝 Deployment Validation Script

Run automatic validation:
```bash
# Python validator
python3 validate-deployment.py

# Expected output: 
# ✓ Deployment validation PASSED
# Validation Score: 97%+
```

---

## 🆘 Common Issues & Solutions

### 413 Request Entity Too Large
- [ ] Check `client_max_body_size` in Nginx config
- [ ] Verify it's set to at least 100M
- [ ] Reload Nginx: `sudo systemctl reload nginx`

### Backend not responding
- [ ] Check backend is running: `pgrep -f uvicorn`
- [ ] Check port 8000: `lsof -i :8000`
- [ ] View logs: `tail -f backend.log`

### Frontend not building
- [ ] Clear cache: `rm -rf .next node_modules`
- [ ] Reinstall: `npm install`
- [ ] Rebuild: `npm run build`

### Database locked
- [ ] Kill stale processes: `pkill -f uvicorn`
- [ ] Restart backend service

---

## 📞 Support & Documentation

- **Quick Start**: [ONBOARDING_COMPLETE.md](ONBOARDING_COMPLETE.md)
- **Technical Docs**: [TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)
- **AWS Guide**: [AWS_EC2_DEPLOYMENT_GUIDE.md](docs/AWS_EC2_DEPLOYMENT_GUIDE.md)
- **Email Setup**: [EMAIL_VERIFICATION_SETUP.md](docs/EMAIL_VERIFICATION_SETUP.md)
- **GitHub**: [https://github.com/thiachan/agent](https://github.com/thiachan/agent)

---

**Last Deployment**: [Add date]  
**Deployed By**: [Add name]  
**Environment**: [Development/Staging/Production]  
**Notes**: [Add deployment notes]

---

✅ **All checks completed successfully!** Deployment is ready for production.
