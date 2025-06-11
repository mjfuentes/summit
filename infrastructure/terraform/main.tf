# Summit Infrastructure Configuration
# 
# This configuration imports and manages existing resources rather than creating new ones.
# This approach requires minimal permissions and avoids IAM/creation permission issues.

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "summit-ai-platform"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "GKE Cluster Name"
  type        = string
  default     = "summit-cluster"
}

variable "manage_cluster" {
  description = "Whether to manage the GKE cluster (requires container.admin permissions)"
  type        = bool
  default     = false
}

variable "manage_database" {
  description = "Whether to manage the Cloud SQL database (requires cloudsql.admin permissions)"
  type        = bool
  default     = false
}

variable "manage_firewall" {
  description = "Whether to manage firewall rules (requires compute.admin permissions)"
  type        = bool
  default     = false
}

variable "manage_tasks" {
  description = "Whether to manage Cloud Tasks queues (requires cloudtasks.admin permissions)"
  type        = bool
  default     = false
}

# IMPORT EXISTING RESOURCES - Read-only operations

# Import existing GKE cluster (if it exists)
data "google_container_cluster" "existing_cluster" {
  count    = var.manage_cluster ? 0 : 1
  name     = var.cluster_name
  location = var.region
  project  = var.project_id
}

# Import existing Cloud SQL instance (if it exists)
data "google_sql_database_instance" "existing_postgres" {
  count   = var.manage_database ? 0 : 1
  name    = "summit-postgres"
  project = var.project_id
}

# CONDITIONAL RESOURCES - Only created if explicitly enabled

# GKE Cluster (only if manage_cluster is true)
resource "google_container_cluster" "summit_cluster" {
  count    = var.manage_cluster ? 1 : 0
  name     = var.cluster_name
  location = var.region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  # Networking
  network    = "default"
  subnetwork = "default"

  # Security
  enable_shielded_nodes = true
  
  # Workload Identity for secure access to GCP services
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Logging and monitoring
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Maintenance policy
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
}

# Cloud Tasks Queue (only if manage_tasks is true)
resource "google_cloud_tasks_queue" "summit_agent_queue" {
  count    = var.manage_tasks ? 1 : 0
  name     = "summit-agent-queue"
  location = var.region
  project  = var.project_id

  retry_config {
    max_attempts       = 3
    max_retry_duration = "300s"
    max_backoff        = "60s"
    min_backoff        = "5s"
    max_doublings      = 3
  }

  rate_limits {
    max_dispatches_per_second = 10
  }
}

# PostgreSQL Database Instance (only if manage_database is true)
resource "google_sql_database_instance" "summit_postgres" {
  count               = var.manage_database ? 1 : 0
  name                = "summit-postgres"
  database_version    = "POSTGRES_15"
  region             = var.region
  deletion_protection = false

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 20
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }

    ip_configuration {
      ipv4_enabled    = true
      authorized_networks {
        name  = "allow-all"
        value = "0.0.0.0/0"
      }
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
  }
}

resource "google_sql_database" "summit_db" {
  count    = var.manage_database ? 1 : 0
  name     = "summit"
  instance = google_sql_database_instance.summit_postgres[0].name
}

resource "google_sql_user" "summit_user" {
  count    = var.manage_database ? 1 : 0
  name     = "summit"
  instance = google_sql_database_instance.summit_postgres[0].name
  password = "***REMOVED***"
}

# Firewall rule (only if manage_firewall is true)
resource "google_compute_firewall" "summit_mcp_firewall" {
  count   = var.manage_firewall ? 1 : 0
  name    = "summit-mcp-firewall"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["3000", "8000", "8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["summit", "opencode"]
}

# Local values for outputs (using either managed or existing resources)
locals {
  cluster_name = var.manage_cluster ? google_container_cluster.summit_cluster[0].name : (
    length(data.google_container_cluster.existing_cluster) > 0 ? data.google_container_cluster.existing_cluster[0].name : var.cluster_name
  )
  cluster_endpoint = var.manage_cluster ? google_container_cluster.summit_cluster[0].endpoint : (
    length(data.google_container_cluster.existing_cluster) > 0 ? data.google_container_cluster.existing_cluster[0].endpoint : ""
  )
  cluster_ca_certificate = var.manage_cluster ? google_container_cluster.summit_cluster[0].master_auth.0.cluster_ca_certificate : (
    length(data.google_container_cluster.existing_cluster) > 0 ? data.google_container_cluster.existing_cluster[0].master_auth.0.cluster_ca_certificate : ""
  )
  database_connection_name = var.manage_database ? google_sql_database_instance.summit_postgres[0].connection_name : (
    length(data.google_sql_database_instance.existing_postgres) > 0 ? data.google_sql_database_instance.existing_postgres[0].connection_name : ""
  )
}

# Output values
output "cluster_name" {
  description = "GKE cluster name"
  value       = local.cluster_name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = local.cluster_endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = local.cluster_ca_certificate
  sensitive   = true
}

output "database_connection_name" {
  description = "PostgreSQL connection name"
  value       = local.database_connection_name
}

output "gke_service_account_email" {
  description = "GKE service account email"
  value       = "${var.project_id}-compute@developer.gserviceaccount.com"
}

output "summit_agent_service_account_email" {
  description = "Summit agent service account email"
  value       = "summit-agent@${var.project_id}.iam.gserviceaccount.com"
}
