# EKS ca-central-1 Deployment Guide
Full instructions — from zero to production — for migrating the Agent platform
from the us-west-1 EC2 to a ca-central-1 EKS cluster with auto-scale and
auto-heal, while keeping the EC2 live until DNS cutover.

---

## Overview

| What | Where |
|---|---|
| Cluster | `agent-prod-ca` in `ca-central-1` |
| Namespace | `agent` |
| Backend | FastAPI — ECR → EKS deployment |
| Frontend | Next.js — ECR → EKS deployment |
| Relational DB | Aurora PostgreSQL Serverless v2 |
| Vector DB | ChromaDB on EBS PVC (`chroma-vector-db`) |
| File storage | S3 uploads bucket |
| Secrets | AWS Secrets Manager → External Secrets Operator → k8s Secret `app-secrets` |
| CI/CD | GitHub Actions `deploy-ca.yml` — auto-deploys on every push to `main` |

The us-west-1 EC2 continues running untouched throughout. You only cut DNS
at the very end once everything is verified.

---

## Phase 0 — Install Prerequisites on the EC2

All commands run on the **us-west-1 EC2** itself (`ssh` in first).
The codebase is already there at `/home/ubuntu/AGENT`.

```bash
# 1. Terraform
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common curl unzip
wget -O- https://apt.releases.hashicorp.com/gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y terraform

# 2. kubectl (Linux amd64 — correct for EC2)
curl -Lo /tmp/kubectl "https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl"
chmod +x /tmp/kubectl && sudo mv /tmp/kubectl /usr/local/bin/kubectl

# 3. Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 4. AWS CLI (check first — probably already installed)
aws --version || (
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip /tmp/awscliv2.zip -d /tmp
  sudo /tmp/aws/install
)

# 5. pgloader (needed for Phase 4 — DB migration)
sudo apt-get install -y pgloader sqlite3

# Verify everything
terraform version && kubectl version --client && helm version --short \
  && aws --version && pgloader --version && sqlite3 --version
```

---

## Phase 1 — AWS Credentials

The EC2's current IAM instance role only has app-level permissions (S3, Secrets
Manager, etc.). To create EKS, VPC, RDS, and IAM roles, you need admin-level
credentials. Use one of these two approaches:

**Option A — Temporary environment variables (simplest, credentials gone when session ends):**
```bash
export AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxxxxx
export AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export AWS_DEFAULT_REGION=ca-central-1
aws sts get-caller-identity   # confirm it shows the right account
```

**Option B — Attach AdministratorAccess to the EC2 IAM role temporarily:**
1. Go to AWS Console → EC2 → select your instance → Actions → Security → Modify IAM role
2. Attach a role that has `AdministratorAccess`
3. Run bootstrap
4. Detach the permissive role and re-attach the original restricted role

---

## Phase 2 — Fill In Secrets Before Bootstrap

### 2a. Set the RDS password in terraform.tfvars

```bash
cd /home/ubuntu/AGENT
nano infra/terraform-ca/terraform.tfvars
```

Replace:
```
db_password = "REPLACE_STRONG_PASSWORD_HERE"
```
With a strong password (16+ chars, mixed case + numbers + symbols). Example:
```
db_password = "MyStr0ng!Pass#2026"
```
> **Warning:** do not commit this to git. Add `*.tfvars` to `.gitignore` if not already there.

### 2b. Prepare the Secrets Manager JSON

Copy the template and fill in your real values:
```bash
cp infra/secrets-template.json /tmp/secrets-prod-ca.json
nano /tmp/secrets-prod-ca.json
```

Fill in every `REPLACE` field. The file looks like this — here is what each key means:

