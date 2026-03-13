variable "aws_region" {
  type    = string
  default = "ca-central-1"
}

variable "project" {
  type    = string
  default = "agent"
}

variable "environment" {
  type    = string
  default = "prod"
}

# ── Networking ────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  type    = string
  default = "10.1.0.0/16"   # differs from existing 10.0.0.0/16 (no overlap)
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.1.1.0/24", "10.1.2.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.1.11.0/24", "10.1.12.0/24"]
}

variable "availability_zones" {
  type    = list(string)
  default = ["ca-central-1a", "ca-central-1b"]
}

# ── EKS ───────────────────────────────────────────────────────────────────────

variable "eks_cluster_version" {
  type    = string
  default = "1.30"
}

# On-demand node group — always-on, for system workloads
variable "node_ondemand_min" {
  type    = number
  default = 2
}

variable "node_ondemand_max" {
  type    = number
  default = 4
}

# Spot node group — burst capacity, cheaper (70% savings)
variable "node_spot_min" {
  type    = number
  default = 0
}

variable "node_spot_max" {
  type    = number
  default = 10
}

# ── Application scaling ───────────────────────────────────────────────────────

variable "backend_min_replicas" {
  type    = number
  default = 2
}

variable "backend_max_replicas" {
  type    = number
  default = 10
}

variable "frontend_min_replicas" {
  type    = number
  default = 2
}

variable "frontend_max_replicas" {
  type    = number
  default = 8
}

# ── Database ──────────────────────────────────────────────────────────────────

variable "db_name" {
  type    = string
  default = "agentdb"
}

variable "db_username" {
  type    = string
  default = "agentuser"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Set via terraform.tfvars — never commit the real value"
}

# ── Domain / TLS (optional) ───────────────────────────────────────────────────

variable "domain_name" {
  type        = string
  default     = ""
  description = "Your domain, e.g. agent.example.com — leave empty until DNS is ready"
}

variable "acm_certificate_arn" {
  type        = string
  default     = ""
  description = "ACM cert ARN for HTTPS; must be in ca-central-1"
}
