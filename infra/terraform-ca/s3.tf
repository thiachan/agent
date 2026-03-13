# ── S3 Buckets ────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "uploads" {
  bucket        = "${local.name}-uploads-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
  tags          = merge(local.tags, { Name = "${local.name}-uploads" })
}

resource "aws_s3_bucket" "generated" {
  bucket        = "${local.name}-generated-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
  tags          = merge(local.tags, { Name = "${local.name}-generated" })
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "generated" {
  bucket = aws_s3_bucket.generated.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "generated" {
  bucket                  = aws_s3_bucket.generated.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
