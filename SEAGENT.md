# SEAGENT — Sales Engineer AI Agent Initiative

**SEAGENT** is a focused initiative within the AGENT platform that delivers purpose-built AI capabilities for Cisco's Global Sales & Systems Engineering (GSSO) team.

---

## Overview

SEAGENT extends AGENT's core RAG and document intelligence foundation into a dedicated workspace for Sales Engineers — providing instant access to knowledge, competitive intelligence, deal support, and continuous enablement, all in one place.

---

## Goals

| Goal | Description |
|---|---|
| **Faster Ramp** | Reduce SE time-to-productivity through AI-guided onboarding and contextual answers |
| **Deal Support** | Surface relevant case studies, battlecards, and technical docs during active opportunities |
| **Knowledge Retention** | Capture institutional knowledge and make it queryable across the SE community |
| **Continuous Enablement** | Keep SEs up to date on product launches, competitive changes, and best practices |

---

## Core Capabilities

- **AI Chat (AGENT)** — RAG-powered Q&A grounded in curated SE knowledge bases
- **SE Onboarding Playbook** — 4-mission interactive guide (Ninja → Samurai → Daimyo → Sensei)
- **Bookmarks** — Save and resurface key resources during customer engagements
- **Incubation Lab** — Experimental features and new AI tools before general availability
- **Knowledge Base** — Admin-managed document repository (admin access required)

---

## Roadmap

### Phase 1 — Foundation ✅
- AGENT chat with RAG
- SE Onboarding Playbook
- Document upload & management
- User management & authentication

### Phase 2 — Enablement ✅
- Bookmarks
- Incubation Lab
- Email verification & onboarding improvements

### Phase 3 — SEAGENT *(current)*
- Dedicated SEAGENT workspace and landing page
- SE-specific knowledge workflows
- Deeper deal-stage AI assistance

### Phase 4 — Scale *(planned)*
- Multi-team support
- Advanced analytics and usage insights
- Integration with Cisco CRM / Salesforce

---

## Access

| Environment | URL |
|---|---|
| Production | https://agent.alexcty.com |
| Development | https://agent-dev.alexcty.com |

---

## Stack

Built on the AGENT platform:

```
Next.js 14 · FastAPI · ChromaDB · Aurora PostgreSQL
AWS EKS (ca-central-1) · S3 · Secrets Manager
```

See [README.md](README.md) for full architecture details.

---

## Team

**Owner:** GSSO Engineering — Cisco  
**Platform:** [AGENT](README.md)  
**Branch:** `EKS-CA-v1`
