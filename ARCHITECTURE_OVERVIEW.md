# AGENT — Architecture Overview

> **AI for GSSO Engineering Team** — Ask questions. Get answers. Generate content.

---

## How It Works (30-Second Version)

```
  You upload documents ──→ AGENT chunks & embeds them ──→ Stored in Vector DB
                                                              │
  You ask a question   ──→ AGENT finds relevant chunks  ◄────┘
                              │
                              ▼
                         Cisco GPT-4.1 generates a grounded answer
                              │
                              ▼
                         You get a cited, accurate response
```

---

## System Architecture

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   👤  USER                                                               ║
║   Browser (Desktop / Mobile)                                             ║
║                                                                          ║
╚════════════════════════════════╤═════════════════════════════════════════╝
                                 │
                                 │  HTTPS
                                 ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🖥️  FRONTEND — Next.js 14                                             ║
║                                                                          ║
║   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  ║
║   │  Login &     │  │  Dashboard   │  │    Chat      │                  ║
║   │  Auth Pages  │  │  & KB Mgmt   │  │  Interface   │                  ║
║   └──────────────┘  └──────────────┘  └──────────────┘                  ║
║                                                                          ║
║   React · TypeScript · Tailwind CSS · Zustand State                      ║
║                                                                          ║
╚════════════════════════════════╤═════════════════════════════════════════╝
                                 │
                                 │  REST API + JWT Token
                                 ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   ⚙️  BACKEND — FastAPI (Python)                                        ║
║                                                                          ║
║   ┌─────────────────────────────────────────────────────────────────┐    ║
║   │                    API Gateway + Auth (JWT / OAuth2)            │    ║
║   │                    Role-Based Access Control (RBAC)             │    ║
║   └─────────────────────────────────────────────────────────────────┘    ║
║                                                                          ║
║   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐      ║
║   │              │  │              │  │                          │      ║
║   │  RAG Chat    │  │  Document    │  │  Content Generation      │      ║
║   │  Service     │  │  Processor   │  │                          │      ║
║   │              │  │              │  │  • PowerPoint (Presenton)│      ║
║   │  • Query     │  │  • Upload    │  │  • Podcast   (OpenAI TTS)│      ║
║   │  • Retrieve  │  │  • Parse     │  │  • Speech    (OpenAI TTS)│      ║
║   │  • Generate  │  │  • Chunk     │  │  • Word Doc  (python-docx)│     ║
║   │  • Cite      │  │  • Embed     │  │  • PDF       (reportlab)│      ║
║   │              │  │  • Store     │  │                          │      ║
║   └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘      ║
║          │                 │                       │                     ║
║   ┌──────┴─────────────────┴───────────────────────┴─────────────┐      ║
║   │                                                               │      ║
║   │                    MCP Agent Framework                        │      ║
║   │                                                               │      ║
║   │   🎥 Demo Video Agent    📄 Doc Gen Agent    🔧 Custom Agents │      ║
║   │                                                               │      ║
║   └───────────────────────────────────────────────────────────────┘      ║
║                                                                          ║
╚═══════╤══════════════════╤══════════════════╤═══════════════════════════╝
        │                  │                  │
        ▼                  ▼                  ▼
╔═══════════════╗  ╔═══════════════╗  ╔═══════════════╗
║               ║  ║               ║  ║               ║
║  SQLite DB    ║  ║  ChromaDB     ║  ║  File Storage ║
║               ║  ║  (Vector DB)  ║  ║               ║
║  • Users      ║  ║               ║  ║  • Uploads    ║
║  • Documents  ║  ║  • Embeddings ║  ║  • Generated  ║
║  • KB config  ║  ║  • Chunks     ║  ║    files      ║
║  • Chat logs  ║  ║  • Metadata   ║  ║  • Audio      ║
║               ║  ║               ║  ║               ║
╚═══════════════╝  ╚═══════════════╝  ╚═══════════════╝

        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
              External AI Services
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│               │  │               │  │               │
│  Cisco        │  │  OpenAI       │  │  Presenton.ai │
│  GPT-4.1      │  │               │  │               │
│               │  │  • Embeddings │  │  • PowerPoint │
│  Chat LLM     │  │    (3-small)  │  │    generation │
│  (OAuth2)     │  │  • TTS        │  │               │
│               │  │  • Whisper    │  │               │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## Flow 1 — Asking a Question (RAG)

> This is the core flow. Everything else builds on top of it.

