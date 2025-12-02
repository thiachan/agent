# AGENT Platform - Comprehensive Technical Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Database Schema](#database-schema)
5. [API Architecture](#api-architecture)
6. [Core Services](#core-services)
7. [Authentication & Authorization](#authentication--authorization)
8. [RAG Implementation](#rag-implementation)
9. [Frontend Architecture](#frontend-architecture)
10. [Document Processing](#document-processing)
11. [AI Model Management](#ai-model-management)
12. [Security](#security)
13. [Performance & Scalability](#performance--scalability)
14. [Deployment](#deployment)
15. [Development Guide](#development-guide)

---

## System Overview

**AGENT (AI for GSSE Engineering Team)** is an enterprise-grade AI-powered platform that enables employees to interact with business knowledge through natural language queries. The system uses Retrieval-Augmented Generation (RAG) to provide context-aware responses based on uploaded documents.

### Key Capabilities

- **Intelligent Chat Interface**: Natural language Q&A powered by GPT-4.1 (Cisco) with RAG
- **Knowledge Base Management**: Organize documents into knowledge bases with full CRUD operations
- **Multi-Format Document Processing**: Supports PDF, DOC, PPT, XLS, MP4, MOV, MP3, WAV, TXT, MD, CSV, JSON
- **Semantic Search**: Vector-based search using ChromaDB and OpenAI embeddings
- **Content Generation**: Generate PowerPoint presentations, Word documents, PDFs, podcasts, and speeches
- **Demo Video Search**: Intelligent search for existing demo videos with YouTube integration
- **Role-Based Access Control**: Admin and employee roles with permission-based document access
- **Email Verification & Password Reset**: Secure user onboarding and account recovery

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Next.js    │  │   React       │  │   Zustand    │      │
│  │   (App Router)│  │   Components │  │   State Mgmt │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │ HTTP/REST
                            │ JWT Auth
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend API Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   FastAPI    │  │   SQLAlchemy │  │   Pydantic   │      │
│  │   Routers    │  │   ORM        │  │   Validation │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Services   │  │   Database   │  │   Vector DB   │
│   Layer      │  │   (SQLite)   │  │  (ChromaDB)   │
└──────────────┘  └──────────────┘  └──────────────┘
        │
        ├─── RAG Service
        ├─── Model Manager
        ├─── Document Processor
        ├─── Document Generator
        ├─── Demo Video Service
        ├─── MCP Service
        ├─── Email Service
        └─── TTS Service
```

### Component Architecture

#### Backend Structure

```
backend/
├── app/
│   ├── api/              # API route handlers
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── chat.py       # Chat message handling
│   │   ├── documents.py # Document CRUD
│   │   ├── upload.py     # File upload handling
│   │   ├── generate.py  # Content generation
│   │   ├── models.py     # Model management
│   │   ├── agents.py     # MCP agent endpoints
│   │   └── knowledge_bases.py  # Knowledge base CRUD
│   │
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration management
│   │   ├── database.py   # Database connection
│   │   ├── dependencies.py  # FastAPI dependencies
│   │   └── security.py   # JWT & password hashing
│   │
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── user.py       # User model
│   │   ├── document.py   # Document model
│   │   ├── chat.py       # Chat session/message models
│   │   └── knowledge_base.py  # Knowledge base model
│   │
│   └── services/         # Business logic services
│       ├── rag_service.py         # RAG implementation
│       ├── model_manager.py        # AI model management
│       ├── document_processor.py  # Document text extraction
│       ├── document_generator.py  # Content generation
│       ├── demo_video_service.py  # Demo video search
│       ├── mcp_service.py         # MCP agent service
│       ├── email_service.py       # Email sending
│       ├── tts_service.py         # Text-to-speech
│       └── presenton_service.py   # PowerPoint generation
│
├── main.py               # FastAPI application entry point
├── init_db.py            # Database initialization
└── requirements.txt      # Python dependencies
```

#### Frontend Structure

```
src/
├── app/                  # Next.js App Router pages
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Login page
│   ├── verify-email/     # Email verification page
│   └── reset-password/   # Password reset page
│
├── components/           # React components
│   ├── auth/
│   │   └── LoginForm.tsx # Login/signup form
│   └── portal/
│       ├── MainPortal.tsx        # Main layout with sidebar
│       ├── ChatWithGeneration.tsx # Chat interface
│       └── DocumentUpload.tsx    # Document management
│
├── lib/
│   └── api.ts            # Axios API client with interceptors
│
└── stores/
    └── authStore.ts      # Zustand authentication store
```

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Core language |
| **FastAPI** | 0.104.1 | Web framework |
| **Uvicorn** | 0.24.0 | ASGI server |
| **SQLAlchemy** | 2.0.23 | ORM |
| **Pydantic** | 2.5.2 | Data validation |
| **LangChain** | 0.1.0 | LLM orchestration |
| **ChromaDB** | 0.4.18 | Vector database |
| **OpenAI** | 1.0.0+ | Embeddings & TTS |
| **PyPDF2** | 3.0.1 | PDF processing |
| **python-docx** | 1.1.0 | Word document processing |
| **python-pptx** | 0.6.23 | PowerPoint processing |
| **openpyxl** | 3.1.2 | Excel processing |
| **pydub** | 0.25.1 | Audio processing |
| **moviepy** | 1.0.3 | Video processing |
| **openai-whisper** | Latest | Audio/video transcription |
| **fastapi-mail** | 1.4.1 | Email sending |
| **python-jose** | 3.3.0 | JWT handling |
| **passlib** | 1.7.4 | Password hashing |
| **boto3** | 1.34.72+ | AWS Bedrock integration |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 14.0.4 | React framework |
| **React** | 18.2.0 | UI library |
| **TypeScript** | 5.3.3 | Type safety |
| **Tailwind CSS** | 3.4.0 | Styling |
| **Zustand** | 4.4.7 | State management |
| **Axios** | 1.6.2 | HTTP client |
| **Lucide React** | 0.303.0 | Icons |
| **react-dropzone** | 14.2.3 | File upload |

### External Services

- **Cisco GPT-4.1**: Primary LLM for chat (OAuth2 authentication)
- **OpenAI API**: Embeddings (text-embedding-3-small) and TTS
- **Presenton.ai**: PowerPoint generation
- **HeyGen**: Video generation (optional)
- **AWS Bedrock**: Alternative LLM provider (optional)

---

## Database Schema

### SQLite Database (intranet.db)

#### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'employee',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR,
    verification_token_expires DATETIME,
    reset_token VARCHAR,
    reset_token_expires DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**User Roles:**
- `admin`: Full access including document upload/management
- `employee`: Chat access, cannot upload documents
- `engineer`: Engineering team access
- `hr`: HR team access
- `manager`: Management access

#### Documents Table

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    file_type VARCHAR NOT NULL,
    file_size INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    knowledge_base_id INTEGER,
    is_public BOOLEAN DEFAULT FALSE,
    allowed_roles VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id),
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id)
);
```

#### Knowledge Bases Table

```sql
CREATE TABLE knowledge_bases (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
```

#### Chat Sessions Table

```sql
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Chat Messages Table

```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role VARCHAR NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    message_metadata JSON,  -- Stores sources, agent calls, etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);
```

### ChromaDB Vector Database

**Location**: `./vector_db/` (configurable via `VECTOR_DB_PATH`)

**Collection Structure:**
- **Collection Name**: `langchain` (default)
- **Embedding Model**: OpenAI `text-embedding-3-small`
- **Metadata Fields**:
  - `document_id`: Links to SQLite documents table
  - `filename`: Original filename
  - `title`: Document title
  - `tags`: Comma-separated tags
  - `is_public`: Boolean
  - `allowed_roles`: Comma-separated roles
  - `owner_id`: Document owner ID
  - `knowledge_base_id`: Knowledge base ID

**Chunking Strategy:**
- **Chunk Size**: 1000 characters
- **Chunk Overlap**: 200 characters
- **Splitter**: RecursiveCharacterTextSplitter (LangChain)

---

## API Architecture

### FastAPI Application Structure

**Entry Point**: `backend/main.py`

```python
app = FastAPI(
    title="GSSE AI Center API",
    description="GSSE AI-Powered Enterprise Platform Backend",
    version="1.0.0"
)
```

### API Routes

#### Authentication (`/api/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/register` | Register new user | No |
| POST | `/login` | Login user | No |
| GET | `/me` | Get current user info | Yes |
| POST | `/verify-email` | Verify email with token | No |
| POST | `/resend-verification` | Resend verification email | No |
| POST | `/forgot-password` | Request password reset | No |
| POST | `/reset-password` | Reset password with token | No |

**Request/Response Examples:**

```python
# Register
POST /api/auth/register
{
    "email": "user@example.com",
    "password": "secure_password",
    "full_name": "John Doe",
    "role": "employee"
}

# Login
POST /api/auth/login
{
    "email": "user@example.com",
    "password": "secure_password"
}

Response:
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "full_name": "John Doe",
        "role": "employee"
    }
}
```

#### Chat (`/api/chat`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/message` | Send chat message | Yes |
| GET | `/sessions` | List chat sessions | Yes |
| GET | `/sessions/{id}/messages` | Get session messages | Yes |
| DELETE | `/sessions/{id}` | Delete session | Yes |

**Chat Message Request:**

```python
POST /api/chat/message
{
    "message": "What is Cloud Edge?",
    "session_id": 123,  # Optional, creates new if not provided
    "model_id": "auto",  # Optional, defaults to "auto"
    "content_type": null  # Optional: "doc", "ppt", "mp4", "podcast", "speech"
}

Response:
{
    "session_id": 123,
    "message": {
        "id": 456,
        "role": "assistant",
        "content": "Cloud Edge is...",
        "metadata": {
            "sources": [...],
            "model_used": "cisco-gpt-4.1"
        }
    }
}
```

#### Documents (`/api/documents`)

| Method | Endpoint | Description | Auth Required | Role Required |
|--------|----------|-------------|---------------|---------------|
| GET | `/` | List documents | Yes | Any |
| DELETE | `/{id}` | Delete document | Yes | Admin |

#### Upload (`/api/upload`)

| Method | Endpoint | Description | Auth Required | Role Required |
|--------|----------|-------------|---------------|---------------|
| POST | `/file` | Upload document | Yes | Admin |

**Upload Request:**

```python
POST /api/upload/file
Content-Type: multipart/form-data

FormData:
- file: <file>
- knowledge_base_id: 1 (optional)
- is_public: true/false (optional)
- allowed_roles: "admin,employee" (optional)
```

#### Generation (`/api/generate`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/document` | Generate document (PPT, DOC, PDF, MP3, WAV, Speech, Podcast) | Yes |
| POST | `/confirm-ppt` | Confirm and generate PowerPoint | Yes |

**Generation Request:**

```python
POST /api/generate/document
{
    "content_type": "ppt",  # "ppt", "doc", "pdf", "mp3", "wav", "speech", "podcast"
    "content": "Content to generate...",
    "topic": "Cloud Edge Overview",
    "session_id": 123
}
```

#### Knowledge Bases (`/api/knowledge-bases`)

| Method | Endpoint | Description | Auth Required | Role Required |
|--------|----------|-------------|---------------|---------------|
| GET | `/` | List knowledge bases | Yes | Any |
| POST | `/` | Create knowledge base | Yes | Admin |
| PUT | `/{id}` | Update knowledge base | Yes | Admin |
| DELETE | `/{id}` | Delete knowledge base | Yes | Admin |

#### Models (`/api/models`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List available AI models | Yes |

#### Agents (`/api/agents`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List available MCP agents | Yes |
| POST | `/{agent_id}/call` | Call an MCP agent | Yes |

### Authentication Flow

1. **Registration**:
   - User registers with email, password, full_name
   - Password is hashed using bcrypt
   - User is created with `is_verified=False` (if email verification enabled)
   - Verification email sent (if email verification enabled)

2. **Email Verification** (if enabled):
   - User clicks link in email
   - Token validated (expires after 24 hours)
   - User `is_verified` set to `True`

3. **Login**:
   - User provides email and password
   - Password verified against hash
   - JWT token generated (expires in 24 hours)
   - Token returned to client

4. **Authenticated Requests**:
   - Client sends token in `Authorization: Bearer <token>` header
   - FastAPI dependency `get_current_user` validates token
   - User object attached to request

### Authorization

**Role-Based Access Control (RBAC):**

- **Admin**: Full access to all endpoints
- **Employee**: Read-only access to documents, can chat
- **Document-Level Permissions**:
  - `is_public=True`: All authenticated users can access
  - `allowed_roles`: Only specified roles can access
  - Owner always has access

**Permission Check Flow:**

```python
# In document search/retrieval
has_access = (
    metadata.get("is_public", False) or
    user_role in (metadata.get("allowed_roles", "") or "").split(",") or
    metadata.get("owner_id") == current_user.id
)
```

---

## Core Services

### RAG Service (`rag_service.py`)

**Purpose**: Implements Retrieval-Augmented Generation for context-aware responses.

**Key Methods:**

1. **`add_document(text, metadata)`**
   - Splits text into chunks (1000 chars, 200 overlap)
   - Generates embeddings using OpenAI
   - Stores in ChromaDB with metadata

2. **`search(query, user_role, limit=10)`**
   - Converts query to embedding
   - Performs similarity search in ChromaDB
   - Applies multiple search strategies:
     - Direct similarity search
     - Normalized query (hyphens → spaces)
     - Hyphenated query (spaces → hyphens)
     - Term-based search
     - Filename-based search
   - Applies relevance boosting:
     - Filename matches: -0.4 to -0.5 score boost
     - Title matches: -0.35 to -0.45 boost
     - Tag matches: -0.3 boost
     - Conversation continuity: -0.3 boost
   - Filters by user permissions
   - Returns top N chunks sorted by relevance

3. **`query(question, user_role, model_id, conversation_history, content_type)`**
   - Retrieves relevant context using `search()`
   - Builds prompt with context and conversation history
   - Invokes LLM (Cisco GPT-4.1) with prompt
   - Returns answer and source citations

**RAG Prompt Template:**

```
You are an AI assistant for GSSE AI Center. Your role is to be extremely helpful by extracting, synthesizing, and presenting information directly from the uploaded documents.

CRITICAL INSTRUCTIONS:
1. USE CONVERSATION HISTORY: If the user refers to "it", "this", "that", or uses pronouns, look at the previous conversation to understand what they're referring to.
2. EXTRACT AND PRESENT DIRECTLY: Your primary goal is to extract key information from the documents and present it directly to the user.
3. BE COMPREHENSIVE: Dig deep into the context provided. Extract all relevant information, key points, features, benefits, and details.
4. USE ONLY DOCUMENT CONTEXT: Base your answer ONLY on the information provided in the "Context from documents" section below.

{history_context}

Context from documents (extract and synthesize information from this):
{context}

Current Question: {question}
```

**Search Strategy Details:**

1. **Multi-Strategy Search**: Searches with original query, normalized query, hyphenated query, and individual terms
2. **Relevance Boosting**: Documents with matching filenames/titles/tags rank higher
3. **Document Prioritization**: Prioritizes chunks from boosted documents
4. **Conversation Continuity**: Boosts documents used in previous messages
5. **Permission Filtering**: Only returns documents user has access to

### Model Manager (`model_manager.py`)

**Purpose**: Manages multiple AI models from different providers.

**Supported Providers:**

1. **Cisco GPT-4.1** (Primary)
   - OAuth2 authentication via `https://id.cisco.com/oauth2/default/v1/token`
   - Uses Azure OpenAI-compatible endpoint
   - Token auto-refreshes when expired
   - Deployment name extracted from endpoint or config

2. **OpenAI** (Embeddings & TTS)
   - Embeddings: `text-embedding-3-small`
   - TTS: Multiple voices (alloy, echo, fable, onyx, nova, shimmer)

3. **AWS Bedrock** (Optional)
   - Supports multiple models (Claude, Llama, Mistral, etc.)
   - Handles throttling with exponential backoff
   - Supports both ChatBedrock and BedrockLLM interfaces

**Key Methods:**

- `get_chat_model(model_id, temperature)`: Returns LLM instance
- `get_embedding_model()`: Returns embedding model
- `list_models()`: Lists available models
- `_get_cisco_token()`: Gets/refreshes Cisco OAuth2 token

**Token Management:**

- Cisco tokens expire after 1 hour
- Auto-refreshes 5 minutes before expiration
- Token stored in memory with expiration timestamp

### Document Processor (`document_processor.py`)

**Purpose**: Extracts text from various file formats.

**Supported Formats:**

| Format | Library | Method |
|--------|---------|--------|
| PDF | PyPDF2 | `_extract_from_pdf()` |
| DOC/DOCX | python-docx | `_extract_from_docx()` |
| PPT/PPTX | python-pptx | `_extract_from_pptx()` |
| XLS/XLSX | openpyxl | `_extract_from_xlsx()` |
| MP3/WAV/M4A | Whisper | `_extract_from_audio()` |
| MP4/MOV/AVI | Whisper + MoviePy | `_extract_from_video()` |
| TXT/MD | File read | `_extract_from_text()` |
| JSON | json.load | `_extract_from_json()` |
| JSONL | Line-by-line JSON | `_extract_from_jsonl()` |

**Processing Flow:**

1. File uploaded via `/api/upload/file`
2. File saved to `UPLOAD_DIR` (default: `./uploads`)
3. `DocumentProcessor.extract_text()` called
4. Text extracted based on file type
5. Text passed to RAG service for chunking and embedding
6. Document metadata stored in SQLite
7. Chunks stored in ChromaDB

### Document Generator (`document_generator.py`)

**Purpose**: Generates various content types from text.

**Supported Generation Types:**

1. **PowerPoint (PPT)**
   - Uses Presenton.ai API
   - Custom template and theme
   - Content preview before generation
   - User confirmation required

2. **Word Document (DOC)**
   - Uses python-docx
   - Formats content with headings, paragraphs, lists
   - Exports as .docx

3. **PDF**
   - Uses reportlab
   - Converts content to PDF format
   - Exports as .pdf

4. **Podcast (MP3)**
   - Generates dialogue script (Host/Guest)
   - Uses OpenAI TTS with different voices
   - Combines audio segments
   - Exports as .mp3

5. **Speech (MP3/WAV)**
   - Generates monologue script
   - Uses OpenAI TTS
   - Exports as .mp3 or .wav

**Generation Flow:**

1. User requests generation (via chat or API)
2. Content extracted from conversation or provided directly
3. Script/content generated using LLM
4. For audio: TTS conversion (non-blocking, async)
5. File generated and returned to user

### Demo Video Service (`demo_video_service.py`)

**Purpose**: Intelligent search for existing demo videos.

**Features:**

- **Precise Matching**: Matches product names, tags, filenames
- **Acronym Support**: Handles acronyms (EVE, AIOps, RTC, etc.)
- **RAG Integration**: Semantic search across demo video documents
- **Suggestion System**: Provides relevant videos when exact match not found
- **YouTube Integration**: Extracts YouTube links from documents

**Search Flow:**

1. Query cleaned (removes common words, normalizes)
2. Multiple search strategies:
   - Exact product name match
   - Tag matching
   - Filename matching
   - RAG semantic search
3. Results ranked by relevance
4. YouTube links extracted from document content
5. Returns videos with titles, descriptions, embed URLs

### MCP Service (`mcp_service.py`)

**Purpose**: Model Context Protocol agent service for specialized tasks.

**Available Agents:**

- `create_video`: Demo video search
- `video_generate`: Video generation (HeyGen integration)
- `create_ppt`: PowerPoint generation
- `create_doc`: Document generation
- `create_podcast`: Podcast generation
- `create_speech`: Speech generation

**Agent Call Flow:**

1. User intent detected in chat message
2. Appropriate agent selected
3. Agent called with parameters
4. Result returned to user

### Email Service (`email_service.py`)

**Purpose**: Sends transactional emails (verification, password reset).

**Features:**

- SMTP configuration (Gmail, custom SMTP)
- HTML email templates
- Token generation and validation
- Email verification links
- Password reset links

**Email Types:**

1. **Verification Email**: Sent on registration
2. **Password Reset Email**: Sent on forgot password request
3. **Resend Verification**: Resends verification email

### TTS Service (`tts_service.py`)

**Purpose**: Text-to-speech conversion using OpenAI TTS API.

**Features:**

- Multiple voice options
- MP3 and WAV formats
- Non-blocking async execution
- Dialogue support (Host/Guest voices)

**Usage:**

```python
# Generate speech
audio_file = await tts_service.generate_speech(
    text="Hello world",
    voice="nova",
    format="mp3"
)

# Generate podcast dialogue
audio_file = await tts_service.generate_podcast(
    dialogue=[
        {"role": "host", "text": "Welcome..."},
        {"role": "guest", "text": "Thank you..."}
    ],
    host_voice="nova",
    guest_voice="onyx",
    format="mp3"
)
```

---

## Authentication & Authorization

### Password Hashing

**Algorithm**: bcrypt

**Implementation:**

```python
def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]  # bcrypt limit
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

### JWT Tokens

**Algorithm**: HS256

**Token Structure:**

```json
{
    "sub": "user_id",
    "exp": 1234567890,
    "email": "user@example.com",
    "role": "employee"
}
```

**Token Expiration**: 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

**Token Generation:**

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if 'sub' in to_encode:
        to_encode['sub'] = str(to_encode['sub'])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### Email Verification

**Flow:**

1. User registers → Verification token generated
2. Token stored in database with expiration (24 hours)
3. Verification email sent with link: `{FRONTEND_URL}/verify-email?token={token}`
4. User clicks link → Token validated
5. User `is_verified` set to `True`
6. User can now login

**Token Generation:**

```python
import secrets
token = secrets.token_urlsafe(32)
verification_token_expires = datetime.utcnow() + timedelta(hours=24)
```

### Password Reset

**Flow:**

1. User requests reset → Reset token generated
2. Token stored in database with expiration (1 hour)
3. Reset email sent with link: `{FRONTEND_URL}/reset-password?token={token}`
4. User clicks link → Enters new password
5. Token validated → Password hashed and updated
6. Reset token cleared

---

## RAG Implementation

### Vector Database (ChromaDB)

**Configuration:**

- **Path**: `./vector_db/` (configurable)
- **Embedding Model**: OpenAI `text-embedding-3-small`
- **Collection**: `langchain` (default)

**Chunking Strategy:**

- **Chunk Size**: 1000 characters
- **Chunk Overlap**: 200 characters
- **Splitter**: `RecursiveCharacterTextSplitter`

**Why These Values:**

- 1000 chars: Balances context size with retrieval precision
- 200 overlap: Ensures continuity between chunks
- Recursive splitter: Preserves sentence boundaries

### Embedding Process

1. **Document Upload**:
   ```
   File → DocumentProcessor.extract_text() → Text
   ```

2. **Chunking**:
   ```
   Text → RecursiveCharacterTextSplitter → [Chunk1, Chunk2, ...]
   ```

3. **Embedding**:
   ```
   [Chunk1, Chunk2, ...] → OpenAI Embeddings → [Vector1, Vector2, ...]
   ```

4. **Storage**:
   ```
   [Vector1, Vector2, ...] + Metadata → ChromaDB.add_texts()
   ```

### Retrieval Process

1. **Query Embedding**:
   ```
   User Query → OpenAI Embeddings → Query Vector
   ```

2. **Similarity Search**:
   ```
   Query Vector → ChromaDB.similarity_search_with_score() → [(Doc, Score), ...]
   ```

3. **Relevance Boosting**:
   - Filename matches: -0.4 to -0.5 score boost
   - Title matches: -0.35 to -0.45 boost
   - Tag matches: -0.3 boost
   - Conversation continuity: -0.3 boost

4. **Permission Filtering**:
   - Check `is_public`, `allowed_roles`, `owner_id`
   - Only return accessible documents

5. **Context Building**:
   ```
   Top N Chunks → Join with "\n\n" → Context String
   ```

6. **LLM Generation**:
   ```
   Context + Query + History → LLM Prompt → Answer
   ```

### Search Strategies

**Multi-Strategy Approach:**

1. **Direct Similarity**: Original query as-is
2. **Normalized Query**: Hyphens → spaces ("zero-trust" → "zero trust")
3. **Hyphenated Query**: Spaces → hyphens ("zero trust" → "zero-trust")
4. **Term-Based**: Individual important terms
5. **Filename-Based**: Match query terms to filenames

**Why Multiple Strategies:**

- Handles variations in query formatting
- Improves recall (finds more relevant documents)
- Accounts for different document naming conventions

### Relevance Boosting Algorithm

**Score Calculation:**

```python
boosted_score = original_score + filename_match_score + title_match_score + tag_match_score + conversation_boost
```

**Boosting Rules:**

- **Filename Match**:
  - 50%+ terms match: -0.4 boost
  - <50% terms match: -0.25 * match_ratio boost
  - All terms in filename: -0.5 boost

- **Title Match**:
  - 50%+ terms match: -0.35 boost
  - <50% terms match: -0.2 * match_ratio boost
  - All terms in title: -0.45 boost

- **Tag Match**:
  - 50%+ terms match: -0.3 boost
  - <50% terms match: -0.15 * match_ratio boost

- **Conversation Continuity**:
  - Document used in previous messages: -0.3 boost

**Why Negative Scores:**

- ChromaDB uses distance metrics (lower = better)
- Boosting reduces the score (makes it better)

### Conversation Context

**Context Extraction:**

1. **Previous Messages**: Last 10 messages included in prompt
2. **Source Tracking**: Documents cited in previous messages tracked
3. **Topic Keywords**: Extracted from previous questions
4. **Pronoun Resolution**: "it", "this", "that" resolved from history

**Context Usage:**

- Enhances search query with topic keywords
- Boosts documents used in previous messages
- Helps LLM understand references

---

## Frontend Architecture

### Next.js App Router

**Structure:**

```
app/
├── layout.tsx          # Root layout (providers, global styles)
├── page.tsx            # Login page
├── verify-email/
│   └── page.tsx        # Email verification page
└── reset-password/
    └── page.tsx        # Password reset page
```

**Routing:**

- File-based routing
- Server Components by default
- Client Components with `'use client'` directive

### State Management (Zustand)

**Auth Store (`authStore.ts`):**

```typescript
interface AuthState {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  register: (email: string, password: string, fullName: string) => Promise<void>
}
```

**Usage:**

```typescript
const { user, login, logout } = useAuthStore()
```

### API Client (`api.ts`)

**Axios Configuration:**

- Base URL from `NEXT_PUBLIC_API_URL`
- Request interceptor: Adds JWT token to headers
- Response interceptor: Handles 401 errors (token expired)

**Request Interceptor:**

```typescript
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

**Response Interceptor:**

```typescript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem('auth_token')) {
      localStorage.removeItem('auth_token')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)
```

### Components

#### MainPortal (`MainPortal.tsx`)

**Features:**

- Collapsible sidebar
- Navigation (Chat, Knowledge Base)
- Recent chats list
- User profile
- Logout

**State:**

- `activeView`: 'chat' | 'upload'
- `sidebarOpen`: boolean
- `recentChats`: ChatSession[]
- `selectedChatId`: number | null

#### ChatWithGeneration (`ChatWithGeneration.tsx`)

**Features:**

- Chat message display
- Message input
- Session management
- Content generation buttons (PPT, DOC, PDF, MP3, etc.)
- Video embedding
- Connection status

**State:**

- `messages`: Message[]
- `sessionId`: number | null
- `isLoading`: boolean
- `connectionStatus`: 'connected' | 'disconnected'

#### DocumentUpload (`DocumentUpload.tsx`)

**Features:**

- Drag-and-drop file upload
- Knowledge base selection
- Document list with filtering
- Document deletion
- Upload progress

**State:**

- `documents`: Document[]
- `knowledgeBases`: KnowledgeBase[]
- `selectedKnowledgeBase`: number | null
- `uploadProgress`: number

### Styling

**Tailwind CSS Configuration:**

- Dark theme: `bg-[#07182D]` (background)
- Cyan-blue gradients: `from-cyan-500 to-blue-600`
- Custom scrollbars
- Responsive design

**Color Scheme:**

- Background: `#07182D` (dark blue)
- Primary: Cyan (`#06b6d4`) to Blue (`#2563eb`)
- Text: White/Gray scale
- Borders: `slate-700/50`

---

## Document Processing

### Supported File Types

| Type | Extension | Processor | Notes |
|------|-----------|-----------|-------|
| PDF | `.pdf` | PyPDF2 | Text extraction from all pages |
| Word | `.doc`, `.docx` | python-docx | Paragraph extraction |
| PowerPoint | `.ppt`, `.pptx` | python-pptx | Slide text extraction |
| Excel | `.xls`, `.xlsx` | openpyxl | Sheet and cell extraction |
| Audio | `.mp3`, `.wav`, `.m4a` | Whisper | Speech-to-text transcription |
| Video | `.mp4`, `.mov`, `.avi` | Whisper + MoviePy | Audio track transcription |
| Text | `.txt`, `.md` | File read | Direct text read |
| Data | `.json`, `.jsonl`, `.csv` | JSON/CSV parser | Structured data extraction |

### Processing Pipeline

```
1. File Upload
   ↓
2. File Validation (type, size)
   ↓
3. Save to UPLOAD_DIR
   ↓
4. Extract Text (DocumentProcessor)
   ↓
5. Chunk Text (RecursiveCharacterTextSplitter)
   ↓
6. Generate Embeddings (OpenAI)
   ↓
7. Store in ChromaDB (with metadata)
   ↓
8. Store Document Record (SQLite)
   ↓
9. Return Success
```

### Text Extraction Details

**PDF (`_extract_from_pdf`):**

```python
def _extract_from_pdf(file_path: str) -> str:
    text = ""
    with open(file_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text
```

**Word (`_extract_from_docx`):**

```python
def _extract_from_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])
```

**PowerPoint (`_extract_from_pptx`):**

```python
def _extract_from_pptx(file_path: str) -> str:
    prs = Presentation(file_path)
    text_parts = []
    for slide_num, slide in enumerate(prs.slides, 1):
        text_parts.append(f"Slide {slide_num}:\n")
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_parts.append(shape.text)
    return "\n".join(text_parts)
```

**Excel (`_extract_from_xlsx`):**

```python
def _extract_from_xlsx(file_path: str) -> str:
    workbook = load_workbook(file_path)
    text_parts = []
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        text_parts.append(f"Sheet: {sheet_name}\n")
        for row in sheet.iter_rows(values_only=True):
            text_parts.append("\t".join([str(cell) if cell else "" for cell in row]))
    return "\n".join(text_parts)
```

**Audio/Video (`_extract_from_audio` / `_extract_from_video`):**

```python
def _extract_from_audio(file_path: str) -> str:
    model = self._load_whisper_model()  # Lazy load
    result = model.transcribe(file_path)
    return result["text"]

def _extract_from_video(file_path: str) -> str:
    # Extract audio track
    video = VideoFileClip(file_path)
    audio_path = file_path.replace(file_path.split('.')[-1], 'wav')
    video.audio.write_audiofile(audio_path)
    
    # Transcribe audio
    model = self._load_whisper_model()
    result = model.transcribe(audio_path)
    return result["text"]
```

### Chunking Strategy

**RecursiveCharacterTextSplitter:**

- **Chunk Size**: 1000 characters
- **Chunk Overlap**: 200 characters
- **Separators**: `["\n\n", "\n", " ", ""]` (in order of preference)

**Why Recursive:**

- Preserves sentence boundaries
- Handles different document structures
- Falls back gracefully if preferred separators not found

**Chunk ID Format:**

```
{document_id}_{chunk_index}
```

Example: `123_0`, `123_1`, `123_2`

### Metadata Storage

**ChromaDB Metadata:**

```python
{
    "document_id": 123,
    "filename": "cloud-edge-guide.pdf",
    "title": "Cloud Edge Architecture Guide",
    "tags": "cloud,edge,networking",
    "is_public": False,
    "allowed_roles": "admin,engineer",
    "owner_id": 1,
    "knowledge_base_id": 5
}
```

**Why Metadata:**

- Enables permission filtering
- Improves search relevance (filename/title matching)
- Supports knowledge base organization
- Tracks document ownership

---

## AI Model Management

### Model Providers

#### 1. Cisco GPT-4.1 (Primary)

**Authentication:**

- **Method**: OAuth2 Client Credentials Flow
- **Token URL**: `https://id.cisco.com/oauth2/default/v1/token`
- **Grant Type**: `client_credentials`
- **Credentials**: Base64 encoded `CLIENT_ID:CLIENT_SECRET`

**Token Management:**

```python
def _get_cisco_token(self) -> Optional[str]:
    current_time = time.time()
    if (not self.cisco_access_token or 
        not self.cisco_token_expires_at or 
        current_time >= self.cisco_token_expires_at):
        self._initialize_cisco()  # Refresh
    return self.cisco_access_token
```

**Endpoint Configuration:**

- **Base URL**: `https://chat-ai.cisco.com`
- **Deployment**: Extracted from `CISCO_ENDPOINT` or `CISCO_DEPLOYMENT`
- **API Version**: `2024-08-01-preview`
- **Format**: Azure OpenAI-compatible

**Usage:**

```python
llm = AzureChatOpenAI(
    azure_endpoint="https://chat-ai.cisco.com",
    azure_deployment="gpt-4.1",
    openai_api_key=token,  # OAuth2 token
    openai_api_version="2024-08-01-preview",
    temperature=0
)
```

#### 2. OpenAI (Embeddings & TTS)

**Embeddings:**

- **Model**: `text-embedding-3-small`
- **Dimensions**: 1536
- **Usage**: Document chunk embeddings, query embeddings

**TTS:**

- **Model**: `tts-1` or `tts-1-hd`
- **Voices**: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
- **Formats**: `mp3`, `wav`, `opus`, `aac`
- **Usage**: Podcast generation, speech generation

#### 3. AWS Bedrock (Optional)

**Configuration:**

- **Region**: Configurable (default: `us-east-1`)
- **Credentials**: AWS Access Key ID + Secret Access Key
- **Models**: Claude, Llama, Mistral, Titan, etc.

**Throttling Handling:**

```python
max_retries = 5
base_delay = 2  # seconds

for attempt in range(max_retries):
    try:
        response = llm.invoke(messages)
        break
    except ThrottlingException:
        delay = base_delay * (2 ** attempt) + (attempt * 0.5)
        time.sleep(delay)
```

### Model Selection

**Auto Mode:**

- Defaults to `cisco-gpt-4.1`
- Falls back to configured models if Cisco unavailable

**Manual Selection:**

- User can specify `model_id` in chat request
- Available models listed via `/api/models`

**Model Loading:**

- Models initialized on-demand
- Lazy loading for performance
- Token refresh handled automatically

---

## Security

### Authentication Security

**Password Hashing:**

- **Algorithm**: bcrypt
- **Salt**: Auto-generated per password
- **Rounds**: Default (10)
- **Max Length**: 72 bytes (bcrypt limit)

**JWT Security:**

- **Algorithm**: HS256
- **Secret Key**: Minimum 32 characters (configurable)
- **Expiration**: 24 hours (configurable)
- **Token Storage**: localStorage (frontend)

**Email Verification:**

- **Token**: 32-byte URL-safe random token
- **Expiration**: 24 hours
- **One-time Use**: Token cleared after verification

**Password Reset:**

- **Token**: 32-byte URL-safe random token
- **Expiration**: 1 hour
- **One-time Use**: Token cleared after reset

### Authorization Security

**Role-Based Access Control:**

- Roles enforced at API level
- Document-level permissions checked in RAG search
- Admin-only endpoints protected

**Permission Checks:**

```python
# API level
if current_user.role != UserRole.ADMIN:
    raise HTTPException(403, "Admin access required")

# Document level
has_access = (
    metadata.get("is_public", False) or
    user_role in (metadata.get("allowed_roles", "") or "").split(",") or
    metadata.get("owner_id") == current_user.id
)
```

### Data Security

**File Upload Security:**

- **File Type Validation**: Whitelist of allowed extensions
- **File Size Limit**: 100MB maximum
- **Path Traversal Prevention**: Filenames sanitized
- **Storage**: Files stored in `UPLOAD_DIR` (not web-accessible)

**SQL Injection Prevention:**

- SQLAlchemy ORM (parameterized queries)
- No raw SQL queries

**XSS Prevention:**

- React escapes content by default
- No `dangerouslySetInnerHTML` usage

**CORS Configuration:**

- Explicit origin whitelist
- Credentials allowed
- Methods and headers configured

### API Security

**Rate Limiting:**

- Not currently implemented (can be added with FastAPI middleware)

**Input Validation:**

- Pydantic models for all requests
- Email validation
- File type validation
- Size limits

**Error Handling:**

- Generic error messages (no sensitive info leaked)
- Detailed errors logged server-side only

---

## Performance & Scalability

### Database Performance

**SQLite Considerations:**

- **Pros**: Simple, no server required, good for small-medium scale
- **Cons**: Single writer, limited concurrency
- **Upgrade Path**: Can migrate to PostgreSQL

**Optimization:**

- Indexes on frequently queried columns (`email`, `user_id`, `session_id`)
- Connection pooling via SQLAlchemy
- Query optimization (eager loading, select only needed columns)

**PostgreSQL Migration:**

```python
# Change DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost/dbname

# Update requirements.txt
psycopg2-binary>=2.9.9
```

### Vector Database Performance

**ChromaDB Performance:**

- **In-Memory Index**: Fast similarity search
- **Persistence**: Disk-based storage for durability
- **Scalability**: Can handle millions of vectors

**Optimization:**

- Chunk size balanced (1000 chars)
- Limit search results (top 10-20)
- Metadata filtering before similarity search

**Scaling Considerations:**

- Can migrate to cloud vector DB (Pinecone, Weaviate, etc.)
- Embedding caching possible
- Batch processing for large uploads

### API Performance

**Async Operations:**

- FastAPI async/await for I/O operations
- Non-blocking TTS generation (`asyncio.to_thread()`)
- Concurrent request handling

**Caching:**

- Not currently implemented
- Can add Redis for:
  - Token caching
  - Model response caching
  - Document metadata caching

**Response Times:**

- **Chat Response**: 2-5 seconds (LLM dependent)
- **Document Upload**: 5-30 seconds (file size dependent)
- **RAG Search**: <1 second
- **Generation**: 10-60 seconds (content type dependent)

### Frontend Performance

**Next.js Optimizations:**

- Server Components (reduced client bundle)
- Code splitting (automatic)
- Image optimization (Next.js Image component)

**State Management:**

- Zustand (lightweight, minimal re-renders)
- Local state where appropriate

**API Calls:**

- Axios interceptors (reusable)
- Error handling centralized
- Loading states for UX

---

## Deployment

### Environment Variables

#### Backend (`.env`)

```env
# Database
DATABASE_URL=sqlite:///./intranet.db

# Cisco OpenAI (Required)
CISCO_CLIENT_ID=your_client_id
CISCO_CLIENT_SECRET=your_client_secret
CISCO_ENDPOINT=https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions
CISCO_APPKEY=your_appkey_optional

# OpenAI (Required for embeddings and TTS)
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# File Storage
UPLOAD_DIR=./uploads
VECTOR_DB_PATH=./vector_db

# Security
SECRET_KEY=your-secret-key-min-32-characters-change-in-production

# Email Configuration
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@agent.com
MAIL_FROM_NAME=AGENT
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
FRONTEND_URL=http://localhost:3000

# Presenton.ai (Optional)
PRESENTON_API_KEY=your_presenton_api_key
PRESENTON_API_URL=https://api.presenton.ai
PRESENTON_MAX_SLIDES=15

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

#### Frontend (`.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development Setup

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python init_db.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
npm install
cp .env.example .env.local
# Edit .env.local with API URL
npm run dev
```

### Production Deployment

**Backend (Uvicorn):**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Frontend (Next.js):**

```bash
npm run build
npm start
```

**With Process Manager (PM2):**

```bash
# Backend
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name agent-backend

# Frontend
pm2 start "npm start" --name agent-frontend
```

### Docker Deployment

**Backend Dockerfile:**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile:**

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

CMD ["npm", "start"]
```

**Docker Compose:**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./intranet.db
      - CISCO_CLIENT_ID=${CISCO_CLIENT_ID}
      - CISCO_CLIENT_SECRET=${CISCO_CLIENT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/vector_db:/app/vector_db
      - ./backend/intranet.db:/app/intranet.db

  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
```

### AWS EC2 Deployment

See `docs/AWS_EC2_DEPLOYMENT_GUIDE.md` for detailed instructions.

**Key Steps:**

1. Launch EC2 instance (Ubuntu 22.04)
2. Install dependencies (Python, Node.js, nginx)
3. Clone repository
4. Configure environment variables
5. Initialize database
6. Set up nginx reverse proxy
7. Configure SSL (Let's Encrypt)
8. Set up systemd services

---

## Development Guide

### Adding a New API Endpoint

1. **Create Route Handler** (`backend/app/api/new_feature.py`):

```python
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/endpoint")
async def new_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": "Hello"}
```

2. **Register Router** (`backend/main.py`):

```python
from app.api import new_feature

app.include_router(new_feature.router, prefix="/api/new-feature", tags=["New Feature"])
```

3. **Add Frontend API Call** (`src/lib/api.ts`):

```typescript
export const getNewFeature = () => api.get('/api/new-feature/endpoint')
```

### Adding a New Service

1. **Create Service File** (`backend/app/services/new_service.py`):

```python
class NewService:
    def __init__(self):
        pass
    
    def do_something(self):
        pass

new_service = NewService()
```

2. **Use in API** (`backend/app/api/some_endpoint.py`):

```python
from app.services.new_service import new_service

@router.post("/action")
async def perform_action():
    result = new_service.do_something()
    return result
```

### Adding a New Document Type

1. **Add Extraction Method** (`backend/app/services/document_processor.py`):

```python
def _extract_from_new_format(self, file_path: str) -> str:
    # Implement extraction logic
    pass
```

2. **Update `extract_text` Method**:

```python
def extract_text(self, file_path: str, file_type: str) -> str:
    # ...
    elif file_type_lower == "newformat":
        return self._extract_from_new_format(file_path)
```

3. **Update Allowed Extensions** (`backend/app/core/config.py`):

```python
ALLOWED_EXTENSIONS: List[str] = [
    # ... existing types
    "newformat"
]
```

### Adding a New Generation Type

1. **Add Generation Method** (`backend/app/services/document_generator.py`):

```python
async def generate_new_format(self, content: str, **kwargs):
    # Implement generation logic
    pass
```

2. **Update API Endpoint** (`backend/app/api/generate.py`):

```python
@router.post("/document")
async def generate_document(request: GenerateRequest):
    # ...
    elif request.content_type == "newformat":
        result = await document_generator.generate_new_format(...)
```

3. **Update Frontend** (`src/components/portal/ChatWithGeneration.tsx`):

```typescript
// Add generation button/option
```

### Testing

**Backend Tests:**

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_endpoint():
    response = client.get("/api/endpoint")
    assert response.status_code == 200
```

**Frontend Tests:**

```typescript
// __tests__/component.test.tsx
import { render, screen } from '@testing-library/react'
import { Component } from './Component'

test('renders component', () => {
  render(<Component />)
  expect(screen.getByText('Hello')).toBeInTheDocument()
})
```

### Code Style

**Backend:**

- PEP 8 style guide
- Type hints where possible
- Docstrings for functions/classes
- Black formatter (optional)

**Frontend:**

- TypeScript strict mode
- ESLint configuration
- Prettier formatting (optional)

### Debugging

**Backend Logging:**

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

**Frontend Logging:**

```typescript
console.log("Debug message")
console.error("Error message")
```

**API Debugging:**

- FastAPI auto-generated docs: `http://localhost:8000/docs`
- Request/response logging middleware
- ChromaDB telemetry suppressed (harmless warnings)

---

## Conclusion

This technical documentation provides a comprehensive overview of the AGENT platform architecture, implementation details, and development guidelines. For specific deployment instructions, see the guides in the `docs/` directory.

**Key Takeaways:**

- **RAG-Based**: System uses RAG for context-aware responses
- **Multi-Provider**: Supports Cisco GPT-4.1, OpenAI, AWS Bedrock
- **Extensible**: Easy to add new features, document types, generation types
- **Secure**: JWT authentication, role-based access, permission filtering
- **Scalable**: Can migrate to PostgreSQL, cloud vector DB, Redis caching

For questions or contributions, contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: January 2025
