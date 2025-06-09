# Summit Infrastructure Configuration
# 
# This is a minimal Terraform configuration designed to work with limited
# IAM permissions in CI/CD environments. It assumes:
# - APIs are already enabled manually
# - Service accounts exist and have proper roles assigned
# - Focus on managing cluster and database resources only

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

variable "create_service_accounts" {
  description = "Whether to create service accounts (requires IAM admin permissions)"
  type        = bool
  default     = false
}

variable "create_iam_bindings" {
  description = "Whether to create IAM bindings (requires IAM admin permissions)"
  type        = bool
  default     = false
}

variable "enable_apis" {
  description = "Whether to enable APIs (requires serviceusage.serviceUsageAdmin)"
  type        = bool
  default     = false
}

variable "gke_service_account_email" {
  description = "Email of existing GKE service account"
  type        = string
  default     = ""
}

variable "summit_agent_service_account_email" {
  description = "Email of existing Summit agent service account"
  type        = string
  default     = ""
}

# Local variables for service account emails
locals {
  gke_sa_email = var.create_service_accounts ? google_service_account.gke_service_account[0].email : (
    var.gke_service_account_email != "" ? var.gke_service_account_email : "${var.project_id}-compute@developer.gserviceaccount.com"
  )
  summit_agent_sa_email = var.create_service_accounts ? google_service_account.summit_agent_sa[0].email : (
    var.summit_agent_service_account_email != "" ? var.summit_agent_service_account_email : "summit-agent@${var.project_id}.iam.gserviceaccount.com"
  )
}

# CONDITIONAL RESOURCES - Only created if explicitly enabled

# Enable required APIs (only if enabled)
resource "google_project_service" "apis" {
  for_each = var.enable_apis ? toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtasks.googleapis.com",
    "sqladmin.googleapis.com"
  ]) : toset([])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = true
}

# Service accounts (only if enabled)
resource "google_service_account" "gke_service_account" {
  count        = var.create_service_accounts ? 1 : 0
  account_id   = "summit-gke-sa"
  display_name = "Summit GKE Service Account"
  project      = var.project_id
}

resource "google_service_account" "summit_agent_sa" {
  count        = var.create_service_accounts ? 1 : 0
  account_id   = "summit-agent"
  display_name = "Summit Agent Service Account"
  project      = var.project_id
}

# IAM bindings (only if enabled)
resource "google_project_iam_member" "gke_service_account_roles" {
  for_each = var.create_iam_bindings ? toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer"
  ]) : toset([])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${local.gke_sa_email}"
}

resource "google_project_iam_member" "summit_agent_roles" {
  for_each = var.create_iam_bindings ? toset([
    "roles/cloudsql.client",
    "roles/cloudtasks.admin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ]) : toset([])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${local.summit_agent_sa_email}"
}

resource "google_service_account_iam_binding" "summit_workload_identity" {
  count              = var.create_iam_bindings ? 1 : 0
  service_account_id = local.summit_agent_sa_email
  role               = "roles/iam.workloadIdentityUser"
  
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[summit/summit-ksa]"
  ]
}

# CORE INFRASTRUCTURE - Always managed

# GKE Cluster
resource "google_container_cluster" "summit_cluster" {
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

  depends_on = [google_project_service.apis]
}

# OpenCode Node Pool
resource "google_container_node_pool" "opencode_nodes" {
  name       = "opencode-pool"
  location   = var.region
  cluster    = google_container_cluster.summit_cluster.name
  node_count = 1

  autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    preemptible  = false
    machine_type = "e2-standard-4"
    disk_size_gb = 50

    # Use existing service account
    service_account = local.gke_sa_email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    tags = ["summit", "opencode"]
  }

  depends_on = [google_container_cluster.summit_cluster]
}

# Cloud Tasks Queue
resource "google_cloud_tasks_queue" "summit_agent_queue" {
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

# PostgreSQL Database Instance
resource "google_sql_database_instance" "summit_postgres" {
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
  name     = "summit"
  instance = google_sql_database_instance.summit_postgres.name
}

resource "google_sql_user" "summit_user" {
  name     = "summit"
  instance = google_sql_database_instance.summit_postgres.name
  password = "***REMOVED***"
}

# Firewall rule for MCP server (only if network permissions available)
resource "google_compute_firewall" "summit_mcp_firewall" {
  name    = "summit-mcp-firewall"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["3000", "8000", "8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["summit", "opencode"]
}

# Output values
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.summit_cluster.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.summit_cluster.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = google_container_cluster.summit_cluster.master_auth.0.cluster_ca_certificate
  sensitive   = true
}

output "database_connection_name" {
  description = "PostgreSQL connection name"
  value       = google_sql_database_instance.summit_postgres.connection_name
}

output "database_public_ip" {
  description = "PostgreSQL public IP"
  value       = google_sql_database_instance.summit_postgres.public_ip_address
}

output "database_private_ip" {
  description = "PostgreSQL private IP"
  value       = google_sql_database_instance.summit_postgres.private_ip_address
}

output "gke_service_account_email" {
  description = "GKE service account email"
  value       = local.gke_sa_email
}

output "summit_agent_service_account_email" {
  description = "Summit agent service account email"
  value       = local.summit_agent_sa_email
}
