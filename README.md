# AI for GSSO Engineering Team (AGENT)

An enterprise-grade AI-powered platform that enables employees to interact with business knowledge through natural language queries, powered by RAG (Retrieval Augmented Generation) and integrated with document generation capabilities.

## 🚀 Features

### Core Features
- **🤖 AI-Powered Chat**: Interactive chat interface powered by GPT-4.1 (Cisco) with RAG capabilities
- **📚 Knowledge Base Management**: Organize documents into knowledge bases with full CRUD operations
- **📄 Document Processing**: Upload and process various file types (PDF, DOC, PPT, XLS, MP4, MOV, MP3, WAV)
- **🔍 Intelligent Search**: Semantic search across uploaded documents using ChromaDB vector database
- **🎥 Demo Video Search**: Intelligent search for existing demo videos with precise matching and suggestions
- **📊 PowerPoint Generation**: Generate professional PowerPoint presentations using Presenton.ai API
- **🎙️ Audio Generation**: Generate podcasts and speeches from content using OpenAI TTS (non-blocking)
- **📝 Document Generation**: Generate Word documents and PDFs from chat content
- **🔐 Role-Based Access Control**: Admin and employee roles with permission-based document access
- **📧 Email Verification**: New users must verify their email before logging in
- **🔑 Password Reset**: Secure password reset via email link
- **💬 Chat History**: Persistent chat sessions with conversation history

### User Interface
- **Modern Dark Theme**: Beautiful cyan-blue gradient UI with custom scrollbars
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Real-time Updates**: Live connection status and document processing updates
- **Drag & Drop Upload**: Easy document upload with progress tracking

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Icons**: Lucide React

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (can be upgraded to PostgreSQL)
- **Vector Database**: ChromaDB
- **RAG Framework**: LangChain
- **AI Models**:
  - **Chat**: GPT-4.1 (Cisco) via OAuth2
  - **Embeddings**: OpenAI text-embedding-3-small
  - **TTS**: OpenAI TTS API
- **Document Processing**: PyPDF2, python-docx, python-pptx, openpyxl
- **External Services**: Presenton.ai (PowerPoint generation)

## 📋 Prerequisites

- **Node.js**: 18.x or higher
- **Python**: 3.10 or higher
- **pip**: Python package manager
- **API Keys**:
  - Cisco OpenAI credentials (CLIENT_ID, CLIENT_SECRET)
  - OpenAI API key (for embeddings and TTS)
  - Presenton.ai API key (optional, for PowerPoint generation)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd hrsp_ai_hub
```

### 2. Frontend Setup

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

Edit `backend/.env`:
```env
# Database
DATABASE_URL=sqlite:///./intranet.db

# Cisco OpenAI (Required for chat)
CISCO_CLIENT_ID=your_cisco_client_id
CISCO_CLIENT_SECRET=your_cisco_client_secret
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

# Email Configuration (for verification and password reset)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@hrsp-ai-hub.com
MAIL_FROM_NAME=HRSP AI Hub
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
FRONTEND_URL=http://localhost:3000

# Presenton.ai (Optional, for PowerPoint generation)
PRESENTON_API_KEY=your_presenton_api_key
PRESENTON_API_URL=https://api.presenton.ai
PRESENTON_MAX_SLIDES=15

# CORS (Add your frontend URLs)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://172.31.19.92:3000,http://172.31.19.92:3001
```

### 4. Initialize Database

```bash
cd backend
python init_db.py
```

This will create the database tables and set up the initial schema.

**Note**: If you have an existing database, run the migration script to add email verification fields:
```bash
python migrate_add_email_verification.py
```

### 5. Create Admin User (Optional)

```bash
cd backend
python create_admin.py
```

Or register through the UI - the first user can be manually promoted to admin.

## 🚀 Running the Application

### Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### Production Mode

**Backend:**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
npm run build
npm start
```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 Project Structure

