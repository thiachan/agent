# AGENT Platform — 15-Minute Enablement Presentation Guide

**Audience:** Cisco Enablement Team  
**Duration:** 15 Minutes  
**Presenter Notes:** This document is your head-to-toe walkthrough. Timings are guides — adjust based on audience engagement.

---

## Presentation Outline at a Glance

| # | Section | Time | What to Show |
|---|---------|------|--------------|
| 1 | Opening & Problem Statement | 1 min | Slide / verbal |
| 2 | What is AGENT? | 2 min | Architecture diagram |
| 3 | Live Demo — Chat + RAG | 4 min | Live product |
| 4 | Live Demo — Generation (PPT, Podcast, Docs) | 3 min | Live product |
| 5 | Architecture & Tech Stack | 2 min | Diagram slide |
| 6 | Security, Roles & Enterprise Readiness | 1 min | Slide |
| 7 | Roadmap & Extensibility | 1 min | Slide |
| 8 | Q&A | 1 min | Open floor |
| | **Total** | **15 min** | |

---

## Section 1 — Opening & Problem Statement (1 min)

### Talking Points

> "Every engineering team at Cisco sits on a goldmine of documents — demo videos, technical PDFs, presentations, runbooks — but finding the right information at the right time is still painful. Engineers waste hours searching SharePoint, emails, and shared drives. What if they could just *ask* a question and get an accurate, sourced answer in seconds?"

### Key Messages
- **The Pain:** Information is scattered across formats (PDF, DOCX, PPTX, MP4, MP3, spreadsheets). Search is keyword-based and unreliable.
- **The Cost:** Engineers spend significant time hunting for information instead of delivering value.
- **The Solution:** AGENT — an AI-powered platform purpose-built for GSSO Engineering that turns your documents into a searchable, conversational knowledge base.

---

## Section 2 — What is AGENT? (2 min)

### One-Liner
> **AGENT** (AI for GSSO Engineering Team) is an enterprise-grade, RAG-powered AI platform that lets employees ask natural language questions against their business knowledge and generate content — presentations, podcasts, documents — all from a single chat interface.

### Core Capabilities (show as bullet slide)

| Capability | Description |
|------------|-------------|
| **AI Chat (RAG)** | Ask questions in plain English. The system retrieves relevant document chunks from a vector database and generates grounded, cited answers using Cisco GPT-4.1. |
| **Knowledge Base Management** | Organize documents into topic-based knowledge bases with full CRUD. Admins control what goes in; everyone benefits. |
| **Multi-Format Ingestion** | Upload PDF, DOCX, PPTX, XLSX, MP4, MOV, MP3, WAV, TXT, MD, CSV, JSON, JSONL. Video and audio files are auto-transcribed via Whisper. |
| **PowerPoint Generation** | Ask the AI to generate a professional slide deck on any topic. Powered by Presenton.ai integration. |
| **Podcast & Speech Generation** | Generate a podcast or speech audio file from any topic using OpenAI TTS — fully non-blocking. |
| **Demo Video Search** | Intelligent semantic search over your existing demo video library with YouTube link retrieval and multi-layer precision matching. |
| **Document Generation** | Export chat content or AI-generated content to Word or PDF with one click. |
| **Role-Based Access Control** | Admin, employee, engineer, HR, manager roles — control who can upload, who can view, and what content each role can access. |

### Architecture Diagram (show on screen)

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                      │
│           React · TypeScript · Tailwind · Zustand             │
└──────────────────────┬───────────────────────────────────────┘
                       │  REST API + JWT
┌──────────────────────▼───────────────────────────────────────┐
│                 BACKEND (FastAPI / Python)                     │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────────┐ │
│  │ Auth & RBAC │ │ RAG Pipeline │ │ Generation Services    │ │
│  │ (JWT/OAuth2)│ │ (LangChain)  │ │ PPT · Audio · Docs    │ │
│  └─────────────┘ └──────┬───────┘ └────────────────────────┘ │
│                         │                                     │
│  ┌──────────────┐ ┌─────▼──────┐ ┌────────────────────────┐ │
│  │ SQLite DB    │ │ ChromaDB   │ │ MCP Agents             │ │
│  │ (Users, Docs │ │ (Vectors & │ │ (Demo Video, DocGen,   │ │
│  │  KB, Chat)   │ │ Embeddings)│ │  Custom Tasks)         │ │
│  └──────────────┘ └────────────┘ └────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌───────────┐ ┌───────────┐ ┌─────────────┐
  │ Cisco     │ │ OpenAI    │ │ Presenton   │
  │ GPT-4.1   │ │ Embeddings│ │ .ai         │
  │ (Chat LLM)│ │ & TTS     │ │ (Slides)    │
  └───────────┘ └───────────┘ └─────────────┘
