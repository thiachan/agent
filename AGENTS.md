# AGENT — GSSO AI Center · Copilot Instructions

## Project Summary

**AGENT** is an AI-powered sales enablement platform for Cisco's GSSO Engineering Team.

| Dimension | Detail |
|-----------|--------|
| Live URL | https://agent.alexcty.com |
| Cluster | `agent-prod-ca` · EKS · `ca-central-1` |
| Branch | `EKS-CA-v1` |
| Frontend | Next.js 14 · React 18 · TypeScript · Tailwind CSS · Zustand |
| Backend | FastAPI · Python 3.11 · SQLAlchemy 2.0 · LangChain · ChromaDB |
| Database | Aurora PostgreSQL (prod) · SQLite (dev) |
| AI Models | Cisco GPT-4.1 (`chat-ai.cisco.com`) · OpenAI · AWS Bedrock |
| Infrastructure | AWS EKS · Terraform · Docker · ECR · S3 · Secrets Manager |

### Core Features
- **AI Chat** — RAG-powered Q&A over uploaded documents (ChromaDB + LangChain)
- **Document Management** — PDF/DOCX/PPTX/Video; auto-chunked into vector DB
- **SE Onboarding Playbook** — 4-mission interactive playbook (Ninja → Samurai → Daimyo → Sensei)
- **Podcast Generation** — Two-voice AI audio from prompts (MoviePy + TTS)
- **PowerPoint Generation** — Slide decks via Presenton.ai API
- **Role-Based Access** — Admin / Employee / Engineer / HR / Manager

---

## Architecture

```
Users → Cloudflare → AWS ALB → EKS (ca-central-1)
                                  ├── frontend pods  (Next.js :3000)
                                  └── backend pods   (FastAPI  :8000)
                                        ├── Aurora PostgreSQL (RDS)
                                        ├── ChromaDB (EBS PVC)
                                        ├── S3 (uploads + generated assets)
                                        └── Secrets Manager (all credentials)
```

See [REFERENCE_ARCHITECTURE.md](REFERENCE_ARCHITECTURE.md) for the full diagram.

---

## Repository Structure

```
/
├── src/                        # Next.js frontend (App Router)
│   ├── app/                    # Routes (SEAGENT/, reset-password/, verify-email/)
│   ├── components/portal/      # Feature UI (ChatWithGeneration, DocumentUpload, …)
│   ├── lib/api.ts              # Axios client with JWT interceptors
│   └── stores/                 # Zustand: authStore, themeStore
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── app/api/                # Route handlers (auth, chat, documents, onboarding, …)
│   ├── app/services/           # Business logic (rag_service, podcast_service, …)
│   ├── app/models/             # SQLAlchemy ORM models
│   └── app/core/               # config, database, security, migrate, storage
├── infra/
│   ├── scripts/deploy-ca.sh   # Build + ECR push + rolling EKS deploy
│   ├── scripts/bootstrap-ca.sh# One-time Terraform infra setup
│   ├── terraform-ca/           # EKS, RDS, S3, IAM, ECR definitions
│   └── k8s/                    # Kubernetes manifests
├── docs/                       # Reference docs (see Documentation below)
├── Dockerfile                  # Frontend multi-stage image (Node 20-alpine)
├── backend/Dockerfile          # Backend multi-stage image (Python 3.11-slim)
└── ecosystem.config.js         # PM2 config for local/EC2 process management
```

---

## Key Commands

### Frontend
```bash
npm run dev       # Dev server → http://0.0.0.0:3000
npm run build     # Production build → .next/standalone
npm run start     # Serve production build
npm run lint      # ESLint check
```

### Backend
```bash
cd backend
source venv/bin/activate
./start_backend.sh            # Starts uvicorn on :8000
# or directly:
uvicorn main:app --host 0.0.0.0 --port 8000 \
  --limit-concurrency 1000 --ws-max-size 16777216
```

### Both Services (PM2 / local)
```bash
./start-services.sh           # Start both via nohup
pm2 start ecosystem.config.js # Or via PM2
pm2 logs / pm2 restart all
```

### Deploy to EKS
```bash
./infra/scripts/deploy-ca.sh              # Build + push ECR + rolling deploy (both)
./infra/scripts/deploy-ca.sh backend      # Backend only
./infra/scripts/deploy-ca.sh frontend     # Frontend only
./infra/scripts/migrate-db-ca.sh          # Run DB migrations on EKS pod
```

