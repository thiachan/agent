# ── RDS Aurora PostgreSQL Serverless v2 ───────────────────────────────────────
# Serverless v2 scales ACUs (Aurora Capacity Units) from 0.5 to 8 automatically;
# you pay per-second for what you use.

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  tags       = local.tags
}

# Allow inbound 5432 only from EKS worker nodes
resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "PostgreSQL from EKS nodes only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.name}-rds-sg" })
}

resource "aws_rds_cluster" "main" {
  cluster_identifier        = "${local.name}-aurora"
  engine                    = "aurora-postgresql"
  engine_mode               = "provisioned"
  engine_version            = "15.4"
  database_name             = var.db_name
  master_username           = var.db_username
  master_password           = var.db_password
  db_subnet_group_name      = aws_db_subnet_group.main.name
  vpc_security_group_ids    = [aws_security_group.rds.id]
  storage_encrypted         = true
  backup_retention_period   = 7
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-final-snapshot"

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 8
  }

  tags = local.tags
}

resource "aws_rds_cluster_instance" "writer" {
  identifier           = "${local.name}-aurora-writer"
  cluster_identifier   = aws_rds_cluster.main.id
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.main.engine
  engine_version       = aws_rds_cluster.main.engine_version
  db_subnet_group_name = aws_db_subnet_group.main.name
  publicly_accessible  = false
  tags                 = local.tags
}