```
 ┌─────────┐
 │  USER   │  "What are the key features of Encrypted Visibility Engine?"
 └────┬────┘
      │
      ▼
 ┌─────────────────────────────────────────────────────┐
 │  1. EMBED THE QUESTION                              │
 │                                                     │
 │  Your question → OpenAI text-embedding-3-small      │
 │  Result: a 1,536-dimension vector                   │
 └────────────────────────┬────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  2. SEARCH THE VECTOR DATABASE                      │
 │                                                     │
 │  ChromaDB finds the most similar document chunks    │
 │  Ranked by cosine similarity                        │
 │  Returns top-k chunks + source metadata             │
 └────────────────────────┬────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  3. BUILD THE PROMPT                                │
 │                                                     │
 │  System prompt                                      │
 │  + Retrieved document chunks (with sources)         │
 │  + Conversation history (follow-up context)         │
 │  + User's question                                  │
 └────────────────────────┬────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  4. GENERATE ANSWER                                 │
 │                                                     │
 │  Cisco GPT-4.1 produces a grounded response         │
 │  Cites specific documents as sources                │
 │  No hallucination — answers only from your docs     │
 └────────────────────────┬────────────────────────────┘
                          │
                          ▼
 ┌─────────┐
 │  USER   │  Gets an accurate, cited answer + sources
 └─────────┘
```

**Technical Details:**
- Chunk size: 1,000 chars with 200-char overlap
- Embedding model: OpenAI `text-embedding-3-small` (1,536 dimensions)
- LLM: Cisco GPT-4.1 via OAuth2
- Conversation history maintained per session

---

## Flow 2 — Uploading a Document

> How your documents become searchable knowledge.

```
 ┌─────────┐
 │  ADMIN  │  Drags & drops a file (PDF, DOCX, PPTX, MP4, MP3, etc.)
 └────┬────┘
      │
      ▼
 ┌──────────────────────────────────────────┐
 │  1. UPLOAD & STORE                       │
 │                                          │
 │  File saved to /uploads directory        │
 │  Metadata recorded in SQLite             │
 │  Assigned to a Knowledge Base            │
 └──────────────────┬───────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────┐
 │  2. PARSE & EXTRACT TEXT                 │
 │                                          │
 │  PDF  → PyPDF2                           │
 │  DOCX → python-docx                     │
 │  PPTX → python-pptx                     │
 │  XLSX → openpyxl                         │
 │  MP4/MOV/AVI → moviepy → Whisper 🎙️     │
 │  MP3/WAV/M4A → Whisper 🎙️               │
 │  TXT/MD/CSV/JSON → direct read          │
 └──────────────────┬───────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────┐
 │  3. CHUNK THE TEXT                       │
 │                                          │
 │  Split into ~1,000-char segments         │
 │  200-char overlap between chunks         │
 │  (LangChain RecursiveCharacterSplitter)  │
 └──────────────────┬───────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────┐
 │  4. EMBED & STORE IN VECTOR DB          │
 │                                          │
 │  Each chunk → OpenAI embedding           │
 │  Stored in ChromaDB with metadata:       │
 │    • document_id                         │
 │    • filename                            │
 │    • knowledge_base_id                   │
 │    • allowed_roles                       │
 └──────────────────┬───────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────┐
 │  ✅  DOCUMENT IS NOW SEARCHABLE          │
 │                                          │
 │  Any user can ask questions about it     │
 │  (subject to role-based access)          │
 └──────────────────────────────────────────┘
```

**Supported File Types (16+):**
`PDF` · `DOCX` · `PPTX` · `XLSX` · `MP4` · `MOV` · `AVI` · `MP3` · `WAV` · `M4A` · `TXT` · `MD` · `CSV` · `JSON` · `JSONL`

---

## Flow 3 — Generating Content

> Turn knowledge into deliverables — presentations, podcasts, documents.

