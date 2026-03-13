terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # ── Bootstrap ONCE before first terraform init ────────────────────────────
  # Run infra/scripts/bootstrap-ca.sh — it creates the state bucket and lock
  # table in ca-central-1, then calls terraform init automatically.
  backend "s3" {
    bucket         = "agent-tfstate-ca-978027421922"   # replaced by bootstrap-ca.sh
    key            = "prod-ca/terraform.tfstate"
    region         = "ca-central-1"
    dynamodb_table = "agent-tfstate-lock-ca"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}
