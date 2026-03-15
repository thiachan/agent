# AGENT Platform — Reference Architecture

**AWS EKS · ca-central-1 · Branch: EKS-CA-v1**

---

## End-to-End Request Flow

```mermaid
flowchart TD
    User(["👤 User Browser"])

    subgraph CDN["Edge / CDN"]
        CF["Cloudflare\nDNS + Proxy\nagent.alexcty.com"]
    end

    subgraph AWS_CA["AWS ca-central-1"]
        ALB["AWS ALB\n(Internet-facing)\nHTTPS :443 / HTTP :80→443 redirect\nACM TLS Certificate"]

        subgraph EKS["EKS Cluster — agent-prod-ca"]
            direction TB
            ING["ALB Ingress Controller\npath: / → frontend :3000\npath: /api → backend :8000"]

            subgraph FE_NS["frontend pods (HPA: 2–8)"]
                FE1["frontend-pod-1\nNext.js :3000"]
                FE2["frontend-pod-2\nNext.js :3000"]
            end

            subgraph BE_NS["backend pods (HPA: 1–10)"]
                BE1["backend-pod-1\nFastAPI uvicorn :8000\n2 workers · 4Gi RAM"]
                BE2["backend-pod-2\nFastAPI uvicorn :8000\n2 workers · 4Gi RAM"]
            end

            PVC[("EBS PVC\nchroma-vector-db\nChromaDB vectors")]
            SM_ESO["External Secrets Operator\nSecrets Manager → k8s Secret\napp-secrets"]
        end

        subgraph DATA["Managed Data Layer"]
            RDS[("Aurora PostgreSQL\nServerless v2\n0.5–8 ACU\nUsers, sessions, docs, onboarding")]
            S3_UP["S3 Bucket\nagent-prod-ca-uploads-*\nRaw uploaded files"]
            S3_GEN["S3 Bucket\nagent-prod-ca-generated-*\nPodcasts, slides, exports"]
        end

        SM["AWS Secrets Manager\nagent-prod-ca-app-secrets\nAll API keys + DB creds"]
        ECR["ECR\nBackend image\nFrontend image"]
    end

    subgraph AI["External AI Services"]
        CISCO["Cisco GPT-4.1\nchat-ai.cisco.com\nOAuth2 token exchange"]
        OAI["OpenAI API\nEmbeddings: text-embedding-ada-002\nTTS fallback"]
        RESEMBLE["Resemble AI\np.cluster.resemble.ai\nHigh-quality TTS"]
        PRESENTON["Presenton\n172.31.11.64:80\nPowerPoint generation"]
    end

    User -->|"HTTPS"| CF
    CF -->|"HTTPS (proxied)"| ALB
    ALB --> ING
    ING -->|"GET / assets"| FE1 & FE2
    ING -->|"POST /api/*"| BE1 & BE2

    BE1 & BE2 -->|"SQL"| RDS
    BE1 & BE2 -->|"vector read/write\n(ReadWriteOnce: same node)"| PVC
    BE1 & BE2 -->|"upload/download"| S3_UP
    BE1 & BE2 -->|"store generated files"| S3_GEN
    BE1 & BE2 -->|"chat completions\nOAuth2"| CISCO
    BE1 & BE2 -->|"embeddings\nTTS fallback"| OAI
    BE1 & BE2 -->|"TTS synthesis"| RESEMBLE
    BE1 & BE2 -->|"slide generation"| PRESENTON

    SM -->|"synced every 1h"| SM_ESO
    SM_ESO -->|"k8s Secret: app-secrets\nenvFrom in pods"| BE1 & BE2 & FE1 & FE2
    ECR -->|"imagePullPolicy: Always"| BE1 & BE2 & FE1 & FE2
```

---

## AI Chat — RAG Pipeline

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend<br/>(Next.js)
    participant BE as Backend<br/>(FastAPI)
    participant OAI as OpenAI<br/>Embeddings
    participant Chroma as ChromaDB<br/>(EBS PVC)
    participant Cisco as Cisco GPT-4.1

    User->>FE: Type message + click Send
    FE->>BE: POST /api/chat/message<br/>{message, session_id, model_id:"auto"}
    BE->>BE: Validate JWT token
    BE->>OAI: POST /v1/embeddings<br/>{input: user_message}
    OAI-->>BE: 1536-dim embedding vector
    BE->>Chroma: similarity_search(vector, k=6)
    Chroma-->>BE: Top-6 relevant document chunks
    BE->>BE: Build prompt:<br/>system + context chunks + history + user msg
    BE->>Cisco: POST /openai/deployments/gpt-4.1/chat/completions<br/>(OAuth2 Bearer token)
    Cisco-->>BE: AI response text
    BE->>BE: Save message to Aurora (session history)
    BE-->>FE: {session_id, message: {role:"assistant", content}}
    FE-->>User: Display response
```

---

## Document Ingestion Pipeline

```mermaid
flowchart LR
    subgraph Upload["Admin Upload"]
        FILE["File\nPDF / DOCX / PPTX\nMP4 / MP3"]
    end

    subgraph Backend["Backend Processing"]
        API["POST /api/documents/upload"]
        PARSE["File Parser\nPyPDF2 / python-docx\npython-pptx / moviepy+Whisper"]
        CHUNK["Text Chunker\nLangChain RecursiveCharacterTextSplitter\nchunk_size=1000, overlap=200"]
        EMBED["Embedding\nOpenAI text-embedding-ada-002\n1536 dimensions"]
    end

    subgraph Storage["Storage"]
        S3[("S3\nuploads bucket\noriginal file")]
        CHROMA[("ChromaDB\nEBS PVC\nvector embeddings")]
        PG[("Aurora PostgreSQL\ndocument metadata\nfilename, role, namespace")]
    end

    FILE -->|"multipart/form-data"| API
    API --> PARSE
    API -->|"store original"| S3
    PARSE --> CHUNK
    CHUNK --> EMBED
    EMBED -->|"upsert vectors + metadata"| CHROMA
    API -->|"save metadata"| PG
