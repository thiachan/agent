# EC2 → AWS ECS Auto-Scaling Migration
## Step-by-Step Runbook — EC2 Stays Live Throughout

> **Guiding principle:** At every single step, the EC2 instance remains fully operational and serving real traffic. The ECS environment is built in parallel. The only user-facing event is a DNS record change at the very end, which takes under 60 seconds.

---

## How the pieces connect (and what could break)

Before touching anything, understand the current runtime dependencies:

```
Browser
  └─► Next.js (port 3000)
        └─► FastAPI (port 8000)
              ├─► SQLite  (intranet.db on local disk)          ← STATEFUL
              ├─► ChromaDB  (./vector_db/ on local disk)       ← STATEFUL
              ├─► ./uploads/{user_id}_{filename}               ← STATEFUL
              ├─► ./temp_generated_files/{uuid}.{ext}          ← STATEFUL
              ├─► Cisco GPT-4.1 API  (external, stateless)
              ├─► OpenAI API  (external, stateless)
              └─► Presenton API  (internal ECS, stateless)
```

**The three stateful local-disk dependencies are the only things that must be migrated before ECS can run correctly.** Everything else (JWT auth, LLM calls, Presenton) is already stateless and works unchanged on ECS.

### What breaks if you skip a step:

| If you run ECS without migrating... | What breaks |
|---|---|
| SQLite → RDS | Users can't log in (sessions), documents lost, chat history gone |
| uploads/ → S3 | File uploads appear to succeed but document processing fails silently; existing documents return 404 |
| temp_generated_files/ → S3 | Generated PPT/PDF/MP3 files return 404 when downloaded; the `FileResponse` in `generate.py` points to a path that doesn't exist on the new container |
| ChromaDB → shared storage | RAG chat returns empty results or errors; each ECS task has its own isolated empty vector DB |

---

## Prerequisites — Install on EC2 once

```bash
# Terraform (infrastructure as code)
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform -y
terraform version   # must be >= 1.7

# Docker
sudo apt install docker.io -y
sudo usermod -aG docker ubuntu
newgrp docker
docker ps   # must work without sudo

# PostgreSQL client (for data migration)
sudo apt install postgresql-client -y

# pgloader (SQLite → PostgreSQL migration)
sudo apt install pgloader -y

# AWS CLI (should already be present; if not:)
sudo apt install awscli -y
aws --version

# Python dependencies for migration script
cd /home/ubuntu/AGENT/backend
pip install psycopg2-binary pgvector 2>/dev/null || true
```

---

## Phase 0 — Fix GitHub PAT & Push Branch (10 minutes)

Your local commit is ready. The push is blocked because your GitHub Personal Access Token is missing the `workflow` scope (needed to push `.github/workflows/`).

**Fix the PAT scope:**
1. Go to: `https://github.com/settings/tokens`
2. Click your token → **Edit** → check **`workflow`** → **Update token**
3. Copy the new token value

**Update the stored credential on EC2:**
```bash
# Clear the old credential
git credential reject <<'EOF'
protocol=https
host=github.com
EOF

# Store the new one (replace YOUR_TOKEN with the actual token)
git credential approve <<'EOF'
protocol=https
host=github.com
username=thiachan
password=YOUR_TOKEN
EOF

# Push
git push origin ecs-migration
```

**Verify on GitHub:** `https://github.com/thiachan/agent` → branches → `ecs-migration` should have all 14 new files.

---

## Phase 1 — Provision AWS Infrastructure with Terraform (45–60 minutes)

> EC2 is completely unaffected by this phase. You are only creating new AWS resources.

### Step 1.1 — Bootstrap Terraform remote state (one-time, ~5 minutes)

Terraform needs an S3 bucket to store its state file. Run these from EC2:

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $AWS_ACCOUNT_ID"

# Create state bucket (versioned, encrypted)
aws s3 mb s3://agent-tfstate-${AWS_ACCOUNT_ID} --region us-west-1
aws s3api put-bucket-versioning \
  --bucket agent-tfstate-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name agent-tfstate-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-1

echo "State infrastructure ready"
```

### Step 1.2 — Update Terraform backend config

```bash
cd /home/ubuntu/AGENT/infra/terraform

# Replace placeholder with your real account ID
sed -i "s/agent-tfstate-REPLACE_WITH_ACCOUNT_ID/agent-tfstate-${AWS_ACCOUNT_ID}/" versions.tf

