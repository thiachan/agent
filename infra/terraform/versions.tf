terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # One-time bootstrap before first apply:
  #   aws s3 mb s3://agent-tfstate-<ACCOUNT_ID> --region us-east-1
  #   aws dynamodb create-table --table-name agent-tfstate-lock \
  #     --attribute-definitions AttributeName=LockID,AttributeType=S \
  #     --key-schema AttributeName=LockID,KeyType=HASH \
  #     --billing-mode PAY_PER_REQUEST --region us-east-1
  backend "s3" {
    bucket         = "agent-tfstate-REPLACE_WITH_ACCOUNT_ID"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "agent-tfstate-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}
