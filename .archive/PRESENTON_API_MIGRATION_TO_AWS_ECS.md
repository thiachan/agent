# Presenton API Migration: Public API → AWS ECS (No Auth)

## 📋 Current Implementation Summary

### 1. **Presenton Service Location**
- **File**: `/home/ubuntu/AGENT/backend/app/services/presenton_service.py`
- **Purpose**: Makes API calls to Presenton.ai for PowerPoint generation

### 2. **Current API Configuration**
```python
# From: backend/app/core/config.py (Lines 53-55)
PRESENTON_API_KEY: str = os.getenv("PRESENTON_API_KEY", "")
PRESENTON_API_URL: str = os.getenv("PRESENTON_API_URL", "https://api.presenton.ai")
PRESENTON_MAX_SLIDES: int = int(os.getenv("PRESENTON_MAX_SLIDES", "10"))
```

### 3. **Current API Implementation**
```python
# From: backend/app/services/presenton_service.py (Lines 17-117)

class PresentonService:
    def __init__(self):
        self.api_key = settings.PRESENTON_API_KEY      # ← REQUIRES API KEY
        self.api_url = settings.PRESENTON_API_URL.rstrip('/')
        self.max_slides = settings.PRESENTON_MAX_SLIDES
    
    async def generate_powerpoint(...):
        # Current endpoint
        endpoint = f"{self.api_url}/api/v1/ppt/presentation/generate"
        
        # Current authentication
        headers = {
            "Authorization": f"Bearer {self.api_key}",  # ← AUTH REQUIRED
            "Content-Type": "application/json"
        }
        
        # Payload sent to API
        payload = {
            "content": content,
            "n_slides": 12,
            "language": "English",
            "template": "custom-31ec1f9f-6111-43d8-95db-217e051a021b",
            "theme": "36dada46-7c64-47f2-aad8-4930660e3e7b",
            "export_as": "pptx",
            "tone": "professional",
            "verbosity": "standard",
            "image_type": "stock",
            "include_table_of_contents": True,
            "include_title_slide": True
        }
```

### 4. **How It's Used**
```
User Request → ChatWithGeneration.tsx (Frontend)
              ↓
              → generate.py API endpoint
              ↓
              → document_generator.py
              ↓
              → presenton_service.py → Presenton.ai Public API
```

---

## 🎯 Migration Plan: AWS ECS (No Authentication)

### Option 1: Remove Authentication (Internal ECS Service)

If your AWS ECS hosted Presenton service is **internal** (within VPC) and doesn't require authentication:

#### Step 1: Update Configuration (`backend/app/core/config.py`)

```python
# BEFORE (Lines 53-55)
PRESENTON_API_KEY: str = os.getenv("PRESENTON_API_KEY", "")
PRESENTON_API_URL: str = os.getenv("PRESENTON_API_URL", "https://api.presenton.ai")
PRESENTON_MAX_SLIDES: int = int(os.getenv("PRESENTON_MAX_SLIDES", "10"))

# AFTER (for AWS ECS without auth)
PRESENTON_API_KEY: str = os.getenv("PRESENTON_API_KEY", "")  # Keep for backward compatibility
PRESENTON_API_URL: str = os.getenv("PRESENTON_API_URL", "http://presenton-service.internal:8080")
PRESENTON_MAX_SLIDES: int = int(os.getenv("PRESENTON_MAX_SLIDES", "10"))
PRESENTON_REQUIRE_AUTH: bool = os.getenv("PRESENTON_REQUIRE_AUTH", "true").lower() == "true"  # NEW
```

#### Step 2: Update Presenton Service (`backend/app/services/presenton_service.py`)

**Replace lines 12-36 with:**

```python
def __init__(self):
    self.api_key = settings.PRESENTON_API_KEY
    self.api_url = settings.PRESENTON_API_URL.rstrip('/')
    self.max_slides = settings.PRESENTON_MAX_SLIDES
    self.require_auth = settings.PRESENTON_REQUIRE_AUTH  # NEW

async def generate_powerpoint(
    self,
    content: str,
    topic: Optional[str] = None,
    template_path: Optional[str] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Generate PowerPoint presentation using Presenton API
    
    Args:
        content: The content to generate slides from
        topic: Optional topic/title for the presentation
        template_path: Path to the template PPTX file (not used for now, using "general" template)
    
    Returns:
        Tuple of (response_dict with path, filename)
        The response_dict contains: presentation_id, path (download URL), edit_path, credits_consumed
    """
    try:
        logger.info("=" * 60)
        logger.info("PRESENTON SERVICE: Starting PowerPoint generation")
        logger.info(f"   API URL: {self.api_url}")
        logger.info(f"   Require Auth: {self.require_auth}")
        logger.info(f"   Max slides: {self.max_slides}")
        logger.info("=" * 60)
```

