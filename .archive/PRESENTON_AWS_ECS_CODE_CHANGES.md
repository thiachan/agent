# Ready-to-Apply Code Changes for AWS ECS Migration

## 🎯 These changes remove the API key requirement and make authentication optional

---

## Change 1: Update Configuration

**File**: `backend/app/core/config.py`

**Action**: Add new setting after line 55

```python
# Find this section (lines 52-55):
# Presenton.ai PowerPoint Generation
PRESENTON_API_KEY: str = os.getenv("PRESENTON_API_KEY", "")
PRESENTON_API_URL: str = os.getenv("PRESENTON_API_URL", "https://api.presenton.ai")
PRESENTON_MAX_SLIDES: int = int(os.getenv("PRESENTON_MAX_SLIDES", "10"))

# ADD THIS NEW LINE after line 55:
PRESENTON_REQUIRE_AUTH: bool = os.getenv("PRESENTON_REQUIRE_AUTH", "true").lower() == "true"
```

---

## Change 2: Update Presenton Service

**File**: `backend/app/services/presenton_service.py`

### Change 2a: Update __init__ method (around line 12-15)

**FIND:**
```python
def __init__(self):
    self.api_key = settings.PRESENTON_API_KEY
    self.api_url = settings.PRESENTON_API_URL.rstrip('/')
    self.max_slides = settings.PRESENTON_MAX_SLIDES
```

**REPLACE WITH:**
```python
def __init__(self):
    self.api_key = settings.PRESENTON_API_KEY
    self.api_url = settings.PRESENTON_API_URL.rstrip('/')
    self.max_slides = settings.PRESENTON_MAX_SLIDES
    self.require_auth = settings.PRESENTON_REQUIRE_AUTH  # NEW: Make auth optional
```

---

### Change 2b: Update API key validation (around line 35-36)

**FIND:**
```python
if not self.api_key:
    raise ValueError("Presenton.ai API key not configured")
```

**REPLACE WITH:**
```python
if self.require_auth and not self.api_key:
    raise ValueError("Presenton API authentication required but API key not configured")
```

---

### Change 2c: Update logging (around line 40-43)

**FIND:**
```python
logger.info("=" * 60)
logger.info("PRESENTON.AI SERVICE: Starting PowerPoint generation")
logger.info(f"   API URL: {self.api_url}")
logger.info(f"   Max slides: {self.max_slides}")
logger.info("=" * 60)
```

**REPLACE WITH:**
```python
logger.info("=" * 60)
logger.info("PRESENTON SERVICE: Starting PowerPoint generation")
logger.info(f"   API URL: {self.api_url}")
logger.info(f"   Auth Required: {self.require_auth}")
logger.info(f"   Max slides: {self.max_slides}")
logger.info("=" * 60)
```

---

### Change 2d: Update headers section (around lines 64-73)

**FIND:**
```python
# Make the request to Presenton.ai API
endpoint = f"{self.api_url}/api/v1/ppt/presentation/generate"
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}

async with httpx.AsyncClient(timeout=300.0) as client:
    logger.info(f"Calling Presenton.ai API: {endpoint}")
    logger.info(f"Payload: {payload}")
```

**REPLACE WITH:**
```python
# Make the request to Presenton API
endpoint = f"{self.api_url}/api/v1/ppt/presentation/generate"

# Build headers - conditionally include authentication
headers = {"Content-Type": "application/json"}
if self.require_auth:
    headers["Authorization"] = f"Bearer {self.api_key}"
    logger.info("Using authenticated request (Bearer token)")
else:
    logger.info("Using non-authenticated request (internal service)")

async with httpx.AsyncClient(timeout=300.0) as client:
    logger.info(f"Calling Presenton API: {endpoint}")
    logger.info(f"Payload: {payload}")
```

---

### Change 2e: Update error messages (around lines 86-88, 111-116)

**FIND:**
```python
# Extract download path
if "path" not in result:
    raise ValueError(f"Presenton.ai API did not return a download path. Response: {result}")
```

**REPLACE WITH:**
```python
# Extract download path
if "path" not in result:
    raise ValueError(f"Presenton API did not return a download path. Response: {result}")
```

**FIND:**
```python
except httpx.HTTPStatusError as e:
    logger.error(f"Presenton.ai API HTTP error: {e.response.status_code} - {e.response.text}")
    raise ValueError(f"Presenton.ai API error: {e.response.status_code} - {e.response.text}")
except Exception as e:
    logger.error(f"Error calling Presenton.ai API: {e}", exc_info=True)
    raise ValueError(f"Failed to generate PowerPoint using Presenton.ai: {str(e)}")
```

**REPLACE WITH:**
```python
except httpx.HTTPStatusError as e:
    logger.error(f"Presenton API HTTP error: {e.response.status_code} - {e.response.text}")
    raise ValueError(f"Presenton API error: {e.response.status_code} - {e.response.text}")
except Exception as e:
    logger.error(f"Error calling Presenton API: {e}", exc_info=True)
    raise ValueError(f"Failed to generate PowerPoint using Presenton API: {str(e)}")
```

---

## Change 3: Update Environment Variables

**File**: `backend/.env` or your environment configuration

**For AWS ECS Internal Service (No Authentication):**

