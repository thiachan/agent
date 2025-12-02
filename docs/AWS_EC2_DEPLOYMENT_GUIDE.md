# AWS EC2 Deployment Guide - Step by Step

This guide will walk you through deploying your HRSP AI Hub platform to AWS EC2 as a prototype.

---

## Prerequisites

- AWS Account with appropriate permissions
- Basic knowledge of Linux command line
- SSH key pair (or ability to create one)
- Domain name (optional, for custom domain)

---

## Phase 1: EC2 Instance Setup

### Step 1.1: Launch EC2 Instance

1. **Log in to AWS Console**
   - Go to https://console.aws.amazon.com
   - Navigate to **EC2** service

2. **Launch Instance**
   - Click **"Launch Instance"**
   - Configure:
     - **Name:** `hrsp-ai-hub-prototype`
     - **AMI:** Ubuntu Server 22.04 LTS (64-bit x86)
     - **Instance Type:** `t3.large` (2 vCPU, 8GB RAM) - sufficient for prototype
     - **Key Pair:** 
       - Create new key pair OR use existing
       - Download `.pem` file and save securely
       - **IMPORTANT:** You'll need this to SSH into the server
     - **Network Settings:**
       - Create new security group OR use existing
       - **Inbound Rules:**
         - SSH (22) - Your IP only
         - HTTP (80) - 0.0.0.0/0 (all)
         - HTTPS (443) - 0.0.0.0/0 (all)
         - Custom TCP (8000) - 0.0.0.0/0 (for FastAPI backend)
         - Custom TCP (3000) - 0.0.0.0/0 (for Next.js frontend)
     - **Storage:** 30GB gp3 (minimum, increase if needed)
     - **Advanced Details (optional):**
       - Add user data script (see Step 1.2)

3. **Launch Instance**
   - Click **"Launch Instance"**
   - Wait for instance to be in "Running" state
   - Note the **Public IP** and **Public DNS**

### Step 1.2: Initial Server Setup (via SSH)

1. **Connect to EC2 Instance**
   ```bash
   # On Windows (PowerShell or Git Bash)
   ssh -i "your-key.pem" ubuntu@<PUBLIC_IP>
   
   # On Mac/Linux
   chmod 400 your-key.pem
   ssh -i your-key.pem ubuntu@<PUBLIC_IP>
   ```

2. **Update System**
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. **Install Essential Tools**
   ```bash
   sudo apt install -y \
     curl \
     wget \
     git \
     build-essential \
     software-properties-common \
     apt-transport-https \
     ca-certificates \
     gnupg \
     lsb-release
   ```

4. **Install Docker**
   ```bash
   # Add Docker's official GPG key
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg
   
   # Set up repository
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   
   # Install Docker
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   
   # Add ubuntu user to docker group
   sudo usermod -aG docker ubuntu
   
   # Verify installation
   docker --version
   docker compose version
   ```

5. **Install Node.js 18.x**
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt install -y nodejs
   node --version
   npm --version
   ```

6. **Install Python 3.10+ and pip**
   ```bash
   sudo apt install -y python3.10 python3.10-venv python3-pip
   python3 --version
   ```

7. **Install PostgreSQL (Optional - for production, or use SQLite for prototype)**
   ```bash
   # For prototype, you can skip this and use SQLite
   # For production, install PostgreSQL:
   sudo apt install -y postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

8. **Install Nginx**
   ```bash
   sudo apt install -y nginx
   sudo systemctl start nginx
   sudo systemctl enable nginx
   ```

