# ── Secrets Manager ───────────────────────────────────────────────────────────
#
# One secret, JSON-encoded, with all app config.
# Populate it once with:
#   aws secretsmanager create-secret \
#     --name agent-prod-app-secrets \
#     --secret-string file://infra/secrets-template.json
#
# Then update individual fields:
#   aws secretsmanager put-secret-value \
#     --secret-id agent-prod-app-secrets \
#     --secret-string '{"OPENAI_API_KEY":"sk-...",...}'

resource "aws_secretsmanager_secret" "app" {
  name        = "${local.name}-app-secrets"
  description = "All application secrets for ${local.name}"

  # Prevents accidental deletion — remove recovery_window_in_days = 0 to disable
  recovery_window_in_days = 7

  tags = local.tags
}

# Placeholder secret value — CI/CD or ops team fills in real values
resource "aws_secretsmanager_secret_version" "app_placeholder" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL        = "postgresql+psycopg2://${var.db_username}:REPLACE@${aws_rds_cluster.main.endpoint}:5432/${var.db_name}"
    SECRET_KEY          = "REPLACE_WITH_STRONG_RANDOM_KEY"
    OPENAI_API_KEY      = "REPLACE"
    CISCO_CLIENT_ID     = "REPLACE"
    CISCO_CLIENT_SECRET = "REPLACE"
    CISCO_ENDPOINT      = "https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions"
    CISCO_APPKEY        = "REPLACE"
    PRESENTON_API_URL   = "REPLACE"
    PRESENTON_API_KEY   = "REPLACE"
    MAIL_USERNAME       = "REPLACE"
    MAIL_PASSWORD       = "REPLACE"
    MAIL_FROM           = "noreply@REPLACE"
    NEXT_PUBLIC_API_URL = "https://REPLACE/api"
  })

  lifecycle {
    # Never overwrite real secrets once set by ops team
    ignore_changes = [secret_string]
  }
}

# ── IAM: ECS Execution Role ───────────────────────────────────────────────────
# Used by ECS agent to pull images from ECR and inject secrets at task start.

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "${local.name}-ecs-execution-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.app.arn]
    }]
  })
}

# ── IAM: ECS Task Role ────────────────────────────────────────────────────────
# Used by application code running inside the container (S3, Bedrock, etc.)

resource "aws_iam_role" "ecs_task" {
  name = "${local.name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${local.name}-ecs-task-s3"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
          "s3:GetObjectAttributes", "s3:HeadObject"
        ]
        Resource = [
          "${aws_s3_bucket.uploads.arn}/*",
          "${aws_s3_bucket.generated.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.uploads.arn, aws_s3_bucket.generated.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "${local.name}-ecs-task-bedrock"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ]
      Resource = ["arn:aws:bedrock:${var.aws_region}::foundation-model/*"]
    }]
  })
}

# ── IAM: GitHub Actions deploy user ──────────────────────────────────────────
# Create this user once. Add its access key to GitHub Secrets.

resource "aws_iam_user" "github_actions" {
  name = "${local.name}-github-actions"
  tags = local.tags
}

resource "aws_iam_user_policy" "github_actions" {
  name = "${local.name}-github-actions-policy"
  user = aws_iam_user.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR push
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload", "ecr:PutImage"
        ]
        Resource = [
          aws_ecr_repository.backend.arn,
          aws_ecr_repository.frontend.arn
        ]
      },
      # ECS rolling deploy
      {
        Effect = "Allow"
        Action = [
          "ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition",
          "ecs:UpdateService", "ecs:DescribeServices",
          "ecs:ListTasks", "ecs:DescribeTasks"
        ]
        Resource = ["*"]
      },
      # Pass execution + task roles to ECS
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.ecs_execution.arn, aws_iam_role.ecs_task.arn]
      }
    ]
  })
}
