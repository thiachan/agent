#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# migrate-db-ca.sh
# Full data migration from us-west-1 EC2 → ca-central-1 EKS.
#
# Migrates THREE data stores:
#   1. Relational DB  — SQLite (intranet.db) → Aurora PostgreSQL
#                       users, passwords, roles, chat history, bookmarks, etc.
#   2. ChromaDB       — ./vector_db/ directory → EBS PVC
#                       all RAG embeddings, document chunks, knowledge bases
#   3. Uploaded files — ./uploads/ → S3 (ca-central-1 uploads bucket)
#                       all user-uploaded PDFs, videos, audio, Office docs
#
# Prerequisites:
#   - bootstrap-ca.sh has been run (EKS running, images pushed, PVC created)
#   - Secrets Manager contains the real DATABASE_URL for Aurora
#   - SSH access to the us-west-1 EC2
#   - pgloader installed: sudo apt install pgloader  /  brew install pgloader
#
# Usage:
#   export EC2_HOST=<us-west-1-ec2-public-ip>
#   export EC2_USER=ubuntu           # or ec2-user
#   export EC2_KEY=~/.ssh/your-key.pem
#   export AWS_PROFILE=ca-migration
#   ./infra/scripts/migrate-db-ca.sh
#
# Safe to re-run: each part is idempotent. Re-run on the day of DNS cutover
# to capture any writes made since the first run.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="ca-central-1"
TF_DIR="$(cd "$(dirname "$0")/../terraform-ca" && pwd)"
# Adjust EC2_BASE_DIR if your project lives somewhere other than ~/AGENT
EC2_BASE_DIR="${EC2_BASE_DIR:-/home/ubuntu/AGENT}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Validate prerequisites ────────────────────────────────────────────────────
[[ -z "${EC2_HOST:-}" ]] && die "EC2_HOST is not set. Export the us-west-1 EC2 public IP."
[[ -z "${EC2_KEY:-}"  ]] && die "EC2_KEY is not set. Export path to your SSH key file."
EC2_USER="${EC2_USER:-ubuntu}"
command -v pgloader >/dev/null 2>&1  || die "pgloader not found. Install: sudo apt install pgloader  OR  brew install pgloader"
command -v kubectl  >/dev/null 2>&1  || die "kubectl not found."
command -v aws      >/dev/null 2>&1  || die "aws CLI not found."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
  "${EC2_USER}@${EC2_HOST}" "echo ok" >/dev/null 2>&1 \
  || die "Cannot SSH to ${EC2_USER}@${EC2_HOST} with key $EC2_KEY"
success "All prerequisites satisfied."

# ── Resolve terraform outputs ─────────────────────────────────────────────────
cd "$TF_DIR"
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
S3_UPLOADS=$(terraform output -raw s3_uploads_bucket)
ECR_BACKEND=$(terraform output -raw ecr_backend_url)
DB_NAME="agentdb"
DB_USER="agentuser"

# Extract password from Secrets Manager — never hardcode credentials
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id agent-prod-ca-app-secrets \
  --region "$REGION" \
  --query 'SecretString' --output text \
  | python3 -c "
import sys, json, re
d = json.load(sys.stdin)
url = d['DATABASE_URL']
m = re.search(r':([^:@]+)@', url)
print(m.group(1))")

info "EC2 source  : ${EC2_USER}@${EC2_HOST}  (${EC2_BASE_DIR}/backend)"
info "Aurora      : ${RDS_ENDPOINT} / ${DB_NAME}"
info "S3 uploads  : s3://${S3_UPLOADS}"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — RELATIONAL DATABASE  (SQLite → Aurora PostgreSQL)
# ══════════════════════════════════════════════════════════════════════════════
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "PART 1: Relational DB  (intranet.db → Aurora PostgreSQL)"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1a. Briefly pause the EC2 backend to prevent writes mid-copy, then copy
info "Pausing EC2 backend process for consistent snapshot..."
EC2_BACKEND_PID=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
  "${EC2_USER}@${EC2_HOST}" "pgrep -f 'uvicorn main:app' || true")

if [[ -n "$EC2_BACKEND_PID" ]]; then
  ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_HOST}" "kill -STOP $EC2_BACKEND_PID"
  info "EC2 backend paused (PID $EC2_BACKEND_PID). Copying SQLite now..."
fi

scp -i "$EC2_KEY" -o StrictHostKeyChecking=no \
  "${EC2_USER}@${EC2_HOST}:${EC2_BASE_DIR}/backend/intranet.db" \
  /tmp/intranet.db

if [[ -n "$EC2_BACKEND_PID" ]]; then
  ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_HOST}" "kill -CONT $EC2_BACKEND_PID"
  success "EC2 backend resumed."
