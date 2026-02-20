#!/usr/bin/env bash
# =============================================================================
# migrate.sh — Live-migration runbook
#
# EC2 stays fully live at every step. Cut-over is a single DNS change at the
# end. Rolling back is reverting that one DNS record.
#
# Prerequisites on this EC2 box:
#   aws CLI configured (aws configure) with an IAM user that has:
#     rds:*, s3:*, secretsmanager:*, ecr:*, ecs:* on the new resources
#   docker, psql, python3 installed
#
# Usage:
#   chmod +x infra/scripts/migrate.sh
#   PHASE=1a ./infra/scripts/migrate.sh   # or 1b, 1c, 2, 3, cutover
# =============================================================================

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
confirm() { read -rp "$(echo -e "${YELLOW}[CONFIRM]${NC} $* (y/N): ")" ans; [[ "$ans" == "y" ]]; }

PHASE="${PHASE:-}"

# ─── Read outputs from Terraform ─────────────────────────────────────────────
TF_DIR="$REPO_ROOT/infra/terraform"
tf_output() { terraform -chdir="$TF_DIR" output -raw "$1" 2>/dev/null || echo ""; }

RDS_ENDPOINT=$(tf_output rds_endpoint)
S3_UPLOADS=$(tf_output s3_uploads_bucket)
S3_GENERATED=$(tf_output s3_generated_bucket)
ECR_BACKEND=$(tf_output ecr_backend_url)
ECR_FRONTEND=$(tf_output ecr_frontend_url)
SECRETS_ARN=$(tf_output secrets_manager_arn)
ECS_CLUSTER=$(tf_output ecs_cluster_name)
ALB_DNS=$(tf_output alb_dns_name)
AWS_REGION="${AWS_REGION:-us-east-1}"

# =============================================================================
phase_1a_migrate_database() {
  # ── Phase 1a: SQLite → RDS Aurora PostgreSQL ──────────────────────────────
  info "=== PHASE 1a: Database migration SQLite → RDS Aurora ==="
  info "RDS endpoint: $RDS_ENDPOINT"

  confirm "Have you set the DB password in Secrets Manager?" || { warn "Do that first."; exit 1; }

  # Get DB credentials from Secrets Manager
  SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id "$SECRETS_ARN" \
    --query SecretString --output text --region "$AWS_REGION")
  DB_URL=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['DATABASE_URL'])")

  info "Enabling pgvector extension on RDS..."
  psql "$DB_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || \
    warn "pgvector extension not available — install it or skip if using ChromaDB on EFS"

  info "Running schema migration against RDS..."
  cd backend
  DATABASE_URL="$DB_URL" python3 init_db.py
  info "Schema created on RDS."

  info "Migrating data from SQLite → PostgreSQL..."
  python3 - <<'PYEOF'
import os, sqlite3, sqlalchemy as sa, json
from pathlib import Path

src = sqlite3.connect("intranet.db")
src.row_factory = sqlite3.Row
dest_url = os.environ["DATABASE_URL"]
engine = sa.create_engine(dest_url)

tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print(f"Tables to migrate: {tables}")

with engine.begin() as conn:
    for table in tables:
        rows = src.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: empty, skipping")
            continue
        cols = rows[0].keys()
        data = [dict(r) for r in rows]
        # Upsert — safe to re-run
        conn.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE"))
        for row in data:
            placeholders = ", ".join(f":{k}" for k in cols)
            col_list = ", ".join(cols)
            conn.execute(sa.text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"), row)
        print(f"  {table}: {len(data)} rows migrated")

print("✅ SQLite → RDS migration complete")
PYEOF

  info "Verifying: pointing backend at RDS (set DATABASE_URL in .env)..."
  warn "ACTION REQUIRED: Update backend/.env DATABASE_URL to: $DB_URL"
  warn "Then restart backend: sudo systemctl restart agent-backend (or your process manager)"
  warn "EC2 is still fully live — test it before proceeding."
  cd "$REPO_ROOT"
}

# =============================================================================
phase_1b_migrate_files() {
  # ── Phase 1b: Local files → S3 ────────────────────────────────────────────
  info "=== PHASE 1b: Migrate existing files to S3 ==="
  info "Uploads bucket:  $S3_UPLOADS"
  info "Generated bucket: $S3_GENERATED"

  if [[ -d "backend/uploads" && "$(ls -A backend/uploads)" ]]; then
    info "Syncing uploads/ → s3://$S3_UPLOADS/uploads/"
    aws s3 sync backend/uploads/ "s3://$S3_UPLOADS/uploads/" \
      --region "$AWS_REGION" --no-progress
    info "✅ uploads synced"
  else
    info "uploads/ is empty — nothing to sync"
  fi

  if [[ -d "backend/temp_generated_files" && "$(ls -A backend/temp_generated_files)" ]]; then
    info "Syncing temp_generated_files/ → s3://$S3_GENERATED/temp_generated_files/"
    aws s3 sync backend/temp_generated_files/ "s3://$S3_GENERATED/temp_generated_files/" \
      --region "$AWS_REGION" --no-progress
    info "✅ generated files synced"
  else
    info "temp_generated_files/ is empty — nothing to sync"
  fi

  info "Add to backend/.env:"
  echo "  STORAGE_BACKEND=s3"
  echo "  S3_UPLOADS_BUCKET=$S3_UPLOADS"
  echo "  S3_GENERATED_BUCKET=$S3_GENERATED"
  warn "Then restart backend and test uploads/downloads still work."
}

