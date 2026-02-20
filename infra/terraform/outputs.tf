# ── Outputs ───────────────────────────────────────────────────────────────────

output "alb_dns_name" {
  description = "ALB DNS — point your domain here if not using CloudFront"
  value       = aws_lb.main.dns_name
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain (if domain_name was set)"
  value       = var.domain_name != "" ? aws_cloudfront_distribution.main[0].domain_name : "CloudFront not created (domain_name not set)"
}

output "ecr_backend_url" {
  description = "ECR URL for backend image — use in CI/CD"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR URL for frontend image — use in CI/CD"
  value       = aws_ecr_repository.frontend.repository_url
}

output "rds_endpoint" {
  description = "Aurora cluster writer endpoint"
  value       = aws_rds_cluster.main.endpoint
}

output "s3_uploads_bucket" {
  description = "S3 bucket name for uploads"
  value       = aws_s3_bucket.uploads.bucket
}

output "s3_generated_bucket" {
  description = "S3 bucket name for generated files"
  value       = aws_s3_bucket.generated.bucket
}

output "secrets_manager_arn" {
  description = "ARN of the app secrets — update values here after tf apply"
  value       = aws_secretsmanager_secret.app.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name — use in GitHub Actions secrets"
  value       = aws_ecs_cluster.main.name
}

output "github_actions_user_arn" {
  description = "IAM user ARN for GitHub Actions — create an access key for it"
  value       = aws_iam_user.github_actions.arn
}

output "next_steps" {
  description = "Manual steps required after terraform apply"
  value       = <<-EOT
    ═══════════════════════════════════════════════════════════════════════
    POST-APPLY STEPS
    ═══════════════════════════════════════════════════════════════════════

    1. CREATE GITHUB ACTIONS ACCESS KEY
       aws iam create-access-key --user-name ${aws_iam_user.github_actions.name}
       → Add AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to GitHub Secrets

    2. POPULATE SECRETS MANAGER
       aws secretsmanager put-secret-value \
         --secret-id ${aws_secretsmanager_secret.app.name} \
         --secret-string file://infra/secrets-prod.json
       (copy infra/secrets-template.json, fill in real values, never commit it)

    3. PUSH INITIAL IMAGES
       ./infra/scripts/initial-push.sh
       (builds and pushes images so ECS can start tasks)

    4. MIGRATE DATABASE
       ./infra/scripts/migrate-db.sh
       (runs init_db.py against new RDS instance)

    5. (OPTIONAL) ADD DOMAIN
       Set domain_name and acm_certificate_arn in terraform.tfvars and re-apply

    6. SET GITHUB SECRETS
       AWS_ACCOUNT_ID, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
       NEXT_PUBLIC_API_URL (= https://<your-alb-or-domain>/api),
       BACKEND_ALB_URL (= https://<alb-dns>)

    7. VERIFY EC2 IS STILL RUNNING
       The existing EC2 instance is completely untouched by this Terraform.
       Cut over DNS only after smoke-testing ECS.
    ═══════════════════════════════════════════════════════════════════════
  EOT
}
