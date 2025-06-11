# Claude Code Deployment Guide for Render.com

This guide explains how to deploy Summit's Claude Code instances to Render.com using our automated container build and deployment process.

## Overview

Our deployment strategy leverages:
- **GitHub Actions** to build and publish Claude Code container images
- **Render.com** to automatically deploy when the main branch changes
- **Container Registry** (GitHub Container Registry) to store built images

## Automated Process

### 1. Container Build & Publish

When you push changes to the main branch that affect Claude Code files, GitHub Actions automatically:

1.  **Validates** required files (`Dockerfile.autonomous`, `claude_code_task.sh`, etc.)
2.  **Builds** the Claude Code container image
3.  **Publishes** to GitHub Container Registry (`ghcr.io`)
4.  **Tests** container startup
5.  **Creates** Render.com configuration files
6.  **Commits** configuration updates

### 2. Render.com Auto-Deployment

Render.com monitors the main branch and automatically deploys when it detects changes.

## Setup Instructions

### Prerequisites

1. **GitHub Repository** with Summit code
2. **Render.com Account** connected to your GitHub repository
3. **Environment Variables** configured in Render.com

### Step 1: Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```bash
ANTHROPIC_API_KEY=sk-ant-...     # Your Anthropic API key
GITHUB_TOKEN=ghp_...             # GitHub token with repo access
```

### Step 2: Set Up Render.com Services

#### Option A: Using render.yaml (Recommended)

The GitHub Action automatically creates a `render.yaml` file. Simply:

1. Connect your repository to Render.com
2. Render will automatically detect the `render.yaml` configuration
3. Set environment variables in Render dashboard

#### Option B: Manual Service Creation

Create two services in Render.com:

**Service 1: Summit Web Interface**
```yaml
Name: summit-web-interface
Environment: Docker
Dockerfile Path: ./Dockerfile.render
Build Command: pip install -r requirements.txt
Start Command: python start_server.py
Plan: Starter
Region: Oregon
```

**Service 2: Claude Code Autonomous**
```yaml
Name: summit-claude-code
Environment: Docker
Dockerfile Path: ./web/Dockerfile.autonomous
Docker Context: ./web
Build Command: cp ../requirements.txt . && chmod +x claude_code_task.sh
Start Command: python3 autonomous_server.py
Plan: Starter
Region: Oregon
```

### Step 3: Configure Environment Variables

Set these environment variables in **both** Render services:

#### Required Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...     # Your Anthropic API key
GITHUB_TOKEN=ghp_...             # GitHub token for repository access
SUMMIT_ENV=production            # Environment identifier
PORT=8000                        # Port for the web service
```

#### Optional Variables
```bash
SUMMIT_LOG_LEVEL=info           # Logging level
SUMMIT_READONLY_MODE=false      # Allow modifications
SUMMIT_DEBUG=false              # Debug mode
```

### Step 4: Enable Auto-Deploy

In each Render service:
1. Go to Settings → Auto-Deploy
2. Enable "Auto-Deploy" for the main branch
3. Render will now automatically deploy on main branch changes

## Container Images

### Published Images

GitHub Actions publishes container images to:
```
ghcr.io/mjfuentes/summit/claude-code:latest
ghcr.io/mjfuentes/summit/claude-code:main-<sha>
ghcr.io/mjfuentes/summit/claude-code:render
```

### Image Contents

The Claude Code container includes:
- **Ubuntu 22.04** base system
- **Python 3.12** with all dependencies
- **Node.js 18** for Claude Code CLI
- **Claude Code CLI** (`@anthropic-ai/claude-code`)
- **Development tools** (git, curl, vim, etc.)
- **Web terminal** (ttyd) for monitoring
- **Summit source code** and configuration

## Deployment Workflow

### Automatic Deployment

1. **Developer pushes** to main branch
2. **GitHub Actions** builds and publishes container
3. **Render.com** detects branch change
4. **Render.com** pulls latest code and rebuilds services
5. **Services** restart with new code
6. **Health checks** verify deployment success

### Manual Deployment

You can also trigger deployments manually:

1. **GitHub Actions**: Go to Actions → "Claude Code Container Build & Publish" → Run workflow
2. **Render.com**: Go to service dashboard → Manual Deploy

## Monitoring & Troubleshooting

### Health Checks

Both services include health check endpoints:
- **Web Interface**: `https://your-service.onrender.com/health`
- **Claude Code**: `https://your-claude-service.onrender.com/health`

### Logs

Monitor deployment and runtime logs in:
1. **GitHub Actions**: Actions tab → Workflow runs
2. **Render.com**: Service dashboard → Logs tab

### Common Issues

#### Container Build Failures
- Check GitHub Actions logs for build errors
- Verify all required files are present
- Ensure Dockerfile syntax is correct

#### Deployment Failures
- Check Render.com logs for startup errors
- Verify environment variables are set correctly
- Ensure health check endpoints are responding

#### Claude Code Issues
- Verify `ANTHROPIC_API_KEY` is valid
- Check that `claude_code_task.sh` is executable
- Monitor container logs for Claude Code CLI errors

### Debugging Commands

Access your deployed service logs:
```bash
# View recent logs
curl https://your-service.onrender.com/api/logs

# Check service health
curl https://your-service.onrender.com/health

# View active tasks
curl https://your-service.onrender.com/api/tasks
```

## Cost Optimization

### Render.com Pricing

- **Starter Plan**: $7/month per service
- **Standard Plan**: $25/month per service (recommended for production)
- **Pro Plan**: $85/month per service (high-traffic applications)

### Optimization Tips

1. **Use Starter Plan** for development/testing
2. **Combine services** if possible to reduce costs
3. **Monitor resource usage** in Render dashboard
4. **Set up alerts** for unusual activity
5. **Use sleep/wake** features for non-production environments

## Security Considerations

### Environment Variables
- Never commit API keys to the repository
- Use Render's environment variable encryption
- Rotate keys regularly

### Container Security
- Images are scanned for vulnerabilities during build
- Non-root user is used in containers
- Minimal attack surface with slim base images

### Network Security
- HTTPS is enforced by default on Render
- Internal service communication is encrypted
- Health check endpoints are publicly accessible

## Advanced Configuration

### Custom Domains

1. Add custom domain in Render service settings
2. Configure DNS records as instructed
3. SSL certificates are automatically provisioned

### Scaling

Render.com automatically scales based on traffic:
- **Horizontal scaling**: Multiple instances during high load
- **Vertical scaling**: Upgrade to higher-tier plans for more resources

### CI/CD Integration

The deployment integrates with your existing CI/CD:
- **Quality gates**: Container builds only on successful tests
- **Security scanning**: Vulnerability scanning during build
- **Rollback**: Easy rollback through Render dashboard

## Support

### Documentation
- [Render.com Documentation](https://render.com/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Claude Code CLI Documentation](https://github.com/anthropics/claude-code)

### Troubleshooting
1. Check GitHub Actions logs for build issues
2. Check Render.com logs for deployment issues
3. Use health check endpoints to verify service status
4. Monitor resource usage in Render dashboard

### Getting Help
- **GitHub Issues**: Report bugs or request features
- **Render Support**: Contact Render.com support for platform issues
- **Community**: Join discussions in project repositories 