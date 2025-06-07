# summit.ai CI/CD Pipeline

Complete deployment and continuous integration setup for summit.ai autonomous development system.

##  Quick Start

```bash
# Deploy to development
./deploy.sh dev

# Deploy to staging
./deploy.sh staging --image v1.2.3

# Deploy to production (with confirmation)
./deploy.sh production --backup

# Rollback production
./deploy.sh production --rollback
```

##  Table of Contents

- [Architecture Overview](#architecture-overview)
- [CI/CD Workflows](#cicd-workflows)
- [Deployment Environments](#deployment-environments)
- [Configuration Management](#configuration-management)
- [Monitoring & Observability](#monitoring--observability)
- [Deployment Commands](#deployment-commands)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Autonomous Integration](#autonomous-integration)

##  Architecture Overview

summit.ai uses a modern containerized architecture with comprehensive CI/CD pipelines:

```
        
   Development        Staging        Production    
   Environment          Environment          Environment   
        
                                                      
                                                      
        
  Local Docker         GitHub Actions       GitHub Actions 
   Development          Integration          Deployment    
        
```

### Core Components

- **summit.ai Web Server**: Main application with autonomous task management
- **Redis**: Task queues and caching
- **PostgreSQL**: Persistent data storage (production)
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Loki**: Log aggregation
- **Traefik**: Reverse proxy and load balancer

##  CI/CD Workflows

### 1. Main Deployment Pipeline (`.github/workflows/summit-autodeploy.yml`)

Triggered on push to `main` branch with comprehensive stages:

#### Stage 1: Quality Assurance
- **Code Formatting**: Black code formatter validation
- **Linting**: Flake8 code quality checks
- **Type Checking**: MyPy static type analysis
- **Test Suite**: Full pytest execution with coverage
- **Coverage Requirements**: Minimum 70% coverage enforced

#### Stage 2: Security Scanning
- **Vulnerability Scanning**: Bandit security analysis
- **Secret Detection**: TruffleHog secret scanning
- **Dependency Audit**: Known vulnerability checks

#### Stage 3: Build & Registry
- **Docker Image Build**: Multi-stage optimized builds
- **Container Registry**: Push to GitHub Container Registry
- **Image Scanning**: Anchore security vulnerability scan
- **SBOM Generation**: Software Bill of Materials creation

#### Stage 4: Deployment
- **Environment Validation**: Prerequisites and health checks
- **Zero-Downtime Deployment**: Rolling updates with health verification
- **Rollback Capability**: Automatic rollback on failure

#### Stage 5: Integration Testing
- **Autonomous System Testing**: Verify Claude Code integration
- **API Endpoint Validation**: Complete API functionality tests
- **Performance Benchmarks**: Response time and throughput validation

### 2. Monitoring Pipeline (`.github/workflows/autonomous-monitoring.yml`)

Continuous monitoring with automated alerts:

#### Scheduled Monitoring
- **Business Hours**: Every 15 minutes (9 AM - 6 PM UTC)
- **Off Hours**: Every hour
- **Manual Trigger**: On-demand comprehensive checks

#### Monitoring Checks
- **System Health**: Core service availability
- **Performance Metrics**: Response times and throughput
- **Resource Usage**: CPU, memory, and disk utilization
- **Task Analytics**: Autonomous task success rates
- **Security Status**: Vulnerability and access monitoring

#### Alert Management
- **Threshold-based Alerts**: Configurable failure rate thresholds
- **Multi-channel Notifications**: Slack, email, Discord integration
- **Escalation Policies**: Critical vs warning alert handling
- **Automated Remediation**: Self-healing for common issues

##  Deployment Environments

### Development Environment
- **Purpose**: Local development and testing
- **Infrastructure**: Docker Compose on local machine
- **Database**: SQLite or local PostgreSQL
- **Monitoring**: Basic health checks
- **Cost Controls**: $5/day budget limit
- **Features**: Debug logging, hot reload, relaxed security

### Staging Environment
- **Purpose**: Pre-production testing and validation
- **Infrastructure**: Kubernetes or Docker Swarm
- **Database**: PostgreSQL with test data
- **Monitoring**: Full observability stack
- **Cost Controls**: $20/day budget limit
- **Features**: Production-like configuration, performance testing

### Production Environment
- **Purpose**: Live system serving users
- **Infrastructure**: High-availability cluster
- **Database**: PostgreSQL with replication
- **Monitoring**: Comprehensive monitoring and alerting
- **Cost Controls**: $50/day budget limit
- **Features**: SSL/TLS, backup automation, scaling policies

##  Configuration Management

### Environment Files

Each environment has dedicated configuration:

```
deploy/config/
 development.env    # Local development settings
 staging.env       # Staging environment settings
 production.env    # Production environment settings
```

### Required Environment Variables

#### Core Application
```bash
ANTHROPIC_API_KEY=sk-ant-...        # Required: Claude AI API access
GITHUB_TOKEN=ghp_...               # Required: Git operations
SUMMIT_ENV=production              # Environment identifier
```

#### Database (Production)
```bash
POSTGRES_DB=summit
POSTGRES_USER=summit  
POSTGRES_PASSWORD=secure_password  # Set via secrets
```

#### Monitoring (Optional)
```bash
GRAFANA_PASSWORD=admin_password     # Dashboard access
SLACK_WEBHOOK_URL=https://...      # Alert notifications
```

### Secrets Management

Sensitive values are managed through:
- **GitHub Secrets**: For CI/CD pipeline
- **Environment Variables**: For runtime configuration
- **External Secret Management**: HashiCorp Vault, AWS Secrets Manager

##  Monitoring & Observability

### Metrics Collection (Prometheus)
- **Application Metrics**: Request rates, response times, error rates
- **System Metrics**: CPU, memory, disk, network utilization
- **Business Metrics**: Task completion rates, cost tracking
- **Custom Metrics**: Autonomous system performance

### Dashboards (Grafana)
- **Overview Dashboard**: System health and key metrics
- **Autonomous Tasks**: Task execution monitoring
- **Performance Dashboard**: Detailed performance analytics
- **Cost Tracking**: Budget utilization and trends

### Log Aggregation (Loki)
- **Centralized Logging**: All service logs in one place
- **Structured Logging**: JSON format for better parsing
- **Log Correlation**: Trace requests across services
- **Alert Integration**: Log-based alerting rules

### Health Checks
```bash
# Application health
curl -f http://localhost:8000/health

# Service health
curl -f http://localhost:8000/api/status

# Database health  
docker exec summit-postgres pg_isready
```

##  Deployment Commands

### Basic Deployment
```bash
# Deploy latest to production
./deploy.sh production

# Deploy specific version to staging
./deploy.sh staging --image v1.2.3

# Development deployment with hot reload
./deploy.sh dev
```

### Advanced Options
```bash
# Dry run (see what would be deployed)
./deploy.sh production --dry-run

# Force deployment without confirmation
./deploy.sh production --force

# Deploy with backup
./deploy.sh production --backup

# Health check only
./deploy.sh production --health-check
```

### Rollback Operations
```bash
# Rollback to previous version
./deploy.sh production --rollback

# Rollback with backup verification
./deploy.sh production --rollback --backup
```

### Docker Compose Operations
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f summit-web

# Scale services
docker-compose up -d --scale summit-worker=3

# Stop all services
docker-compose down
```

##  Troubleshooting

### Common Issues

#### 1. Deployment Failures
```bash
# Check service logs
docker-compose logs summit-web

# Verify health checks
curl -f http://localhost:8000/health

# Check resource usage
docker stats
```

#### 2. Autonomous Task Issues
```bash
# Check task logs
ls -la task_logs/

# Verify Docker daemon
docker info

# Check Claude Code availability
docker exec summit-web claude --version
```

#### 3. Database Connection Issues
```bash
# Test database connection
docker exec summit-postgres pg_isready -U summit

# Check connection string
docker-compose exec summit-web env | grep POSTGRES
```

#### 4. Performance Issues
```bash
# Check resource limits
docker inspect summit-web | grep -A 5 "Resources"

# Monitor real-time metrics
docker stats summit-web

# Check application metrics
curl http://localhost:9090/metrics
```

### Debug Mode
```bash
# Enable debug logging
export SUMMIT_LOG_LEVEL=debug

# Run with development configuration
./deploy.sh dev --dry-run

# Access container shell
docker exec -it summit-web bash
```

### Log Analysis
```bash
# View recent application logs
docker-compose logs --tail=100 summit-web

# Follow logs in real-time
docker-compose logs -f

# Search logs for errors
docker-compose logs | grep ERROR

# Export logs for analysis
docker-compose logs > debug_logs.txt
```

##  Security Considerations

### Container Security
- **Non-root Execution**: All containers run as non-privileged users
- **Resource Limits**: CPU and memory constraints enforced
- **Network Isolation**: Services communicate via dedicated networks
- **Secret Management**: No secrets in images or environment files

### API Security
- **Rate Limiting**: Request throttling per endpoint
- **CORS Protection**: Cross-origin request validation
- **Input Validation**: All inputs sanitized and validated
- **Authentication**: API key and token-based access control

### Infrastructure Security
- **TLS Encryption**: HTTPS for all external communications
- **Regular Updates**: Automated security patch application
- **Vulnerability Scanning**: Continuous image and dependency scanning
- **Access Control**: Role-based access to deployment systems

### Autonomous System Security
- **Isolated Execution**: Each task runs in separate containers
- **Resource Constraints**: Limited CPU, memory, and network access
- **Code Review**: All autonomous changes go through CI/CD validation
- **Audit Logging**: Complete trail of autonomous actions

##  Autonomous Integration

### How It Works

1. **Task Creation**: User submits task via web interface
2. **Container Spawning**: Isolated Docker container created
3. **Claude Code Execution**: AI completes task autonomously
4. **Git Integration**: Changes committed and pushed automatically
5. **CI/CD Trigger**: Deployment pipeline activated
6. **Validation**: Tests run on autonomous changes
7. **Deployment**: Validated changes deployed to staging/production

### Autonomous Task Monitoring

```bash
# View active autonomous tasks
curl http://localhost:8000/api/tasks

# Monitor specific task
curl http://localhost:8000/api/tasks/{task_id}

# Check task logs
cat task_logs/task_{task_id}.log

# View container status
docker ps | grep claude-task
```

### Integration Points

- **Git Workflow**: Automatic commits with proper messages
- **CI/CD Pipeline**: Triggers on autonomous commits
- **Quality Gates**: All changes must pass tests
- **Rollback Safety**: Failed deployments automatically rolled back
- **Monitoring**: Real-time tracking of autonomous operations

##  Additional Resources

### Documentation
- [Summit AI Overview](../README.md)
- [API Documentation](../docs/api.md)
- [Development Guide](../docs/development.md)
- [Architecture Guide](../docs/architecture.md)

### External Dependencies
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions Guide](https://docs.github.com/en/actions)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

### Support
- **Issues**: Submit via GitHub Issues
- **Discussions**: GitHub Discussions
- **Security**: security@summit.ai
- **General**: support@summit.ai

---

**summit.ai CI/CD Pipeline** - Enabling autonomous development with confidence  