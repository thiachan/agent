#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# bootstrap-ca.sh
# Full bootstrap for the ca-central-1 EKS environment.
#
# Run this ONCE from a machine that has:
#   - AWS CLI configured (profile with admin-level permissions)
#   - terraform >= 1.7
#   - kubectl
#   - helm >= 3
#
# Usage:
#   export AWS_PROFILE=your-profile   # or set AWS_ACCESS_KEY_ID etc.
#   ./infra/scripts/bootstrap-ca.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="ca-central-1"
PROJECT="agent"
ENV="prod"
CLUSTER_NAME="${PROJECT}-${ENV}-ca"
TF_DIR="$(cd "$(dirname "$0")/../terraform-ca" && pwd)"
K8S_DIR="$(cd "$(dirname "$0")/../k8s" && pwd)"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Step 0: pre-flight checks ─────────────────────────────────────────────────
info "Checking required tools..."
for cmd in aws terraform kubectl helm; do
  command -v "$cmd" >/dev/null 2>&1 || die "Missing required command: $cmd"
done
success "All tools found."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
info "AWS Account: $ACCOUNT_ID  Region: $REGION"

# ── Step 1: create Terraform state backend ────────────────────────────────────
STATE_BUCKET="agent-tfstate-ca-${ACCOUNT_ID}"
LOCK_TABLE="agent-tfstate-lock-ca"

info "Creating S3 state bucket: $STATE_BUCKET"
if aws s3api head-bucket --bucket "$STATE_BUCKET" --region "$REGION" 2>/dev/null; then
  warn "Bucket already exists — skipping."
else
  aws s3 mb "s3://$STATE_BUCKET" --region "$REGION"
  aws s3api put-bucket-versioning \
    --bucket "$STATE_BUCKET" \
    --versioning-configuration Status=Enabled \
    --region "$REGION"
  aws s3api put-bucket-encryption \
    --bucket "$STATE_BUCKET" \
    --server-side-encryption-configuration \
      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
    --region "$REGION"
  aws s3api put-public-access-block \
    --bucket "$STATE_BUCKET" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
    --region "$REGION"
  success "State bucket created."
fi

info "Creating DynamoDB lock table: $LOCK_TABLE"
if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$REGION" 2>/dev/null; then
  warn "Lock table already exists — skipping."
else
  aws dynamodb create-table \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"
  success "Lock table created."
fi

# ── Step 2: patch bucket name in versions.tf ──────────────────────────────────
info "Patching Terraform state bucket name..."
sed -i "s/agent-tfstate-ca-ACCOUNT_ID/${STATE_BUCKET}/g" "$TF_DIR/versions.tf"
success "versions.tf patched."

# ── Step 3: terraform init + apply ────────────────────────────────────────────
info "Running terraform init..."
cd "$TF_DIR"
terraform init -upgrade

info "Running terraform apply (this takes ~15 minutes for EKS cluster)..."
terraform apply -auto-approve

# Capture outputs
ECR_BACKEND=$(terraform output -raw ecr_backend_url)
ECR_FRONTEND=$(terraform output -raw ecr_frontend_url)
CLUSTER_AUTOSCALER_ROLE=$(terraform output -raw cluster_autoscaler_role_arn)
LBC_ROLE=$(terraform output -raw aws_lbc_role_arn)
EXTERNAL_SECRETS_ROLE=$(terraform output -raw external_secrets_role_arn)
BACKEND_POD_ROLE=$(terraform output -raw backend_pod_role_arn)
S3_UPLOADS=$(terraform output -raw s3_uploads_bucket)
S3_GENERATED=$(terraform output -raw s3_generated_bucket)
success "Terraform apply complete."

# ── Step 4: configure kubectl ─────────────────────────────────────────────────
info "Updating kubeconfig for cluster: $CLUSTER_NAME"
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION"
kubectl cluster-info
success "kubectl configured."

# ── Step 5: install metrics-server ───────────────────────────────────────────
info "Installing metrics-server (required for HPA)..."
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ --force-update
helm upgrade --install metrics-server metrics-server/metrics-server \
  --namespace kube-system \
  --set args="{--kubelet-insecure-tls}" \
  --wait
success "metrics-server installed."

# ── Step 6: install Cluster Autoscaler ────────────────────────────────────────
info "Installing Cluster Autoscaler..."
helm repo add autoscaler https://kubernetes.github.io/autoscaler --force-update
helm upgrade --install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName="$CLUSTER_NAME" \
  --set awsRegion="$REGION" \
  --set rbac.serviceAccount.create=true \
  --set rbac.serviceAccount.name=cluster-autoscaler \
  --set rbac.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="$CLUSTER_AUTOSCALER_ROLE" \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.skip-nodes-with-system-pods=false \
  --set extraArgs.scale-down-delay-after-add=5m \
  --set extraArgs.scale-down-unneeded-time=5m \
  --wait
success "Cluster Autoscaler installed."

# ── Step 7: install AWS Load Balancer Controller ──────────────────────────────
info "Installing AWS Load Balancer Controller..."
helm repo add eks https://aws.github.io/eks-charts --force-update
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --set clusterName="$CLUSTER_NAME" \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="$LBC_ROLE" \
  --set region="$REGION" \
  --set vpcId="$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.resourcesVpcConfig.vpcId' --output text)" \
  --wait