9. **Install Certbot (for SSL/HTTPS)**
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   ```

---

## Phase 2: Application Deployment

### Step 2.1: Clone Repository

1. **Create Application Directory**
   ```bash
   cd /home/ubuntu
   mkdir -p apps
   cd apps
   ```

2. **Clone Your Repository**
   ```bash
   # Option A: If using Git
   git clone <your-repository-url> AGENT
   cd AGENT
   
   # Option B: If uploading files manually
   # Use SCP or SFTP to upload your project files
   ```

3. **If Uploading Manually (SCP)**
   ```bash
   # From your local machine (Windows PowerShell or Git Bash)
   scp -i "your-key.pem" -r C:\Users\tyung\AGENT ubuntu@<PUBLIC_IP>:/home/ubuntu/apps/
   ```

### Step 2.2: Backend Setup

1. **Navigate to Backend**
   ```bash
   cd /home/ubuntu/apps/AGENT/backend
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create Environment File**
   ```bash
   nano .env
   ```
   
   Add the following (update with your actual values):
   ```env
   # Database
   DATABASE_URL=sqlite:///./app.db
   # For PostgreSQL (if using):
   # DATABASE_URL=postgresql://username:password@localhost:5432/AGENT
   
   # Security
   SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # OpenAI
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   
   # Azure OpenAI (if using)
   AZURE_OPENAI_API_KEY=your-azure-key
   AZURE_OPENAI_ENDPOINT=your-azure-endpoint
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
   
   # AWS Bedrock (if using)
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_REGION=us-east-1
   
   # Cisco App Key (if using)
   CISCO_APPKEY=your-cisco-appkey
   
   # Vector Database
   VECTOR_DB_PATH=/home/ubuntu/apps/AGENT/backend/data/vector_db
   
   # File Storage
   UPLOAD_DIR=/home/ubuntu/apps/AGENT/backend/data/uploads
   
   # CORS
   CORS_ORIGINS=http://localhost:3000,http://<YOUR_EC2_PUBLIC_IP>:3000,http://<YOUR_DOMAIN>
   
   # Environment
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

5. **Create Required Directories**
   ```bash
   mkdir -p data/vector_db
   mkdir -p data/uploads
   mkdir -p public/demo-videos
   ```

6. **Initialize Database**
   ```bash
   # If using SQLite (prototype)
   python -c "from app.core.database import engine, Base; Base.metadata.create_all(bind=engine)"
   
   # If using PostgreSQL
   # First create database:
   # sudo -u postgres psql
   # CREATE DATABASE AGENT;
   # CREATE USER hrsp_user WITH PASSWORD 'your_password';
   # GRANT ALL PRIVILEGES ON DATABASE AGENT TO hrsp_user;
   # \q
   ```

### Step 2.3: Frontend Setup

1. **Navigate to Frontend**
   ```bash
   cd /home/ubuntu/apps/AGENT
   ```

2. **Install Node Dependencies**
   ```bash
   npm install
   ```

3. **Create Environment File**
   ```bash
   nano .env.local
   ```
   
   Add:
   ```env
   NEXT_PUBLIC_API_URL=http://<YOUR_EC2_PUBLIC_IP>:8000
   # Or if using domain:
   # NEXT_PUBLIC_API_URL=https://yourdomain.com/api
   ```

4. **Build Frontend**
   ```bash
   npm run build
   ```

---

## Phase 3: Running the Application

### Step 3.1: Run Backend (Development Mode)

1. **Start Backend**
   ```bash
   cd /home/ubuntu/apps/AGENT/backend
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Test Backend**
   - Open browser: `http://<YOUR_EC2_PUBLIC_IP>:8000/docs`
   - Should see FastAPI Swagger UI

### Step 3.2: Run Frontend (Development Mode)

1. **In a New SSH Session, Start Frontend**
   ```bash
   cd /home/ubuntu/apps/AGENT
   npm run dev
   ```

2. **Test Frontend**
   - Open browser: `http://<YOUR_EC2_PUBLIC_IP>:3000`
   - Should see your application

### Step 3.3: Run as Systemd Services (Production)