# =============================================================================
phase_2_build_images() {
  # ── Phase 2: Build Docker images and push to ECR ──────────────────────────
  info "=== PHASE 2: Build and push Docker images to ECR ==="

  info "Logging into ECR..."
  aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "${ECR_BACKEND%/*}"

  SHORT_SHA=$(git rev-parse --short HEAD)

  info "Building backend image..."
  docker build \
    --file backend/Dockerfile \
    --tag "$ECR_BACKEND:$SHORT_SHA" \
    --tag "$ECR_BACKEND:latest" \
    ./backend

  info "Pushing backend image..."
  docker push "$ECR_BACKEND:$SHORT_SHA"
  docker push "$ECR_BACKEND:latest"

  info "Building frontend image..."
  NEXT_PUBLIC_API_URL="https://$ALB_DNS/api"
  docker build \
    --file Dockerfile \
    --build-arg "NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL" \
    --build-arg "NEXT_BUILD_STANDALONE=true" \
    --tag "$ECR_FRONTEND:$SHORT_SHA" \
    --tag "$ECR_FRONTEND:latest" \
    .

  info "Pushing frontend image..."
  docker push "$ECR_FRONTEND:$SHORT_SHA"
  docker push "$ECR_FRONTEND:latest"

  info "✅ Both images pushed. SHA: $SHORT_SHA"
}

# =============================================================================
phase_3_verify_ecs() {
  # ── Phase 3: Smoke-test ECS before cutting over ────────────────────────────
  info "=== PHASE 3: Verify ECS services are healthy ==="

  info "ECS cluster: $ECS_CLUSTER"
  info "ALB endpoint: https://$ALB_DNS"

  info "Checking ECS service status..."
  aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "agent-prod-backend-svc" "agent-prod-frontend-svc" \
    --region "$AWS_REGION" \
    --query 'services[*].{name:serviceName,running:runningCount,desired:desiredCount,status:status}' \
    --output table

  info "Testing ALB backend health..."
  for i in {1..10}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$ALB_DNS/health" 2>/dev/null || echo "000")
    if [[ "$STATUS" == "200" ]]; then
      info "✅ Backend healthy on ALB (HTTP 200)"
      break
    fi
    warn "Attempt $i: HTTP $STATUS — waiting 15s..."
    sleep 15
  done

  info "Testing ALB frontend..."
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$ALB_DNS/" 2>/dev/null || echo "000")
  info "Frontend status: HTTP $STATUS"

  info "EC2 is still running and handling all traffic."
  info "ECS is running in parallel — safe to inspect and test."
}

# =============================================================================
phase_cutover() {
  # ── DNS Cut-Over (final step, < 60s of dual-routing if TTL was pre-lowered) ─
  info "=== CUT-OVER: Switching traffic from EC2 → ECS ==="
  warn "PRE-FLIGHT CHECKLIST:"
  warn "  ✅ Phase 1a: RDS migration verified"
  warn "  ✅ Phase 1b: S3 file migration verified"
  warn "  ✅ Phase 2: Docker images built and pushed"
  warn "  ✅ Phase 3: ECS tasks healthy on ALB"
  warn "  ✅ Secrets Manager populated with real values"
  warn "  ✅ DNS TTL lowered to 60s (do this 30min beforehand)"

  confirm "All items confirmed? This will switch user traffic to ECS." || exit 1

  warn "Update your DNS record to point to: $ALB_DNS"
  warn "If using Route53 + Terraform: set domain_name var and run terraform apply"
  warn ""
  info "ROLLBACK: Change DNS back to EC2 IP at any time. Zero data risk because"
  info "EC2 and ECS both read from the same RDS + S3."
  info ""
  info "Monitor ECS logs:"
  info "  aws logs tail /ecs/agent-prod/backend --follow --region $AWS_REGION"
  info "  aws logs tail /ecs/agent-prod/frontend --follow --region $AWS_REGION"
}

# =============================================================================
# Main dispatcher
# =============================================================================
case "$PHASE" in
  1a)      phase_1a_migrate_database ;;
  1b)      phase_1b_migrate_files ;;
  2)       phase_2_build_images ;;
  3)       phase_3_verify_ecs ;;
  cutover) phase_cutover ;;
  all)
    phase_1a_migrate_database
    phase_1b_migrate_files
    phase_2_build_images
    phase_3_verify_ecs
    phase_cutover
    ;;
  *)
    echo ""
    echo "Usage: PHASE=<phase> $0"
    echo ""
    echo "Phases:"
    echo "  1a      — SQLite → RDS Aurora PostgreSQL"
    echo "  1b      — Local files → S3"
    echo "  2       — Build + push Docker images to ECR"
    echo "  3       — Smoke-test ECS via ALB"
    echo "  cutover — Final DNS cut-over instructions"
    echo "  all     — Run all phases in sequence"
    echo ""
    echo "Run phases in order. EC2 stays live throughout."
    exit 1
    ;;
esac
