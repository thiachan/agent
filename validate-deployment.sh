#!/bin/bash

###############################################################################
# AGENT Platform - Deployment Validation Script
# This script validates the complete deployment and onboarding process
# Usage: ./validate-deployment.sh
###############################################################################

set -e

echo "=========================================="
echo "AGENT Platform - Deployment Validator"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNING=0

# Functions
pass() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((WARNING++))
}

# Phase 1: Check Prerequisites
echo ""
echo "=== Phase 1: Checking Prerequisites ==="
echo ""

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    pass "Python 3 found: $PYTHON_VERSION"
else
    fail "Python 3 not found"
fi

# Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    pass "Node.js found: $NODE_VERSION"
else
    warn "Node.js not found"
fi

# Git
if command -v git &> /dev/null; then
    pass "Git found"
else
    warn "Git not found"
fi

# Phase 2: Check File Structure
echo ""
echo "=== Phase 2: Checking File Structure ==="
echo ""

check_file() {
    if [ -f "$1" ]; then
        pass "File exists: $1"
    else
        fail "File missing: $1"
    fi
}

check_file "backend/main.py"
check_file "backend/requirements.txt"
check_file "backend/app/core/config.py"
check_file "backend/init_db.py"
check_file "package.json"
check_file "tsconfig.json"
check_file "README.md"

# Phase 3: Check Environment
echo ""
echo "=== Phase 3: Checking Environment Configuration ==="
echo ""

if [ -f "backend/.env" ]; then
    pass "Backend .env found"
    # Check for required variables
    if grep -q "OPENAI_API_KEY" backend/.env; then
        pass "OPENAI_API_KEY configured"
    else
        fail "OPENAI_API_KEY not configured"
    fi
    
    if grep -q "CISCO_CLIENT_ID" backend/.env; then
        pass "CISCO_CLIENT_ID configured"
    else
        fail "CISCO_CLIENT_ID not configured"
    fi
else
    fail "Backend .env file not found"
fi

if [ -f ".env.local" ]; then
    pass "Frontend .env.local found"
else
    warn "Frontend .env.local not found (will use defaults)"
fi

# Phase 4: Check Backend Setup
echo ""
echo "=== Phase 4: Checking Backend Setup ==="
echo ""

if [ -d "backend/venv" ]; then
    pass "Backend venv exists"
    # Check if key packages are installed
    if backend/venv/bin/pip list 2>/dev/null | grep -q "fastapi"; then
        pass "FastAPI installed"
    else
        warn "FastAPI not installed (may need to run: pip install -r backend/requirements.txt)"
    fi
else
    warn "Backend venv not found (may need to create: python3 -m venv backend/venv)"
fi

if [ -f "backend/intranet.db" ]; then
    pass "Database initialized (intranet.db found)"
else
    warn "Database not initialized (run: python backend/init_db.py)"
fi

# Phase 5: Check Frontend Setup
echo ""
echo "=== Phase 5: Checking Frontend Setup ==="
echo ""

if [ -d "node_modules" ]; then
    pass "Node modules installed"
else
    warn "Node modules not found (may need to run: npm install)"
fi

if [ -d ".next" ]; then
    pass "Frontend built (.next found)"
else
    warn "Frontend not built (run: npm run build)"
fi

# Phase 6: Check Running Services
echo ""
echo "=== Phase 6: Checking Running Services ==="
echo ""

# Backend health check
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    pass "Backend is running (port 8000)"
else
    warn "Backend not responding on port 8000"
fi

# Frontend health check
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    pass "Frontend is running (port 3000)"
else
    warn "Frontend not responding on port 3000"
fi

# Nginx check
if command -v nginx &> /dev/null; then
    if sudo nginx -t > /dev/null 2>&1; then
        pass "Nginx configuration is valid"
    else
        warn "Nginx configuration has issues"
    fi
else
    warn "Nginx not installed"
fi

# Phase 7: Check Documentation
echo ""
echo "=== Phase 7: Checking Documentation ==="
echo ""

check_file "ONBOARDING_COMPLETE.md"
check_file "INSTALL.md"
check_file "docs/DEPLOYMENT_PLAN.md"
check_file "docs/AWS_EC2_DEPLOYMENT_GUIDE.md"
check_file "docs/TECHNICAL_DOCUMENTATION.md"
check_file "docs/EMAIL_VERIFICATION_SETUP.md"

# Phase 8: Check Git Status
echo ""
echo "=== Phase 8: Checking Git Status ==="
echo ""

if [ -d ".git" ]; then
    pass "Git repository found"
    
    BRANCH=$(git branch --show-current)
    pass "Current branch: $BRANCH"
    
    if [ "$BRANCH" != "vscode-optimized-v1" ] && [ "$BRANCH" != "main" ]; then
        warn "Current branch is $BRANCH (recommended: vscode-optimized-v1 or main)"
    fi
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD --; then
        pass "No uncommitted changes"
    else
        warn "You have uncommitted changes"
    fi
else
    fail "Git repository not found"
fi

# Summary
echo ""
echo "=========================================="
echo "VALIDATION SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNING"
echo "=========================================="
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment validation PASSED${NC}"
    if [ $WARNING -gt 0 ]; then
        echo "Note: There are $WARNING warnings - please address them for production"
    fi
    exit 0
else
    echo -e "${RED}✗ Deployment validation FAILED${NC}"
    echo "Please fix the above errors before deploying"
    exit 1
fi
