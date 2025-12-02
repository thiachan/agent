#!/bin/bash

###############################################################################
# HRSP AI Hub - Complete Setup Script for Ubuntu 22.04 LTS
# This script installs all required packages, services, and dependencies
# for running the HRSP AI Hub platform on AWS EC2 Ubuntu
###############################################################################

set -e  # Exit on any error

echo "=========================================="
echo "HRSP AI Hub - Complete Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run as root. The script will use sudo when needed."
    exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install essential tools
print_status "Installing essential tools..."
sudo apt install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    zip

# Install Python 3.10+ and development tools
print_status "Installing Python 3.10+ and development tools..."
sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel

# Verify Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$(printf '%s\n' "3.10" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.10" ]; then
    print_error "Python 3.10+ is required. Found: $(python3 --version)"
    exit 1
fi

print_status "Python version: $(python3 --version)"

# Install system dependencies for Python packages
print_status "Installing system dependencies for Python packages..."

# For ChromaDB and vector operations
sudo apt install -y \
    libgomp1 \
    libatlas-base-dev \
    libblas-dev \
    liblapack-dev

# For PostgreSQL (optional, but recommended for production)
print_status "Installing PostgreSQL client libraries..."
sudo apt install -y \
    postgresql-client \
    libpq-dev

# For audio processing (pydub, moviepy, whisper)
print_status "Installing audio processing dependencies..."
sudo apt install -y \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev

# For image processing (Pillow)
print_status "Installing image processing dependencies..."
sudo apt install -y \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    zlib1g-dev

# For cryptography (used by python-jose)
print_status "Installing cryptography dependencies..."
sudo apt install -y \
    libssl-dev \
    libffi-dev

# Install Node.js 18.x
print_status "Installing Node.js 18.x..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
else
    print_warning "Node.js is already installed: $(node --version)"
fi

print_status "Node.js version: $(node --version)"
print_status "npm version: $(npm --version)"

# Install PostgreSQL (optional - can be skipped for SQLite prototype)
read -p "Do you want to install PostgreSQL server? (y/n, default: n): " install_postgres
if [[ $install_postgres =~ ^[Yy]$ ]]; then
    print_status "Installing PostgreSQL server..."
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    print_status "PostgreSQL installed and started"
    print_warning "Remember to create database and user manually"
else
    print_status "Skipping PostgreSQL installation (will use SQLite)"
fi

# Install Nginx
print_status "Installing Nginx..."
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
print_status "Nginx installed and started"

# Install Certbot (for SSL/HTTPS)
print_status "Installing Certbot for SSL certificates..."
sudo apt install -y certbot python3-certbot-nginx

# Create application directory structure
print_status "Creating application directory structure..."
APP_DIR="$HOME/apps/hrsp_ai_hub"
mkdir -p "$APP_DIR"/backend/data/{uploads,vector_db}
mkdir -p "$APP_DIR"/public/demo-videos
print_status "Application directories created at: $APP_DIR"

# Check if we're in the project directory
if [ -f "backend/requirements.txt" ]; then
    PROJECT_DIR="$(pwd)"
    print_status "Found project directory: $PROJECT_DIR"
    
    # Setup backend Python environment
    print_status "Setting up Python virtual environment..."
    cd "$PROJECT_DIR/backend"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment and install Python packages
    print_status "Installing Python packages from requirements.txt..."
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    
    print_status "Python packages installed successfully"
    
    # Setup frontend
    print_status "Setting up frontend..."
    cd "$PROJECT_DIR"
    if [ -f "package.json" ]; then
        npm install
        print_status "Frontend dependencies installed"
    else
        print_warning "package.json not found, skipping frontend setup"
    fi
    
    deactivate
else
    print_warning "Not in project directory. Skipping application setup."
    print_warning "Please run this script from the project root directory."
fi

# Create systemd service files (templates)
print_status "Creating systemd service file templates..."
sudo tee /tmp/hrsp-backend.service > /dev/null <<EOF
[Unit]
Description=HRSP AI Hub Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
ExecStart=$APP_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Systemd service template created at /tmp/hrsp-backend.service"
print_warning "To install the service, run:"
print_warning "  sudo cp /tmp/hrsp-backend.service /etc/systemd/system/"
print_warning "  sudo systemctl daemon-reload"
print_warning "  sudo systemctl enable hrsp-backend"
print_warning "  sudo systemctl start hrsp-backend"

# Summary
echo ""
echo "=========================================="
print_status "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Installed components:"
echo "  ✓ Python 3.10+ with pip and venv"
echo "  ✓ Node.js 18.x and npm"
echo "  ✓ System dependencies for Python packages"
echo "  ✓ FFmpeg for audio processing"
echo "  ✓ Image processing libraries"
echo "  ✓ PostgreSQL client libraries"
echo "  ✓ Nginx web server"
echo "  ✓ Certbot for SSL"
if [[ $install_postgres =~ ^[Yy]$ ]]; then
    echo "  ✓ PostgreSQL server"
fi
echo ""
echo "Next steps:"
echo "  1. Configure environment variables in backend/.env"
echo "  2. Initialize database: cd backend && python init_db.py"
echo "  3. Build frontend: npm run build"
echo "  4. Start services (see systemd service template above)"
echo ""
print_status "Setup script completed!"


