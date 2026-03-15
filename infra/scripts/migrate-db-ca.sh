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
# LOCAL_MODE=true — run from the source EC2 itself (no SSH needed).
# LOCAL_MODE=false (default) — run from any machine with SSH access to the source EC2.
LOCAL_MODE="${LOCAL_MODE:-false}"

if [[ "$LOCAL_MODE" == "true" ]]; then
  # We ARE on the source EC2 — data lives right here.
  EC2_HOST="localhost"
  EC2_USER="$(whoami)"
  EC2_KEY=""
  info "LOCAL_MODE=true: reading data from local disk (no SSH)."
else
  [[ -z "${EC2_HOST:-}" ]] && die "EC2_HOST is not set. Export the us-west-1 EC2 public IP."
  [[ -z "${EC2_KEY:-}"  ]] && die "EC2_KEY is not set. Export path to your SSH key file."
  EC2_USER="${EC2_USER:-ubuntu}"
  ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "${EC2_USER}@${EC2_HOST}" "echo ok" >/dev/null 2>&1 \
    || die "Cannot SSH to ${EC2_USER}@${EC2_HOST} with key $EC2_KEY"
fi
command -v pgloader >/dev/null 2>&1  || die "pgloader not found. Install: sudo apt install pgloader  OR  brew install pgloader"
command -v kubectl  >/dev/null 2>&1  || die "kubectl not found."
command -v aws      >/dev/null 2>&1  || die "aws CLI not found."
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

# 1a. Pause backend for consistent snapshot, copy intranet.db
info "Pausing backend process for consistent snapshot..."
EC2_BACKEND_PID=$(pgrep -f 'uvicorn main:app' || true)

if [[ -n "$EC2_BACKEND_PID" ]]; then
  kill -STOP $EC2_BACKEND_PID
  info "Backend paused (PID $EC2_BACKEND_PID). Copying SQLite now..."
fi

if [[ "$LOCAL_MODE" == "true" ]]; then
  cp "${EC2_BASE_DIR}/backend/intranet.db" /tmp/intranet.db
else
  scp -i "$EC2_KEY" -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_HOST}:${EC2_BASE_DIR}/backend/intranet.db" \
    /tmp/intranet.db
fi

if [[ -n "$EC2_BACKEND_PID" ]]; then
  kill -CONT $EC2_BACKEND_PID
  success "Backend resumed."
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

# 1c. Migrate all data via a k8s Job inside the cluster (has VPC access to Aurora)
info "Uploading SQLite to S3 staging for in-cluster migration..."
S3_SQLITE_KEY="migration-staging/intranet_$(date +%Y%m%d_%H%M%S).db"
aws s3 cp /tmp/intranet.db "s3://${S3_UPLOADS}/${S3_SQLITE_KEY}" --region "$REGION"
success "SQLite uploaded to s3://${S3_UPLOADS}/${S3_SQLITE_KEY}"

info "Running in-cluster Python migration job (SQLite → Aurora)..."
kubectl delete job db-data-migrate -n agent --ignore-not-found=true
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-data-migrate
  namespace: agent
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      serviceAccountName: backend
      restartPolicy: Never
      containers:
        - name: db-data-migrate
          image: ${ECR_BACKEND}:latest
          command:
            - python
            - -c
            - |
              import os, sqlite3, boto3, tempfile
              from sqlalchemy import create_engine, text, inspect

              region = "${REGION}"
              s3_bucket = "${S3_UPLOADS}"
              s3_key    = "${S3_SQLITE_KEY}"
              db_url    = os.environ["DATABASE_URL"]

              # Download SQLite from S3
              print("Downloading SQLite from S3...")
              s3 = boto3.client("s3", region_name=region)
              with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                  s3.download_fileobj(s3_bucket, s3_key, f)
                  sqlite_path = f.name
              print(f"Downloaded to {sqlite_path}")

              src = sqlite3.connect(sqlite_path)
              src.row_factory = sqlite3.Row
              dst = create_engine(db_url)
              inspector = inspect(dst)

              # Build a map of boolean columns per table from the PG schema
              bool_cols = {}
              for tname in inspector.get_table_names():
                  bool_cols[tname] = {
                      col["name"]
                      for col in inspector.get_columns(tname)
                      if str(col["type"]).upper() == "BOOLEAN"
                  }

              tables = [r[0] for r in src.execute(
                  "SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('alembic_version','sqlite_sequence')"
              ).fetchall()]
              print(f"Tables to migrate: {tables}")

              for table in tables:
                  rows = src.execute(f"SELECT * FROM {table}").fetchall()
                  if not rows:
                      print(f"  {table}: empty, skipping")
                      continue
                  cols = rows[0].keys()
                  col_list = ", ".join(f'"{c}"' for c in cols)
                  placeholders = ", ".join(f":{c}" for c in cols)

                  # Convert SQLite int 0/1 → Python bool for boolean PG columns
                  bools = bool_cols.get(table, set())
                  def fix_row(r):
                      d = dict(r)
                      for k in bools:
                          if k in d and d[k] is not None:
                              d[k] = bool(d[k])
                      return d

                  with dst.begin() as conn:
                      conn.execute(text("SET session_replication_role = replica"))  # disable FK checks
                      conn.execute(text(f"DELETE FROM {table}"))
                      conn.execute(
                          text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"),
                          [fix_row(r) for r in rows],
                      )
                      conn.execute(text("SET session_replication_role = DEFAULT"))
                  print(f"  {table}: {len(rows)} rows migrated")

              # Fix sequences
              with dst.begin() as conn:
                  for tbl, col in [("users","id"),("documents","id")]:
                      try:
                          conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{tbl}','{col}'), COALESCE((SELECT MAX({col}) FROM {tbl}),1))"))
                      except Exception as e:
                          print(f"  sequence fix {tbl}.{col}: {e}")

              src.close()
              os.unlink(sqlite_path)
              print("Migration complete.")
          envFrom:
            - secretRef:
                name: app-secrets
