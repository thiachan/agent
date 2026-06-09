# AGENT Platform — Architecture Documentation

**GSSO AI Center · AWS EKS · ca-central-1 · Branch: `EKS-CA-v1`**

This document describes the full system architecture of the AGENT platform — an AI-powered sales enablement platform for Cisco's GSSO Engineering Team.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [End-to-End Request Flow](#2-end-to-end-request-flow)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Backend Architecture](#4-backend-architecture)
5. [RAG Chat Pipeline](#5-rag-chat-pipeline)
6. [Document Ingestion Pipeline](#6-document-ingestion-pipeline)
7. [Podcast Generation Pipeline](#7-podcast-generation-pipeline)
8. [PowerPoint Generation Pipeline](#8-powerpoint-generation-pipeline)
9. [Authentication & Authorization Flow](#9-authentication--authorization-flow)
10. [Database Schema](#10-database-schema)
11. [Infrastructure & Scaling](#11-infrastructure--scaling)
12. [Secrets Management](#12-secrets-management)
13. [CI/CD & Deployment Pipeline](#13-cicd--deployment-pipeline)
14. [External Service Integrations](#14-external-service-integrations)

---

## 1. System Overview

```mermaid
graph TB
    subgraph Users["Users"]
        U1["Admin"]
        U2["Engineer / SE"]
        U3["Manager / HR"]
    end

    subgraph Platform["AGENT Platform (EKS — ca-central-1)"]
        FE["Frontend\nNext.js 14 · React 18\nTypeScript · Tailwind CSS\n:3000"]
        BE["Backend\nFastAPI · Python 3.11\nSQLAlchemy · LangChain\n:8000"]
    end

    subgraph Data["Data Layer"]
        PG[("Aurora PostgreSQL\nUsers · Sessions\nDocs · Onboarding")]
        CHROMA[("ChromaDB\nEBS PVC\nVector Embeddings")]
        S3_UP[("S3\nUploads")]
        S3_GEN[("S3\nGenerated Assets")]
    end

    subgraph AI_Ext["AI & External Services"]
        CISCO["Cisco GPT-4.1\nchat-ai.cisco.com"]
        OAI["OpenAI\nEmbeddings + TTS"]
        RESEMBLE["Resemble AI\nTTS (high quality)"]
        PRESENTON["Presenton.ai\nPowerPoint generation"]
        DRIFT["Cisco DRIFT\nRAG pipeline"]
        QC["Cisco Data RAG\nContent validation"]
    end

    U1 & U2 & U3 -->|HTTPS| FE
    FE -->|REST API / JWT| BE
    BE --> PG
    BE --> CHROMA
    BE --> S3_UP
    BE --> S3_GEN
    BE --> CISCO
    BE --> OAI
    BE --> RESEMBLE
    BE --> PRESENTON
    BE --> DRIFT
    BE --> QC
```

---

## 2. End-to-End Request Flow

```mermaid
flowchart TD
    User(["👤 User Browser"])

    subgraph Edge["Edge / CDN"]
        CF["Cloudflare\nDNS + Proxy\nagent.alexcty.com"]
    end

    subgraph AWS["AWS ca-central-1"]
        ALB["AWS ALB\nInternet-facing · HTTPS :443\nACM TLS Certificate\nHTTP :80 → :443 redirect"]

        subgraph EKS["EKS Cluster — agent-prod-ca"]
            ING["ALB Ingress Controller\n/ → frontend :3000\n/api → backend :8000"]

            subgraph FE_PODS["Frontend Pods (HPA: 2–8)"]
                FE1["frontend-pod-1\nNext.js :3000"]
                FE2["frontend-pod-2\nNext.js :3000"]
            end

            subgraph BE_PODS["Backend Pods (HPA: 1–10)"]
                BE1["backend-pod-1\nFastAPI :8000\n2 workers · 4Gi RAM"]
                BE2["backend-pod-2\nFastAPI :8000\n2 workers · 4Gi RAM"]
            end

            ESO["External Secrets Operator\nSecrets Manager → k8s Secret"]
            PVC[("EBS PVC\nchroma-vector-db\nReadWriteOnce")]
        end

        subgraph Managed["Managed Services"]
            RDS[("Aurora PostgreSQL\nServerless v2 · 0.5–8 ACU")]
            S3U[("S3 · uploads bucket")]
            S3G[("S3 · generated bucket")]
            SM["Secrets Manager\nagent-prod-ca-app-secrets"]
            ECR["ECR\nBackend + Frontend images"]
        end
    end

    subgraph ExtAI["External AI Services"]
        CISCO["Cisco GPT-4.1\nOAuth2 token exchange"]
        OAI["OpenAI\ntext-embedding-ada-002 · TTS"]
        RESEMBLE["Resemble AI\nHigh-quality TTS"]
        PRESENTON["Presenton.ai\nSlide generation"]
    end

    User -->|HTTPS| CF
    CF -->|HTTPS proxied| ALB
    ALB --> ING
    ING -->|GET / static| FE1 & FE2
    ING -->|POST /api/*| BE1 & BE2

    BE1 & BE2 -->|SQL| RDS
    BE1 & BE2 -->|vector r/w| PVC
    BE1 & BE2 -->|file upload/download| S3U
    BE1 & BE2 -->|generated assets| S3G
    BE1 & BE2 -->|chat completions| CISCO
    BE1 & BE2 -->|embeddings + TTS| OAI
    BE1 & BE2 -->|TTS synthesis| RESEMBLE
    BE1 & BE2 -->|slide generation| PRESENTON

    SM -->|sync every 1h| ESO
    ESO -->|k8s Secret: app-secrets| BE1 & BE2 & FE1 & FE2
    ECR -->|imagePullPolicy:Always| BE1 & BE2 & FE1 & FE2
```

---

## 3. Frontend Architecture

```mermaid
graph TD
    subgraph NextJS["Next.js 14 — App Router (src/app/)"]
        ROOT["layout.tsx\nRoot Layout + Providers"]
        HOME["page.tsx\nLanding / Login"]

        subgraph SEAGENT["src/app/SEAGENT/"]
            PORTAL["Main Portal\nRole-based dashboard"]
        end

        RESET["reset-password/"]
        VERIFY["verify-email/"]
    end

    subgraph Components["src/components/portal/"]
        CHAT["ChatWithGeneration.tsx\nRAG chat + generation UI"]
        UPLOAD["DocumentUpload.tsx\nDrag & drop file upload"]
        ONBOARD["Onboarding.tsx\n4-mission SE playbook"]
        PODCAST_UI["Podcast UI\n(inside ChatWithGeneration)"]
        PPT_UI["Generate (PowerPoint)\n(inside ChatWithGeneration)"]
        QC_UI["QCAgent.tsx\nContent validation"]
        INCUB["Incubation.tsx\nCisco DRIFT RAG UI"]
        USERMGMT["UserManagement.tsx\nAdmin user controls"]
        BOOKMARK["BookmarkPage.tsx"]
    end

    subgraph State["State Management"]
        AUTH_STORE["authStore.ts (Zustand)\nuser, token, login/logout"]
        THEME_STORE["themeStore.ts (Zustand)\ndark mode toggle"]
        RQ["React Query\nServer state, caching, polling"]
    end

    subgraph APILayer["src/lib/api.ts"]
        AXIOS["Axios instance\nbaseURL: NEXT_PUBLIC_API_URL\nJWT interceptor (Authorization header)\n401 → redirect to login"]
    end

    HOME -->|authenticated| PORTAL
    PORTAL --> CHAT & UPLOAD & ONBOARD & QC_UI & INCUB & USERMGMT & BOOKMARK
    CHAT --> PODCAST_UI & PPT_UI
    Components -->|API calls| AXIOS
    AXIOS -->|HTTP| BE["Backend :8000"]
    Components -->|read/write| AUTH_STORE & THEME_STORE
    Components -->|server state| RQ
```

---

## 4. Backend Architecture

```mermaid
graph TD
    subgraph Entry["Entry Point"]
        MAIN["main.py\nFastAPI app\nCORS · Lifespan · Middleware"]
    end

    subgraph API["app/api/ — Route Handlers (prefix: /api)"]
        A_AUTH["auth.py\nPOST /auth/login\nPOST /auth/register\nPOST /auth/refresh\nGET  /auth/verify-email\nPOST /auth/reset-password"]
        A_UPLOAD["upload.py\nPOST /upload\n500 MB limit\nPDF·DOCX·PPTX·MP4·MP3…"]
        A_DOCS["documents.py\nGET  /documents\nDELETE /documents/{id}"]
        A_CHAT["chat.py\nPOST /chat/message (RAG)\nPOST /chat/generate-podcast\nPOST /chat/generate-speech\nPOST /chat/generate-video"]
        A_KB["knowledge_bases.py\nCRUD for ChromaDB collections"]
        A_GEN["generate.py\nPOST /generate/powerpoint\nvia Presenton.ai"]
        A_ONBOARD["onboarding.py\nSE 4-mission playbook\nprogress tracking"]
        A_INCUB["incubation.py\nCisco DRIFT RAG pipeline"]
        A_QC["qc_agent.py\nCisco Data RAG content validation"]
        A_AGENTS["agents.py\nMCP agents endpoint"]
        A_MODELS["models.py\nGET /models → available LLMs"]
        A_BOOK["bookmarks.py\nSave/manage bookmarks"]
    end

    subgraph Services["app/services/ — Business Logic"]
        SVC_RAG["rag_service.py\nChromaDB + LangChain\nvector search · chunk · embed"]
        SVC_MODEL["model_manager.py\nPlugin: OpenAI · Cisco · Bedrock\nembedding model factory"]
        SVC_POD["podcast_service.py\nScript gen (Cisco GPT)\nTTS → pydub merge → S3"]
        SVC_SPEECH["speech_service.py\nSingle-voice TTS\nResemble AI primary\nOpenAI TTS fallback"]
        SVC_TTS["tts_service.py\nOpenAI TTS wrapper"]
        SVC_PPT["presenton_service.py\nPresenton.ai HTTP client"]
        SVC_DOC["document_processor.py\nPyPDF2 · python-docx\nopenpyxl · python-pptx\nWhisper (video transcript)"]
        SVC_DOCGEN["document_generator.py\nReportLab PDF generation"]
        SVC_VIDEO["demo_video_service.py\nDemo video generation"]
        SVC_EMAIL["email_service.py\nSMTP verification + reset"]
        SVC_JOB["job_tracker.py\nAsync job status tracking\nfor long-running tasks"]
        SVC_MCP["mcp_service.py\nModel Context Protocol"]
    end

    subgraph Core["app/core/ — Cross-cutting"]
        CFG["config.py\nPydantic Settings\nall env vars"]
        DB["database.py\nSQLAlchemy engine\nsession factory"]
        SEC["security.py\nJWT encode/decode\nbcrypt password hashing"]
        MIG["migrate.py\nIdempotent schema migrations\nrun on every startup"]
        STOR["storage.py\nS3 / local filesystem abstraction"]
        DEP["dependencies.py\nget_db · get_current_user\nFastAPI dependency injection"]
    end

    subgraph Models["app/models/ — ORM"]
        M_USER["user.py"]
        M_DOC["document.py"]
        M_CHAT["chat.py"]
        M_KB["knowledge_base.py"]
        M_BOOK["bookmark.py"]
        M_ONBOARD["onboarding.py"]
    end

    MAIN --> API
    API --> Services
    API --> Core
    Services --> Core
    Core --> Models
    Models -->|SQLAlchemy| PG[("Aurora PostgreSQL")]
    SVC_RAG -->|vectors| CHROMA[("ChromaDB EBS")]
    STOR -->|files| S3[("AWS S3")]
```

---

## 5. RAG Chat Pipeline

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Next.js)
    participant BE as Backend (FastAPI)
    participant SEC as security.py (JWT)
    participant OAI as OpenAI Embeddings
    participant Chroma as ChromaDB (EBS)
    participant GPT as Cisco GPT-4.1
    participant PG as Aurora PostgreSQL

    User->>FE: Type message → Send
    FE->>BE: POST /api/chat/message\n{message, session_id, model:"auto"}
    BE->>SEC: Verify JWT token
    SEC-->>BE: user_id, role
    BE->>OAI: POST /v1/embeddings\n{input: message}
    OAI-->>BE: 1536-dim vector
    BE->>Chroma: similarity_search(vector, k=6)
    Chroma-->>BE: Top-6 document chunks + metadata
    BE->>PG: SELECT last N messages (session history)
    PG-->>BE: Chat history
    BE->>BE: Build prompt:\nsystem_prompt + context_chunks\n+ history + user_message
    BE->>GPT: POST /openai/deployments/gpt-4.1/chat/completions\n(OAuth2 Bearer · max_tokens:4000)
    GPT-->>BE: AI response text
    BE->>PG: INSERT ChatMessage (role:assistant, content)
    BE-->>FE: {session_id, message:{role, content}}
    FE-->>User: Display streamed response
```

---

## 6. Document Ingestion Pipeline

```mermaid
flowchart LR
    subgraph Input["Input"]
        FILE["File\nPDF · DOCX · PPTX\nMP4 · MP3 · TXT · CSV…\nmax 500 MB"]
    end

    subgraph Upload["POST /api/upload"]
        VAL["Validate\nextension + size"]
        META["Save metadata\nto PostgreSQL"]
        S3_STORE["Store original\nto S3 uploads bucket"]
    end

    subgraph Process["Document Processor"]
        PARSE["Parser\nPyPDF2 → PDF\npython-docx → DOCX\npython-pptx → PPTX\nopenpyxl → XLSX\nWhisper → Video/Audio"]
        CHUNK["Text Chunker\nRecursiveCharacterTextSplitter\nchunk_size=1000\noverlap=200"]
    end

    subgraph Vectorize["Embedding + Storage"]
        EMBED["OpenAI\ntext-embedding-ada-002\n1536-dim vectors"]
        CHROMA_UPSERT["ChromaDB upsert\nid · vector · metadata\n(filename, role, namespace)"]
    end

    FILE --> VAL --> META --> S3_STORE
    VAL --> PARSE
    PARSE --> CHUNK
    CHUNK --> EMBED
    EMBED --> CHROMA_UPSERT
```

---

## 7. Podcast Generation Pipeline

```mermaid
flowchart TD
    User(["👤 User"])
    API["POST /api/generate/podcast\n{prompt, topic, duration}"]
    JOB["job_tracker.py\nCreate async job\nReturn job_id immediately"]
    SCRIPT["Cisco GPT-4.1\nGenerate Host + Guest script\nstructured dialogue turns"]
    SPLIT["Split utterances\nHost lines / Guest lines"]

    subgraph TTS["Parallel TTS Synthesis (Resemble AI)"]
        TTS_H["Host voice\n1ff0045f\nmax 1900 chars/call"]
        TTS_G["Guest voice\n3e907bcc\nmax 1900 chars/call"]
        TTS_OAI["OpenAI TTS fallback\nnova (host) · onyx (guest)"]
    end

    MERGE["pydub\nInterleave host + guest\naudio segments"]
    MP3["Final .mp3 file\ntemp_generated_files/"]
    S3_UP["Upload to S3\ngenerated bucket"]
    URL["Presigned S3 URL\n→ returned to frontend"]

    User -->|HTTP POST| API
    API --> JOB
    JOB -->|background task| SCRIPT
    SCRIPT --> SPLIT
    SPLIT --> TTS_H & TTS_G
    TTS_H -.->|if Resemble fails| TTS_OAI
    TTS_G -.->|if Resemble fails| TTS_OAI
    TTS_H & TTS_G --> MERGE
    TTS_OAI --> MERGE
    MERGE --> MP3
    MP3 --> S3_UP
    S3_UP --> URL
    URL -->|job status poll| User
```

---

## 8. PowerPoint Generation Pipeline

```mermaid
flowchart LR
    User(["👤 User"])
    FE_UI["ChatWithGeneration.tsx\nGenerate tab"]
    API_GEN["POST /api/generate/powerpoint\n{prompt, slide_count, style}"]
    SVC_PPT["presenton_service.py\nHTTP client"]
    PRESENTON["Presenton.ai API\nhttps://api.presenton.ai\nmax 12 slides"]
    PPTX["Generated .pptx file"]
    S3_GEN["S3 generated bucket"]
    DOWNLOAD["Download link → User"]

    User --> FE_UI --> API_GEN --> SVC_PPT
    SVC_PPT -->|POST with API key| PRESENTON
    PRESENTON -->|.pptx binary| SVC_PPT
    SVC_PPT --> PPTX --> S3_GEN --> DOWNLOAD --> User
```

---

## 9. Authentication & Authorization Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant BE as Backend
    participant SEC as security.py
    participant PG as PostgreSQL
    participant MAIL as Email Service (SMTP)

    Note over User,MAIL: Registration Flow
    User->>FE: Fill register form
    FE->>BE: POST /api/auth/register\n{email, password, full_name}
    BE->>SEC: bcrypt hash password
    BE->>PG: INSERT User (is_verified=false, verification_token)
    BE->>MAIL: Send verification email\n(token link)
    BE-->>FE: 201 Created — check email

    Note over User,MAIL: Email Verification
    User->>BE: GET /api/auth/verify-email?token=…
    BE->>PG: UPDATE User SET is_verified=true
    BE-->>FE: 200 OK

    Note over User,MAIL: Login Flow
    User->>FE: Enter email + password
    FE->>BE: POST /api/auth/login
    BE->>PG: SELECT User WHERE email=…
    BE->>SEC: bcrypt verify password
    SEC->>SEC: JWT encode\n{sub:user_id, exp:+24h, role}
    BE-->>FE: {access_token, token_type:"bearer"}
    FE->>FE: authStore.setToken(token)\nlocalStorage.setItem

    Note over User,MAIL: Authenticated Request
    User->>FE: Any action (chat, upload…)
    FE->>BE: Request + Authorization: Bearer <token>
    BE->>SEC: JWT decode + verify expiry
    BE->>PG: SELECT User by id (verify active)
    BE-->>FE: Response data

    Note over User,MAIL: Role-Based Access
    BE->>BE: Check user.role\n(ADMIN · EMPLOYEE · ENGINEER\nHR · MANAGER)
    BE-->>FE: 403 if insufficient role
```

---

## 10. Database Schema

```mermaid
erDiagram
    USER {
        int id PK
        string email UK
        string hashed_password
        string full_name
        string role
        bool is_active
        bool is_verified
        string verification_token
        string reset_token
        datetime created_at
        datetime updated_at
    }

    DOCUMENT {
        int id PK
        string filename
        string original_filename
        string file_type
        string s3_key
        string status
        string namespace
        string allowed_roles
        int uploaded_by FK
        datetime created_at
    }

    KNOWLEDGE_BASE {
        int id PK
        string name
        string description
        string collection_id
        string embedder
        string status
        int created_by FK
        datetime created_at
    }

    CHAT_SESSION {
        int id PK
        int user_id FK
        string title
        string model_id
        datetime created_at
        datetime updated_at
    }

    CHAT_MESSAGE {
        int id PK
        int session_id FK
        string role
        text content
        json metadata
        datetime created_at
    }

    BOOKMARK {
        int id PK
        int user_id FK
        string item_type
        string item_id
        string title
        json metadata
        datetime created_at
    }

    ONBOARDING_TASK {
        int id PK
        int user_id FK
        string mission
        string task_name
        string status
        int progress_pct
        json response_data
        datetime completed_at
        datetime created_at
    }

    USER ||--o{ DOCUMENT : "uploads"
    USER ||--o{ CHAT_SESSION : "owns"
    USER ||--o{ BOOKMARK : "saves"
    USER ||--o{ ONBOARDING_TASK : "tracks"
    USER ||--o{ KNOWLEDGE_BASE : "creates"
    CHAT_SESSION ||--o{ CHAT_MESSAGE : "contains"
```

---

## 11. Infrastructure & Scaling

```mermaid
flowchart TD
    subgraph EKS["EKS Cluster — ca-central-1 (2 AZs)"]
        subgraph AZ_A["ca-central-1a"]
            NODE_A["EC2 Node\nm5.large / spot"]
            FE_A["frontend pod"]
            BE_A["backend pod\n← EBS pinned here"]
        end
        subgraph AZ_B["ca-central-1b"]
            NODE_B["EC2 Node\nm5.large / spot"]
            FE_B["frontend pod"]
        end

        HPA_FE["HPA: frontend\nmin:2 max:8\nCPU > 70% or MEM > 75%"]
        HPA_BE["HPA: backend\nmin:1 max:10\nCPU > 60% or MEM > 70%\n⚠ practical max:2 (EBS RWO)"]
        CA["Cluster Autoscaler\nadds/removes EC2 nodes\nwhen pods are Pending"]
        EBS[("EBS Volume\nchroma-vector-db PVC\nReadWriteOnce\npinned to AZ-A")]
    end

    HPA_FE -.->|scale| FE_A & FE_B
    HPA_BE -.->|scale| BE_A
    CA -.->|provision| NODE_A & NODE_B
    BE_A -->|mount| EBS

    NOTE["⚠ Backend pods are pinned to AZ-A\ndue to ReadWriteOnce EBS constraint.\nNEVER delete chroma-vector-db PVC."]
```

---

## 12. Secrets Management

```mermaid
flowchart LR
    DEV["Developer / Terraform\nbootstrap-ca.sh"]
    SM["AWS Secrets Manager\nagent-prod-ca-app-secrets\n(JSON blob: all API keys + DB URL)"]
    IRSA["IAM Role for Service Account\n(IRSA)\nbackend ServiceAccount → IAM policy"]
    ESO["External Secrets Operator\nClusterSecretStore\nrefresh: every 1 hour"]
    K8S_SEC["k8s Secret: app-secrets\n(namespace: agent)"]
    BE_POD["Backend pods\nenvFrom: secretRef: app-secrets"]
    FE_POD["Frontend pods\nenvFrom: secretRef: app-secrets\n(NEXT_PUBLIC_API_URL, etc.)"]

    DEV -->|aws secretsmanager put-secret-value| SM
    SM -->|IRSA auth| IRSA
    IRSA --> ESO
    ESO -->|creates/updates| K8S_SEC
    K8S_SEC -->|env vars injected| BE_POD
    K8S_SEC -->|env vars injected| FE_POD
```

**Key secrets** (see [infra/secrets-template.json](infra/secrets-template.json)):

| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | Aurora PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `OPENAI_API_KEY` | Embeddings + TTS fallback |
| `CISCO_CLIENT_ID/SECRET` | Cisco GPT-4.1 OAuth2 |
| `DRIFT_CLIENT_ID/SECRET` | Cisco DRIFT RAG (Incubation) |
| `QC_CLIENT_ID/SECRET/APP_ID` | Cisco Data RAG (QC Agent) |
| `PRESENTON_API_KEY` | PowerPoint generation |
| `MAIL_USERNAME/PASSWORD` | SMTP email verification |

---

## 13. CI/CD & Deployment Pipeline

```mermaid
flowchart TD
    DEV["Developer\ngit push → EKS-CA-v1"]

    subgraph Deploy["./infra/scripts/deploy-ca.sh"]
        ECR_LOGIN["aws ecr get-login-password\nDocker login to ECR\n(978027421922.dkr.ecr.ca-central-1)"]
        BUILD_BE["docker build\nbackend/Dockerfile\nPython 3.11-slim\nnon-root user 1001"]
        BUILD_FE["docker build\nDockerfile (root)\nNode 20-alpine\nstandalone output"]
        PUSH_BE["docker push\nagent-prod-ca-backend:latest"]
        PUSH_FE["docker push\nagent-prod-ca-frontend:latest"]
        K8S_APPLY["kubectl apply -f infra/k8s/\nUpdate Deployment image tags"]
        ROLLOUT["kubectl rollout status\nWait for rolling update\nzero-downtime"]
    end

    subgraph Bootstrap["One-time: bootstrap-ca.sh"]
        TF["terraform apply\nEKS · Aurora · S3 · ECR\nIAM · Secrets Manager · ALB"]
        KUBECONFIG["aws eks update-kubeconfig\n--cluster agent-prod-ca"]
        INSTALL["helm install\nALB Ingress Controller\nExternal Secrets Operator\nCluster Autoscaler"]
        MIGRATE["migrate-db-ca.sh\nkubectl exec → python migrate.py"]
    end

    DEV --> ECR_LOGIN
    ECR_LOGIN --> BUILD_BE & BUILD_FE
    BUILD_BE --> PUSH_BE
    BUILD_FE --> PUSH_FE
    PUSH_BE & PUSH_FE --> K8S_APPLY
    K8S_APPLY --> ROLLOUT

    Bootstrap -->|first time only| EKS_CLUSTER["Live EKS Cluster"]
    ROLLOUT --> EKS_CLUSTER
```

**Startup sequence inside each pod:**

```mermaid
flowchart LR
    POD_START["Pod starts\nenvFrom: app-secrets"]
    MIG["migrate.py\nrun_migrations()\nidempotent schema updates"]
    UVICORN["uvicorn main:app\n--host 0.0.0.0 --port 8000\n--limit-concurrency 1000\n--ws-max-size 16777216"]
    READY["Pod READY\nHealthcheck: GET /api/health"]

    POD_START --> MIG --> UVICORN --> READY
```

---

## 14. External Service Integrations

```mermaid
graph LR
    BE["Backend\n(FastAPI)"]

    subgraph Cisco["Cisco Internal APIs"]
        GPT41["Cisco GPT-4.1\nchat-ai.cisco.com\nOAuth2 client_credentials\nEndpoint: /openai/deployments/gpt-4.1/chat/completions"]
        DRIFT_API["Cisco DRIFT\nRAG pipeline\nIncubation feature"]
        QC_API["Cisco Data RAG\nContent quality validation\nQC Agent feature"]
    end

    subgraph OpenAI_G["OpenAI"]
        EMBED["Embeddings\ntext-embedding-ada-002\n1536 dims\nused for ALL vector search"]
        TTS_OAI_SVC["TTS (fallback)\nnova voice (host)\nonyx voice (guest)"]
    end

    subgraph ResembleAI["Resemble AI (Primary TTS)"]
        TTS_H["Host voice\n1ff0045f"]
        TTS_G["Guest voice\n3e907bcc"]
    end

    subgraph AWS_SVC["AWS Services"]
        BEDROCK["Bedrock (optional)\namazon.titan-embed-text-v1\nchat models via BEDROCK_CHAT_MODELS"]
        S3_SVC["S3\nuploads + generated"]
        SM_SVC["Secrets Manager\napp-secrets JSON"]
    end

    subgraph GenAI["Generative Tools"]
        PRESENTON_SVC["Presenton.ai\nhttps://api.presenton.ai\nmax 12 slides per deck"]
    end

    BE -->|OAuth2 Bearer| GPT41
    BE -->|OAuth2 Bearer| DRIFT_API
    BE -->|OAuth2 Bearer| QC_API
    BE -->|API key| EMBED
    BE -->|API key| TTS_OAI_SVC
    BE -->|API key| TTS_H & TTS_G
    BE -->|AWS SDK / boto3| BEDROCK
    BE -->|AWS SDK / boto3| S3_SVC
    BE -->|AWS SDK / boto3| SM_SVC
    BE -->|API key| PRESENTON_SVC
```

---

> **See also:**
> - [REFERENCE_ARCHITECTURE.md](REFERENCE_ARCHITECTURE.md) — original end-to-end flow + RAG sequence diagrams
> - [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) — API reference & DB schema detail
> - [docs/EKS_CA_DEPLOYMENT_GUIDE.md](docs/EKS_CA_DEPLOYMENT_GUIDE.md) — cluster setup walkthrough
> - [docs/RAG_IMPROVEMENT_ANALYSIS.md](docs/RAG_IMPROVEMENT_ANALYSIS.md) — RAG tuning notes
> - [infra/secrets-template.json](infra/secrets-template.json) — all required secret keys