**Replace lines 64-79 with:**

```python
# Make the request to Presenton API
endpoint = f"{self.api_url}/api/v1/ppt/presentation/generate"

# Build headers based on authentication requirement
headers = {"Content-Type": "application/json"}

if self.require_auth:
    if not self.api_key:
        raise ValueError("Presenton API key required but not configured")
    headers["Authorization"] = f"Bearer {self.api_key}"
    logger.info("Using authenticated request (Bearer token)")
else:
    logger.info("Using non-authenticated request (internal ECS service)")

async with httpx.AsyncClient(timeout=300.0) as client:
    logger.info(f"Calling Presenton API: {endpoint}")
    logger.info(f"Payload: {payload}")
    
    response = await client.post(
        endpoint,
        json=payload,
        headers=headers  # Will include auth if require_auth=True
    )
```

#### Step 3: Update Environment Variables

Create or update `.env` file:

```bash
# For AWS ECS Internal Service (No Auth)
PRESENTON_API_URL=http://presenton-service.internal:8080
PRESENTON_REQUIRE_AUTH=false
PRESENTON_API_KEY=  # Leave empty or remove

# For Public API (With Auth) - Current setup
# PRESENTON_API_URL=https://api.presenton.ai
# PRESENTON_REQUIRE_AUTH=true
# PRESENTON_API_KEY=your_api_key_here
```

---

### Option 2: Use AWS IAM / Internal Load Balancer

If your ECS service uses AWS IAM or internal ALB:

#### Step 1: Add AWS Dependencies

Add to `backend/requirements.txt`:
```
boto3>=1.26.0
botocore>=1.29.0
```

#### Step 2: Update Config (`backend/app/core/config.py`)

```python
# Add these new settings
PRESENTON_AUTH_TYPE: str = os.getenv("PRESENTON_AUTH_TYPE", "bearer")  # bearer, aws_iam, none
PRESENTON_AWS_REGION: str = os.getenv("PRESENTON_AWS_REGION", "us-east-1")
```

#### Step 3: Create AWS SigV4 Auth Helper

Create new file: `backend/app/services/aws_auth.py`

```python
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from typing import Dict

def sign_request_with_iam(url: str, method: str, headers: Dict, body: str, region: str = "us-east-1") -> Dict:
    """
    Sign HTTP request with AWS SigV4 for IAM authentication
    """
    credentials = boto3.Session().get_credentials()
    request = AWSRequest(method=method, url=url, headers=headers, data=body)
    SigV4Auth(credentials, "execute-api", region).add_auth(request)
    return dict(request.headers)
```

#### Step 4: Update Presenton Service

Add AWS auth support in `presenton_service.py`:

```python
# At top of file
from app.core.config import settings
if settings.PRESENTON_AUTH_TYPE == "aws_iam":
    from app.services.aws_auth import sign_request_with_iam

# In generate_powerpoint method
headers = {"Content-Type": "application/json"}

if settings.PRESENTON_AUTH_TYPE == "bearer":
    headers["Authorization"] = f"Bearer {self.api_key}"
elif settings.PRESENTON_AUTH_TYPE == "aws_iam":
    # Sign with AWS SigV4
    body = json.dumps(payload)
    headers = sign_request_with_iam(
        url=endpoint,
        method="POST",
        headers=headers,
        body=body,
        region=settings.PRESENTON_AWS_REGION
    )
# else: no auth (settings.PRESENTON_AUTH_TYPE == "none")
```

---

## 🔧 Quick Migration Steps

### For Internal ECS (No Auth) - RECOMMENDED

1. **Update config file**:
```bash
cd /home/ubuntu/AGENT/backend/app/core
nano config.py
```

