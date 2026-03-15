# AGENT Platform — Installation Guide

**Environment: AWS EKS · ca-central-1**

> For day-to-day deploys after the cluster is running, jump straight to [Standard Deployment](#standard-deployment).

---

## Architecture Summary

The platform runs entirely on AWS. There is no local setup to run in production — everything is containerized on EKS.

| Layer | Technology |
|---|---|
| Compute | AWS EKS (Kubernetes) — `agent-prod-ca`, `ca-central-1` |
| Database | Aurora PostgreSQL Serverless v2 |
| Vector DB | ChromaDB on EBS (persistent volume) |
| File Storage | S3 (uploads + generated files) |
| Secrets | AWS Secrets Manager → External Secrets Operator |
| DNS / CDN | Cloudflare → AWS ALB |
| Images | AWS ECR |

---

## Machine Requirements (Dev / Deploy Machine)

You need one machine with:
- AWS CLI v2
- docker (for building and pushing images)
- kubectl
- git
- Python 3.11+ (optional — for local backend testing only)

```bash
# Ubuntu/Debian quick install
sudo apt-get update && sudo apt-get install -y git docker.io python3 python3-pip awscli
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

---

## First-Time Cluster Bootstrap

### 1. Clone the repository
```bash
git clone <repo-url>
cd AGENT
git checkout EKS-CA-v1
```

### 2. Configure AWS credentials
```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region:        ca-central-1
# Default output:        json
```

Verify:
```bash
aws sts get-caller-identity
# Should return account: 978027421922
```

### 3. Bootstrap AWS infrastructure (once)
```bash
chmod +x infra/scripts/bootstrap-ca.sh
./infra/scripts/bootstrap-ca.sh
```

This script provisions:
- VPC + subnets (if not existing)
- EKS cluster `agent-prod-ca`
- Aurora PostgreSQL cluster
- S3 buckets (`uploads` and `generated`)
- ECR repositories
- IAM roles (IRSA for External Secrets, S3, ECR)
- External Secrets Operator installation

### 4. Confirm kubeconfig is set
```bash
aws eks update-kubeconfig --region ca-central-1 --name agent-prod-ca
kubectl get nodes
# Should show m5.large nodes in Ready state
```

### 5. Deploy the application (first time)
```bash
./infra/scripts/deploy-ca.sh both
```

This builds backend and frontend Docker images, pushes to ECR, and triggers rolling restarts on EKS.

### 6. Run database migrations
```bash
kubectl exec -n agent deploy/backend -- python init_db.py
```

### 7. Create the admin user
```bash
kubectl exec -n agent deploy/backend -- python create_admin.py
  # Creates the admin account — change the password immediately after first login.
```

### 8. Verify
```bash
kubectl get pods -n agent
# All pods Running

curl -s https://agent.alexcty.com/health
# {"status": "healthy"}
```

---

## Standard Deployment

After initial setup, all updates are one command:

```bash
git pull origin EKS-CA-v1
./infra/scripts/deploy-ca.sh both      # rebuild + redeploy both services
./infra/scripts/deploy-ca.sh backend   # backend only
./infra/scripts/deploy-ca.sh frontend  # frontend only
```

> **Important:** The frontend must always be built with `NEXT_PUBLIC_API_URL=https://agent.alexcty.com` baked in at Docker build time. The `deploy-ca.sh` script handles this automatically. Do not build the frontend image manually without this arg.

---

## Local Development (Optional)

For local backend iteration only:

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Copy secrets from Secrets Manager for local use
aws secretsmanager get-secret-value \
  --secret-id agent-prod-ca-app-secrets \
  --query SecretString --output text > .env.local
# Edit .env.local to set DATABASE_URL to a local Postgres or tunnel to Aurora

uvicorn app.main:app --reload --port 8000
```

For local frontend:
```bash
# At root
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Updating Secrets

All secrets are managed in AWS Secrets Manager under `agent-prod-ca-app-secrets`.

To add or update a key:
```bash
# Fetch current secret JSON
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id agent-prod-ca-app-secrets \
  --query SecretString --output text)

# Edit and update
echo "$CURRENT" | python3 -c "import json,sys; d=json.load(sys.stdin); d['NEW_KEY']='value'; print(json.dumps(d))" \
  | aws secretsmanager put-secret-value \
      --secret-id agent-prod-ca-app-secrets \
      --secret-string file:///dev/stdin
```

The External Secrets Operator will sync the new value to the k8s Secret within 1 hour, or force it immediately:
```bash
kubectl annotate externalsecret app-secrets -n agent force-sync=$(date +%s) --overwrite
kubectl rollout restart deployment/backend deployment/frontend -n agent
```

---

## Teardown

> **Destructive — this deletes all AWS resources including the database.**

```bash
cd infra/terraform-ca
terraform destroy
```

---

*AGENT Platform · Installation Guide · EKS-CA-v1*
