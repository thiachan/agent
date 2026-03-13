#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# initial-push-ca.sh
# Builds both Docker images and pushes them to ECR in ca-central-1.
# Run this ONCE after bootstrap-ca.sh to give EKS something to pull.
# After this, GitHub Actions (deploy-ca.yml) handles subsequent deployments.
#
# Usage:
#   export AWS_PROFILE=your-profile
#   ./infra/scripts/initial-push-ca.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="ca-central-1"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TF_DIR="$(cd "$(dirname "$0")/../terraform-ca" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Get ECR URLs from terraform output ────────────────────────────────────────
cd "$TF_DIR"
ECR_BACKEND=$(terraform output -raw ecr_backend_url)
ECR_FRONTEND=$(terraform output -raw ecr_frontend_url)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ── Login to ECR ──────────────────────────────────────────────────────────────
info "Logging in to ECR in $REGION..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
success "ECR login success."

# ── Build & push backend ──────────────────────────────────────────────────────
info "Building backend image..."
cd "$ROOT_DIR"
docker build \
  --file backend/Dockerfile \
  --tag "${ECR_BACKEND}:latest" \
  ./backend
info "Pushing backend image..."
docker push "${ECR_BACKEND}:latest"
success "Backend pushed: ${ECR_BACKEND}:latest"

# ── Build & push frontend ─────────────────────────────────────────────────────
info "Building frontend image..."
# NEXT_PUBLIC_API_URL must be set at build time; use a placeholder here —
# the real value comes from the k8s secret at runtime via env var injection.
docker build \
  --file Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-/api}" \
  --build-arg NEXT_BUILD_STANDALONE=true \
  --tag "${ECR_FRONTEND}:latest" \
  .
info "Pushing frontend image..."
docker push "${ECR_FRONTEND}:latest"
success "Frontend pushed: ${ECR_FRONTEND}:latest"

# ── Restart k8s deployments to pull the new images ────────────────────────────
info "Restarting EKS deployments..."
kubectl rollout restart deployment/backend  -n agent
kubectl rollout restart deployment/frontend -n agent
kubectl rollout status  deployment/backend  -n agent --timeout=180s
kubectl rollout status  deployment/frontend -n agent --timeout=180s

success "Initial image push complete!"
info "Monitor: kubectl get pods -n agent -w"
