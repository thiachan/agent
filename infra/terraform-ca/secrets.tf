# ── Secrets Manager ───────────────────────────────────────────────────────────
# One JSON secret holds all app config. The External Secrets Operator reads this
# and projects it into a Kubernetes Secret that pods consume as env vars.
#
# After terraform apply, populate the real values:
#   cp infra/secrets-template.json /tmp/secrets-prod-ca.json
#   # edit /tmp/secrets-prod-ca.json with real values
#   aws secretsmanager put-secret-value \
#     --secret-id agent-prod-ca-app-secrets \
#     --secret-string file:///tmp/secrets-prod-ca.json \
#     --region ca-central-1
#   rm /tmp/secrets-prod-ca.json

resource "aws_secretsmanager_secret" "app" {
  name        = "${local.name}-app-secrets"
  description = "All application secrets for ${local.name}"

  recovery_window_in_days = 7

  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "app_placeholder" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL           = "postgresql+psycopg2://${var.db_username}:REPLACE@${aws_rds_cluster.main.endpoint}:5432/${var.db_name}"
    SECRET_KEY             = "REPLACE_WITH_STRONG_RANDOM_KEY"
    OPENAI_API_KEY         = "REPLACE"
    CISCO_CLIENT_ID        = "REPLACE"
    CISCO_CLIENT_SECRET    = "REPLACE"
    CISCO_ENDPOINT         = "https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions"
    CISCO_APPKEY           = "REPLACE"
    PRESENTON_API_URL      = "REPLACE"
    PRESENTON_API_KEY      = "REPLACE"
    MAIL_USERNAME          = "REPLACE"
    MAIL_PASSWORD          = "REPLACE"
    MAIL_FROM              = "noreply@REPLACE"
    MAIL_SERVER            = "smtp.gmail.com"
    MAIL_PORT              = "587"
    NEXT_PUBLIC_API_URL    = "https://REPLACE/api"
    FRONTEND_URL           = "https://REPLACE"
    OPENAI_TTS_VOICE_HOST  = "nova"
    OPENAI_TTS_VOICE_GUEST = "onyx"
  })

  lifecycle {
    # Never overwrite real secrets once the ops team fills them in
    ignore_changes = [secret_string]
  }
}
