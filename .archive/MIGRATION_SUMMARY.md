# Windows to Ubuntu Migration Summary

## ✅ What Was Done

### 1. System Setup
- ✅ Updated all system packages
- ✅ Installed Python 3.12.3 (upgraded from 3.10 requirement)
- ✅ Installed Node.js v18.20.8
- ✅ Installed system dependencies: FFmpeg, build tools, image libraries, PostgreSQL client, etc.

### 2. Backend Setup
- ✅ Created Python virtual environment at `/home/ubuntu/AGENT/backend/venv`
- ✅ Installed **129 Python packages** including:
  - FastAPI, Uvicorn, SQLAlchemy, Pydantic
  - LangChain (langchain, langchain-core, langchain-openai, langchain-community, langchain-aws)
  - OpenAI SDK
  - Document processing: pypdf2, python-docx, python-pptx, openpyxl, reportlab, pillow
  - Audio: pydub, moviepy, gtts, imageio-ffmpeg
  - AWS: boto3
  - Email: fastapi-mail
  - Security: python-jose, passlib, bcrypt

- ✅ **Fixed LangChain import issues** (updated for new package structure):
  - Changed `langchain.text_splitter` → `langchain_text_splitters`
  - Changed `langchain.prompts` → `langchain_core.prompts`
  - Changed `langchain.schema` → `langchain_core.messages` and `langchain_core.documents`

- ✅ Environment configuration verified
- ✅ Database exists and is intact (19MB SQLite DB)

### 3. Code Updates
- ✅ Fixed LangChain imports in:
  - `/home/ubuntu/AGENT/backend/app/services/rag_service.py`
  - `/home/ubuntu/AGENT/backend/app/services/speech_service.py`
  - `/home/ubuntu/AGENT/backend/app/services/podcast_service.py`
- ✅ Removed Windows batch files

### 4. PyTorch Optimization
- ✅ Installed **PyTorch CPU-only** version (184MB instead of 900MB+CUDA)
  - This is appropriate for AWS instances without GPU
  - Saves significant disk space

## ❌ What's Missing (Due to Disk Space)

**Critical Issue**: Root disk is only 6.8GB and is 100% full.

### Packages Not Installed:
1. **ChromaDB 0.4.18** - Vector database (needs ~100MB+)
   - Required for: RAG, semantic search, document embeddings
   
2. **sentence-transformers 2.2.2** - Embedding model (needs ~300MB+)
   - Required for: Document embeddings, similarity search
   - Dependencies: scikit-learn, scipy, numba, llvmlite, triton
   
3. **openai-whisper** - Audio transcription (needs ~50MB+)
   - Required for: Audio/video transcription features
   
4. **Frontend node_modules** - (needs ~400MB)
   - Required for: Running Next.js frontend

## 🚨 IMMEDIATE ACTION REQUIRED

### You MUST expand the root disk to 20GB minimum

**Option 1: Expand Root Volume (AWS EC2)**
```bash
# 1. In AWS Console:
#    EC2 > Volumes > Select root volume > Actions > Modify Volume > 20GB
# 2. After modification, SSH into instance:

sudo growpart /dev/nvme0n1 1
sudo resize2fs /dev/nvme0n1p1
df -h /  # Verify new size
```

**Option 2: Add EBS Volume**
```bash
# Attach new 20GB EBS volume as /dev/xvdf, then:
sudo mkfs.ext4 /dev/xvdf
sudo mkdir /mnt/agent-data
sudo mount /dev/xvdf /mnt/agent-data
sudo mv /home/ubuntu/AGENT/backend/venv /mnt/agent-data/
ln -s /mnt/agent-data/venv /home/ubuntu/AGENT/backend/venv
```

## 📝 Next Steps After Disk Expansion

### 1. Install Missing Python Packages
```bash
cd /home/ubuntu/AGENT/backend
source venv/bin/activate

# Install ChromaDB (matching version in requirements.txt)
pip install --no-cache-dir chromadb==0.4.18

# Install sentence-transformers (for embeddings)
pip install --no-cache-dir sentence-transformers==2.2.2

# Install openai-whisper
pip install --no-cache-dir openai-whisper

# Verify all packages
pip install -r requirements.txt
pip list | wc -l  # Should show 150+ packages
```

### 2. Install Frontend Dependencies
```bash
cd /home/ubuntu/AGENT
npm cache clean --force
npm install
```

### 3. Start Services

**Terminal 1 - Backend:**
```bash
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /home/ubuntu/AGENT
npm run dev
```

### 4. Test the Application
Open browser: `http://<your-server-ip>:3000`

Test:
- ✅ Login/Signup
- ✅ Document upload
- ✅ Chat with RAG
- ✅ Knowledge base management
- ✅ Document generation

## 📊 Current Disk Usage

```
Total: 6.8GB
Used: 6.7GB (100%)
Available: 0

Breakdown:
- Backend (venv + app): 1.8GB
- System packages: ~4.5GB
- Uploads: 14MB
- Vector DB: 78MB
- Database: 19MB
- Frontend (partial): 277MB
```

## 🔧 Technical Notes

### Import Changes Made:
```python
# OLD (doesn't work with langchain 1.x):
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.schema import Document, HumanMessage

# NEW (fixed):
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
```

### Package Versions:
- Python: 3.12.3 (was 3.10 on Windows)
- Node.js: v18.20.8
- FastAPI: 0.128.0
- LangChain: 1.2.1
- OpenAI: 2.14.0
- PyTorch: 2.9.1+cpu (CPU-only)

### Environment Files:
- Backend: `/home/ubuntu/AGENT/backend/.env` ✅ (configured)
- Frontend: `/home/ubuntu/AGENT/.env.local` ✅ (configured with API URL)

## 🎯 What Works Now (Without ChromaDB)

With current setup, these features work:
- ✅ Backend API server
- ✅ User authentication
- ✅ Database operations
- ✅ Document generation (PowerPoint, Word, PDF)
- ✅ Basic chat (OpenAI/Cisco GPT)
- ✅ Email service
- ✅ AWS integration

These features need ChromaDB & embeddings:
- ❌ RAG (document context in chat)
- ❌ Semantic search
- ❌ Knowledge base document search
- ❌ Demo video search
- ❌ Document embeddings

## 📞 Troubleshooting

### If Backend Won't Start:
```bash
cd /home/ubuntu/AGENT/backend
source venv/bin/activate
python main.py  # Check error messages
```

### If Import Errors:
```bash
pip list | grep langchain
# Should show: langchain, langchain-core, langchain-openai, langchain-community, langchain-aws, langchain-text-splitters
```

### If Disk Full:
```bash
# Clean caches
pip cache purge
npm cache clean --force
sudo apt clean
sudo journalctl --vacuum-time=1d

# Check usage
df -h /
du -sh /home/ubuntu/AGENT/*
```

## 📄 Documentation

See these files for detailed information:
- `UBUNTU_SETUP_STATUS.md` - Detailed status and requirements
- `README.md` - General project documentation
- `INSTALL.md` - Installation instructions
- `docs/` - Additional documentation

## ✨ Migration Complete (Pending Disk Expansion)

Your AGENT project has been successfully migrated to Ubuntu with most dependencies installed. The code has been updated for compatibility, and the environment is configured. 

**Status**: Ready for disk expansion and final package installation

---
**Date**: January 7, 2026  
**Migrated From**: Windows  
**Target Environment**: Ubuntu 24.04 LTS on AWS EC2  
**Python**: 3.10 → 3.12.3  
**Node.js**: v18.20.8