### One-Time Infrastructure Bootstrap
```bash
./infra/scripts/bootstrap-ca.sh          # Terraform: EKS, RDS, S3, IAM, Secrets
aws eks update-kubeconfig --region ca-central-1 --name agent-prod-ca
```

---

## Backend Conventions

- **API prefix**: all routes under `/api/v1/` (auto-docs at `/api/docs`)
- **Auth**: JWT 24-hour tokens; `get_current_user` dependency injected per route
- **DB session**: injected via `get_db` dependency; use `async with` for long operations
- **Migrations**: idempotent, run automatically on startup in `app/core/migrate.py` — never use Alembic
- **Uploads**: max 500 MB; stored to S3 in prod, `backend/uploads/` in dev
- **Async jobs**: use `job_tracker.py` for long-running tasks (video, podcast, doc generation)
- **Vector search**: all RAG goes through `rag_service.py` (ChromaDB collection per knowledge base)
- **Multi-model**: add new LLM providers in `model_manager.py` only, not in route handlers

### Secrets / Environment
All secrets come from AWS Secrets Manager in production — never hard-code.  
See [infra/secrets-template.json](infra/secrets-template.json) for the full list of required keys.  
See [docs/USER_CREDENTIALS_STORAGE.md](docs/USER_CREDENTIALS_STORAGE.md) for secret handling details.

### Default Admin (dev/init only)
```
Email: thiachan@pseudo-ai.com  Password: password123  Role: ADMIN
```
Created by `backend/init_db.py` — **do not use in production**.

---

## Frontend Conventions

- **Router**: Next.js App Router (not Pages router) — all routes in `src/app/`
- **API calls**: always via the singleton in [src/lib/api.ts](src/lib/api.ts) (handles auth headers)
- **Global state**: Zustand only (`authStore`, `themeStore`); use React Query for server state
- **Styling**: Tailwind CSS with class-based dark mode; primary color `#0ea5e9` (sky-500)
- **Path alias**: `@/*` → `./src/*`
- **Build output**: `standalone` mode — copy `.next/standalone`, `.next/static`, `public/` only
- **TypeScript**: strict mode; no `any` unless unavoidable

---

## Pitfalls

| Issue | Fix |
|-------|-----|
| ChromaDB emits noisy telemetry logs | Disabled in `main.py` via env vars — don't remove |
| Pydub `RuntimeWarning` | Filtered in `main.py` — do not remove the warning filter |
| WebSocket 16 MB limit | `--ws-max-size 16777216` in uvicorn args — required for large file uploads |
| `swcMinify: false` in next.config.js | Intentional — avoids SWC minification compatibility issues |
| CORS origins | Dev origins hard-coded in `app/core/config.py`; add new local ports there |
| DB migrations run on every startup | This is intentional and idempotent — do not change to one-shot |
| ChromaDB lives on EBS PVC | In EKS, never delete the `chroma-vector-db` PVC — data loss |

---

## Documentation

| File | Topic |
|------|-------|
| [README.md](README.md) | Quick start, stack overview |
| [REFERENCE_ARCHITECTURE.md](REFERENCE_ARCHITECTURE.md) | Full end-to-end architecture diagram |
| [docs/EKS_CA_DEPLOYMENT_GUIDE.md](docs/EKS_CA_DEPLOYMENT_GUIDE.md) | Complete EKS cluster setup walkthrough |
| [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) | API reference, DB schema, architecture detail |
| [docs/INSTALL.md](docs/INSTALL.md) | Local dev environment setup |
| [docs/EMAIL_VERIFICATION_SETUP.md](docs/EMAIL_VERIFICATION_SETUP.md) | SMTP / email verification config |
| [docs/RAG_IMPROVEMENT_ANALYSIS.md](docs/RAG_IMPROVEMENT_ANALYSIS.md) | RAG tuning, embedding analysis |
| [docs/WHY_IT_WASNT_WORKING.md](docs/WHY_IT_WASNT_WORKING.md) | Common debugging notes |
| [docs/PHASE2_IMPLEMENTATION_SUMMARY.md](docs/PHASE2_IMPLEMENTATION_SUMMARY.md) | Phase 2 features (RAG limits, QC agent) |
| [docs/USER_CREDENTIALS_STORAGE.md](docs/USER_CREDENTIALS_STORAGE.md) | Where all secrets live |
| [SEAGENT.md](SEAGENT.md) | SEAGENT feature documentation |