Add after line 55:
```python
PRESENTON_REQUIRE_AUTH: bool = os.getenv("PRESENTON_REQUIRE_AUTH", "true").lower() == "true"
```

2. **Update presenton service**:
```bash
cd /home/ubuntu/AGENT/backend/app/services
nano presenton_service.py
```

- Add `self.require_auth = settings.PRESENTON_REQUIRE_AUTH` to `__init__`
- Replace headers section (lines 66-69) with conditional auth code shown above

3. **Update environment variables**:
```bash
cd /home/ubuntu/AGENT/backend
nano .env
```

Add/update:
```env
# AWS ECS Internal Presenton Service
PRESENTON_API_URL=http://your-ecs-service-url:port
PRESENTON_REQUIRE_AUTH=false
# Remove or comment out PRESENTON_API_KEY
```

4. **Restart backend**:
```bash
# If using systemd
sudo systemctl restart hrsp-backend

# If running manually
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📝 Files That Need Changes

### Required Changes (No Auth Migration)

1. **`backend/app/core/config.py`** (Line 55)
   - Add `PRESENTON_REQUIRE_AUTH` setting

2. **`backend/app/services/presenton_service.py`** (Lines 12-15, 64-79)
   - Add conditional authentication
   - Check `require_auth` before adding Bearer token

3. **`.env` or environment variables**
   - Set `PRESENTON_API_URL` to ECS endpoint
   - Set `PRESENTON_REQUIRE_AUTH=false`

### Optional Changes

4. **`backend/app/services/document_generator.py`** (Lines 58-112)
   - No changes needed (just uses presenton_service)

5. **Frontend files** (No changes needed)
   - Frontend already handles response from backend
   - No direct API calls to Presenton

---

## 🧪 Testing

After migration, test with:

```python
# Test from backend
cd /home/ubuntu/AGENT/backend
python3 -c "
from app.services.presenton_service import presenton_service
import asyncio

async def test():
    result = await presenton_service.generate_powerpoint(
        content='Test presentation about AWS',
        topic='AWS Services'
    )
    print('Success:', result)

asyncio.run(test())
"
```

Or test from UI:
1. Login to application
2. Ask: "Create a presentation about cloud computing"
3. Click "Yes, generate PowerPoint"
4. Check logs: `sudo journalctl -u hrsp-backend -f`

---

## 🚨 Important Notes

1. **Endpoint Format**: 
   - Internal ECS: `http://service-name.internal:port`
   - ALB: `http://your-alb-url.region.elb.amazonaws.com`
   - Private DNS: `http://presenton.private.yourdomain.com`

2. **Network Security**:
   - Ensure backend ECS task can reach Presenton ECS service
   - Check security groups allow outbound to Presenton port
   - Check Presenton security group allows inbound from backend

3. **Service Discovery**:
   - If using AWS Cloud Map / Service Discovery:
     ```env
     PRESENTON_API_URL=http://presenton.local:8080
     ```

4. **Health Checks**:
   - Add health check endpoint to verify connection
   - Test endpoint accessibility before migration

---

## 📊 Migration Checklist

- [ ] Identify AWS ECS Presenton service URL
- [ ] Verify network connectivity (backend → presenton)
- [ ] Update `config.py` with `PRESENTON_REQUIRE_AUTH` setting
- [ ] Update `presenton_service.py` with conditional auth
- [ ] Update `.env` with new URL and `PRESENTON_REQUIRE_AUTH=false`
- [ ] Test API connectivity (curl/httpx test)
- [ ] Restart backend service
- [ ] Test PowerPoint generation from UI
- [ ] Monitor logs for errors
- [ ] Update documentation

---

## 🔗 Key API Endpoint

**Current Public API Endpoint**:
```
POST https://api.presenton.ai/api/v1/ppt/presentation/generate
Authorization: Bearer {api_key}
```

**Your AWS ECS Endpoint** (example):
```
POST http://presenton-service.internal:8080/api/v1/ppt/presentation/generate
(No Authorization header)
```

---

## 📞 Need Help?

If you need the actual code changes made for you, let me know:
1. Your AWS ECS Presenton service URL
2. Whether it requires any authentication (IAM, custom headers, etc.)
3. Any custom payload differences from public API

I can then make the exact changes to your files!

---

**Created**: $(date)
**For**: AGENT Platform - Presenton API Migration
