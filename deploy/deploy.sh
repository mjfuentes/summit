#!/bin/bash

# Summit AI Deployment Script
# Handles deployment to different environments with proper validation and rollback

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_ENV="production"
DEFAULT_REGISTRY="ghcr.io/mjfuentes/summit"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Summit AI Deployment Script

Usage: $0 [OPTIONS] ENVIRONMENT

ENVIRONMENTS:
    dev         Development environment (local)
    staging     Staging environment (testing)
    production  Production environment (live)

OPTIONS:
    -i, --image TAG     Docker image tag (default: latest)
    -r, --registry URL  Docker registry URL (default: $DEFAULT_REGISTRY)
    -d, --dry-run       Show what would be deployed without executing
    -f, --force         Force deployment without confirmation
    -h, --help          Show this help message
    --rollback          Rollback to previous version
    --health-check      Run health checks only
    --backup            Create backup before deployment
    
EXAMPLES:
    $0 production                                   # Deploy latest to production
    $0 staging --image v1.2.3                     # Deploy specific version to staging  
    $0 dev --dry-run                               # Dry run for development
    $0 production --rollback                       # Rollback production
    $0 staging --health-check                      # Health check staging

ENVIRONMENT VARIABLES:
    ANTHROPIC_API_KEY     Required for AI functionality
    GITHUB_TOKEN          Required for autonomous git operations
    POSTGRES_PASSWORD     Required for database (production)
    GRAFANA_PASSWORD      Optional for monitoring dashboard
    
EOF
}

# Parse command line arguments
parse_args() {
    ENVIRONMENT=""
    IMAGE_TAG="latest"
    REGISTRY="$DEFAULT_REGISTRY"
    DRY_RUN=false
    FORCE=false
    ROLLBACK=false
    HEALTH_CHECK_ONLY=false
    BACKUP=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--image)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            --health-check)
                HEALTH_CHECK_ONLY=true
                shift
                ;;
            --backup)
                BACKUP=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                log_error "Unknown option $1"
                usage
                exit 1
                ;;
            *)
                if [[ -z "$ENVIRONMENT" ]]; then
                    ENVIRONMENT="$1"
                else
                    log_error "Multiple environments specified"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment is required"
        usage
        exit 1
    fi
    
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        usage
        exit 1
    fi
}

# Validate environment
validate_environment() {
    log_info "Validating environment: $ENVIRONMENT"
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    # Check environment variables
    local required_vars=("ANTHROPIC_API_KEY" "GITHUB_TOKEN")
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        required_vars+=("POSTGRES_PASSWORD")
    fi
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable not set: $var"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

# Load environment configuration
load_config() {
    local config_file="$SCRIPT_DIR/config/$ENVIRONMENT.env"
    
    if [[ -f "$config_file" ]]; then
        log_info "Loading configuration from $config_file"
        set -a
        source "$config_file"
        set +a
    else
        log_warning "No configuration file found for $ENVIRONMENT"
    fi
    
    # Set environment-specific defaults
    case "$ENVIRONMENT" in
        dev)
            export SUMMIT_ENV="development"
            export SUMMIT_LOG_LEVEL="debug"
            ;;
        staging)
            export SUMMIT_ENV="staging"
            export SUMMIT_LOG_LEVEL="info"
            ;;
        production)
            export SUMMIT_ENV="production"
            export SUMMIT_LOG_LEVEL="warning"
            export SUMMIT_READONLY_MODE="false"
            ;;
    esac
}

# Health check function
health_check() {
    local service_url="$1"
    local max_attempts=30
    local attempt=1
    
    log_info "Running health check for $service_url"
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url/health" > /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying in 10s..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Backup function
create_backup() {
    if [[ "$ENVIRONMENT" != "production" ]]; then
        log_info "Skipping backup for non-production environment"
        return 0
    fi
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_dir="$SCRIPT_DIR/backups/$timestamp"
    
    log_info "Creating backup: $backup_dir"
    mkdir -p "$backup_dir"
    
    # Backup data volumes
    if docker volume ls | grep -q "summit-data"; then
        docker run --rm -v summit-data:/data -v "$backup_dir":/backup alpine tar czf /backup/summit-data.tar.gz -C /data .
    fi
    
    # Backup database
    if docker ps | grep -q "summit-postgres"; then
        docker exec summit-postgres pg_dump -U summit summit > "$backup_dir/database.sql"
    fi
    
    log_success "Backup created: $backup_dir"
}

# Rollback function
rollback_deployment() {
    log_warning "Rolling back deployment for $ENVIRONMENT"
    
    local backup_dir=$(ls -1t "$SCRIPT_DIR/backups" | head -n 1)
    if [[ -z "$backup_dir" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    log_info "Rolling back to backup: $backup_dir"
    
    # Stop current services
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down
    
    # Restore data
    if [[ -f "$SCRIPT_DIR/backups/$backup_dir/summit-data.tar.gz" ]]; then
        docker run --rm -v summit-data:/data -v "$SCRIPT_DIR/backups/$backup_dir":/backup alpine tar xzf /backup/summit-data.tar.gz -C /data
    fi
    
    # Start services with previous image
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
    
    log_success "Rollback completed"
}

# Deployment function
deploy_services() {
    log_info "Deploying Summit AI to $ENVIRONMENT"
    
    cd "$SCRIPT_DIR"
    
    # Set image tag in environment
    export IMAGE_TAG="$IMAGE_TAG"
    export REGISTRY="$REGISTRY"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN - Would execute:"
        echo "docker-compose -f docker-compose.yml pull"
        echo "docker-compose -f docker-compose.yml up -d"
        return 0
    fi
    
    # Pull latest images
    log_info "Pulling Docker images..."
    docker-compose -f docker-compose.yml pull
    
    # Start services
    log_info "Starting services..."
    docker-compose -f docker-compose.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 30
    
    # Run health checks
    health_check "http://localhost:8000"
    
    log_success "Deployment completed successfully"
}

# Main deployment workflow
main() {
    parse_args "$@"
    
    log_info "Summit AI Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Image: $REGISTRY:$IMAGE_TAG"
    log_info "Date: $(date)"
    
    if [[ "$HEALTH_CHECK_ONLY" == "true" ]]; then
        health_check "http://localhost:8000"
        exit $?
    fi
    
    if [[ "$ROLLBACK" == "true" ]]; then
        rollback_deployment
        exit 0
    fi
    
    validate_environment
    load_config
    
    if [[ "$BACKUP" == "true" ]] || [[ "$ENVIRONMENT" == "production" ]]; then
        create_backup
    fi
    
    # Confirmation for production
    if [[ "$ENVIRONMENT" == "production" ]] && [[ "$FORCE" != "true" ]]; then
        echo -n "Deploy to PRODUCTION? (yes/no): "
        read -r confirmation
        if [[ "$confirmation" != "yes" ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    deploy_services
    
    log_success "Summit AI deployment to $ENVIRONMENT completed!"
    log_info "Access points:"
    case "$ENVIRONMENT" in
        dev)
            log_info "  Web Interface: http://localhost:8000"
            log_info "  API Docs: http://localhost:8000/docs"
            ;;
        staging)
            log_info "  Web Interface: https://staging.summit.ai"
            log_info "  Monitoring: https://monitoring.staging.summit.ai"
            ;;
        production)
            log_info "  Web Interface: https://summit.ai"
            log_info "  Monitoring: https://monitoring.summit.ai"
            log_info "  Status: https://status.summit.ai"
            ;;
    esac
}

# Run main function
main "$@" 