# Verify
grep "bucket" versions.tf
```

### Step 1.3 — Create a `terraform.tfvars` file

```bash
cat > /home/ubuntu/AGENT/infra/terraform/terraform.tfvars <<EOF
aws_region   = "us-west-1"
project      = "agent"
environment  = "prod"

# RDS password — use a strong password (16+ chars, mixed case + symbols)
db_password  = "REPLACE_WITH_STRONG_PASSWORD"

# Leave empty for now — add your domain after ECS is verified
domain_name         = ""
acm_certificate_arn = ""
EOF
```

> ⚠️ **Never commit `terraform.tfvars`** — it contains the DB password. It is already listed in `.gitignore`.

### Step 1.4 — Initialize and apply Terraform

```bash
cd /home/ubuntu/AGENT/infra/terraform

terraform init      # downloads AWS provider, connects to S3 backend
terraform plan      # review what will be created — should be ~60 new resources
terraform apply     # type "yes" when prompted
```

**This takes 15–25 minutes.** Aurora RDS provisioning is the slow step. Expected output at the end:

```
Apply complete! Resources: 62 added, 0 changed, 0 destroyed.

Outputs:
  alb_dns_name          = "agent-prod-alb-xxxx.us-west-1.elb.amazonaws.com"
  ecr_backend_url       = "123456789.dkr.ecr.us-west-1.amazonaws.com/agent-prod-backend"
  ecr_frontend_url      = "123456789.dkr.ecr.us-west-1.amazonaws.com/agent-prod-frontend"
  rds_endpoint          = "agent-prod-aurora.cluster-xxxx.us-west-1.rds.amazonaws.com"
  s3_uploads_bucket     = "agent-prod-uploads-123456789"
  s3_generated_bucket   = "agent-prod-generated-123456789"
  secrets_manager_arn   = "arn:aws:secretsmanager:us-west-1:123456789:secret:agent-prod-app-secrets-xxxx"
  ecs_cluster_name      = "agent-prod-cluster"
```

**Save these output values — you'll need them in every subsequent step.**

```bash
# Save outputs to a local file for easy reference
terraform output > /home/ubuntu/AGENT/infra/tf-outputs.txt
cat /home/ubuntu/AGENT/infra/tf-outputs.txt
```

---

## Phase 2 — Populate Secrets Manager (15 minutes)

> EC2 still serving all traffic.

The ECS containers will read all secrets from AWS Secrets Manager at startup. You need to populate it with the real values from your current `.env`.

```bash
# Pull your current .env values
cat /home/ubuntu/AGENT/backend/.env

# Get the values you need from Terraform outputs
RDS_ENDPOINT=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw rds_endpoint)
S3_UPLOADS=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw s3_uploads_bucket)
S3_GENERATED=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw s3_generated_bucket)
ALB_DNS=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw alb_dns_name)
SECRETS_ARN=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw secrets_manager_arn)
DB_PASS="REPLACE_WITH_SAME_PASSWORD_YOU_SET_IN_TFVARS"

# Generate a strong SECRET_KEY
NEW_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Write the secrets JSON (fill in your real values from .env)
cat > /tmp/agent-secrets.json <<SECRETSEOF
{
  "DATABASE_URL":        "postgresql+psycopg2://agentuser:${DB_PASS}@${RDS_ENDPOINT}:5432/agentdb",
  "SECRET_KEY":          "${NEW_SECRET_KEY}",
  "OPENAI_API_KEY":      "sk-proj-YOUR_OPENAI_API_KEY",
  "CISCO_CLIENT_ID":     "YOUR_CISCO_CLIENT_ID",
  "CISCO_CLIENT_SECRET": "YOUR_CISCO_CLIENT_SECRET",
  "CISCO_ENDPOINT":      "https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions",
  "CISCO_APPKEY":        "YOUR_CISCO_APPKEY",
  "PRESENTON_API_URL":   "http://172.31.11.64:80",
  "PRESENTON_API_KEY":   "",
  "PRESENTON_REQUIRE_AUTH": "false",
  "PRESENTON_MAX_SLIDES": "12",
  "MAIL_USERNAME":       "your-email@gmail.com",
  "MAIL_PASSWORD":       "your-app-password",
  "MAIL_FROM":           "noreply@agent.com",
  "MAIL_SERVER":         "smtp.gmail.com",
  "MAIL_PORT":           "587",
  "NEXT_PUBLIC_API_URL": "https://${ALB_DNS}/api",
  "FRONTEND_URL":        "https://${ALB_DNS}",
  "OPENAI_TTS_VOICE_HOST":  "nova",
  "OPENAI_TTS_VOICE_GUEST": "onyx"
}
SECRETSEOF