1. **Create Backend Service**
   ```bash
   sudo nano /etc/systemd/system/hrsp-backend.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=HRSP AI Hub Backend
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/apps/AGENT/backend
   Environment="PATH=/home/ubuntu/apps/AGENT/backend/venv/bin"
   ExecStart=/home/ubuntu/apps/AGENT/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

2. **Create Frontend Service**
   ```bash
   sudo nano /etc/systemd/system/hrsp-frontend.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=HRSP AI Hub Frontend
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/apps/AGENT
   Environment="PATH=/usr/bin:/usr/local/bin"
   ExecStart=/usr/bin/npm run start
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and Start Services**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hrsp-backend
   sudo systemctl enable hrsp-frontend
   sudo systemctl start hrsp-backend
   sudo systemctl start hrsp-frontend
   ```

4. **Check Status**
   ```bash
   sudo systemctl status hrsp-backend
   sudo systemctl status hrsp-frontend
   ```

5. **View Logs**
   ```bash
   sudo journalctl -u hrsp-backend -f
   sudo journalctl -u hrsp-frontend -f
   ```

---

## Phase 4: Nginx Reverse Proxy Setup

### Step 4.1: Configure Nginx

1. **Create Nginx Configuration**
   ```bash
   sudo nano /etc/nginx/sites-available/hrsp-ai-hub
   ```
   
   Add:
   ```nginx
   server {
       listen 80;
       server_name <YOUR_DOMAIN_OR_IP>;
       
       # Frontend
       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       # Backend API
       location /api {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Increase timeouts for long-running requests
           proxy_read_timeout 300s;
           proxy_connect_timeout 300s;
           proxy_send_timeout 300s;
       }
       
       # WebSocket support (if needed)
       location /ws {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

2. **Enable Site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/hrsp-ai-hub /etc/nginx/sites-enabled/
   sudo nginx -t  # Test configuration
   sudo systemctl reload nginx
   ```

3. **Update Frontend .env.local**
   ```bash
   cd /home/ubuntu/apps/AGENT
   nano .env.local
   ```
   
   Update:
   ```env
   NEXT_PUBLIC_API_URL=http://<YOUR_EC2_PUBLIC_IP>/api
   # Or if using domain:
   # NEXT_PUBLIC_API_URL=https://yourdomain.com/api
   ```

---

## Phase 5: SSL/HTTPS Setup (Optional but Recommended)

### Step 5.1: Setup with Domain Name

1. **Point Domain to EC2 IP**
   - Go to your domain registrar
   - Add A record: `@` → `<YOUR_EC2_PUBLIC_IP>`
   - Add A record: `www` → `<YOUR_EC2_PUBLIC_IP>`
   - Wait for DNS propagation (5-30 minutes)

2. **Get SSL Certificate**
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

3. **Auto-Renewal**
   ```bash
   sudo certbot renew --dry-run  # Test
   # Certbot auto-renewal is already set up via cron
   ```

### Step 5.2: Update Configuration for HTTPS

1. **Update Backend CORS**
   ```bash
   cd /home/ubuntu/apps/AGENT/backend
   nano .env
   ```
   
   Update:
   ```env
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

2. **Update Frontend .env.local**
   ```bash
   cd /home/ubuntu/apps/AGENT
   nano .env.local
   ```
   
   Update:
   ```env
   NEXT_PUBLIC_API_URL=https://yourdomain.com/api
   ```

3. **Restart Services**
   ```bash
   sudo systemctl restart hrsp-backend
   sudo systemctl restart hrsp-frontend
   sudo systemctl reload nginx
   ```

---

## Phase 6: Security Hardening

### Step 6.1: Firewall (UFW)

1. **Configure UFW**
   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   sudo ufw status
   ```

### Step 6.2: Update Security Group

1. **In AWS Console:**
   - Go to EC2 → Security Groups
   - Edit inbound rules:
     - Remove port 8000 and 3000 (not needed if using Nginx)
     - Keep SSH (22) - Your IP only
     - Keep HTTP (80) - 0.0.0.0/0
     - Keep HTTPS (443) - 0.0.0.0/0

### Step 6.3: Regular Updates

```bash
# Set up automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Phase 7: Monitoring & Maintenance

### Step 7.1: Check Application Status

```bash
# Backend status
sudo systemctl status hrsp-backend

# Frontend status
sudo systemctl status hrsp-frontend

# Nginx status
sudo systemctl status nginx

# View logs
sudo journalctl -u hrsp-backend -n 50
sudo journalctl -u hrsp-frontend -n 50
```

### Step 7.2: Backup Strategy

1. **Database Backup (SQLite)**
   ```bash
   # Create backup script
   nano /home/ubuntu/backup.sh
   ```
   
   Add:
   ```bash
   #!/bin/bash
   BACKUP_DIR="/home/ubuntu/backups"
   mkdir -p $BACKUP_DIR
   DATE=$(date +%Y%m%d_%H%M%S)
   
   # Backup database
   cp /home/ubuntu/apps/AGENT/backend/app.db $BACKUP_DIR/app_$DATE.db
   
   # Backup uploads
   tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /home/ubuntu/apps/AGENT/backend/data/uploads
   
   # Keep only last 7 days
   find $BACKUP_DIR -name "*.db" -mtime +7 -delete
   find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
   ```
   
   ```bash
   chmod +x /home/ubuntu/backup.sh
   
   # Add to crontab (daily at 2 AM)
   crontab -e
   # Add: 0 2 * * * /home/ubuntu/backup.sh
   ```

### Step 7.3: Log Rotation

```bash
sudo nano /etc/logrotate.d/hrsp-ai-hub
```

Add:
```
/home/ubuntu/apps/AGENT/backend/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## Phase 8: Troubleshooting

### Common Issues

1. **Backend not starting**
   ```bash
   # Check logs
   sudo journalctl -u hrsp-backend -n 100
   
   # Check if port is in use
   sudo netstat -tulpn | grep 8000
   
   # Test manually
   cd /home/ubuntu/apps/AGENT/backend
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Frontend not starting**
   ```bash
   # Check logs
   sudo journalctl -u hrsp-frontend -n 100
   
   # Check if port is in use
   sudo netstat -tulpn | grep 3000
   
   # Test manually
   cd /home/ubuntu/apps/AGENT
   npm run start
   ```

3. **Nginx 502 Bad Gateway**
   ```bash
   # Check if backend is running
   curl http://localhost:8000/docs
   
   # Check Nginx error logs
   sudo tail -f /var/log/nginx/error.log
   ```

4. **Permission Issues**
   ```bash
   # Fix ownership
   sudo chown -R ubuntu:ubuntu /home/ubuntu/apps/AGENT
   ```

---

## Phase 9: Next Steps (Optional Enhancements)

1. **Set up CloudWatch Monitoring**
   - Monitor EC2 instance metrics
   - Set up alarms for CPU, memory, disk

2. **Set up S3 for File Storage**
   - Move uploads to S3
   - Update `backend/app/api/upload.py`

3. **Set up RDS PostgreSQL**
   - Create RDS instance
   - Migrate from SQLite
   - Update `DATABASE_URL`

4. **Set up Auto Scaling**
   - Create AMI of current instance
   - Configure Auto Scaling Group
   - Set up Application Load Balancer

5. **Set up CI/CD**
   - GitHub Actions or AWS CodePipeline
   - Automated deployments

---

## Quick Reference Commands

```bash
# Start services
sudo systemctl start hrsp-backend
sudo systemctl start hrsp-frontend

# Stop services
sudo systemctl stop hrsp-backend
sudo systemctl stop hrsp-frontend

# Restart services
sudo systemctl restart hrsp-backend
sudo systemctl restart hrsp-frontend

# View logs
sudo journalctl -u hrsp-backend -f
sudo journalctl -u hrsp-frontend -f

# Check status
sudo systemctl status hrsp-backend
sudo systemctl status hrsp-frontend

# Test Nginx config
sudo nginx -t
sudo systemctl reload nginx
```

---

## Estimated Costs (Prototype)

- **EC2 t3.large:** ~$60/month
- **EBS Storage (30GB):** ~$3/month
- **Data Transfer:** ~$5-10/month
- **Total:** ~$70-75/month

---

## Support

If you encounter issues:
1. Check application logs
2. Check Nginx logs
3. Check system resources: `htop`, `df -h`
4. Review security group rules
5. Verify environment variables

---

**Good luck with your deployment! 🚀**

