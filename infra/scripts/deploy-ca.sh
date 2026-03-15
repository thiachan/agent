#!/usr/bin/env bash
# =============================================================================
# deploy-ca.sh  —  Build & deploy AGENT to the ca-central-1 EKS cluster
#
# Prerequisites (run once on a fresh machine):
#   1. AWS CLI configured with credentials that have ECR/EKS access
#   2. kubectl pointing at the EKS cluster:
#        aws eks update-kubeconfig --region ca-central-1 --name agent-prod-ca
#   3. Docker installed and running
#
# Usage:
#   ./infra/scripts/deploy-ca.sh              # build + deploy both
#   ./infra/scripts/deploy-ca.sh backend      # backend only
#   ./infra/scripts/deploy-ca.sh frontend     # frontend only
# =============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REGION="ca-central-1"
ACCOUNT="978027421922"
ECR="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
NAMESPACE="agent"
FRONTEND_URL="https://agent.alexcty.com"

BACKEND_IMAGE="${ECR}/agent-prod-ca-backend:latest"
FRONTEND_IMAGE="${ECR}/agent-prod-ca-frontend:latest"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }

TARGET="${1:-both}"

# ── ECR login ─────────────────────────────────────────────────────────────────
info "Logging in to ECR..."
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR}"
success "ECR login OK"

# ── Build & push backend ──────────────────────────────────────────────────────
build_backend() {
  info "Building backend image..."
  docker build \
    -t "${BACKEND_IMAGE}" \
    "${REPO_ROOT}/backend/"
  info "Pushing backend image..."
  docker push "${BACKEND_IMAGE}"
  success "Backend image pushed: ${BACKEND_IMAGE}"
}

# ── Build & push frontend ─────────────────────────────────────────────────────
# IMPORTANT: NEXT_PUBLIC_API_URL must be passed at build time.
# Next.js inlines it into the JS bundle — it is NOT a runtime env var.
build_frontend() {
  info "Building frontend image (NEXT_PUBLIC_API_URL=${FRONTEND_URL})..."
  docker build \
    --build-arg NEXT_PUBLIC_API_URL="${FRONTEND_URL}" \
    -t "${FRONTEND_IMAGE}" \
    "${REPO_ROOT}/"
  info "Pushing frontend image..."
  docker push "${FRONTEND_IMAGE}"
  success "Frontend image pushed: ${FRONTEND_IMAGE}"
}

# ── Rolling deploy ────────────────────────────────────────────────────────────
deploy() {
  local component="$1"
  info "Applying k8s manifests for ${component}..."
  kubectl apply -f "${REPO_ROOT}/infra/k8s/${component}/" -n "${NAMESPACE}"
  info "Rolling restart ${component}..."
  kubectl rollout restart deployment/"${component}" -n "${NAMESPACE}"
  kubectl rollout status  deployment/"${component}" -n "${NAMESPACE}" --timeout=120s
  success "${component} deployed"
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "${TARGET}" in
  backend)
    build_backend
    deploy backend
    ;;
  frontend)
    build_frontend
    deploy frontend
    ;;
  both|*)
    build_backend
    build_frontend
    deploy backend
    deploy frontend
    ;;
esac

echo ""
success "All done! Site: ${FRONTEND_URL}"
kubectl get pods -n "${NAMESPACE}"