```env
# Presenton API - AWS ECS Internal Service
PRESENTON_API_URL=http://your-ecs-service-url:port
PRESENTON_REQUIRE_AUTH=false
# PRESENTON_API_KEY=  # Not needed when REQUIRE_AUTH=false
PRESENTON_MAX_SLIDES=12
```

**For Public API (Keep Current Setup):**

```env
# Presenton API - Public API with Authentication
PRESENTON_API_URL=https://api.presenton.ai
PRESENTON_REQUIRE_AUTH=true
PRESENTON_API_KEY=your_api_key_here
PRESENTON_MAX_SLIDES=12
```

---

## 📋 Summary of Changes

| File | Lines Changed | Type of Change |
|------|--------------|----------------|
| `config.py` | +1 line | Add new config option |
| `presenton_service.py` | ~15 lines | Make auth conditional |
| `.env` | 2 lines | Update URL, disable auth |

**Total Code Changes**: ~20 lines
**Files Modified**: 2 files (+ 1 config file)
**Complexity**: Low
**Risk**: Low (backward compatible)

---

## 🧪 Testing After Changes

### Test 1: Check Configuration

```bash
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
python3 -c "from app.core.config import settings; print('API URL:', settings.PRESENTON_API_URL); print('Require Auth:', settings.PRESENTON_REQUIRE_AUTH)"
```

Expected output:
```
API URL: http://your-ecs-service-url:port
Require Auth: False
```

### Test 2: Test Service Initialization

```bash
python3 -c "from app.services.presenton_service import presenton_service; print('Service initialized'); print('Auth required:', presenton_service.require_auth)"
```

Expected output:
```
Service initialized
Auth required: False
```

### Test 3: Test API Call (with test endpoint)

```bash
# Test connectivity to your ECS service
curl -X POST http://your-ecs-service-url:port/api/v1/ppt/presentation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test presentation",
    "n_slides": 3,
    "language": "English",
    "export_as": "pptx"
  }'
```

### Test 4: Test from Application

1. Start backend: `uvicorn app.main:app --reload`
2. Open frontend
3. Login
4. Send message: "Create a presentation about AWS"
5. Click "Generate PowerPoint"
6. Check backend logs: `tail -f logs/*.log` or `journalctl -u hrsp-backend -f`

---

## 🚀 Deployment Steps

### Step 1: Backup Current Files

```bash
cd /home/ubuntu/AGENT/backend
cp app/core/config.py app/core/config.py.backup
cp app/services/presenton_service.py app/services/presenton_service.py.backup
cp .env .env.backup
```

### Step 2: Apply Code Changes

You can either:

**Option A: Manual editing**
```bash
nano app/core/config.py         # Add PRESENTON_REQUIRE_AUTH line
nano app/services/presenton_service.py  # Apply all changes
nano .env                        # Update URL and add PRESENTON_REQUIRE_AUTH=false
```

**Option B: Let me apply the changes for you**
- Reply with your AWS ECS Presenton service URL
- I'll apply all changes automatically

### Step 3: Restart Backend

```bash
# If using systemd
sudo systemctl restart hrsp-backend

# If running manually
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Verify

```bash
# Check logs for successful startup
sudo journalctl -u hrsp-backend -f

# Or if running manually, check console output
```

### Step 5: Test

Test PowerPoint generation from the UI as described in Test 4 above.

---

## ↩️ Rollback Plan

If something goes wrong:

```bash
cd /home/ubuntu/AGENT/backend
cp app/core/config.py.backup app/core/config.py
cp app/services/presenton_service.py.backup app/services/presenton_service.py
cp .env.backup .env
sudo systemctl restart hrsp-backend
```

---

## 🔍 Troubleshooting

### Issue: "Presenton API authentication required but API key not configured"

**Solution**: Make sure `.env` has:
```env
PRESENTON_REQUIRE_AUTH=false
```

### Issue: Connection refused / timeout

**Possible causes**:
1. Wrong ECS service URL
2. Network security groups blocking traffic
3. ECS service not running
4. Wrong port number

**Debug**:
```bash
# Test from backend EC2 instance
curl -v http://your-ecs-service-url:port/health  # or whatever health endpoint

# Check DNS resolution
nslookup your-ecs-service-url

# Test connection
telnet your-ecs-service-url port
```

### Issue: 404 Not Found

**Solution**: Verify the endpoint path on your ECS service matches:
```
/api/v1/ppt/presentation/generate
```

### Issue: Different payload format

If your AWS ECS Presenton service expects a different payload format, update line 46-58 in `presenton_service.py`.

---

## 📞 Ready to Apply?

**What I need from you**:

1. **Your AWS ECS Presenton Service URL**
   - Example: `http://presenton-service.internal:8080`
   - Or: `http://my-presenton-alb-123456.us-east-1.elb.amazonaws.com`

2. **Confirmation that no authentication is needed**
   - Does your ECS service accept requests without auth headers?
   - Or does it use IAM / custom headers?

3. **Endpoint path confirmation**
   - Is it: `/api/v1/ppt/presentation/generate` ?
   - Or different?

Once you provide these details, I can either:
- Apply all changes automatically, or
- Provide exact commands to run

---

**Created**: January 2026
**Status**: Ready to apply
**Backward Compatible**: Yes (set `PRESENTON_REQUIRE_AUTH=true` to use old behavior)