| Key | What to put |
|---|---|
| `DATABASE_URL` | Leave as-is for now — you'll update after Phase 3 with the real RDS endpoint |
| `SECRET_KEY` | Run `python3 -c "import secrets; print(secrets.token_hex(32))"` to generate |
| `OPENAI_API_KEY` | Your OpenAI API key (`sk-proj-...`) |
| `CISCO_CLIENT_ID` | Cisco WebEx OAuth client ID |
| `CISCO_CLIENT_SECRET` | Cisco WebEx OAuth client secret |
| `CISCO_ENDPOINT` | `https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions` (already set) |
| `CISCO_APPKEY` | Your Cisco app key |
| `PRESENTON_API_URL` | Presenton API base URL |
| `PRESENTON_API_KEY` | Presenton API key |
| `MAIL_USERNAME` | SMTP username (e.g. Gmail address) |
| `MAIL_PASSWORD` | SMTP app password |
| `MAIL_FROM` | Sender email |
| `NEXT_PUBLIC_API_URL` | Leave as `https://REPLACE_ALB_OR_DOMAIN/api` for now — update after Phase 3 |
| `FRONTEND_URL` | Leave as `https://REPLACE_ALB_OR_DOMAIN` for now — update after Phase 3 |

> Leave `DATABASE_URL`, `NEXT_PUBLIC_API_URL`, and `FRONTEND_URL` as placeholders
> for now. You will update them in Phase 3 once the ALB and RDS endpoints are known.

---

## Phase 3 — Bootstrap (Run Once)

This single script:
1. Creates the Terraform S3 state bucket and DynamoDB lock table in ca-central-1
2. Runs `terraform init` and `terraform apply` (~15 minutes)
3. Configures `kubectl` for the new cluster
4. Installs metrics-server, Cluster Autoscaler, AWS Load Balancer Controller, External Secrets Operator via Helm
5. Applies all Kubernetes manifests (namespace, StorageClass, PVC, deployments, services, HPAs, ingress)

```bash
cd /home/ubuntu/AGENT
./infra/scripts/bootstrap-ca.sh
```

Watch the output — it takes about 15–20 minutes total. At the end you will see:
```
[OK]    Bootstrap complete!
```
Followed by a table of nodes, pods, and the ingress ALB DNS name.

### After bootstrap — capture the outputs

```bash
cd infra/terraform-ca
terraform output
```

Note down these values — you need them for the next steps:

```
eks_cluster_name       = "agent-prod-ca"
ecr_backend_url        = "ACCOUNT_ID.dkr.ecr.ca-central-1.amazonaws.com/agent-prod-ca-backend"
ecr_frontend_url       = "ACCOUNT_ID.dkr.ecr.ca-central-1.amazonaws.com/agent-prod-ca-frontend"
rds_endpoint           = "agent-prod-ca-aurora.cluster-xxxx.ca-central-1.rds.amazonaws.com"
s3_uploads_bucket      = "agent-prod-ca-uploads-ACCOUNT_ID"
s3_generated_bucket    = "agent-prod-ca-generated-ACCOUNT_ID"
github_actions_user_name = "agent-prod-ca-github-actions"
```

---

## Phase 4 — Update Secrets with Real Values

Now that you have the real RDS endpoint and ALB URL, update Secrets Manager:

```bash
# Get the ALB URL
ALB=$(kubectl get ingress agent-ingress -n agent \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ALB: $ALB"

# Get RDS endpoint
RDS=$(cd infra/terraform-ca && terraform output -raw rds_endpoint)
echo "RDS: $RDS"
```

Edit `/tmp/secrets-prod-ca.json` and replace the three placeholder values:
```json
"DATABASE_URL": "postgresql+psycopg2://agentuser:YOUR_DB_PASSWORD@RDS_ENDPOINT:5432/agentdb",
"NEXT_PUBLIC_API_URL": "http://ALB_HOSTNAME/api",
"FRONTEND_URL": "http://ALB_HOSTNAME"
```

Push the updated secrets to Secrets Manager:
```bash
aws secretsmanager put-secret-value \
  --secret-id agent-prod-ca-app-secrets \
  --secret-string file:///tmp/secrets-prod-ca.json \
  --region ca-central-1

# IMPORTANT: delete the file after — never leave credentials on disk
rm /tmp/secrets-prod-ca.json
```