# Push to Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id "$SECRETS_ARN" \
  --secret-string file:///tmp/agent-secrets.json \
  --region us-west-1

# Clean up — never leave secrets in /tmp
rm /tmp/agent-secrets.json

echo "✅ Secrets Manager populated"
```

---

## Phase 3 — Migrate Database: SQLite → RDS Aurora (30 minutes)

> EC2 still serving all traffic. You will switch EC2 to use RDS at the end of this phase while ECS is still not deployed.

### Step 3.1 — Allow your EC2 to reach RDS

The RDS security group only allows traffic from ECS tasks by default. Temporarily add your EC2's private IP:

```bash
EC2_PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
RDS_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=agent-prod-rds-sg" \
  --query 'SecurityGroups[0].GroupId' --output text --region us-west-1)

aws ec2 authorize-security-group-ingress \
  --group-id "$RDS_SG_ID" \
  --protocol tcp \
  --port 5432 \
  --cidr "${EC2_PRIVATE_IP}/32" \
  --region us-west-1

echo "EC2 ($EC2_PRIVATE_IP) can now reach RDS"
```

### Step 3.2 — Create schema on RDS

```bash
RDS_ENDPOINT=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw rds_endpoint)
DB_PASS="YOUR_DB_PASSWORD"
DB_URL="postgresql+psycopg2://agentuser:${DB_PASS}@${RDS_ENDPOINT}:5432/agentdb"

# Enable pgvector extension (for future vector storage)
psql "postgresql://agentuser:${DB_PASS}@${RDS_ENDPOINT}:5432/agentdb" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || echo "pgvector not available — skip"

# Create all tables using the existing init script
cd /home/ubuntu/AGENT/backend
DATABASE_URL="$DB_URL" python3 init_db.py

echo "✅ Tables created on RDS"
```

### Step 3.3 — Migrate existing data from SQLite

```bash
cd /home/ubuntu/AGENT/backend

python3 - <<'PYEOF'
import os, sqlite3, sqlalchemy as sa
from sqlalchemy import text

src_path = "intranet.db"
dest_url = os.environ["DATABASE_URL"]

if not os.path.exists(src_path):
    print("No SQLite DB found — skipping data migration (fresh install)")
    exit(0)

src = sqlite3.connect(src_path)
src.row_factory = sqlite3.Row
engine = sa.create_engine(dest_url)

# Get all user tables (skip sqlite internal tables)
tables = [r[0] for r in src.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()]
print(f"Tables to migrate: {tables}")

with engine.begin() as conn:
    for table in tables:
        rows = src.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: empty — skipping")
            continue
        data = [dict(r) for r in rows]
        cols = list(data[0].keys())
        col_list = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        # Clear destination and re-insert (idempotent — safe to re-run)
        conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        conn.execute(text(f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'), data)
        print(f"  {table}: {len(data)} rows migrated ✅")

src.close()
print("\n✅ SQLite → RDS migration complete")
PYEOF
```

### Step 3.4 — Switch EC2 backend to use RDS (zero downtime)

```bash
# Update .env on EC2 to point at RDS
sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg2://agentuser:${DB_PASS}@${RDS_ENDPOINT}:5432/agentdb|" \
  /home/ubuntu/AGENT/backend/.env

# Restart backend (choose whichever matches how you run it)
sudo systemctl restart agent-backend 2>/dev/null || \
  pkill -f "uvicorn main:app" && \
  cd /home/ubuntu/AGENT/backend && \
  nohup uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait 5 seconds and verify
sleep 5
curl -s http://localhost:8000/health && echo " ← EC2 backend is up on RDS"
```

**Test the running EC2 app now:** Open the browser, log in, verify chat history and documents are present. If anything is wrong, revert:
```bash
sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///./intranet.db|" /home/ubuntu/AGENT/backend/.env
# restart backend
```

---

## Phase 4 — Migrate Files: Local Disk → S3 (15 minutes)

> EC2 still serving traffic, now using RDS.

### Step 4.1 — Sync existing files to S3

```bash
S3_UPLOADS=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw s3_uploads_bucket)
S3_GENERATED=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw s3_generated_bucket)

