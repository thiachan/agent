# AGENT — GSSO AI Center

**AI-powered sales enablement platform for Cisco's GSSO Engineering Team.**

Combines RAG (Retrieval-Augmented Generation), document intelligence, SE onboarding playbooks, AI chat, podcast generation, and PowerPoint automation — running on AWS EKS in `ca-central-1`.

- **Live URL**: https://agent.alexcty.com
- **Cluster**: `agent-prod-ca` · EKS · `ca-central-1`
- **Branch**: `EKS-CA-v1`

---

## Quick Start — Deploy to EKS

```bash
# 1. Clone and checkout
git clone https://github.com/thiachan/agent.git
cd agent
git checkout EKS-CA-v1

# 2. Point kubectl at the EKS cluster
aws eks update-kubeconfig --region ca-central-1 --name agent-prod-ca

# 3. Build images + push to ECR + rolling deploy
./infra/scripts/deploy-ca.sh            # both backend + frontend
./infra/scripts/deploy-ca.sh backend    # backend only
./infra/scripts/deploy-ca.sh frontend   # frontend only
```

> **First-time setup?** The full cluster (EKS, Aurora, S3, ALB, Secrets Manager) is provisioned once via Terraform:
> ```bash
> ./infra/scripts/bootstrap-ca.sh
> ```
> See [docs/EKS_CA_DEPLOYMENT_GUIDE.md](docs/EKS_CA_DEPLOYMENT_GUIDE.md) for the complete walkthrough.

---

## Architecture

```
Users → Cloudflare → AWS ALB → EKS (ca-central-1)
                                  ├── frontend pods (Next.js :3000)
                                  └── backend pods  (FastAPI  :8000)
                                        ├── Aurora PostgreSQL (RDS)
                                        ├── ChromaDB (EBS PVC)
                                        ├── S3 (uploads + generated)
                                        └── Secrets Manager (all keys)
```

See [REFERENCE_ARCHITECTURE.md](REFERENCE_ARCHITECTURE.md) for the full end-to-end diagram.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 · React 18 · TypeScript · Tailwind CSS · Zustand |
| Backend | FastAPI · Python 3.12 · SQLAlchemy · LangChain · Pydantic |
| Relational DB | Aurora PostgreSQL Serverless v2 (0.5–8 ACU) |
| Vector DB | ChromaDB on AWS EBS PVC (`chroma-vector-db`) |
| File Storage | AWS S3 (`agent-prod-ca-uploads-*`, `agent-prod-ca-generated-*`) |
| Secrets | AWS Secrets Manager → External Secrets Operator → k8s Secret |
| Container Runtime | EKS 1.30 · Docker · ECR |
| Infra-as-Code | Terraform (VPC, EKS, Aurora, S3, IAM, Secrets) |
| AI — Chat | Cisco GPT-4.1 via OAuth2 (`chat-ai.cisco.com`) |
| AI — Embeddings | OpenAI `text-embedding-ada-002` |
| AI — TTS | Resemble AI (primary) · OpenAI TTS (fallback) |
| AI — Slides | Presenton (internal ECS service at `172.31.11.64:80`) |

---

## Key Features

- **AI Chat** — RAG-powered Q&A over uploaded documents using Cisco GPT-4.1
- **Document Management** — Upload PDF/DOCX/PPTX/video; auto-chunked into vector DB
- **SE Onboarding Playbook** — 4-mission interactive playbook (Ninja→Samurai→Daimyo→Sensei) with progress tracking, admin-editable content, and collapsible Learn More panels
- **Podcast Generation** — AI generates two-voice audio podcasts from prompts
- **PowerPoint Generation** — Automated slide decks via Presenton
- **Role-Based Access** — Admin / Employee / Engineer / HR / Manager roles
- **Knowledge Base** — Document namespacing by role/department

---

## Project Structure

```
AGENT/
├── src/                        # Next.js frontend (App Router)
│   ├── app/                    # Pages and layouts
│   ├── components/portal/      # Main portal components
│   │   ├── Onboarding.tsx      # SE Onboarding Playbook (4 missions)
│   │   ├── ChatWithGeneration.tsx
│   │   └── MainPortal.tsx
│   ├── lib/api.ts              # Axios client (baseURL = NEXT_PUBLIC_API_URL)
│   └── stores/authStore.ts     # Zustand auth state
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── app/api/                # Route handlers (chat, auth, onboarding, …)
│   ├── app/services/           # RAG, chat, TTS, generation services
│   ├── app/models/             # SQLAlchemy ORM models
│   ├── Dockerfile              # 2 uvicorn workers (4Gi RAM limit)
│   └── requirements.txt
├── infra/
│   ├── k8s/                    # Kubernetes manifests
│   │   ├── backend/            # Deployment, Service, HPA, PVC, ServiceAccount
│   │   ├── frontend/           # Deployment, Service, HPA
│   │   ├── external-secrets/   # ClusterSecretStore + ExternalSecret
│   │   └── ingress.yaml        # AWS ALB Ingress (HTTP→HTTPS redirect)
│   ├── terraform-ca/           # Terraform for ca-central-1 (EKS, Aurora, S3, IAM)
│   └── scripts/
│       ├── deploy-ca.sh        # ← Day-to-day deploy script (build + push + deploy)
│       └── bootstrap-ca.sh     # ← First-time full cluster provisioning
├── docs/                       # Detailed guides
│   └── EKS_CA_DEPLOYMENT_GUIDE.md
├── Dockerfile                  # Frontend image (requires --build-arg NEXT_PUBLIC_API_URL)
└── next.config.js
```

---

## Environment Variables

All secrets live in **AWS Secrets Manager** (`agent-prod-ca-app-secrets`) and are injected into pods via the External Secrets Operator. Key variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | Aurora PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI embeddings + TTS fallback |
| `CISCO_CLIENT_ID` / `CISCO_CLIENT_SECRET` | Cisco GPT-4.1 OAuth2 |
| `CISCO_ENDPOINT` / `CISCO_APPKEY` | Cisco AI endpoint |
| `RESEMBLE_API_KEY` / `RESEMBLE_ENDPOINT` | Resemble AI TTS |
| `MAIL_FROM` / `MAIL_SERVER` / `MAIL_PASSWORD` | Email (password reset) |

> **`NEXT_PUBLIC_API_URL`** is NOT a runtime secret — it must be baked into the frontend Docker image at build time via `--build-arg NEXT_PUBLIC_API_URL=https://agent.alexcty.com`. The [deploy-ca.sh](infra/scripts/deploy-ca.sh) script handles this automatically.

---

## Admin Access

| | |
|---|---|
| URL | https://agent.alexcty.com |
| Email | `admin@cisco.com` |
| Password | `Cisco123!` |

---

## Monitoring

```bash
# Pod health
kubectl get pods -n agent

# Live backend logs (filter health noise)
kubectl logs -n agent -l app=backend -f --tail=50 | grep -v "GET /health"

# Crash logs from previous container run
kubectl logs -n agent <pod-name> --previous

# HPA scaling status
kubectl get hpa -n agent
```

---

*AGENT Platform · Branch: EKS-CA-v1 · AWS ca-central-1 · March 2026*
