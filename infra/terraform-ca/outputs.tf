# ── Outputs ───────────────────────────────────────────────────────────────────

output "eks_cluster_name" {
  description = "EKS cluster name — add to GitHub Secrets as EKS_CLUSTER_NAME_CA"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "ecr_backend_url" {
  description = "ECR backend image URL — use in GitHub Actions and k8s manifests"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR frontend image URL — use in GitHub Actions and k8s manifests"
  value       = aws_ecr_repository.frontend.repository_url
}

output "rds_endpoint" {
  description = "Aurora writer endpoint — put in Secrets Manager DATABASE_URL"
  value       = aws_rds_cluster.main.endpoint
}

output "s3_uploads_bucket" {
  description = "S3 bucket name for uploads — add to k8s deployment env S3_UPLOADS_BUCKET"
  value       = aws_s3_bucket.uploads.bucket
}

output "s3_generated_bucket" {
  description = "S3 bucket name for generated files — add to k8s deployment env S3_GENERATED_BUCKET"
  value       = aws_s3_bucket.generated.bucket
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN — update values after apply"
  value       = aws_secretsmanager_secret.app.arn
}

output "cluster_autoscaler_role_arn" {
  description = "Add to bootstrap-ca.sh CLUSTER_AUTOSCALER_ROLE_ARN variable"
  value       = aws_iam_role.cluster_autoscaler.arn
}

output "aws_lbc_role_arn" {
  description = "Add to bootstrap-ca.sh LBC_ROLE_ARN variable"
  value       = aws_iam_role.aws_lbc.arn
}

output "external_secrets_role_arn" {
  description = "Add to bootstrap-ca.sh EXTERNAL_SECRETS_ROLE_ARN variable"
  value       = aws_iam_role.external_secrets.arn
}

output "backend_pod_role_arn" {
  description = "Add to infra/k8s/backend/serviceaccount.yaml annotation"
  value       = aws_iam_role.backend_pod.arn
}

output "github_actions_user_name" {
  description = "Run: aws iam create-access-key --user-name <name>"
  value       = aws_iam_user.github_actions_ca.name
}

output "next_steps" {
  description = "Manual steps required after terraform apply"
  value       = <<-EOT

    ══════════════════════════════════════════════════════════════════════
    POST-APPLY STEPS  (ca-central-1 EKS)
    ══════════════════════════════════════════════════════════════════════

    1. CREATE GITHUB ACTIONS ACCESS KEY
       aws iam create-access-key --user-name ${aws_iam_user.github_actions_ca.name}
       → Add to GitHub Secrets:
           AWS_ACCESS_KEY_ID_CA
           AWS_SECRET_ACCESS_KEY_CA

    2. POPULATE SECRETS MANAGER with real values
       aws secretsmanager put-secret-value \
         --secret-id ${aws_secretsmanager_secret.app.name} \
         --secret-string file:///tmp/secrets-prod-ca.json \
         --region ca-central-1

    3. INSTALL SYSTEM HELM CHARTS + APPLY K8S MANIFESTS
       ./infra/scripts/bootstrap-ca.sh

    4. PUSH INITIAL IMAGES (or push to main to trigger GitHub Actions)
       ./infra/scripts/initial-push-ca.sh

    5. VERIFY
       kubectl get pods -n agent
       kubectl get ingress -n agent

    6. (AFTER VALIDATION) DNS cutover
       Point your domain to the new ALB DNS name, then disable us-west-1 EC2
    ══════════════════════════════════════════════════════════════════════
  EOT
}