# Sync uploads
if [ -d "/home/ubuntu/AGENT/backend/uploads" ] && [ "$(ls -A /home/ubuntu/AGENT/backend/uploads)" ]; then
  aws s3 sync /home/ubuntu/AGENT/backend/uploads/ "s3://${S3_UPLOADS}/uploads/" \
    --region us-west-1 --no-progress
  echo "✅ Uploads synced to S3"
else
  echo "uploads/ is empty — nothing to sync"
fi

# Sync generated files
if [ -d "/home/ubuntu/AGENT/backend/temp_generated_files" ] && [ "$(ls -A /home/ubuntu/AGENT/backend/temp_generated_files)" ]; then
  aws s3 sync /home/ubuntu/AGENT/backend/temp_generated_files/ \
    "s3://${S3_GENERATED}/temp_generated_files/" \
    --region us-west-1 --no-progress
  echo "✅ Generated files synced to S3"
else
  echo "temp_generated_files/ is empty — nothing to sync"
fi
```

### Step 4.2 — Wire S3 storage into backend services

The `storage.py` abstraction is already written. You now need to update the 4 places that write/read files to use it. **This is the only real code change in the entire migration.**

**Update `upload.py`** — replace aiofiles write with storage.save:

```bash
cd /home/ubuntu/AGENT
```

Open `backend/app/api/upload.py` and replace the file-save block (around line 185):

**BEFORE:**
```python
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)
```

**AFTER:**
```python
    # Save file (local disk on EC2 when STORAGE_BACKEND=local,
    #             S3 on ECS when STORAGE_BACKEND=s3)
    from app.core.storage import storage
    relative_path = f"uploads/{current_user.id}_{file.filename}"
    file_path = await storage.save(file_content, relative_path)
```

**Update `generate.py`** — the generated file download endpoint uses `FileResponse` which requires a real local path. On ECS with S3, you return a redirect to a presigned URL instead.

Find the download route in `generate.py` (the route that serves the completed job file) and wrap the response:

```python
# At the top of generate.py, add:
from app.core.storage import storage, STORAGE_BACKEND

# In the file-serving route, replace FileResponse with:
if STORAGE_BACKEND == "s3":
    url = await storage.url(file_path)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)
else:
    return FileResponse(path=file_path, filename=filename, media_type=content_type)
```

**After making these changes, restart the EC2 backend and test** — upload a file, generate a document, verify downloads still work. The EC2 is running `STORAGE_BACKEND=local` so the behaviour is identical to before.

---

## Phase 5 — ChromaDB: Set Up Shared Vector Storage (20 minutes)

> EC2 still serving traffic. ChromaDB stays local on EC2 for now.

ChromaDB on EC2 holds your current embeddings. For ECS tasks to share vector state, you have two options:

**Option A (recommended for your scale): pgvector on RDS**
This adds a vector column to PostgreSQL — no new service needed.

```bash
# Install pgvector Python package
cd /home/ubuntu/AGENT/backend
pip install pgvector

# Enable vector extension on RDS
psql "postgresql://agentuser:${DB_PASS}@${RDS_ENDPOINT}:5432/agentdb" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

> The actual migration of ChromaDB embeddings to pgvector requires updating `rag_service.py` to use `PGVector` instead of `Chroma`. This is a one-file change but warrants its own session. For the initial ECS launch, use **Option B** below — it works immediately with zero code change.

**Option B (zero code change): Mount ChromaDB on Amazon EFS**

```bash
# Create EFS filesystem
EFS_ID=$(aws efs create-file-system \
  --region us-west-1 \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=agent-prod-chromadb \
  --query 'FileSystemId' --output text)
echo "EFS ID: $EFS_ID"

# Get private subnet IDs from Terraform
SUBNET_IDS=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform \
  output -json | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join([]))" 2>/dev/null || \
  aws ec2 describe-subnets --filters "Name=tag:Name,Values=agent-prod-private-*" \
  --query 'Subnets[*].SubnetId' --output text --region us-west-1)

# Create mount targets in each private subnet (ECS tasks will mount EFS here)
for SUBNET in $SUBNET_IDS; do
  aws efs create-mount-target \
    --file-system-id "$EFS_ID" \
    --subnet-id "$SUBNET" \
    --region us-west-1
  echo "Mount target created in $SUBNET"
done

# Sync current ChromaDB to EFS (mount EFS on EC2 first)
sudo apt install nfs-common -y
sudo mkdir -p /mnt/efs-chromadb
sudo mount -t nfs4 "${EFS_ID}.efs.us-west-1.amazonaws.com:/" /mnt/efs-chromadb
sudo cp -r /home/ubuntu/AGENT/backend/vector_db/* /mnt/efs-chromadb/
echo "✅ ChromaDB copied to EFS"
echo "EFS_ID: $EFS_ID  ← save this for terraform.tfvars"
```