Force the External Secrets Operator to re-sync immediately:
```bash
kubectl annotate externalsecret app-secrets -n agent \
  force-sync=$(date +%s) --overwrite
kubectl get externalsecret -n agent   # should show SecretSynced = True
```

Restart the backend to pick up the new DATABASE_URL:
```bash
kubectl rollout restart deployment/backend -n agent
kubectl rollout status deployment/backend -n agent --timeout=120s
```

---

## Phase 5 — Push the First Docker Images

GitHub Actions will handle this on every `git push` going forward, but you need
to do a manual push once to get the `latest` tags into ECR before the pods can
start successfully.

```bash
# Set these from terraform outputs
ECR_BACKEND=$(cd infra/terraform-ca && terraform output -raw ecr_backend_url)
ECR_FRONTEND=$(cd infra/terraform-ca && terraform output -raw ecr_frontend_url)

aws ecr get-login-password --region ca-central-1 \
  | docker login --username AWS --password-stdin "$ECR_BACKEND"

# Build and push backend
docker build -f backend/Dockerfile -t "${ECR_BACKEND}:latest" ./backend
docker push "${ECR_BACKEND}:latest"

# Build and push frontend
docker build -f Dockerfile \
  --build-arg NEXT_BUILD_STANDALONE=true \
  -t "${ECR_FRONTEND}:latest" .
docker push "${ECR_FRONTEND}:latest"

# Update the running deployments to use the new images
kubectl set image deployment/backend  backend="${ECR_BACKEND}:latest"  -n agent
kubectl set image deployment/frontend frontend="${ECR_FRONTEND}:latest" -n agent

kubectl rollout status deployment/backend  -n agent --timeout=300s
kubectl rollout status deployment/frontend -n agent --timeout=300s
```

---

## Phase 6 — Set Up GitHub Actions (Automated CI/CD)

After this, every `git push` to `main` automatically builds, pushes, and
deploys to EKS.

### 6a. Create the GitHub Actions IAM access key

```bash
GH_USER=$(cd infra/terraform-ca && terraform output -raw github_actions_user_name)
aws iam create-access-key --user-name "$GH_USER"
```

This outputs an `AccessKeyId` and `SecretAccessKey`. Copy both immediately —
the secret is shown only once.

### 6b. Add GitHub Secrets

Go to: **GitHub → your repo → Settings → Secrets and variables → Actions → New repository secret**

Add these 5 secrets:

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID_CA` | `AccessKeyId` from the command above |
| `AWS_SECRET_ACCESS_KEY_CA` | `SecretAccessKey` from the command above |
| `ECR_BACKEND_CA` | `terraform output ecr_backend_url` |
| `ECR_FRONTEND_CA` | `terraform output ecr_frontend_url` |
| `NEXT_PUBLIC_API_URL_CA` | Your ALB or domain URL (e.g. `http://ALB_DNS`) |

### 6c. Create the GitHub Actions environment

Go to: **GitHub → Settings → Environments → New environment**
Name it exactly: `production-ca`

No additional protection rules required unless you want manual approval gates
before EKS deployments.

### 6d. Test it

```bash
git add .
git commit -m "chore: trigger first EKS ca-central-1 deployment"
git push origin main
```

Go to **GitHub → Actions** and watch both workflows run in parallel:
- `deploy.yml` → deploys to us-west-1 EC2 (unchanged)
- `deploy-ca.yml` → builds images, pushes to ECR, rolls out to EKS

---

## Phase 7 — Migrate All Data

Run this after Phase 5 (images are working) and before Phase 8 (DNS cutover).
It migrates all three data stores from the EC2:

```bash
export EC2_HOST=<your-us-west-1-ec2-public-ip>
export EC2_USER=ubuntu
export EC2_KEY=~/.ssh/your-ec2-key.pem

./infra/scripts/migrate-db-ca.sh
```