```
hrsp_ai_hub/
├── src/                          # Next.js frontend
│   ├── app/                      # App router pages
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Login page
│   │   └── globals.css          # Global styles
│   ├── components/               # React components
│   │   ├── auth/                # Authentication components
│   │   │   └── LoginForm.tsx    # Login/signup form
│   │   └── portal/              # Main portal components
│   │       ├── MainPortal.tsx   # Main layout with sidebar
│   │       ├── ChatWithGeneration.tsx  # Chat interface
│   │       └── DocumentUpload.tsx     # Document management
│   ├── lib/                     # Utilities
│   │   └── api.ts               # Axios API client
│   └── stores/                  # Zustand stores
│       └── authStore.ts         # Authentication state
├── backend/                      # Python FastAPI backend
│   ├── app/
│   │   ├── api/                 # API routes
│   │   │   ├── auth.py         # Authentication endpoints
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   ├── documents.py    # Document endpoints
│   │   │   ├── upload.py       # File upload endpoints
│   │   │   ├── generate.py     # Document generation endpoints
│   │   │   ├── models.py       # Model management endpoints
│   │   │   └── knowledge_bases.py  # Knowledge base CRUD
│   │   ├── core/               # Core functionality
│   │   │   ├── config.py       # Configuration settings
│   │   │   ├── database.py     # Database connection
│   │   │   ├── dependencies.py # FastAPI dependencies
│   │   │   └── security.py     # JWT and password hashing
│   │   ├── models/             # SQLAlchemy models
│   │   │   ├── user.py         # User model
│   │   │   ├── document.py     # Document model
│   │   │   ├── chat.py         # Chat session/message models
│   │   │   └── knowledge_base.py  # Knowledge base model
│   │   └── services/           # Business logic
│   │       ├── rag_service.py  # RAG implementation
│   │       ├── model_manager.py # AI model management
│   │       ├── document_processor.py  # Document processing
│   │       ├── document_generator.py  # Document generation
│   │       ├── presenton_service.py  # Presenton.ai integration
│   │       ├── tts_service.py  # Text-to-speech service
│   │       ├── demo_video_service.py  # Demo video search service
│   │       └── mcp_service.py  # MCP agent service
│   ├── main.py                 # FastAPI application entry
│   ├── init_db.py              # Database initialization
│   ├── requirements.txt        # Python dependencies
│   └── uploads/                # Uploaded files storage
│   └── vector_db/              # ChromaDB vector database
├── public/                      # Static assets
│   ├── gsse_logo.png          # GSSE logo
│   └── demo-videos/           # Demo video documents
├── docs/                        # Documentation
│   ├── AWS_EC2_DEPLOYMENT_GUIDE.md  # AWS deployment guide
│   ├── REMOTE_DEVELOPMENT_SETUP.md  # Remote development guide
│   ├── DEPLOYMENT_PLAN.md     # Deployment architecture plan
│   └── DEMO_VIDEO_DOCUMENT_FORMAT_GUIDE.md  # Demo video format guide
├── package.json                # Node.js dependencies
├── tailwind.config.js          # Tailwind configuration
└── README.md                   # This file
```

## 🔑 Key Features Explained

### RAG (Retrieval Augmented Generation)
The platform uses RAG to provide context-aware responses:
1. **Document Upload**: Documents are processed and chunked
2. **Embedding**: Text chunks are converted to vectors using OpenAI embeddings
3. **Storage**: Vectors are stored in ChromaDB for semantic search
4. **Retrieval**: Relevant chunks are retrieved based on query similarity
5. **Generation**: LLM generates responses using retrieved context

### Knowledge Base Management
- **Organize Documents**: Group documents into knowledge bases
- **CRUD Operations**: Create, rename, and delete knowledge bases (admin only)
- **Tagging**: Documents are tagged with knowledge base names
- **Filtering**: View documents by knowledge base

### PowerPoint Generation
- **Presenton.ai Integration**: Generates professional PowerPoint presentations
- **Custom Template**: Uses custom template and theme
- **Content Preview**: Shows content before generation
- **Confirmation Flow**: User confirms before generating
- **Download**: Direct download from Presenton.ai

### Chat Features
- **Session Management**: Persistent chat sessions
- **History**: View and resume previous conversations
- **Delete Chats**: Remove unwanted chat sessions
- **Connection Status**: Real-time connection indicator
- **Agent Detection**: Automatic detection of user intent (PPT, document, video, podcast, speech generation)

### Demo Video Search
- **Intelligent Matching**: Precise matching based on product names, tags, and filenames
- **RAG Integration**: Semantic search across demo video documents
- **Suggestion System**: Provides relevant video suggestions when exact match not found
- **YouTube Integration**: Direct links to demo videos from knowledge base
- **Acronym Support**: Handles product acronyms (EVE, AIOps, RTC, etc.)

### Audio Generation
- **Non-Blocking**: Podcast and speech generation runs asynchronously without freezing UI
- **Dialogue Support**: Multi-voice podcast generation with Host/Guest roles
- **OpenAI TTS**: High-quality text-to-speech with multiple voice options
- **Format Support**: MP3 and WAV audio formats

## 🔐 Authentication & Authorization

### User Roles
- **Admin**: Full access including document upload/management
- **Employee**: Chat access, cannot upload documents

### Authentication Flow
1. User registers → Verification email sent
2. User verifies email → Account activated
3. User logs in → JWT token is issued
4. Token is stored in localStorage
5. Token is sent with each API request
6. Backend validates token and user permissions

### Email Verification
- **Registration**: New users receive verification email
- **Verification Required**: Users cannot login until email is verified
- **Token Expiry**: Verification links expire after 24 hours
- **Resend**: Users can request new verification email