success "AWS Load Balancer Controller installed."

# ── Step 8: install External Secrets Operator ─────────────────────────────────
info "Installing External Secrets Operator..."
helm repo add external-secrets https://charts.external-secrets.io --force-update
helm upgrade --install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="$EXTERNAL_SECRETS_ROLE" \
  --wait
success "External Secrets Operator installed."

# Wait for ESO CRDs to be fully registered before applying ClusterSecretStore
info "Waiting for External Secrets CRDs to be ready..."
kubectl wait --for condition=established \
  crd/clustersecretstores.external-secrets.io \
  crd/externalsecrets.external-secrets.io \
  --timeout=60s
success "ESO CRDs ready."

# ── Step 9: apply k8s manifests ───────────────────────────────────────────────
info "Applying Kubernetes manifests..."

kubectl apply -f "$K8S_DIR/namespace.yaml"
kubectl apply -f "$K8S_DIR/external-secrets/cluster-secret-store.yaml"

# StorageClass must exist before the PVC is created
kubectl apply -f "$K8S_DIR/storage-class.yaml"

# Patch backend ServiceAccount with the correct IRSA role ARN
sed "s|BACKEND_POD_ROLE_ARN|${BACKEND_POD_ROLE}|g" \
  "$K8S_DIR/backend/serviceaccount.yaml" | kubectl apply -f -

# Apply ExternalSecret — this creates the k8s Secret from Secrets Manager
kubectl apply -f "$K8S_DIR/external-secrets/external-secret.yaml"

info "Waiting for ExternalSecret to sync (up to 60s)..."
kubectl wait --for=condition=Ready externalsecret/app-secrets -n agent --timeout=60s \
  || warn "ExternalSecret not ready yet — check: kubectl describe externalsecret app-secrets -n agent"

# PVC must be created before the backend deployment tries to mount it
kubectl apply -f "$K8S_DIR/backend/pvc.yaml"

# Patch backend deployment with real S3 bucket names
sed \
  -e "s|BACKEND_IMAGE_PLACEHOLDER|${ECR_BACKEND}:latest|g" \
  -e "s|S3_UPLOADS_BUCKET_PLACEHOLDER|${S3_UPLOADS}|g" \
  -e "s|S3_GENERATED_BUCKET_PLACEHOLDER|${S3_GENERATED}|g" \
  "$K8S_DIR/backend/deployment.yaml" | kubectl apply -f -

sed "s|FRONTEND_IMAGE_PLACEHOLDER|${ECR_FRONTEND}:latest|g" \
  "$K8S_DIR/frontend/deployment.yaml" | kubectl apply -f -

kubectl apply -f "$K8S_DIR/backend/service.yaml"
kubectl apply -f "$K8S_DIR/backend/hpa.yaml"
kubectl apply -f "$K8S_DIR/frontend/service.yaml"
kubectl apply -f "$K8S_DIR/frontend/hpa.yaml"

# Ingress — skip certificate-arn if not set
if [[ -z "${ACM_CERT_ARN:-}" ]]; then
  warn "ACM_CERT_ARN not set — ingress will use HTTP only until you add it."
  sed 's|alb.ingress.kubernetes.io/certificate-arn: "ACM_CERTIFICATE_ARN"||g' \
    "$K8S_DIR/ingress.yaml" | \
  sed 's|alb.ingress.kubernetes.io/ssl-redirect: "443"||g' | \
    kubectl apply -f -
else
  sed "s|ACM_CERTIFICATE_ARN|${ACM_CERT_ARN}|g" \
    "$K8S_DIR/ingress.yaml" | kubectl apply -f -
fi

success "Kubernetes manifests applied."

# ── Step 10: verify ───────────────────────────────────────────────────────────
info "Waiting for deployments to roll out (up to 3 minutes)..."
kubectl rollout status deployment/backend  -n agent --timeout=180s || warn "Backend not ready yet"
kubectl rollout status deployment/frontend -n agent --timeout=180s || warn "Frontend not ready yet"

echo ""
info "Cluster status:"
kubectl get nodes
echo ""
info "Pods:"
kubectl get pods -n agent
echo ""
info "Ingress (ALB DNS):"
kubectl get ingress -n agent
echo ""
success "Bootstrap complete!"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "  1. Populate real secrets:"
echo "     aws secretsmanager put-secret-value --secret-id agent-prod-ca-app-secrets \\"
echo "       --secret-string file:///tmp/secrets-prod-ca.json --region $REGION"
echo ""
echo "  2. Push initial Docker images:"
echo "     ./infra/scripts/initial-push-ca.sh"
echo ""
echo "  3. Add GitHub Secrets (see terraform output for user name):"
echo "     AWS_ACCESS_KEY_ID_CA, AWS_SECRET_ACCESS_KEY_CA"
echo "     EKS_CLUSTER_NAME_CA=$CLUSTER_NAME"
echo "     ECR_BACKEND_CA=$ECR_BACKEND"
echo "     ECR_FRONTEND_CA=$ECR_FRONTEND"
echo "     S3_UPLOADS_BUCKET_CA=$S3_UPLOADS"
echo "     S3_GENERATED_BUCKET_CA=$S3_GENERATED"
