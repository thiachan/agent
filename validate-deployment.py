#!/usr/bin/env python3
"""
AGENT Platform - Deployment Validation Script
This script validates the complete deployment and onboarding process
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# Results tracking
passed = 0
failed = 0
warnings = 0

def pass_check(msg):
    global passed
    print(f"{GREEN}[✓ PASS]{NC} {msg}")
    passed += 1

def fail_check(msg):
    global failed
    print(f"{RED}[✗ FAIL]{NC} {msg}")
    failed += 1

def warn_check(msg):
    global warnings
    print(f"{YELLOW}[⚠ WARN]{NC} {msg}")
    warnings += 1

def section(title):
    print(f"\n{BLUE}=== {title} ==={NC}\n")

def run_command(cmd, show_error=False):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        if show_error:
            return False, "", str(e)
        return False, "", ""

def check_file(filepath, required=True):
    """Check if file exists"""
    if Path(filepath).exists():
        pass_check(f"File exists: {filepath}")
        return True
    else:
        if required:
            fail_check(f"File missing: {filepath}")
        else:
            warn_check(f"File not found: {filepath}")
        return False

def check_command(cmd, name):
    """Check if command exists"""
    success, _, _ = run_command(f"which {cmd}")
    if success:
        pass_check(f"{name} found")
        return True
    else:
        warn_check(f"{name} not found")
        return False

def main():
    print(f"\n{BLUE}{'='*50}{NC}")
    print(f"{BLUE}AGENT Platform - Deployment Validator{NC}")
    print(f"{BLUE}{'='*50}{NC}\n")
    print(f"Validation started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Phase 1: Prerequisites
    section("Phase 1: Checking Prerequisites")
    
    check_command("python3", "Python 3")
    check_command("node", "Node.js")
    check_command("npm", "npm")
    check_command("git", "Git")
    check_command("curl", "curl")
    
    # Phase 2: File Structure
    section("Phase 2: Checking File Structure")
    
    required_files = [
        "backend/main.py",
        "backend/requirements.txt",
        "backend/app/core/config.py",
        "backend/init_db.py",
        "package.json",
        "tsconfig.json",
        "README.md",
        "ONBOARDING_COMPLETE.md",
        "validate-deployment.sh"
    ]
    
    for filepath in required_files:
        check_file(filepath, required=True)
    
    # Phase 3: Environment
    section("Phase 3: Checking Environment Configuration")
    
    if Path("backend/.env").exists():
        pass_check("Backend .env found")
        
        with open("backend/.env") as f:
            env_content = f.read()
            
        if "OPENAI_API_KEY" in env_content:
            pass_check("OPENAI_API_KEY configured")
        else:
            fail_check("OPENAI_API_KEY not configured")
            
        if "CISCO_CLIENT_ID" in env_content:
            pass_check("CISCO_CLIENT_ID configured")
        else:
            fail_check("CISCO_CLIENT_ID not configured")
    else:
        fail_check("Backend .env file not found")
    
    if Path(".env.local").exists():
        pass_check("Frontend .env.local found")
    else:
        warn_check("Frontend .env.local not found (will use defaults)")
    
    # Phase 4: Backend Setup
    section("Phase 4: Checking Backend Setup")
    
    if Path("backend/venv").exists():
        pass_check("Backend venv exists")
        
        success, _, _ = run_command("backend/venv/bin/pip list 2>/dev/null | grep fastapi")
        if success:
            pass_check("FastAPI installed")
        else:
            warn_check("FastAPI may not be installed")
    else:
        warn_check("Backend venv not found (run: python3 -m venv backend/venv)")
    
    if Path("backend/intranet.db").exists():
        pass_check("Database initialized (intranet.db found)")
    else:
        warn_check("Database not initialized (run: python backend/init_db.py)")
    
    # Phase 5: Frontend Setup
    section("Phase 5: Checking Frontend Setup")
    
    if Path("node_modules").exists():
        pass_check("Node modules installed")
    else:
        warn_check("Node modules not found (run: npm install)")
    
    if Path(".next").exists():
        pass_check("Frontend built (.next found)")
    else:
        warn_check("Frontend not built (run: npm run build)")
    
    # Phase 6: Running Services
    section("Phase 6: Checking Running Services")
    
    success, _, _ = run_command("curl -s http://localhost:8000/health")
    if success:
        pass_check("Backend is running (port 8000)")
    else:
        warn_check("Backend not responding on port 8000")
    
    success, _, _ = run_command("curl -s http://localhost:3000")
    if success:
        pass_check("Frontend is running (port 3000)")
    else:
        warn_check("Frontend not responding on port 3000")
    
    # Phase 7: Documentation
    section("Phase 7: Checking Documentation")
    
    docs = [
        "ONBOARDING_COMPLETE.md",
        "INSTALL.md",
        "README.md",
        "docs/DEPLOYMENT_PLAN.md",
        "docs/AWS_EC2_DEPLOYMENT_GUIDE.md",
        "docs/TECHNICAL_DOCUMENTATION.md",
        "docs/EMAIL_VERIFICATION_SETUP.md"
    ]
    
    for doc in docs:
        check_file(doc, required=False)
    
    # Phase 8: Git Status
    section("Phase 8: Checking Git Status")
    
    if Path(".git").exists():
        pass_check("Git repository found")
        
        success, branch, _ = run_command("git branch --show-current")
        if success and branch:
            pass_check(f"Current branch: {branch}")
            if branch not in ["vscode-optimized-v1", "main"]:
                warn_check(f"Branch {branch} (recommended: vscode-optimized-v1 or main)")
        
        success, _, _ = run_command("git diff-index --quiet HEAD --")
        if success:
            pass_check("No uncommitted changes")
        else:
            warn_check("You have uncommitted changes")
    else:
        fail_check("Git repository not found")
    
    # Summary
    section("VALIDATION SUMMARY")
    
    print(f"{GREEN}Passed:  {passed}{NC}")
    print(f"{RED}Failed:  {failed}{NC}")
    print(f"{YELLOW}Warnings: {warnings}{NC}")
    
    total = passed + failed + warnings
    pass_percent = int((passed / total * 100) if total > 0 else 0)
    
    print(f"\nValidation Score: {pass_percent}% ({passed}/{total})\n")
    
    if failed == 0:
        print(f"{GREEN}✓ Deployment validation PASSED{NC}")
        if warnings > 0:
            print(f"{YELLOW}Note: There are {warnings} warnings - please address them for production{NC}")
        return 0
    else:
        print(f"{RED}✗ Deployment validation FAILED{NC}")
        print(f"{RED}Please fix the {failed} error(s) before deploying{NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
