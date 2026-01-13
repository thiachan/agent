# Presenton API - Complete Code Reference

## 📂 All Files Using Presenton API

### 1. Core Service Implementation

#### **`backend/app/services/presenton_service.py`** (Main Implementation)
```
Lines 1-121: Complete Presenton API integration

Key Components:
- Line 9-15:   PresentonService class initialization
- Line 17-34:  generate_powerpoint() method signature
- Line 35-36:  API key validation
- Line 46-58:  Request payload configuration
- Line 65-80:  API endpoint call with authentication
- Line 82-109: Response handling and result formatting
```

**Purpose**: Makes HTTP POST requests to Presenton API to generate PowerPoint presentations.

**Current Authentication**:
```python
headers = {
    "Authorization": f"Bearer {self.api_key}",  # Line 67-68
    "Content-Type": "application/json"
}
```

---

### 2. Configuration

#### **`backend/app/core/config.py`**
```
Line 53: PRESENTON_API_KEY = os.getenv("PRESENTON_API_KEY", "")
Line 54: PRESENTON_API_URL = os.getenv("PRESENTON_API_URL", "https://api.presenton.ai")
Line 55: PRESENTON_MAX_SLIDES = int(os.getenv("PRESENTON_MAX_SLIDES", "10"))
```

**Purpose**: Stores Presenton API configuration from environment variables.

---

### 3. Document Generator (Uses Presenton Service)

#### **`backend/app/services/document_generator.py`**
```
Line 57-115:  _generate_ppt() method
Line 60-112:  Presenton.ai API integration with fallback
Line 67:      Import presenton_service
Line 92-96:   Call presenton_service.generate_powerpoint()
Line 107:     Return JSON response with download path
Line 112:     Fallback to local generation if Presenton fails
```

**Purpose**: Orchestrates PowerPoint generation, tries Presenton first, falls back to local generation.

---

### 4. MCP Service (Model Context Protocol)

#### **`backend/app/services/mcp_service.py`**
```
Line 17:      Tool description: "Generate PowerPoint presentations"
Line 172:     PowerPoint generation using Presenton.ai API or fallback
Line 193:     Generate PowerPoint (tries Presenton first)
Line 203-216: Handle Presenton.ai JSON response with path
```

**Purpose**: Exposes PowerPoint generation as MCP tool for AI agents.

---

### 5. API Endpoint

#### **`backend/app/api/generate.py`**
```
Line 116-134: confirm_and_generate() endpoint
Line 134:     Returns agent result (includes Presenton path or base64)
```

**Purpose**: API endpoint that receives PowerPoint generation requests from frontend.

---

### 6. Frontend Integration

#### **`src/components/portal/ChatWithGeneration.tsx`**
```
Line 4:        Import Presentation icon
Line 31:       PPT type definition with icon
Line 209-211:  Detect PowerPoint generation keywords
Line 293-333:  Handle Presenton.ai response with download path
Line 417-464:  Handle async Presenton response
Line 1096-1100: Hide generation options if Presenton path exists
Line 1165-1189: Presenton.ai download button
Line 1259-1260: Presentation button UI
```

**Purpose**: Frontend component that triggers PowerPoint generation and handles downloads.

---

### 7. Frontend Upload Component

#### **`src/components/portal/DocumentUpload.tsx`**
```
Line 399: MIME type for PowerPoint files
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx']
```

**Purpose**: File upload handling for PPTX files.

---

## 🔍 API Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Request                                             │
│    "Create a presentation about cloud computing"            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Frontend: ChatWithGeneration.tsx                         │
│    - Detects PowerPoint keywords                            │
│    - Shows "Generate PowerPoint" button                     │
│    - User clicks button                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. API Call: POST /api/generate                             │
│    Payload: { type: "ppt", content: "...", topic: "..." }  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend: generate.py                                     │
│    - Receives request                                       │
│    - Calls document_generator._generate_ppt()              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Document Generator: document_generator.py                │
│    - Checks if PRESENTON_API_KEY is set                    │
│    - If yes: calls presenton_service.generate_powerpoint() │
│    - If no: falls back to local python-pptx generation     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Presenton Service: presenton_service.py                  │
│    ┌────────────────────────────────────────────────────┐  │
│    │ API Call Details:                                  │  │
│    │                                                     │  │
│    │ Endpoint:                                          │  │
│    │   POST {PRESENTON_API_URL}/api/v1/ppt/presentation/generate │
│    │                                                     │  │
│    │ Headers:                                           │  │
│    │   Authorization: Bearer {PRESENTON_API_KEY}       │  │
│    │   Content-Type: application/json                  │  │
│    │                                                     │  │
│    │ Payload:                                           │  │
│    │   {                                                │  │
│    │     "content": "...",                             │  │
│    │     "n_slides": 12,                               │  │
│    │     "language": "English",                        │  │
│    │     "template": "custom-31ec...",                 │  │
│    │     "theme": "36dada46-...",                      │  │
│    │     "export_as": "pptx",                          │  │
│    │     "tone": "professional",                       │  │
│    │     "verbosity": "standard",                      │  │
│    │     "image_type": "stock",                        │  │
│    │     "include_table_of_contents": true,            │  │
│    │     "include_title_slide": true                   │  │
│    │   }                                                │  │
│    └────────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Presenton.ai API Response                                │
│    {                                                        │
│      "presentation_id": "abc123",                          │
│      "path": "https://cdn.presenton.ai/.../file.pptx",    │
│      "edit_path": "https://app.presenton.ai/edit/abc123", │
│      "credits_consumed": 2                                 │
│    }                                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Response Flow Back                                       │
│    presenton_service → document_generator → generate.py    │
│    → ChatWithGeneration.tsx                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. Frontend Display                                         │
│    - Shows green "Download PowerPoint" button              │
│    - Clicking downloads from Presenton CDN path            │
│    - File saved as: presentation_{topic}.pptx              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Authentication Details

