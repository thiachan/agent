# Installation Guide - AWS EC2 Ubuntu

This guide provides a one-command installation for all dependencies on AWS EC2 Ubuntu 22.04 LTS.

## Quick Start

### Option 1: Automated Setup Script (Recommended)

1. **Upload the setup script to your EC2 instance:**
   ```bash
   # From your local machine
   scp -i "your-key.pem" setup-ubuntu.sh ubuntu@<EC2_IP>:/home/ubuntu/
   ```

2. **SSH into your EC2 instance:**
   ```bash
   ssh -i "your-key.pem" ubuntu@<EC2_IP>
   ```

3. **Make the script executable and run it:**
   ```bash
   chmod +x setup-ubuntu.sh
   ./setup-ubuntu.sh
   ```

The script will:
- ✅ Update system packages
- ✅ Install Python 3.10+ with all development tools
- ✅ Install Node.js 18.x
- ✅ Install all system dependencies (FFmpeg, image libraries, etc.)
- ✅ Install PostgreSQL client libraries
- ✅ Install Nginx and Certbot
- ✅ Create application directory structure
- ✅ Set up Python virtual environment
- ✅ Install all Python packages from `requirements.txt`
- ✅ Install frontend dependencies
- ✅ Create systemd service templates

### Option 2: Manual Installation

If you prefer to install manually, follow the steps in `docs/AWS_EC2_DEPLOYMENT_GUIDE.md`.

## What Gets Installed

### System Packages
- **Build Tools**: `build-essential`, `python3-dev`, `python3-pip`
- **Audio Processing**: `ffmpeg` and codec libraries (for pydub, moviepy, whisper)
- **Image Processing**: `libjpeg-dev`, `libpng-dev`, `libfreetype6-dev` (for Pillow)
- **Vector Operations**: `libgomp1`, `libatlas-base-dev` (for ChromaDB, sentence-transformers)
- **Database**: `postgresql-client`, `libpq-dev` (PostgreSQL support)
- **Cryptography**: `libssl-dev`, `libffi-dev` (for python-jose)

### Runtime Services
- **Python 3.10+**: With venv support
- **Node.js 18.x**: With npm
- **Nginx**: Web server and reverse proxy
- **Certbot**: SSL certificate management
- **PostgreSQL** (optional): Database server

### Python Packages
All packages from `backend/requirements.txt`:
- FastAPI and Uvicorn
- SQLAlchemy (with PostgreSQL support)
- LangChain and OpenAI libraries
- ChromaDB
- Document processing libraries
- Audio processing libraries
- AWS SDK (boto3)

### Frontend Dependencies
All packages from `package.json`:
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- And all other frontend dependencies

## Post-Installation Steps

### 1. Configure Environment Variables

```bash
cd ~/apps/AGENT/backend
nano .env
```

Add your configuration (see `docs/AWS_EC2_DEPLOYMENT_GUIDE.md` for details).

### 2. Initialize Database

```bash
cd ~/apps/AGENT/backend
source venv/bin/activate
python init_db.py
```

### 3. Build Frontend

```bash
cd ~/apps/AGENT
npm run build
```

### 4. Start Services

**Option A: Using systemd (Production)**
```bash
sudo cp /tmp/hrsp-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hrsp-backend
sudo systemctl start hrsp-backend
```

**Option B: Manual (Development)**
```bash
cd ~/apps/AGENT/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Python Package Installation Fails

If you encounter errors installing Python packages:

```bash
# Ensure all system dependencies are installed
sudo apt install -y python3-dev python3-pip build-essential

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Try installing again
pip install -r requirements.txt
```

### FFmpeg Not Found

If audio processing fails:

```bash
sudo apt install -y ffmpeg
ffmpeg -version  # Verify installation
```

### ChromaDB Installation Issues

If ChromaDB fails to install:

```bash
# Install required system libraries
sudo apt install -y libgomp1 libatlas-base-dev

# Try installing ChromaDB again
pip install chromadb==0.4.18
```

### Node.js Version Issues

If Node.js version is incorrect:

```bash
# Remove existing Node.js
sudo apt remove nodejs npm

# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

## Verification

After installation, verify everything is working:

```bash
# Check Python
python3 --version  # Should be 3.10 or higher
pip --version

# Check Node.js
node --version  # Should be v18.x or higher
npm --version

# Check FFmpeg
ffmpeg -version

# Check PostgreSQL (if installed)
psql --version

# Check Nginx
nginx -v

# Check Python packages
cd ~/apps/AGENT/backend
source venv/bin/activate
pip list | grep -E "(fastapi|uvicorn|chromadb|langchain)"
```

## Additional Resources

- **Deployment Guide**: See `docs/AWS_EC2_DEPLOYMENT_GUIDE.md`
- **Remote Development**: See `docs/REMOTE_DEVELOPMENT_SETUP.md`
- **Architecture Plan**: See `docs/DEPLOYMENT_PLAN.md`

## Support

If you encounter issues during installation:
1. Check the error messages carefully
2. Verify all prerequisites are met
3. Check system logs: `journalctl -xe`
4. Review the troubleshooting section above