The script runs three parts in sequence:

| Part | What it does |
|---|---|
| **Part 1** — Relational DB | Briefly pauses EC2 backend → copies `intranet.db` → resumes EC2 → creates Aurora schema → pgloader moves all users, chat history, bookmarks to Aurora |
| **Part 2** — ChromaDB | Streams `vector_db/` from EC2 → S3 staging → k8s Job extracts to EBS PVC at `/app/vector_db/` → cleans staging |
| **Part 3** — Uploads | Streams `uploads/` from EC2 → S3 staging → k8s Job syncs all files to `s3://<uploads-bucket>/uploads/` → cleans staging |

At the end it prints a verification checklist and the counts of migrated users.

> **Safe to re-run.** Run it once a week before cutover to keep the data in
> sync, then run it one final time right before you change DNS.

---

## Phase 8 — HTTPS / ACM Certificate (Optional but recommended)

If you have a domain, set up HTTPS before cutover.

```bash
# 1. Request a certificate in ACM (must be in ca-central-1)
aws acm request-certificate \
  --domain-name "yourdomain.com" \
  --subject-alternative-names "*.yourdomain.com" \
  --validation-method DNS \
  --region ca-central-1

# 2. Get the CNAME validation records
aws acm describe-certificate \
  --certificate-arn <arn-from-above> \
  --region ca-central-1 \
  --query 'Certificate.DomainValidationOptions'

# 3. Add those CNAME records in your DNS registrar
# 4. Wait for validation (5–30 minutes):
aws acm wait certificate-validated \
  --certificate-arn <arn> --region ca-central-1

# 5. Update the ingress with the certificate ARN:
kubectl annotate ingress agent-ingress -n agent \
  "alb.ingress.kubernetes.io/certificate-arn=<arn>" --overwrite
kubectl annotate ingress agent-ingress -n agent \
  "alb.ingress.kubernetes.io/ssl-redirect=443" --overwrite

# 6. Update terraform.tfvars for future applies:
#    domain_name         = "yourdomain.com"
#    acm_certificate_arn = "arn:aws:acm:ca-central-1:..."
```

---

## Phase 9 — Verify Before DNS Cutover

Run these checks. Everything must pass before you touch DNS.

```bash
# 1. All pods Running (should show 2+ backend, 2+ frontend, all Running)
kubectl get pods -n agent

# 2. HPAs active
kubectl get hpa -n agent

# 3. Secrets synced
kubectl get externalsecret -n agent  # SecretSynced = True

# 4. ChromaDB PVC bound
kubectl get pvc -n agent  # STATUS = Bound

# 5. Test the ALB directly
ALB=$(kubectl get ingress agent-ingress -n agent \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

curl -s "http://${ALB}/health"            # should return {"status":"healthy"}
curl -s "http://${ALB}/api/docs" | head   # should return HTML

# 6. Test user login (confirm DB migration worked)
curl -X POST "http://${ALB}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"<your-admin-user>","password":"<your-password>"}' \
  | python3 -m json.tool

# 7. Test a RAG query (confirm ChromaDB migration worked)
# Log in through the UI at http://$ALB and ask the assistant a question
# that would require retrieval from your document collection.
```

---

## Phase 10 — DNS Cutover

Only do this after all Phase 9 checks pass.

**Run `migrate-db-ca.sh` one final time** to capture any writes since the last run:
```bash
./infra/scripts/migrate-db-ca.sh
```

**Then immediately switch DNS** (do both at the same time to minimise downtime):

In your DNS registrar:
- Change your `A`/`CNAME` record from the EC2 IP to the ALB hostname
- Set a low TTL first (e.g., 60 seconds) — you can raise it back after cutover is stable

```
Before: yourdomain.com → <ec2-public-ip>
After:  yourdomain.com → <alb-hostname>.ca-central-1.elb.amazonaws.com  (CNAME)
```