> Set `VECTOR_DB_PATH=/mnt/efs` in the ECS task definition environment variables, and add an EFS volume mount to the task definition in Terraform. This gives all ECS tasks the same shared ChromaDB state.

---

## Phase 6 — Build & Push Docker Images to ECR (30–45 minutes)

> EC2 still serving all traffic.

```bash
cd /home/ubuntu/AGENT

# Get ECR URLs
ECR_BACKEND=$(terraform -chdir=infra/terraform output -raw ecr_backend_url)
ECR_FRONTEND=$(terraform -chdir=infra/terraform output -raw ecr_frontend_url)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ALB_DNS=$(terraform -chdir=infra/terraform output -raw alb_dns_name)

# Login to ECR
aws ecr get-login-password --region us-west-1 | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.us-west-1.amazonaws.com"

SHORT_SHA=$(git rev-parse --short HEAD)

# Build backend — this takes 10–20 min on first build (whisper, sentence-transformers)
echo "Building backend image..."
docker build \
  --file backend/Dockerfile \
  --tag "$ECR_BACKEND:$SHORT_SHA" \
  --tag "$ECR_BACKEND:latest" \
  ./backend

# Build frontend
echo "Building frontend image..."
docker build \
  --file Dockerfile \
  --build-arg "NEXT_PUBLIC_API_URL=https://${ALB_DNS}/api" \
  --build-arg "NEXT_BUILD_STANDALONE=true" \
  --tag "$ECR_FRONTEND:$SHORT_SHA" \
  --tag "$ECR_FRONTEND:latest" \
  .

# Push both
docker push "$ECR_BACKEND:$SHORT_SHA"
docker push "$ECR_BACKEND:latest"
docker push "$ECR_FRONTEND:$SHORT_SHA"
docker push "$ECR_FRONTEND:latest"

echo "✅ Both images pushed to ECR"
echo "Backend:  $ECR_BACKEND:$SHORT_SHA"
echo "Frontend: $ECR_FRONTEND:$SHORT_SHA"
```

**Verify images locally before pushing to ECS — this catches environment problems early:**

```bash
# Test backend container against the real RDS + S3 (same env as ECS will use)
docker run --rm -it \
  -p 8001:8000 \
  -e STORAGE_BACKEND=s3 \
  -e S3_UPLOADS_BUCKET="$S3_UPLOADS" \
  -e S3_GENERATED_BUCKET="$S3_GENERATED" \
  -e DATABASE_URL="postgresql+psycopg2://agentuser:${DB_PASS}@${RDS_ENDPOINT}:5432/agentdb" \
  -e SECRET_KEY="$NEW_SECRET_KEY" \
  -e OPENAI_API_KEY="YOUR_KEY" \
  -e CISCO_CLIENT_ID="YOUR_ID" \
  -e CISCO_CLIENT_SECRET="YOUR_SECRET" \
  -e CISCO_ENDPOINT="https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions" \
  -e CISCO_APPKEY="YOUR_APPKEY" \
  "$ECR_BACKEND:latest" &

sleep 10
curl -s http://localhost:8001/health && echo " ← Docker backend healthy"

# Stop the test container
docker stop $(docker ps -q --filter "ancestor=$ECR_BACKEND:latest")
```

---

## Phase 7 — Validate ECS Services Are Healthy (30 minutes)

> EC2 still serving all user traffic. ECS is running in parallel.

