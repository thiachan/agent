variable "aws_region"    { type = string; default = "us-east-1" }
variable "project"       { type = string; default = "agent" }
variable "environment"   { type = string; default = "prod" }

variable "vpc_cidr"             { type = string; default = "10.0.0.0/16" }
variable "public_subnet_cidrs"  { type = list(string); default = ["10.0.1.0/24","10.0.2.0/24"] }
variable "private_subnet_cidrs" { type = list(string); default = ["10.0.11.0/24","10.0.12.0/24"] }
variable "availability_zones"   { type = list(string); default = ["us-east-1a","us-east-1b"] }

variable "db_name"           { type = string;  default   = "agentdb" }
variable "db_username"       { type = string;  default   = "agentuser" }
variable "db_password"       { type = string;  sensitive = true; description = "Set via TF_VAR_db_password" }
variable "db_instance_class" { type = string;  default   = "db.serverless" }

variable "backend_cpu"    { type = number; default = 1024 }
variable "backend_memory" { type = number; default = 2048 }
variable "frontend_cpu"   { type = number; default = 512 }
variable "frontend_memory"{ type = number; default = 1024 }

variable "backend_min_tasks"  { type = number; default = 2 }
variable "backend_max_tasks"  { type = number; default = 10 }
variable "frontend_min_tasks" { type = number; default = 2 }
variable "frontend_max_tasks" { type = number; default = 6 }

variable "domain_name"         { type = string; default = "" }
variable "acm_certificate_arn" { type = string; default = "" }