Wait for TTL to expire, then verify:
```bash
dig yourdomain.com
curl -s https://yourdomain.com/health
```

---

## Phase 11 — Post-Cutover

### Keep the EC2 alive temporarily
Leave the EC2 running for at least one week after cutover as a fallback.
If anything is wrong, you can revert DNS to the EC2 IP instantly.

### Disable the EC2 deployment workflow once validated
Edit `.github/workflows/deploy.yml`, comment out the trigger, and push:
```yaml
on:
  # push:
  #   branches: [main]
  workflow_dispatch:   # manual only
```

### Stop the EC2 (not terminate — stop, in case you need the disk)
AWS Console → EC2 → select instance → Instance State → Stop

---

## Day-to-Day Development After Cutover

### Deploying a code change
```bash
# Edit code normally in VS Code
git add .
git commit -m "feat: your feature"
git push origin main
# deploy-ca.yml runs automatically — done.
```

### Watching a deployment roll out
```bash
kubectl rollout status deployment/backend -n agent --timeout=300s
```

### Viewing live logs
```bash
kubectl logs -n agent -l app=backend  -f
kubectl logs -n agent -l app=frontend -f
```

### Shelling into a pod
```bash
kubectl exec -it -n agent deploy/backend -- /bin/bash
```

### Rolling back a bad deploy
```bash
kubectl rollout undo deployment/backend  -n agent
kubectl rollout undo deployment/frontend -n agent
```

### Checking auto-scale activity
```bash
kubectl get hpa -n agent -w          # watch pod scale events
kubectl get nodes -w                  # watch node add/remove
kubectl top pods -n agent             # current CPU/memory per pod
```

### Seeing all events (errors, scheduling issues)
```bash
kubectl get events -n agent --sort-by='.lastTimestamp' | tail -30
```

### Applying a manifest change (e.g., HPA thresholds)
```bash
# Edit the file then:
kubectl apply -f infra/k8s/backend/hpa.yaml
```

---

## VS Code Kubernetes Extension Setup

Install once on your Mac:
```
Extensions: ms-kubernetes-tools.vscode-kubernetes-tools
Extensions: amazonwebservices.aws-toolkit-vscode
```

Connect to the cluster from your Mac terminal:
```bash
aws eks update-kubeconfig --name agent-prod-ca --region ca-central-1
```

The Kubernetes extension sidebar will then show the `agent-prod-ca` cluster.
You can right-click any pod to view logs, open a terminal, or describe it —
without typing any `kubectl` commands.

Switch between the old EC2 context and EKS from the VS Code status bar (bottom-left).

---

## Key Resource Reference

| Resource | Name |
|---|---|
| EKS cluster | `agent-prod-ca` |
| K8s namespace | `agent` |
| Backend deployment | `deployment/backend` |
| Frontend deployment | `deployment/frontend` |
| ChromaDB PVC | `chroma-vector-db` |
| K8s secret | `app-secrets` |
| Secrets Manager secret | `agent-prod-ca-app-secrets` |
| ECR backend | `ACCOUNT_ID.dkr.ecr.ca-central-1.amazonaws.com/agent-prod-ca-backend` |
| ECR frontend | `ACCOUNT_ID.dkr.ecr.ca-central-1.amazonaws.com/agent-prod-ca-frontend` |
| Aurora DB | `agent-prod-ca-aurora` (cluster identifier) |
| DB name / user | `agentdb` / `agentuser` |
| S3 uploads bucket | `agent-prod-ca-uploads-ACCOUNT_ID` |
| Terraform state bucket | `agent-tfstate-ca-ACCOUNT_ID` |
| GitHub Actions workflow | `.github/workflows/deploy-ca.yml` |
| Bootstrap script | `infra/scripts/bootstrap-ca.sh` |
| Data migration script | `infra/scripts/migrate-db-ca.sh` |
| Terraform workspace | `infra/terraform-ca/` |
| K8s manifests | `infra/k8s/` |
