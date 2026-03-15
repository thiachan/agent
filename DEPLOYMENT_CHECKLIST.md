# AGENT Platform — Deployment Checklist

**Environment: AWS EKS · ca-central-1 · Branch: EKS-CA-v1**

Use this checklist for every production deployment. The automated deploy script handles steps 4–7; the manual steps here are for reference and first-time setup.

---

## Prerequisites

### AWS & Kubernetes
- [ ] AWS CLI configured: `aws sts get-caller-identity` returns account `978027421922`
- [ ] kubectl context set: `kubectl config current-context` → `arn:aws:eks:ca-central-1:978027421922:cluster/agent-prod-ca`
- [ ] Logged in to ECR:
  ```bash
  aws ecr get-login-password --region ca-central-1 \
    | docker login --username AWS --password-stdin \
      978027421922.dkr.ecr.ca-central-1.amazonaws.com
  ```
- [ ] Docker running locally

### Code
- [ ] On branch `EKS-CA-v1`: `git checkout EKS-CA-v1 && git pull origin EKS-CA-v1`
- [ ] No uncommitted secrets in code (run `git status`)

---

## First-Time Cluster Setup

> **Only needed once per cluster lifetime.** Skip if cluster is already running.

- [ ] Bootstrap AWS infra (VPC, EKS, Aurora, S3, ECR):
  ```bash
  cd infra/scripts
  chmod +x bootstrap-ca.sh
  ./bootstrap-ca.sh
  ```
- [ ] Verify External Secrets Operator is installed and syncing:
  ```bash
  kubectl get externalsecret -n agent
  # STATUS should be "SecretSynced"
  ```
- [ ] Verify `app-secrets` k8s Secret exists:
  ```bash
  kubectl get secret app-secrets -n agent
  ```
- [ ] Run database migrations:
  ```bash
  kubectl exec -n agent deploy/backend -- python init_db.py
  ```
- [ ] Create admin user:
  ```bash
  kubectl exec -n agent deploy/backend -- python create_admin.py
  # Creates the admin account — see Secrets Manager or ask your admin for credentials
  ```

---

## Standard Deployment (Code Update)

### Deploy Both Services (Recommended)
```bash
cd /home/ubuntu/AGENT
./infra/scripts/deploy-ca.sh both
```

### Deploy Backend Only
```bash
./infra/scripts/deploy-ca.sh backend
```

### Deploy Frontend Only
```bash
./infra/scripts/deploy-ca.sh frontend
# ⚠️ NEXT_PUBLIC_API_URL=https://agent.alexcty.com is baked in at build time.
# Never deploy frontend without this build arg — chat will call localhost:8000.
```

---

## Post-Deployment Verification

### Pods Running
```bash
kubectl get pods -n agent
# All pods should be Running, no CrashLoopBackOff
```

### Rolling Restart Completed
```bash
kubectl rollout status deployment/backend -n agent
kubectl rollout status deployment/frontend -n agent
```

### Health Checks
```bash
# Backend
curl -s https://agent.alexcty.com/health | python3 -m json.tool
# Expected: {"status": "healthy", "db": "connected", "version": "..."}

# Frontend
curl -sI https://agent.alexcty.com | head -5
# Expected: HTTP/2 200
```

### Functional Smoke Test
- [ ] Open https://agent.alexcty.com in browser
- [ ] Login with admin credentials (see Secrets Manager `agent-prod-ca-app-secrets`)
- [ ] Send a chat message — response should arrive from Cisco GPT-4.1
- [ ] Upload a document — should appear in Documents list
- [ ] Check `/api/docs` — FastAPI Swagger UI should load

---

## Rollback

### Rollback to Previous Image
```bash
# Backend
kubectl rollout undo deployment/backend -n agent
kubectl rollout status deployment/backend -n agent

# Frontend
kubectl rollout undo deployment/frontend -n agent
kubectl rollout status deployment/frontend -n agent
```

### View Rollout History
```bash
kubectl rollout history deployment/backend -n agent
kubectl rollout history deployment/frontend -n agent
```

---

## Emergency Diagnostics

### Pod Logs
```bash
# Live logs — backend
kubectl logs -n agent deploy/backend -f --tail=100

# Live logs — frontend
kubectl logs -n agent deploy/frontend -f --tail=100

# Previous (crashed) container logs
kubectl logs -n agent deploy/backend --previous
```

### Pod Shell
```bash
kubectl exec -it -n agent deploy/backend -- /bin/bash
```

### Check HPA Status
```bash
kubectl get hpa -n agent
# REPLICAS column shows current pod count
```

### Check Secrets Sync
```bash
kubectl describe externalsecret app-secrets -n agent
# Look for "SecretSynced" status; check Last Refresh time
```

### Check Aurora Connectivity
```bash
kubectl exec -n agent deploy/backend -- python -c \
  "from app.core.database import engine; print(engine.execute('SELECT 1').scalar())"
```

---

## Secrets Reference

All secrets live in AWS Secrets Manager under `agent-prod-ca-app-secrets`.

To update a secret value:
```bash
aws secretsmanager update-secret \
  --secret-id agent-prod-ca-app-secrets \
  --secret-string '{"key": "new_value", ...}'
```

External Secrets Operator refreshes the k8s Secret every 1 hour. To force an immediate refresh:
```bash
kubectl annotate externalsecret app-secrets -n agent \
  force-sync=$(date +%s) --overwrite
```

---

## Key Endpoints

| Endpoint | Purpose |
|---|---|
| `https://agent.alexcty.com` | Application UI |
| `https://agent.alexcty.com/api/docs` | FastAPI Swagger |
| `https://agent.alexcty.com/health` | Health check |
| `https://agent.alexcty.com/api/admin/...` | Admin API endpoints |

---

*AGENT Platform · Deployment Checklist · EKS-CA-v1*
