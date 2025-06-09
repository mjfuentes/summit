# TODO: Consider migrating from Cloud Tasks to a system with better backpressure handling
# Current Cloud Tasks setup works but has limitations:
# - No native backpressure for overwhelmed agents
# - HTTP endpoint requirement adds complexity
# Future options: Pub/Sub with pull subscriptions, database polling with atomic claiming,
# or custom queue system with agent load awareness

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
  description = "Whether to create new service accounts (requires elevated IAM permissions)"
  type        = bool
  default     = false
}

variable "gke_service_account_email" {
  description = "Email of existing GKE service account (if not creating new ones)"
  type        = string
  default     = ""
}

variable "summit_agent_service_account_email" {
  description = "Email of existing Summit agent service account (if not creating new ones)"
  type        = string
  default     = ""
}

# Google Cloud Provider
# Authentication is handled via:
# 1. GOOGLE_APPLICATION_CREDENTIALS environment variable (service account key)
# 2. gcloud auth application-default login (for local development)  
# 3. Workload Identity (for GitHub Actions)
#
# Required IAM permissions for the service account running this Terraform:
# - roles/container.admin (for GKE cluster management)
# - roles/compute.admin (for firewall rules and networks)
# - roles/iam.serviceAccountAdmin (if creating service accounts)
# - roles/iam.serviceAccountUser (for service account impersonation)
# - roles/cloudsql.admin (for Cloud SQL instance management)
# - roles/cloudtasks.admin (for Cloud Tasks queue management)
# - roles/serviceusage.serviceUsageAdmin (for enabling APIs)
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtasks.googleapis.com",
    "sqladmin.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = true
}

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

# Node Pool for OpenCode agents
resource "google_container_node_pool" "opencode_nodes" {
  name       = "opencode-pool"
  location   = var.region
  cluster    = google_container_cluster.summit_cluster.name
  node_count = 1

  node_config {
    preemptible  = false
    machine_type = "e2-small"  # 2 vCPU, 2GB RAM

    # Use existing service account or default Compute Engine service account
    service_account = var.create_service_accounts ? google_service_account.gke_service_account[0].email : (
      var.gke_service_account_email != "" ? var.gke_service_account_email : "${var.project_id}-compute@developer.gserviceaccount.com"
    )
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      purpose = "opencode-agents"
    }

    tags = ["summit", "opencode"]

    # Shielded VM features
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  # Auto-scaling
  autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

  # Auto-upgrade and auto-repair
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Service Account for GKE nodes (only if create_service_accounts is true)
resource "google_service_account" "gke_service_account" {
  count        = var.create_service_accounts ? 1 : 0
  account_id   = "summit-gke-sa"
  display_name = "Summit GKE Service Account"
}

# Service Account for Summit agents (only if create_service_accounts is true)
resource "google_service_account" "summit_agent_sa" {
  count        = var.create_service_accounts ? 1 : 0
  account_id   = "summit-agent"
  display_name = "Summit Agent Service Account"
}

# Local variables for service account emails (no data sources needed)
locals {
  gke_sa_email = var.create_service_accounts ? google_service_account.gke_service_account[0].email : (
    var.gke_service_account_email != "" ? var.gke_service_account_email : "${var.project_id}-compute@developer.gserviceaccount.com"
  )
  summit_agent_sa_email = var.create_service_accounts ? google_service_account.summit_agent_sa[0].email : (
    var.summit_agent_service_account_email != "" ? var.summit_agent_service_account_email : "summit-agent@${var.project_id}.iam.gserviceaccount.com"
  )
}

# IAM bindings for the GKE service account
resource "google_project_iam_member" "gke_service_account_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${local.gke_sa_email}"
}

# IAM bindings for the Summit agent service account
resource "google_project_iam_member" "summit_agent_roles" {
  for_each = toset([
    "roles/cloudtasks.admin",
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${local.summit_agent_sa_email}"
}

# Cloud Tasks Queue
resource "google_cloud_tasks_queue" "summit_agent_queue" {
  name     = "summit-agent-queue"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 10
    max_concurrent_dispatches = 50
  }

  retry_config {
    max_attempts       = 3
    max_retry_duration = "300s"
    min_backoff        = "1s"
    max_backoff        = "60s"
  }

  depends_on = [google_project_service.apis]
}

# PostgreSQL Database (Cloud SQL)
resource "google_sql_database_instance" "summit_postgres" {
  name             = "summit-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = false

  settings {
    tier = "db-f1-micro"  # 1 vCPU, 0.6GB RAM - cheapest tier
    
    disk_type = "PD_SSD"
    disk_size = 10  # 10GB minimum

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
        value = "0.0.0.0/0"  # In production, restrict this to your IP ranges
      }
    }

    database_flags {
      name  = "max_connections"
      value = "50"
    }
  }

  depends_on = [google_project_service.apis]
}

# Create the summit database
resource "google_sql_database" "summit_db" {
  name     = "summit"
  instance = google_sql_database_instance.summit_postgres.name
}

# Create database user
resource "google_sql_user" "summit_user" {
  name     = "summit"
  instance = google_sql_database_instance.summit_postgres.name
  password = "summit123"  # In production, use a random password
}

# Workload Identity binding for Cloud SQL access (only if creating service accounts)
resource "google_service_account_iam_binding" "summit_workload_identity" {
  count              = var.create_service_accounts ? 1 : 0
  service_account_id = google_service_account.summit_agent_sa[0].name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[summit/summit-ksa]"
  ]
}

# Firewall rules for MCP server (try to create, but don't fail if permissions are insufficient)
resource "google_compute_firewall" "summit_mcp_firewall" {
  name    = "summit-mcp-firewall"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = ["0.0.0.0/0"]  # In production, restrict this
  target_tags   = ["summit", "mcp-server"]

  lifecycle {
    ignore_changes = all
  }
}

# Outputs
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
  value       = google_container_cluster.summit_cluster.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "database_connection_name" {
  description = "PostgreSQL database connection name"
  value       = google_sql_database_instance.summit_postgres.connection_name
}

output "database_private_ip" {
  description = "PostgreSQL database private IP"
  value       = google_sql_database_instance.summit_postgres.private_ip_address
}

output "database_public_ip" {
  description = "PostgreSQL database public IP"
  value       = google_sql_database_instance.summit_postgres.public_ip_address
}

output "gke_service_account_email" {
  description = "Email of the GKE service account being used"
  value       = local.gke_sa_email
}

output "summit_agent_service_account_email" {
  description = "Email of the Summit agent service account being used"
  value       = local.summit_agent_sa_email
}