```

---

## Section 3 — Live Demo: Chat + RAG (4 min)

> This is where you **sell** the platform. Keep it interactive.

### Demo Script

#### Step 1: Login (30 sec)
1. Open the browser to the AGENT URL.
2. Show the **dark-themed login page** — mention it's modern, responsive, works on mobile.
3. Log in with your credentials.

#### Step 2: Knowledge Bases (30 sec)
1. Show the **Dashboard** with existing knowledge bases (e.g., "Security Products", "Demo Videos", "Engineering Runbooks").
2. Click into one knowledge base — show the list of uploaded documents with file types (PDF, PPTX, MP4, etc.).
3. Point out: *"Each knowledge base is like a scoped brain — the AI only searches within the documents you've organized here."*

#### Step 3: Ask a Question (2 min)
1. Open the **Chat Interface**.
2. Type a real question relevant to the audience, for example:
   - *"What are the key features of Encrypted Visibility Engine?"*
   - *"Explain how SnortML works and its benefits"*
   - *"What demo videos do we have for XDR?"*
3. **While it responds**, explain what's happening under the hood:
   > "Right now, the system is embedding your question into a vector, searching ChromaDB for the most semantically similar document chunks, pulling the top results with source metadata, and feeding them as context to Cisco GPT-4.1 — which generates a grounded answer with citations. This is RAG — Retrieval Augmented Generation."
4. Show the response — point out:
   - The answer is **grounded in your documents**, not hallucinated.
   - **Sources are cited** so you can verify.
   - It handles follow-up questions with **conversation context**.

#### Step 4: Demo Video Search (1 min)
1. Ask: *"Find me demo videos about AI protection"*
2. Show how the MCP Demo Video Agent returns precise matches with YouTube links.
3. Point out the **multi-layer matching**: product name → tags → filename → title (priority order).

---

## Section 4 — Live Demo: Content Generation (3 min)

### PowerPoint Generation (1.5 min)
1. In the chat, type: *"Create a presentation about Cisco Secure Firewall features"*
2. Show how AGENT:
   - Uses RAG to pull relevant document content
   - Calls the Presenton.ai API to generate a professional slide deck
   - Returns a downloadable `.pptx` file
3. Open the generated file — show the slides briefly.
4. Key message: *"An engineer can go from question to polished slide deck in under 60 seconds."*

### Podcast Generation (1 min)
1. Type: *"Create a podcast about Encrypted Visibility Engine"*
2. Explain the flow:
   > "AGENT detects the intent, calls the MCP podcast agent, uses the RAG pipeline to gather content, sends it to the LLM with podcast-optimized prompts, then generates audio via OpenAI TTS — all non-blocking."
3. Play a few seconds of the generated audio.
4. Key message: *"Turn any topic in your knowledge base into a listenable podcast. Great for enablement content, onboarding, or commute-friendly learning."*

### Document Export (30 sec)
1. Show how any chat response can be exported to **Word (.docx)** or **PDF**.
2. Key message: *"Every output is reusable — no copy-paste needed."*

---

## Section 5 — Architecture & Tech Stack (2 min)

### The Stack (show as a table slide)

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Zustand | Modern, fast, type-safe, responsive |
| **Backend** | FastAPI (Python), Uvicorn | High-performance async API framework |
| **Database** | SQLite (upgradeable to PostgreSQL) | Lightweight, zero-config, production-capable |
| **Vector DB** | ChromaDB | Purpose-built for embeddings, fast similarity search |
| **RAG Framework** | LangChain | Industry-standard LLM orchestration |
| **Chat LLM** | Cisco GPT-4.1 (OAuth2) | Cisco-approved, enterprise-grade |
| **Embeddings** | OpenAI text-embedding-3-small | Best-in-class embedding model |
| **TTS** | OpenAI TTS API | Natural-sounding speech synthesis |
| **Slides** | Presenton.ai API | Professional presentation generation |
| **Transcription** | OpenAI Whisper | Accurate audio/video-to-text |
| **MCP Agents** | Model Context Protocol | Extensible agent framework for specialized tasks |

### RAG Pipeline — How It Works (30 sec explainer)

```
User Question
    │
    ▼
Embed query (OpenAI text-embedding-3-small)
    │
    ▼
Vector similarity search (ChromaDB)
    │  → Returns top relevant chunks with metadata
    ▼
Build prompt with retrieved context + conversation history
    │
    ▼
Send to Cisco GPT-4.1
    │
    ▼