```bash
ECS_CLUSTER=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw ecs_cluster_name)
ALB_DNS=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw alb_dns_name)

# Check ECS service status
aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services agent-prod-backend-svc agent-prod-frontend-svc \
  --region us-west-1 \
  --query 'services[*].{Name:serviceName,Running:runningCount,Desired:desiredCount,Status:status}' \
  --output table

# Wait for both services to reach desired count
echo "Waiting for ECS services to stabilize..."
aws ecs wait services-stable \
  --cluster "$ECS_CLUSTER" \
  --services agent-prod-backend-svc agent-prod-frontend-svc \
  --region us-west-1
echo "✅ ECS services stable"

# Test backend via ALB
for i in {1..5}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${ALB_DNS}/health")
  echo "Attempt $i: ALB backend health = HTTP $STATUS"
  [[ "$STATUS" == "200" ]] && break
  sleep 10
done

# Full end-to-end test via ALB (do this manually in browser):
echo ""
echo "Manual tests to run in browser against http://${ALB_DNS}:"
echo "  1. Load the frontend — should see login page"
echo "  2. Log in with admin credentials"
echo "  3. Navigate to Knowledge Base — documents should be listed"
echo "  4. Ask a question in Chat — should get a RAG-grounded response"
echo "  5. Upload a new document — should succeed"
echo "  6. Generate a PDF — should download successfully"
echo "  7. Generate an MP3/podcast — should play"
```

**Check CloudWatch logs if anything fails:**
```bash
# Tail backend logs
aws logs tail /ecs/agent-prod/backend --follow --region us-west-1

# Tail frontend logs
aws logs tail /ecs/agent-prod/frontend --follow --region us-west-1
```

---

## Phase 8 — Set Up GitHub Actions CI/CD (20 minutes)

> Do this while ECS is running but before cutting over DNS. Validates the full deploy pipeline.

### Step 8.1 — Create GitHub Actions IAM access key

```bash
IAM_USER="agent-prod-github-actions"

# Create access key for the IAM user Terraform created
KEY_JSON=$(aws iam create-access-key --user-name "$IAM_USER" --output json)
echo "Add these to GitHub Secrets:"
echo "  AWS_ACCESS_KEY_ID:     $(echo $KEY_JSON | python3 -c 'import sys,json; print(json.load(sys.stdin)["AccessKey"]["AccessKeyId"])')"
echo "  AWS_SECRET_ACCESS_KEY: $(echo $KEY_JSON | python3 -c 'import sys,json; print(json.load(sys.stdin)["AccessKey"]["SecretAccessKey"])')"
```

### Step 8.2 — Add GitHub Secrets

Go to: `https://github.com/thiachan/agent/settings/secrets/actions`

Add these 6 secrets:

| Secret Name | Value |
|---|---|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `AWS_ACCESS_KEY_ID` | From Step 8.1 |
| `AWS_SECRET_ACCESS_KEY` | From Step 8.1 |
| `NEXT_PUBLIC_API_URL` | `https://<alb_dns_name>/api` |
| `BACKEND_ALB_URL` | `https://<alb_dns_name>` |

### Step 8.3 — Merge branch to main and watch deploy

```bash
# On EC2:
git checkout main
git merge ecs-migration
git push origin main
```

Go to `https://github.com/thiachan/agent/actions` — you should see the workflow trigger. Watch it complete all 3 jobs (build-backend, build-frontend, deploy). The whole pipeline takes ~15 minutes.

After it finishes, re-run the manual tests from Phase 7 against the ALB URL to confirm the CI/CD deploy produced a working version.

---

## Phase 9 — DNS Cut-Over (10 minutes)

> This is the only step that affects users. Window is under 60 seconds.

### Step 9.1 — Pre-flight checklist

Run through every item before proceeding:

```
[ ] Phase 3 complete: EC2 backend is using RDS ✓
[ ] Phase 4 complete: uploads/ and generated files are in S3 ✓
[ ] Phase 6 complete: Docker images pushed to ECR ✓
[ ] Phase 7 complete: ECS tasks are running and healthy on ALB ✓
[ ] Phase 7 complete: Manual end-to-end test through ALB PASSED ✓
[ ] Phase 8 complete: CI/CD pipeline ran successfully ✓
[ ] CloudWatch logs show no errors in last 30 minutes ✓
```

### Step 9.2 — Lower DNS TTL (do this 30 minutes before cutover)

In your DNS registrar / Route53:
- Find the A or CNAME record for your app's domain
- Change TTL from current value to **60 seconds**
- Wait 30 minutes for the change to propagate

### Step 9.3 — Switch DNS