fi
success "SQLite copied to /tmp/intranet.db"

# 1b. Create schema on Aurora via a k8s Job
info "Creating Aurora schema via k8s Job (init_db.py)..."
kubectl delete job db-schema-init -n agent --ignore-not-found=true
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-schema-init
  namespace: agent
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      serviceAccountName: backend
      restartPolicy: Never
      containers:
        - name: db-schema-init
          image: ${ECR_BACKEND}:latest
          command: ["python", "init_db.py"]
          envFrom:
            - secretRef:
                name: app-secrets
EOF
info "Waiting for schema init job..."
kubectl wait --for=condition=complete job/db-schema-init -n agent --timeout=180s
success "Aurora schema created."

# 1c. Migrate all data with pgloader
info "Migrating data from SQLite → Aurora with pgloader..."
cat <<PGEOF | pgloader --verbose -
LOAD DATABASE
  FROM sqlite:///tmp/intranet.db
  INTO postgresql://${DB_USER}:${DB_PASS}@${RDS_ENDPOINT}/${DB_NAME}

  WITH include drop, create tables, create indexes, reset sequences,
       batch rows = 5000, batch concurrency = 4

  SET work_mem to '128MB', maintenance_work_mem to '512MB'

  EXCLUDING TABLE NAMES MATCHING 'alembic_version'

  AFTER LOAD DO
    \$\$ SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1)); \$\$,
    \$\$ SELECT setval('documents_id_seq', COALESCE((SELECT MAX(id) FROM documents), 1)); \$\$
  ;
PGEOF
success "Relational DB migration complete."

# 1d. Quick verification
EC2_USER_COUNT=$(sqlite3 /tmp/intranet.db "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
AURORA_USER_COUNT=$(PGPASSWORD="$DB_PASS" psql -h "$RDS_ENDPOINT" -U "$DB_USER" -d "$DB_NAME" \
  -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "unknown")
info "User count — EC2 SQLite: ${EC2_USER_COUNT}  |  Aurora: ${AURORA_USER_COUNT}"
[[ "$EC2_USER_COUNT" == "$AURORA_USER_COUNT" ]] \
  && success "Row counts match." \
  || warn "Row counts differ — review pgloader output above before proceeding."

echo ""

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — CHROMADB VECTOR STORE  (EC2 ./vector_db/ → EBS PVC)
# ══════════════════════════════════════════════════════════════════════════════
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "PART 2: ChromaDB vector store → EBS PVC"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 2a. Confirm vector_db directory exists on EC2
VECTOR_DB_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
  "${EC2_USER}@${EC2_HOST}" \
  "du -sh ${EC2_BASE_DIR}/backend/vector_db 2>/dev/null || echo '0'")
info "EC2 vector_db size: ${VECTOR_DB_SIZE}"

# 2b. Stream tar from EC2 directly to S3 staging (no local disk needed)
S3_STAGING_KEY="migration-staging/vector_db_$(date +%Y%m%d_%H%M%S).tar.gz"
info "Streaming vector_db from EC2 → S3 staging (s3://${S3_UPLOADS}/${S3_STAGING_KEY})..."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
  "${EC2_USER}@${EC2_HOST}" \
  "tar -czf - -C ${EC2_BASE_DIR}/backend vector_db" \
  | aws s3 cp - "s3://${S3_UPLOADS}/${S3_STAGING_KEY}" \
      --region "$REGION" \
      --expected-size 0   # suppress size warning for streaming
success "ChromaDB archive uploaded to S3 staging."

