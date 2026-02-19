# AGENT — Architecture Overview

> **AI for GSSO Engineering Team** — Ask questions. Get answers. Generate content.

> 🗣️ **How to use this doc:** Each section has a "Say This" block — your verbal script — followed by the diagram. Walk through top-to-bottom. You don't need to read every label; just follow the arrows and narrate.

---

## How It Works (30-Second Version)

> 🗣️ **Say This:**
> "Before I get into the details, here's the whole platform in one sentence: You upload your documents — PDFs, PowerPoints, MP4s, anything — AGENT processes them and makes them searchable using AI. Then when you ask a question in plain English, it finds the relevant pieces of your content and uses Cisco's GPT-4.1 to write you a grounded, cited answer. That's it. No keyword search, no manual lookup — just ask and get answers."

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

> 🗣️ **Say This:**
> "Let's look at the full picture. There are four horizontal layers here — read it top to bottom. At the top is the user's browser talking to the frontend. The frontend talks to a FastAPI backend over a secure REST API with JWT authentication. The backend holds three core services: the RAG chat engine, the document processor, and the content generation service. Below that are three data stores — SQLite for relational data like users and document metadata, ChromaDB for the vector embeddings that make search work, and a file store for the actual uploaded and generated files. And at the bottom, three external AI services: Cisco GPT-4.1 for the chat brain, OpenAI for embeddings and audio, and Presenton.ai for PowerPoint generation."

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

> 🗣️ **Say This:**
> "This is the heart of the platform — everything else is built on top of this. When you type a question, four things happen in sequence. First, your question gets turned into a mathematical vector — a 1,536-number fingerprint of its meaning — using OpenAI's embedding model. Second, ChromaDB does a similarity search against every chunk of every document we've ingested, and returns the most relevant passages. Third, we package those passages together with your conversation history into a single prompt. Fourth, that prompt goes to Cisco GPT-4.1, which writes a response grounded entirely in your documents. No hallucination — if the answer isn't in your docs, it says so."

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

> 🗣️ **Anticipated question:** *"Why not just use ChatGPT?"*
> "ChatGPT doesn't have access to your internal documents. It will hallucinate or give generic answers. AGENT only answers from your uploaded content — every response is traceable back to a specific document. That's the key difference."

---

## Flow 2 — Uploading a Document

> 🗣️ **Say This:**
> "This is the ingestion pipeline — how raw files become searchable AI knowledge. An admin drags and drops a file. It could be a PDF product sheet, a PPTX slide deck, or even an MP4 demo video. The system saves the file, then extracts the text — and here's the cool part: for video and audio files, we use OpenAI Whisper to automatically transcribe the audio track. Then we split the full text into overlapping chunks of about a thousand characters — that overlap is important so we don't cut a sentence in half at a chunk boundary. Each chunk gets embedded into a vector and stored in ChromaDB. From that point on, that content is live and searchable via the chat interface."

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

> 🗣️ **Pause point:** "Notice the video and audio types — MP4, MOV, MP3, WAV. Most platforms can't handle these. Upload a 20-minute demo recording and AGENT will transcribe it and make every word searchable. That's huge for teams that produce a lot of video enablement content."

---

## Flow 3 — Generating Content

> 🗣️ **Say This:**
> "AGENT doesn't just answer questions — it produces deliverables. Typing something like 'create a presentation about Cisco Secure Firewall' triggers the intent detection layer, which recognizes you want a PowerPoint, not just a text answer. It then does the same RAG retrieval to pull your relevant content, sends it to Cisco GPT-4.1 to structure the content, and then hands off to an external service depending on the output format. For PowerPoint, it calls Presenton.ai — a professional slide generation API — and returns a ready-to-download .pptx file. For podcasts or speeches, it calls OpenAI TTS and returns an MP3. For Word or PDF documents, it generates those locally. One question, one complete deliverable — in under 60 seconds."

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

> 🗣️ **Say This:**
> "The last specialized flow is demo video search. GSSO has a large library of product demo videos and finding the right one is painful. Ask AGENT 'find demo videos for SnortML' and it uses the MCP Demo Video Agent, which applies four layers of matching in priority order — product name, tags, filename, and title metadata — to find the most precise match. It returns the video name, a description, and the direct YouTube link. No more digging through SharePoint or email threads to find a demo."

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

> 🗣️ **Say This:**
> "Security is layered. Transport is HTTPS only. Authentication uses JWT tokens with a 24-hour expiry, and our connection to Cisco GPT-4.1 uses OAuth2 — not API keys — so it goes through Cisco's approved token exchange. Passwords are bcrypt hashed — never stored plain. Authorization is role-based: we have five roles. Admin is the only role that can upload and manage documents. Everyone else is a consumer. And importantly, documents can be scoped to specific roles — engineering docs don't appear for HR users, and vice versa. Everything runs on Cisco-controlled infrastructure — no data leaves your environment except the API calls to Cisco GPT-4.1 and OpenAI for embeddings."

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

> 🗣️ **Say This:**
> "Quick stack overview for the engineers in the room. Frontend is Next.js 14 with TypeScript — modern, fast, type-safe. Backend is FastAPI in Python, which is async and extremely fast for an API layer. We use SQLite today which is perfectly fine for our team size, and it's a drop-in swap to PostgreSQL if we need to scale. ChromaDB is our vector database — purpose-built for AI embeddings. The whole RAG pipeline is orchestrated with LangChain, which is the industry standard for this. And all AI calls go through Cisco's approved GPT-4.1 endpoint via OAuth2."

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

> 🗣️ **Say This:**
> "Deployment is a single AWS EC2 instance — a t3.large running Ubuntu 22.04. Nginx sits at the front as a reverse proxy, handling SSL termination and routing. It proxies port 80/443 traffic to the Next.js frontend on 3000 and the FastAPI backend on 8000. All three data stores — SQLite, ChromaDB, and the file uploads folder — live on the same instance. Setup is fully scripted: clone the repo, run the setup script, fill in your .env with API keys, and you're live. We have automated validation scripts that check all components. Total setup time is under 30 minutes."

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