**Option A — Route53 (if your domain is managed there):**
```bash
ZONE_ID="YOUR_HOSTED_ZONE_ID"
ALB_DNS=$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw alb_dns_name)

aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch "{
    \"Changes\": [{
      \"Action\": \"UPSERT\",
      \"ResourceRecordSet\": {
        \"Name\": \"agent.yourdomain.com\",
        \"Type\": \"CNAME\",
        \"TTL\": 60,
        \"ResourceRecords\": [{\"Value\": \"$ALB_DNS\"}]
      }
    }]
  }"
echo "DNS updated → ALB"
```

**Option B — Any other registrar:**
Change the A/CNAME record to point to the ALB DNS name from Terraform outputs.

### Step 9.4 — Verify after cut-over

```bash
# Verify DNS resolves to ALB (repeat until EC2 IP stops appearing)
dig +short yourdomain.com

# Verify HTTPS works (if ACM cert configured)
curl -sI https://yourdomain.com/health | head -3

# Watch ECS request count go up in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value="$(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw alb_dns_name | cut -d. -f1)" \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Sum \
  --region us-west-1
```

---

## Phase 10 — Keep EC2 as Standby (2 weeks, then retire)

**Right after cut-over, do not stop EC2.** Keep it running for 2 weeks as an instant rollback target.

**Rollback procedure (if anything goes wrong on ECS):**
```bash
# In DNS — point back to EC2 IP (takes 60 seconds to propagate)
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "EC2 IP: $EC2_IP"
# Update DNS CNAME → EC2 public IP (or hostname)
```

Zero data risk on rollback — EC2 and ECS both read from the same RDS + S3 after Phase 3 & 4.

**After 2 weeks of stable ECS operation:**
```bash
# Stop EC2 (don't terminate yet — keep EBS snapshot)
aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID --region us-west-1

# Wait 1 more week, then terminate
aws ec2 terminate-instances --instance-ids YOUR_INSTANCE_ID --region us-west-1
```

---

## GitHub Secrets Reference

| Secret | Description |
|---|---|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `AWS_ACCESS_KEY_ID` | GitHub Actions IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | GitHub Actions IAM user secret key |
| `NEXT_PUBLIC_API_URL` | `https://<alb-dns>/api` |
| `BACKEND_ALB_URL` | `https://<alb-dns>` |

---

## Rollback Map

| Phase | Rollback Action | Time |
|---|---|---|
| Phase 1 (Terraform) | `terraform destroy` | 10 min |
| Phase 3 (RDS) | Revert `DATABASE_URL` in `.env`, restart backend | 30 sec |
| Phase 4 (S3) | Remove `STORAGE_BACKEND` from `.env`, restart backend | 30 sec |
| Phase 7 (ECS) | Do nothing — EC2 still serving traffic | 0 sec |
| Phase 9 (DNS) | Point DNS back to EC2 IP | 60 sec |

---

## Common Problems & Fixes

### ECS task keeps restarting
```bash
# Check the stopped task's exit reason
aws ecs describe-tasks \
  --cluster agent-prod-cluster \
  --tasks $(aws ecs list-tasks --cluster agent-prod-cluster --desired-status STOPPED \
    --query 'taskArns[0]' --output text --region us-west-1) \
  --region us-west-1 \
  --query 'tasks[0].containers[*].{name:name,reason:reason,exitCode:exitCode}'
```

### Secrets not injecting into ECS container
Check the ECS execution role has `secretsmanager:GetSecretValue` on the secret ARN. Terraform creates this — verify with:
```bash
aws iam simulate-principal-policy \
  --policy-source-arn $(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw ... ) \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns $(terraform -chdir=/home/ubuntu/AGENT/infra/terraform output -raw secrets_manager_arn)
```

### File uploads work but documents show "processing failed"
`document_processor.py` uses `open(file_path, "rb")`. On S3 backend, `file_path` is a relative key not a local path. Fix: call `await storage.read_to_tempfile(file_path)` at the start of `process_document_background()` when `STORAGE_BACKEND=s3`, then pass the temp path to `extract_text()`.

### RAG returns empty results on ECS
ChromaDB directory is empty on the container. This means EFS is not mounted or the volume mount in the ECS task definition is misconfigured. Check task definition volume mounts in the ECS console.

### ALB returns 503 for /api/* routes
The backend target group health check is failing. Check:
1. The backend container is listening on port 8000 (not 8080)  
2. `/health` route exists and returns 200 — it does in your `main.py` (add it if missing)
3. Security group allows ALB → ECS on port 8000