### Current Authentication Method

**Type**: Bearer Token (API Key)

**Location**: HTTP Header
```http
Authorization: Bearer {PRESENTON_API_KEY}
```

**Where API Key is Used**:
1. Read from environment: `config.py` line 53
2. Stored in service: `presenton_service.py` line 13
3. Validated: `presenton_service.py` line 35-36
4. Added to headers: `presenton_service.py` line 67-68

---

## 🌐 API Endpoint Details

### Current Public API

**Base URL**: `https://api.presenton.ai`

**Endpoint**: `/api/v1/ppt/presentation/generate`

**Full URL**: `https://api.presenton.ai/api/v1/ppt/presentation/generate`

**Method**: `POST`

**Timeout**: `300.0` seconds (5 minutes)

---

## 📦 Request Payload Structure

```json
{
  "content": "Text content to convert to slides",
  "n_slides": 12,
  "language": "English",
  "template": "custom-31ec1f9f-6111-43d8-95db-217e051a021b",
  "theme": "36dada46-7c64-47f2-aad8-4930660e3e7b",
  "export_as": "pptx",
  "tone": "professional",
  "verbosity": "standard",
  "image_type": "stock",
  "include_table_of_contents": true,
  "include_title_slide": true
}
```

**Customizable Parameters**:
- `content`: Generated from user conversation
- `n_slides`: Fixed at 12 (line 48)
- `template`: Cisco custom template ID (line 50)
- `theme`: Custom theme ID (line 51)

---

## 📤 Response Structure

```json
{
  "presentation_id": "unique-id-abc123",
  "path": "https://cdn.presenton.ai/download/file.pptx",
  "edit_path": "https://app.presenton.ai/edit/abc123",
  "credits_consumed": 2
}
```

**Response Handling**:
- `presentation_id`: Used for logging and filename
- `path`: Direct download URL sent to frontend
- `edit_path`: Optional edit link (not currently used)
- `credits_consumed`: Logged for monitoring

---

## 🛠️ To Migrate to AWS ECS

### Files to Modify:

1. **`backend/app/core/config.py`** - Add auth toggle
2. **`backend/app/services/presenton_service.py`** - Make auth conditional
3. **`.env`** - Update URL and disable auth

### No Changes Needed:

- `document_generator.py` (just uses presenton_service)
- `mcp_service.py` (just uses document_generator)
- `generate.py` (just uses document_generator)
- Frontend files (just handle response)

---

## 📝 Environment Variables

### Current (Public API with Auth)

```env
PRESENTON_API_KEY=sk-1234567890abcdef...
PRESENTON_API_URL=https://api.presenton.ai
PRESENTON_MAX_SLIDES=10
```

### After Migration (AWS ECS without Auth)

```env
# PRESENTON_API_KEY=  # Remove or leave empty
PRESENTON_API_URL=http://presenton-service.internal:8080
PRESENTON_MAX_SLIDES=10
PRESENTON_REQUIRE_AUTH=false  # NEW
```

---

## 📊 Summary Statistics

**Total Files Involved**: 7 files
- Backend Services: 4 files
- Backend Config: 1 file
- Backend API: 1 file
- Frontend: 1 file

**Lines of Code**:
- Main Service: ~120 lines
- Config: 3 lines
- Integration: ~50 lines (document_generator)
- Frontend: ~30 lines (relevant sections)

**API Calls**: 1 POST request per PowerPoint generation

**Average Generation Time**: 15-20 seconds

---

**Last Updated**: January 2026
**For**: AGENT Platform - Presenton Integration