EOF
info "Waiting for db-data-migrate job (up to 5 minutes)..."
kubectl wait --for=condition=complete job/db-data-migrate -n agent --timeout=300s
kubectl logs job/db-data-migrate -n agent
success "Relational DB migration complete."

# Clean up staging SQLite
aws s3 rm "s3://${S3_UPLOADS}/${S3_SQLITE_KEY}" --region "$REGION"

# 1d. Quick verification via a pod exec (has DB access)
EC2_USER_COUNT=$(sqlite3 /tmp/intranet.db "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
AURORA_USER_COUNT=$(kubectl exec -n agent deploy/backend -- \
  python -c "from app.core.database import SessionLocal; s=SessionLocal(); print(s.execute(__import__('sqlalchemy').text('SELECT COUNT(*) FROM users')).scalar()); s.close()" \
  2>/dev/null || echo "unknown")
info "User count — SQLite: ${EC2_USER_COUNT}  |  Aurora: ${AURORA_USER_COUNT}"
[[ "$EC2_USER_COUNT" == "$AURORA_USER_COUNT" ]] \
  && success "Row counts match." \
  || warn "Row counts differ — review job logs above before proceeding."

echo ""

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — CHROMADB VECTOR STORE  (EC2 ./vector_db/ → EBS PVC)
# ══════════════════════════════════════════════════════════════════════════════
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "PART 2: ChromaDB vector store → EBS PVC"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 2a. Confirm vector_db directory exists
VECTOR_DB_SIZE=$(du -sh "${EC2_BASE_DIR}/backend/vector_db" 2>/dev/null || echo '0')
info "vector_db size: ${VECTOR_DB_SIZE}"

# 2b. Stream tar directly to S3 staging (no local disk needed)
S3_STAGING_KEY="migration-staging/vector_db_$(date +%Y%m%d_%H%M%S).tar.gz"
info "Streaming vector_db → S3 staging (s3://${S3_UPLOADS}/${S3_STAGING_KEY})..."
if [[ "$LOCAL_MODE" == "true" ]]; then
  tar -czf - -C "${EC2_BASE_DIR}/backend" vector_db \
    | aws s3 cp - "s3://${S3_UPLOADS}/${S3_STAGING_KEY}" \
        --region "$REGION" --expected-size 0
else
  ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_HOST}" \
    "tar -czf - -C ${EC2_BASE_DIR}/backend vector_db" \
    | aws s3 cp - "s3://${S3_UPLOADS}/${S3_STAGING_KEY}" \
        --region "$REGION" --expected-size 0
fi
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
          image: public.ecr.aws/amazonlinux/amazonlinux:2023
          command:
            - /bin/sh
            - -c
            - |
              set -e
              yum install -y awscli tar gzip -q
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
UPLOADS_SIZE=$(du -sh "${EC2_BASE_DIR}/backend/uploads" 2>/dev/null || echo '0 (empty)')
info "Uploads size: ${UPLOADS_SIZE}"

# 3b. Stream tar to S3 staging, then expand with a k8s Job
S3_UPLOADS_STAGING="migration-staging/uploads_$(date +%Y%m%d_%H%M%S).tar.gz"
info "Streaming uploads → S3 staging..."
if [[ "$LOCAL_MODE" == "true" ]]; then
  cd "${EC2_BASE_DIR}/backend" && \
    tar -czf - uploads 2>/dev/null \
    | aws s3 cp - "s3://${S3_UPLOADS}/${S3_UPLOADS_STAGING}" \
        --region "$REGION" --expected-size 0
  cd - >/dev/null
else
  ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_HOST}" \
    "cd ${EC2_BASE_DIR}/backend && tar -czf - uploads 2>/dev/null || tar -czf - -T /dev/null" \
    | aws s3 cp - "s3://${S3_UPLOADS}/${S3_UPLOADS_STAGING}" \
        --region "$REGION" --expected-size 0
fi
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
          image: public.ecr.aws/amazonlinux/amazonlinux:2023
          command:
            - /bin/sh
            - -c
            - |
              set -e
              yum install -y awscli tar gzip -q
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