Return grounded, cited response to user
```

**Key technical details to mention:**
- **Chunk size:** 1,000 characters with 200-character overlap
- **Embedding model:** OpenAI text-embedding-3-small (1,536 dimensions)
- **Document processing:** Automatic text extraction from 16+ file formats including video/audio transcription
- **Context management:** Conversation history maintained per session for follow-up questions

---

## Section 6 — Security, Roles & Enterprise Readiness (1 min)

### Talking Points

| Feature | Detail |
|---------|--------|
| **Authentication** | JWT-based auth with OAuth2 flow for Cisco GPT-4.1 |
| **Password Security** | bcrypt hashing, secure password reset via email token |
| **Role-Based Access** | 5 roles: Admin, Employee, Engineer, HR, Manager — each with scoped document access |
| **Document Permissions** | Documents can be public or restricted to specific roles |
| **Email Verification** | Optional email verification flow for user onboarding |
| **Deployment** | Runs on AWS EC2 (t3.large), Nginx reverse proxy, SSL/TLS ready |
| **Data Privacy** | All data stays on your infrastructure — no documents leave your environment |
| **Audit Trail** | Chat sessions and message history stored for accountability |

> "This isn't a toy — it's built for enterprise. Role-based access means your sensitive engineering docs stay visible only to the right people. All data lives on Cisco-controlled infrastructure."

---

## Section 7 — Roadmap & Extensibility (1 min)

### What's There Today
- Full RAG chat with 16+ supported file formats
- PowerPoint, podcast, speech, Word, and PDF generation
- Demo video intelligent search with YouTube integration
- MCP Agent framework for extensible tasks
- Role-based access control with 5 user roles
- Production deployment on AWS EC2

### Where It Can Go
| Direction | Description |
|-----------|-------------|
| **More AI Models** | Plug in AWS Bedrock, Azure OpenAI, or any LLM — the model manager is already abstracted |
| **Custom MCP Agents** | Build new agents for any team-specific workflow (e.g., ticket triage, config generation, compliance checks) |
| **PostgreSQL Migration** | Drop-in upgrade from SQLite for multi-user scale |
| **SSO Integration** | Swap JWT for Cisco SSO / SAML for seamless enterprise login |
| **S3 File Storage** | Move from local file storage to S3 for scalability |
| **Multi-Team Expansion** | Each team gets their own knowledge bases — GSSO, CX, TAC, etc. |
| **Analytics Dashboard** | Track usage, popular queries, content gaps |

> "The platform is modular by design. Adding a new AI model, a new agent, or a new file type is straightforward — it's built to grow with your team's needs."

---

## Section 8 — Q&A (1 min)

### Anticipated Questions & Answers

**Q: How is this different from just using ChatGPT?**
> "ChatGPT doesn't know your documents. AGENT uses RAG to ground every answer in your actual uploaded content — PDFs, demos, runbooks. No hallucinations, with source citations."

**Q: What models does it use?**
> "Cisco GPT-4.1 for chat (OAuth2 authenticated through Cisco's approved endpoint), OpenAI for embeddings and text-to-speech. The model manager is abstracted so we can swap in Bedrock or Azure if needed."

**Q: How hard is it to deploy?**
> "It runs on a single EC2 instance (t3.large). Setup is scripted — clone the repo, run the setup script, configure your .env, and start services. We have a 6-phase onboarding guide and automated validation scripts."

**Q: Can other teams use this?**
> "Absolutely. Each team gets their own knowledge bases. The role-based access system ensures document isolation. We can spin up a new team's workspace in minutes."

**Q: What about data security?**
> "Everything runs on Cisco-controlled infrastructure. Documents are stored locally (or S3), embeddings in ChromaDB on-prem. No data leaves your environment except API calls to Cisco GPT-4.1 and OpenAI for embeddings."

**Q: How do you handle video and audio files?**
> "We use OpenAI Whisper for transcription. Upload an MP4 or MP3, and AGENT automatically extracts the audio, transcribes it, chunks the text, and makes it searchable via RAG — just like any text document."

---

## Pre-Presentation Checklist

- [ ] **Backend running** on port 8000 — verify: `curl http://localhost:8000/docs`
- [ ] **Frontend running** on port 3000 — verify: open browser
- [ ] **Knowledge bases populated** with relevant demo content (Cisco security products, demo videos, etc.)
- [ ] **Test the demo questions** you plan to ask — make sure they return good answers
- [ ] **Test PPT generation** — make sure Presenton.ai API key is active
- [ ] **Test podcast generation** — make sure OpenAI TTS is working
- [ ] **Browser bookmarked** to the login page
- [ ] **Screen sharing ready** — use a clean browser window, no embarrassing tabs
- [ ] **Backup plan** — have screenshots or a recorded demo video in case of network issues

---

## Presentation Tips

1. **Lead with the demo, not the architecture.** Everyone understands "I ask a question, I get an answer." Not everyone understands RAG pipelines. Show the magic first, explain the mechanics second.
2. **Use real Cisco content in your demo.** If you're presenting to the enablement team, use demo videos and product docs they already know. When they see *their own content* being surfaced by the AI, it clicks immediately.
3. **Keep the podcast demo short.** Play 5-10 seconds of generated audio — just enough to impress, not enough to bore.
4. **Name-drop the stack strategically.** Mention "Cisco GPT-4.1" (it's their model), "LangChain" and "ChromaDB" (industry standard), "FastAPI" (engineers will nod approvingly).
5. **End with extensibility.** Enablement teams think in terms of scale — show them this isn't a one-team tool, it's a platform that can serve the entire org.

---

*Generated: February 2026 | Platform: AGENT v1.0 | Branch: vscode-optimized-v1*