# 2c. Run a k8s Job that mounts the PVC and extracts the archive into it
info "Running k8s Job to restore ChromaDB into EBS PVC..."
kubectl delete job chroma-restore -n agent --ignore-not-found=true
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: chroma-restore
  namespace: agent
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      serviceAccountName: backend
      restartPolicy: Never
      volumes:
        - name: chroma-vector-db
          persistentVolumeClaim:
            claimName: chroma-vector-db
      containers:
        - name: chroma-restore
          image: amazon/aws-cli:latest
          command:
            - /bin/sh
            - -c
            - |
              set -e
              echo "Downloading archive from S3..."
              aws s3 cp s3://${S3_UPLOADS}/${S3_STAGING_KEY} /tmp/vector_db.tar.gz \
                --region ${REGION}
              echo "Extracting into PVC mount..."
              rm -rf /app/vector_db/*
              tar -xzf /tmp/vector_db.tar.gz -C /app/
              echo "Contents of /app/vector_db:"
              ls -la /app/vector_db/
              rm /tmp/vector_db.tar.gz
              echo "ChromaDB restore complete."
          volumeMounts:
            - name: chroma-vector-db
              mountPath: /app/vector_db
EOF
info "Waiting for chroma-restore job (up to 5 minutes)..."
kubectl wait --for=condition=complete job/chroma-restore -n agent --timeout=300s
success "ChromaDB restored to EBS PVC."

# 2d. Clean up S3 staging object
info "Removing S3 staging archive..."
aws s3 rm "s3://${S3_UPLOADS}/${S3_STAGING_KEY}" --region "$REGION"
success "Staging cleaned up."

echo ""

# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — UPLOADED FILES  (EC2 ./uploads/ → S3 uploads bucket)
# ══════════════════════════════════════════════════════════════════════════════
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "PART 3: User uploads → S3 (s3://${S3_UPLOADS}/uploads/)"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 3a. Show upload size before sync
UPLOADS_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
  "${EC2_USER}@${EC2_HOST}" \
  "du -sh ${EC2_BASE_DIR}/backend/uploads 2>/dev/null || echo '0 (empty)'")
info "EC2 uploads size: ${UPLOADS_SIZE}"

# 3b. Stream tar to a staging key, then expand to uploads/ prefix in S3
# Using aws s3 sync from inside an EC2-side tunnel — but since we may not have
# aws CLI configured on EC2, we stream via tar and extract with a k8s Job.
S3_UPLOADS_STAGING="migration-staging/uploads_$(date +%Y%m%d_%H%M%S).tar.gz"
info "Streaming uploads from EC2 → S3 staging..."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
  "${EC2_USER}@${EC2_HOST}" \
  "cd ${EC2_BASE_DIR}/backend && tar -czf - uploads 2>/dev/null || tar -czf - -T /dev/null" \
  | aws s3 cp - "s3://${S3_UPLOADS}/${S3_UPLOADS_STAGING}" \
      --region "$REGION" \
      --expected-size 0
success "Uploads archive at s3://${S3_UPLOADS}/${S3_UPLOADS_STAGING}"

# 3c. k8s Job: extract archive and sync each file to correct S3 prefix
info "Running k8s Job to expand uploads into s3://${S3_UPLOADS}/uploads/..."
kubectl delete job uploads-restore -n agent --ignore-not-found=true
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: uploads-restore
  namespace: agent
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      serviceAccountName: backend
      restartPolicy: Never
      containers:
        - name: uploads-restore
          image: amazon/aws-cli:latest
          command:
            - /bin/sh
            - -c
            - |
              set -e
              echo "Downloading uploads archive from S3 staging..."
              aws s3 cp s3://${S3_UPLOADS}/${S3_UPLOADS_STAGING} /tmp/uploads.tar.gz \
                --region ${REGION}
              echo "Extracting archive..."
              mkdir -p /tmp/restore
              tar -xzf /tmp/uploads.tar.gz -C /tmp/restore/
              echo "Syncing to s3://${S3_UPLOADS}/uploads/ ..."
              aws s3 sync /tmp/restore/uploads/ s3://${S3_UPLOADS}/uploads/ \
                --region ${REGION} \
                --no-progress
              echo "Sync complete. File count:"
              aws s3 ls s3://${S3_UPLOADS}/uploads/ --recursive --region ${REGION} | wc -l
              rm -rf /tmp/uploads.tar.gz /tmp/restore
EOF
info "Waiting for uploads-restore job (up to 10 minutes)..."
kubectl wait --for=condition=complete job/uploads-restore -n agent --timeout=600s
success "Uploads synced to S3."

# 3d. Clean up staging
info "Removing S3 staging archive..."
aws s3 rm "s3://${S3_UPLOADS}/${S3_UPLOADS_STAGING}" --region "$REGION"
success "Staging cleaned up."

echo ""
# ══════════════════════════════════════════════════════════════════════════════
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "DATA MIGRATION COMPLETE"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Summary:"
info "  ✓ PART 1: Users, roles, chat history → Aurora PostgreSQL"
info "  ✓ PART 2: RAG embeddings (ChromaDB) → EBS PVC (/app/vector_db)"
info "  ✓ PART 3: Uploaded files → s3://${S3_UPLOADS}/uploads/"
echo ""
info "Next steps:"
info "  1. Verify the backend pod is reading from Aurora and ChromaDB:"
info "       kubectl exec -n agent deploy/backend -- python -c \\"
info "         \"from app.core.database import engine; print(engine.url)\""
info "  2. Test a RAG query from the UI to confirm embeddings are intact."
info "  3. Test file download to confirm uploads resolve correctly."
info "  4. Once validated → update DNS to point to the ALB."
info ""
info "  Re-run this script on DNS cutover day to capture any"
info "  writes made since this first run (idempotent)."
