# Summit Folder Organization

This document describes the organized folder structure for the Summit project, implemented to improve code maintainability and clarity.

## Directory Structure

```
summit/
 README.md                     # Main project documentation
 requirements.txt              # Core dependencies
 dev-requirements.txt          # Development dependencies
 pytest.ini                    # Test configuration
 version.txt                   # Version information

 bin/                          # Executable scripts and entry points
    run_summit.py            # Main CLI entry point
    start_web.py             # Web interface launcher
    start_server.py          # Server startup script
    start_mcp_server.sh      # MCP server startup script
    run_tests.py             # Test runner script
    run_coverage.py          # Coverage analysis script

 src/                          # Core application source code
    fastmcp_server.py        # FastMCP server implementation
    agent_git_api.py         # Git automation wrapper
    cost_tracker.py          # Budget management
    pr_reviewers.py          # AI code review system
    task_manager.py          # Task orchestration
    unified_database.py      # Database abstraction layer

 tests/                        # Test suite (70%+ coverage)
    test_*.py                # Unit and integration tests
    archived/                # Legacy test files

 scripts/                      # Development automation scripts
    deploy_*.py              # Deployment automation
    fix_*.py                 # Code quality fixes
    setup_*.py               # Environment setup
    *.sh                     # Shell automation scripts

 examples/                     # Demo and example code
    demo_enhanced_search.py  # Search functionality demo
    demo_save_work.py        # Git workflow demo

 utilities/                    # Utility and helper scripts
    test_*.py                # Testing utilities
    monitor_*.py             # Monitoring tools
    create_pr.py             # PR creation template

 deployment/                   # Deployment configurations
    docker/                  # Docker configurations
       Dockerfile.runpod    # RunPod deployment image
       Dockerfile.opencode-agents # OpenCode agents image
       docker-compose.yml   # Local development setup
   
    runpod/                  # RunPod specific deployments
       runpod_handler.py    # Claude API handler
       runpod_handler_opensource.py # Open source models handler
       deploy_to_runpod.py  # Deployment script
       opencode_config.json # OpenCode configuration
       OPENCODE_RUNPOD_SETUP.md # Setup documentation
   
    render/                  # Render.com deployments
       render.yaml          # Render configuration
       RENDER_DEPLOYMENT.md # Basic deployment guide
       RENDER_DEPLOYMENT_GUIDE.md # Detailed guide
   
    kubernetes/              # Kubernetes deployments
        KUBERNETES_SETUP.md  # K8s setup documentation

 docs/                         # Project documentation
    CODING_STANDARDS.md     # Development guidelines
    PROJECT_STATUS.md       # Current capabilities
    FUTURE_ARCHITECTURE.md  # Architecture roadmap
    FOLDER_ORGANIZATION.md  # Directory structure guide
    CONTAINER_ISOLATION.md  # Security practices
    AI_AGENT_MANIFESTO.md   # AI principles
    SUMMIT_ANALYSIS.md      # System analysis
    GITHUB_SECRETS_SETUP.md # GitHub configuration

 web/                         # Web interface and API
 config/                      # Configuration files
 infrastructure/              # Infrastructure as code
 tools/                       # Development tools
 logs/                        # Application logs
```

## Organizational Principles

### 1. **Clear Separation of Concerns**
- **bin/**: User-facing executable scripts
- **src/**: Core application logic
- **scripts/**: Developer automation tools
- **deployment/**: Environment-specific configurations

### 2. **Logical Grouping**
- **examples/**: Educational and demonstration code
- **utilities/**: Helper scripts and tools
- **tests/**: All testing related files

### 3. **Deployment Isolation**
- Each deployment platform has its own subdirectory
- Platform-specific configurations are contained
- Common patterns are shared where appropriate

### 4. **Developer Experience**
- Entry points are clearly marked in `bin/`
- Development tools are organized in `scripts/`
- Documentation is comprehensive and current

## Migration Notes

The following files were reorganized:

### Moved to `bin/`:
- `run_summit.py`, `start_web.py`, `start_server.py`
- `run_tests.py`, `run_coverage.py`
- `start_mcp_server.sh`

### Moved to `deployment/`:
- Docker files → `deployment/docker/`
- RunPod handlers → `deployment/runpod/`
- Render configs → `deployment/render/`
- Kubernetes docs → `deployment/kubernetes/`

### Moved to `examples/`:
- `demo_*.py` files

### Moved to `utilities/`:
- `test_*.py` utilities
- `monitor_*.py` tools
- `create_pr.py` template

### Moved to `docs/`:
- `CODING_STANDARDS.md` → `docs/CODING_STANDARDS.md`
- `PROJECT_STATUS.md` → `docs/PROJECT_STATUS.md`
- `GITHUB_SECRETS_SETUP.md` → `docs/GITHUB_SECRETS_SETUP.md`
- `AI_AGENT_MANIFESTO.md` → `docs/AI_AGENT_MANIFESTO.md`
- `FUTURE_ARCHITECTURE.md` → `docs/FUTURE_ARCHITECTURE.md`
- `CONTAINER_ISOLATION.md` → `docs/CONTAINER_ISOLATION.md`
- `SUMMIT_ANALYSIS.md` → `docs/SUMMIT_ANALYSIS.md`
- `FOLDER_ORGANIZATION.md` → `docs/FOLDER_ORGANIZATION.md`

## Benefits

1. **Improved Discoverability**: Developers can quickly find what they need
2. **Reduced Root Clutter**: Clean project root with logical organization
3. **Better Maintenance**: Related files are grouped together
4. **Deployment Clarity**: Each platform's needs are clearly separated
5. **Consistent Patterns**: Similar file types follow predictable locations

## Updating References

When moving files, ensure you update:
- README.md instructions
- CI/CD pipeline references
- Docker build contexts
- Import statements
- Documentation links

This organization supports Summit's growth while maintaining clarity and maintainability. 