```

---

## Podcast / Audio Generation

```mermaid
flowchart TD
    User(["User"]) -->|"prompt + voice settings"| API["POST /api/generate/podcast"]
    API --> SCRIPT["Script Generator\nCisco GPT-4.1\nHost + Guest dialogue"]
    SCRIPT --> SPLIT["Split into utterances\nHost lines / Guest lines"]
    SPLIT --> TTS1["Resemble AI TTS\nHost voice: 1ff0045f\nmax 1900 chars/call"]
    SPLIT --> TTS2["Resemble AI TTS\nGuest voice: 3e907bcc\nmax 1900 chars/call"]
    TTS1 --> MERGE["Audio Merge\npydub\nInterleave host + guest segments"]
    TTS2 --> MERGE
    MERGE --> S3[("S3 generated bucket\n.mp3 file")]
    S3 -->|"presigned URL"| User
```

---

## Infrastructure — Scaling & Resilience

```mermaid
flowchart TD
    subgraph EKS["EKS Cluster — ca-central-1 (2 AZs)"]
        subgraph AZ_A["AZ: ca-central-1a"]
            NODE_A["EC2 Node\nm5.large / spot"]
            FE_A["frontend pod"]
            BE_A["backend pod"]
        end
        subgraph AZ_B["AZ: ca-central-1b"]
            NODE_B["EC2 Node\nm5.large / spot"]
            FE_B["frontend pod"]
        end

        HPA_FE["HPA: frontend\nmin:2 max:8\nCPU>70% or MEM>75%"]
        HPA_BE["HPA: backend\nmin:1 max:10\nCPU>60% or MEM>70%"]
        CA["Cluster Autoscaler\nadds/removes EC2 nodes\nwhen pods are pending"]

        EBS[("EBS Volume\nChromaDB PVC\nReadWriteOnce\npinned to AZ-A")]
    end

    HPA_FE -->|"scale"| FE_A & FE_B
    HPA_BE -->|"scale"| BE_A
    CA -->|"provision"| NODE_A & NODE_B
    BE_A -->|"mount"| EBS

    NOTE["⚠️ Backend pods are pinned to the same AZ as the EBS volume\n(ReadWriteOnce constraint).\nHPA max=2 in practice to avoid PVC contention."]
```

---

## Secrets Management Flow

```mermaid
flowchart LR
    SM["AWS Secrets Manager\nagent-prod-ca-app-secrets\n(JSON blob with all keys)"]
    ESO["External Secrets Operator\nClusterSecretStore\nRefresh: every 1 hour"]
    K8S["k8s Secret: app-secrets\n(in namespace: agent)"]
    BE["Backend pods\nenvFrom: secretRef"]
    FE["Frontend pods\nenvFrom: secretRef"]

    SM -->|"IAM role: backend ServiceAccount\n(IRSA)"| ESO
    ESO -->|"creates/updates"| K8S
    K8S -->|"mounted as env vars"| BE
    K8S -->|"mounted as env vars"| FE
```

---

## CI/CD — Code Update Workflow

```mermaid
flowchart LR
    DEV["Developer\nEC2 or local machine"]
    GIT["GitHub\nbranch: EKS-CA-v1"]
    SCRIPT["./infra/scripts/deploy-ca.sh"]
    ECR["AWS ECR\n978027421922.dkr.ecr\n.ca-central-1.amazonaws.com"]
    EKS["EKS\nRolling restart\nzero-downtime"]

    DEV -->|"git push"| GIT
    GIT -->|"git pull + checkout"| SCRIPT
    SCRIPT -->|"docker build\n--build-arg NEXT_PUBLIC_API_URL\n=https://agent.alexcty.com"| ECR
    SCRIPT -->|"kubectl rollout restart"| EKS
    ECR -->|"imagePullPolicy: Always"| EKS
```

---

## Component Inventory

| Component | Value |
|---|---|
| **Domain** | `agent.alexcty.com` |
| **CDN** | Cloudflare (DNS proxy) |
| **AWS Account** | `978027421922` |
| **Region** | `ca-central-1` |
| **EKS Cluster** | `agent-prod-ca` (Kubernetes 1.30) |
| **Namespace** | `agent` |
| **Backend ECR** | `978027421922.dkr.ecr.ca-central-1.amazonaws.com/agent-prod-ca-backend:latest` |
| **Frontend ECR** | `978027421922.dkr.ecr.ca-central-1.amazonaws.com/agent-prod-ca-frontend:latest` |
| **Aurora Cluster** | `agent-prod-ca-aurora` · PostgreSQL Serverless v2 |
| **S3 Uploads** | `agent-prod-ca-uploads-978027421922` |
| **S3 Generated** | `agent-prod-ca-generated-978027421922` |
| **Secrets** | `agent-prod-ca-app-secrets` (Secrets Manager) |
| **ALB** | `k8s-agent-3e85e4c1e2-*.ca-central-1.elb.amazonaws.com` |
| **TLS Cert** | ACM `arn:aws:acm:ca-central-1:978027421922:certificate/796de4c2-…` |
| **Node Types** | `m5.large`, `m5a.large` (on-demand + spot mix) |
| **Backend Resources** | Request: 500m CPU / 1Gi RAM · Limit: 2 CPU / 4Gi RAM |
| **Frontend Resources** | Request: 250m CPU / 256Mi RAM · Limit: 1 CPU / 1Gi RAM |

---

*AGENT Platform · Reference Architecture · EKS-CA-v1 · March 2026*