```
 ┌─────────┐
 │  USER   │  "Create a presentation about Cisco Secure Firewall"
 └────┬────┘
      │
      ▼
 ┌──────────────────────────────────────────────────┐
 │  1. INTENT DETECTION                             │
 │                                                  │
 │  Chat API detects generation keywords:           │
 │  "create presentation" → PPT agent               │
 │  "create podcast"      → Podcast agent            │
 │  "generate document"   → Doc agent                │
 │  "find demo video"     → Demo Video agent         │
 └──────────────────┬───────────────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────────────┐
 │  2. RAG CONTEXT RETRIEVAL                        │
 │                                                  │
 │  Same vector search as chat — pulls relevant     │
 │  document chunks to ground the content           │
 └──────────────────┬───────────────────────────────┘
                    │
                    ├──────────────────────┬──────────────────────┐
                    ▼                      ▼                      ▼
 ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
 │  📊 POWERPOINT       │  │  🎙️ PODCAST / SPEECH │  │  📄 WORD / PDF       │
 │                      │  │                      │  │                      │
 │  LLM structures      │  │  LLM writes script   │  │  LLM formats         │
 │  slide content        │  │  with conversational │  │  content into        │
 │       │               │  │  tone                │  │  document structure   │
 │       ▼               │  │       │              │  │       │              │
 │  Presenton.ai API     │  │       ▼              │  │       ▼              │
 │  generates .pptx      │  │  OpenAI TTS          │  │  python-docx /       │
 │                      │  │  generates audio      │  │  reportlab           │
 │       │               │  │  (.mp3 / .wav)       │  │  generates file      │
 │       ▼               │  │       │              │  │       │              │
 │  Download ready       │  │       ▼              │  │       ▼              │
 │                      │  │  Download ready       │  │  Download ready      │
 └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## Flow 4 — Demo Video Search

> Instantly find the right demo video from your library.

```
 ┌─────────┐
 │  USER   │  "Find demo videos about SnortML"
 └────┬────┘
      │
      ▼
 ┌──────────────────────────────────────────────────────────┐
 │  MCP DEMO VIDEO AGENT                                    │
 │                                                          │
 │  Multi-layer matching (priority order):                  │
 │                                                          │
 │  ① Product Name Match   "SnortML" in title?        ✅    │
 │  ② Tag Match            "SnortML" in TAGS line?     ✅    │
 │  ③ Filename Match       "snortml" in filename?      ✅    │
 │  ④ Title Match          "SnortML" in metadata?      ✅    │
 │                                                          │
 │  Returns:                                                │
 │  • Video title & description                             │
 │  • YouTube link (https://youtube.com/watch?v=...)        │
 │  • Relevance ranking                                     │
 └──────────────────────────────────────────────────────────┘
```

---

## Security & Access Control

```
╔════════════════════════════════════════════════════════════╗
║                    SECURITY LAYERS                         ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║   🔒 TRANSPORT        HTTPS / TLS encryption               ║
║                                                            ║
║   🔑 AUTHENTICATION   JWT tokens (24hr expiry)             ║
║                       OAuth2 for Cisco GPT-4.1             ║
║                       bcrypt password hashing              ║
║                                                            ║
║   👥 AUTHORIZATION     5 roles with scoped access:         ║
║                                                            ║
║       ┌─────────┬────────┬──────────┬───────┬─────────┐   ║
║       │  Admin  │Employee│ Engineer │  HR   │ Manager │   ║
║       ├─────────┼────────┼──────────┼───────┼─────────┤   ║
║       │ Upload  │  Chat  │   Chat   │ Chat  │  Chat   │   ║
║       │ Manage  │  View  │   View   │ View  │  View   │   ║
║       │ Chat    │        │          │       │         │   ║
║       │ All KB  │ Public │ Eng docs │ HR    │ Mgmt    │   ║
║       └─────────┴────────┴──────────┴───────┴─────────┘   ║
║                                                            ║
║   📁 DATA              Documents role-restricted           ║
║                        KB namespace isolation              ║
║                        All data on Cisco infrastructure    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## Tech Stack Summary

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND                                                    │
│  Next.js 14 · React 18 · TypeScript · Tailwind · Zustand    │
├─────────────────────────────────────────────────────────────┤
│  BACKEND                                                     │
│  FastAPI · Python 3.12 · SQLAlchemy · LangChain · Pydantic  │
├─────────────────────────────────────────────────────────────┤
│  DATABASES                                                   │
│  SQLite (relational)  ·  ChromaDB (vector embeddings)       │
├─────────────────────────────────────────────────────────────┤
│  AI SERVICES                                                 │
│  Cisco GPT-4.1 (chat) · OpenAI Embeddings · OpenAI TTS     │
│  OpenAI Whisper (transcription) · Presenton.ai (slides)     │
├─────────────────────────────────────────────────────────────┤
│  DOCUMENT PROCESSING                                         │
│  PyPDF2 · python-docx · python-pptx · openpyxl             │
│  moviepy · pydub · openai-whisper                            │
├─────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                              │
│  AWS EC2 (t3.large) · Nginx · Ubuntu 22.04 · SSL/TLS       │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment

```
┌────────────────────────────────────────────────────────┐
│                   AWS EC2 Instance                      │
│                   (t3.large · Ubuntu 22.04)             │
│                                                        │
│   ┌────────────────────────────────────────────────┐   │
│   │  Nginx (Reverse Proxy · SSL · Port 80/443)    │   │
│   └─────────────┬──────────────────┬───────────────┘   │
│                 │                  │                    │
│                 ▼                  ▼                    │
│   ┌──────────────────┐  ┌──────────────────┐          │
│   │  Next.js          │  │  FastAPI          │          │
│   │  Port 3000        │  │  Port 8000        │          │
│   │  (Frontend)       │  │  (Backend)        │          │
│   └──────────────────┘  └────────┬───────────┘          │
│                                  │                      │
│                    ┌─────────────┼─────────────┐        │
│                    ▼             ▼             ▼        │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│              │ SQLite   │ │ ChromaDB │ │ /uploads │    │
│              │ (.db)    │ │ (vectors)│ │ (files)  │    │
│              └──────────┘ └──────────┘ └──────────┘    │
│                                                        │
└────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
   Cisco GPT-4.1    OpenAI API    Presenton.ai
```

---

*AGENT Platform · v1.0 · Branch: vscode-optimized-v1 · February 2026*
