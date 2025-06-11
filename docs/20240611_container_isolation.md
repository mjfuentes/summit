# Container Isolation for Summit AI

**Last Updated:** December 2024  
**Version:** 1.1

This document describes the container-based isolation strategy for Summit AI development and deployment.

## Overview
This document explains how the Summit AI system ensures that all Claude Code tasks only modify files inside containers and never touch local host files.

## Container Architecture

### Docker Containers
- **Base Images**: `Dockerfile.autonomous` and `Dockerfile.simple`
- **User Isolation**: Tasks run as non-root `claude` user (UID/GID isolation)
- **Workspace**: All work happens in `/workspace/repo` inside containers
- **No Host Volumes**: No directories mounted from host that could modify local files

### Isolation Boundaries

#### File System Isolation
- **Container Workspace**: `/workspace/repo` - isolated container filesystem
- **No Host Mounts**: No volumes mounted from host filesystem
- **Temporary Files**: All temporary files created inside container only
- **Git Repository**: Cloned fresh inside each container

#### Network Isolation
- **Port Mapping**: Random port allocation prevents conflicts
- **No Host Network**: Containers use bridge networking
- **API Access**: Secure environment variable injection for API keys

#### Process Isolation
- **Non-root User**: `claude` user with restricted permissions
- **Container PID Namespace**: Processes isolated from host
- **Resource Limits**: CPU and memory constraints applied

## Security Features

### Permission Restrictions
- **No sudo access**: Claude user cannot escalate privileges
- **Read-only system directories**: System files protected
- **Command restrictions**: Dangerous commands blocked in container

### API Key Security
- **Environment Variables**: Keys passed securely as env vars
- **No Persistence**: Keys exist only during container lifetime
- **No Host Storage**: Keys never written to host filesystem

## Task Execution Flow

1. **Task Creation**: User submits task via web interface
2. **Container Build**: Docker image built with Claude Code
3. **Container Launch**: Isolated container started with task parameters
4. **Code Execution**: Claude Code runs inside container workspace
5. **Git Operations**: All changes committed inside container
6. **Container Cleanup**: Container destroyed after task completion

## Verification Methods

### Container Status Check
```bash
# List active Claude containers
docker ps --filter name=claude

# Check container isolation
docker inspect claude-task-{id} --format '{{.Config.User}}'
```

### File System Verification
```bash
# Verify workspace isolation
docker exec claude-task-{id} pwd
# Should output: /workspace/repo

# Check mounted volumes
docker inspect claude-task-{id} --format '{{.Mounts}}'
# Should show no host mounts
```

### Process Verification
```bash
# Check running user
docker exec claude-task-{id} whoami
# Should output: claude

# Verify git operations are contained
docker exec claude-task-{id} git remote -v
# Shows repository URL, not host git
```

## Compliance Requirements

### Container Isolation Rules
1. **No Host File Modification**: All file operations stay within container
2. **Git Repository Scope**: Changes only to cloned repository inside container
3. **Knowledge Base Updates**: Must be committed to git repository
4. **No Local Dependencies**: All dependencies installed inside container

### Monitoring and Logging
- **Container Logs**: All activities logged inside container
- **Status Tracking**: Container lifecycle monitored
- **Error Isolation**: Failures contained within container boundaries

## Troubleshooting

### Common Issues
- **Port Conflicts**: Automatic port allocation prevents conflicts
- **Permission Errors**: Non-root user prevents system modifications
- **File Access**: All files accessible within container workspace

### Debug Commands
```bash
# Check container status
docker logs claude-task-{id}

# Inspect container configuration
docker inspect claude-task-{id}

# Verify isolation
docker exec claude-task-{id} ls -la /workspace
```

## Best Practices

1. **Always Commit Changes**: All task results must be committed to git
2. **Use Container Commands**: Execute all operations inside container
3. **Monitor Resources**: Track container resource usage
4. **Clean Up**: Ensure containers are properly destroyed after tasks