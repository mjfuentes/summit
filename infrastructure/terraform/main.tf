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

provider "google" {
  credentials = file("../../terraform-key.json")
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
    "firestore.googleapis.com"
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
}

# Node Pool for OpenCode agents
resource "google_container_node_pool" "opencode_nodes" {
  name       = "opencode-pool"
  location   = var.region
  cluster    = google_container_cluster.summit_cluster.name
  node_count = 2

  node_config {
    preemptible  = false
    machine_type = "e2-standard-2"  # 2 vCPU, 8GB RAM

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_service_account.email
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
    max_node_count = 5
  }

  # Auto-upgrade and auto-repair
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Service Account for GKE nodes
resource "google_service_account" "gke_service_account" {
  account_id   = "summit-gke-sa"
  display_name = "Summit GKE Service Account"
}

# Service Account for Summit agents (Cloud Tasks access)
resource "google_service_account" "summit_agent_sa" {
  account_id   = "summit-agent"
  display_name = "Summit Agent Service Account"
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
  member  = "serviceAccount:${google_service_account.gke_service_account.email}"
}

# IAM bindings for the Summit agent service account
resource "google_project_iam_member" "summit_agent_roles" {
  for_each = toset([
    "roles/cloudtasks.admin",
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.summit_agent_sa.email}"
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

# Firestore Database
resource "google_firestore_database" "summit_database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
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