### Password Reset
- **Request Reset**: User requests password reset via email
- **Reset Link**: Secure token sent via email (expires in 1 hour)
- **Password Update**: User sets new password via reset link
- **Security**: Requires verified email before reset

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user (sends verification email)
- `POST /api/auth/login` - Login user (requires verified email)
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/verify-email` - Verify email address with token
- `POST /api/auth/resend-verification` - Resend verification email
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password with token

### Chat
- `POST /api/chat/message` - Send chat message
- `GET /api/chat/sessions` - List chat sessions
- `GET /api/chat/sessions/{id}/messages` - Get session messages
- `DELETE /api/chat/sessions/{id}` - Delete session

### Documents
- `GET /api/documents` - List documents
- `POST /api/upload/file` - Upload document (admin only)
- `DELETE /api/documents/{id}` - Delete document

### Knowledge Bases
- `GET /api/knowledge-bases` - List knowledge bases
- `POST /api/knowledge-bases` - Create knowledge base (admin only)
- `PUT /api/knowledge-bases/{id}` - Update knowledge base (admin only)
- `DELETE /api/knowledge-bases/{id}` - Delete knowledge base (admin only)

### Generation
- `POST /api/generate/document` - Generate document (PPT, DOC, PDF, MP3, WAV, Speech, Podcast)
- `POST /api/generate/confirm-ppt` - Confirm and generate PowerPoint

### Demo Videos
- Demo video search is integrated into chat endpoint
- Automatically searches for relevant demo videos when user requests video content
- Returns YouTube links with precise matching and suggestions

### Models
- `GET /api/models/` - List available AI models

## 🎨 UI/UX Features

### Design
- **Color Scheme**: Dark theme with cyan-blue gradients (#07182D background)
- **Typography**: Clean, modern fonts
- **Icons**: Lucide React icon library
- **Animations**: Smooth transitions and hover effects

### Components
- **Sidebar**: Collapsible sidebar with navigation
- **Chat Interface**: Message bubbles with user/assistant distinction
- **Document Manager**: Tile-based knowledge base view
- **Upload Area**: Drag-and-drop file upload

## 🐛 Troubleshooting

### Common Issues

**ChromaDB Telemetry Errors**
- These are harmless warnings and are suppressed in the code
- RAG functionality is not affected

**Connection Status Shows Disconnected**
- Check if backend is running
- Verify API URL in frontend `.env.local`
- Check CORS settings in backend

**Document Upload Fails**
- Verify user has admin role
- Check file size (max 100MB)
- Ensure file type is allowed
- Check backend logs for errors

**PowerPoint Generation Fails**
- Verify Presenton.ai API key is set
- Check API URL configuration
- Review backend logs for API errors

**Demo Video Not Found**
- Ensure demo video documents are uploaded to knowledge base
- Check document format matches guide in `docs/DEMO_VIDEO_DOCUMENT_FORMAT_GUIDE.md`
- Verify tags and product names are correctly formatted in documents

**Audio Generation Freezes UI**
- This has been fixed - audio generation now runs asynchronously
- If still experiencing issues, check backend logs for errors
- Ensure OpenAI TTS API key is valid

## 🔒 Security Considerations

- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: Bcrypt password hashing
- **CORS**: Configured CORS origins
- **File Validation**: File type and size validation
- **Role-Based Access**: Permission checks on all endpoints

## 📝 Environment Variables Reference

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```env
# Required
CISCO_CLIENT_ID=your_client_id
CISCO_CLIENT_SECRET=your_client_secret
OPENAI_API_KEY=your_openai_key
SECRET_KEY=your_secret_key_min_32_chars

# Optional
PRESENTON_API_KEY=your_presenton_key
PRESENTON_API_URL=https://api.presenton.ai
PRESENTON_MAX_SLIDES=15
```

## 📚 Documentation

Additional documentation is available in the `docs/` folder:

- **AWS_EC2_DEPLOYMENT_GUIDE.md**: Step-by-step guide for deploying to AWS EC2
- **REMOTE_DEVELOPMENT_SETUP.md**: Guide for editing code remotely using VS Code/Cursor
- **DEPLOYMENT_PLAN.md**: Detailed deployment and scalability architecture plan
- **DEMO_VIDEO_DOCUMENT_FORMAT_GUIDE.md**: Format guide for creating demo video documents
- **EMAIL_VERIFICATION_SETUP.md**: Guide for configuring email verification and password reset
- **USER_CREDENTIALS_STORAGE.md**: Guide on where and how user credentials are stored

## 🚧 Development

### Code Style
- **Frontend**: TypeScript with ESLint
- **Backend**: Python with PEP 8 style guide
- **Formatting**: Use your IDE's formatter

### Adding New Features
1. Backend: Add API endpoints in `app/api/`
2. Frontend: Add components in `src/components/`
3. Update API client in `src/lib/api.ts`
4. Test thoroughly before committing

### Performance Optimizations
- **Async Operations**: All long-running operations (LLM calls, TTS) run in thread pools to prevent UI blocking
- **Non-Blocking**: Podcast and speech generation use `asyncio.to_thread()` for async execution
- **Efficient Search**: Demo video search uses RAG with precise matching for accurate results

## 📄 License

Proprietary - Enterprise License

## 👥 Support

For issues, questions, or contributions, please contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: January 2025

## 📋 Recent Updates

- ✅ Email verification system - users must verify email before login
- ✅ Password reset functionality - secure password reset via email
- ✅ Demo video search with precise matching and suggestions
- ✅ Non-blocking audio generation (podcast and speech)
- ✅ Enhanced RAG with metadata tags support
- ✅ Improved query cleaning for better video search accuracy
- ✅ Documentation organized in `docs/` folder
- ✅ AWS EC2 deployment guide added
- ✅ Remote development setup guide added
