# ── EKS Cluster ───────────────────────────────────────────────────────────────
# Uses the official terraform-aws-modules/eks module (v20.x).
# The module creates: cluster, OIDC provider, managed node groups,
# node group IAM roles, security groups, and cluster add-ons.

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = local.cluster_name
  cluster_version = var.eks_cluster_version

  # Allow kubectl access from outside the VPC (e.g., GitHub Actions, devs).
  # The API server is still protected by IAM — no unauthenticated access.
  cluster_endpoint_public_access = true

  # Grant Terraform caller (the IAM identity running `terraform apply`)
  # cluster-admin so it can manage add-ons, Helm charts, and manifests.
  enable_cluster_creator_admin_permissions = true

  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private[*].id

  # ── EKS Managed Add-ons ─────────────────────────────────────────────────────
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent    = true
      # Enable prefix delegation to fit more pods per node
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
    # EBS CSI driver is managed separately below (aws_eks_addon.ebs_csi) to
    # avoid a circular dependency: the addon needs an IAM role ARN, but the
    # IAM role needs the cluster's OIDC URL — which only exists after apply.
  }

  # ── Managed Node Groups ───────────────────────────────────────────────────
  eks_managed_node_groups = {

    # On-demand: always-on nodes for system pods, db-init jobs, etc.
    on_demand = {
      min_size     = var.node_ondemand_min
      max_size     = var.node_ondemand_max
      desired_size = var.node_ondemand_min

      instance_types = ["m5.large", "m5a.large"]
      capacity_type  = "ON_DEMAND"

      labels = {
        "node/type" = "on-demand"
      }

      # Cluster Autoscaler discovery tags (added to the underlying ASG)
      tags = merge(local.tags, {
        "k8s.io/cluster-autoscaler/enabled"                      = "true"
        "k8s.io/cluster-autoscaler/${local.cluster_name}"        = "owned"
      })
    }

    # Spot: burst capacity for application workloads (up to 80% cheaper)
    spot = {
      min_size     = var.node_spot_min
      max_size     = var.node_spot_max
      desired_size = var.node_spot_min

      # Multiple instance types → Spot reduces interruption risk
      instance_types = ["m5.large", "m5a.large", "m6i.large", "m5.xlarge", "m5a.xlarge"]
      capacity_type  = "SPOT"

      labels = {
        "node/type" = "spot"
      }

      # Tolerate interruptions gracefully: allow Spot node eviction taint
      taints = [{
        key    = "spot"
        value  = "true"
        effect = "PREFER_NO_SCHEDULE"
      }]

      tags = merge(local.tags, {
        "k8s.io/cluster-autoscaler/enabled"                      = "true"
        "k8s.io/cluster-autoscaler/${local.cluster_name}"        = "owned"
      })
    }
  }

  # Ship control-plane logs to CloudWatch
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = local.tags
}

# ── CloudWatch Log Group for EKS control plane ────────────────────────────────

resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${local.cluster_name}/cluster"
  retention_in_days = 30
  tags              = local.tags
}

# ── EBS CSI Driver add-on (separate to break circular OIDC dependency) ────────
# IAM role is defined in iam.tf; it depends on module.eks.cluster_oidc_issuer_url.
# By placing the addon in its own resource (not inside the module block),
# Terraform correctly sequences: cluster → IAM role → addon.

resource "aws_eks_addon" "ebs_csi" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = "v1.28.0-eksbuild.1"
  service_account_role_arn = aws_iam_role.ebs_csi_driver.arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [module.eks, aws_iam_role.ebs_csi_driver]
  tags       = local.tags
}

# ── CloudWatch Log Groups for application pods ────────────────────────────────

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/k8s/${local.name}/backend"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/k8s/${local.name}/frontend"
  retention_in_days = 14
  tags              = local.tags
}
