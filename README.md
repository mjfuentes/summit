# Summit: The Learning AI System

[![CI/CD Pipeline](https://github.com/mjfuentes/summit/actions/workflows/summit-autodeploy.yml/badge.svg)](https://github.com/mjfuentes/summit/actions)
[![Coverage](https://img.shields.io/badge/coverage-71.9%25-brightgreen)](https://github.com/mjfuentes/summit)
[![Code Quality](https://img.shields.io/badge/code%20quality-passing-brightgreen)](https://github.com/mjfuentes/summit)

> **Status: archived, June 2025.** First attempt at an agent that extends its own code: it writes the change, runs the tests, and only merges when CI is green. Unfinished. The ideas carried into [AMIGA](https://github.com/mjfuentes/amiga) and then [cc+](https://github.com/kerplunkstudio/ccplus).

Summit modifies its own code to add capabilities: it writes the change, tests it and validates the result before merging. The interesting part is the gate, not the generator.

## Quick Start

### Web Interface (Recommended)
```bash
python bin/start_web.py
```
Visit `http://localhost:8000` for the full web interface with voice input support.

### Command Line
```bash
python bin/run_summit.py
```

### Basic Usage
```bash
# Ask Summit to learn something new
summit_learn "How to process CSV files with Python"

# Share knowledge for Summit to learn from
summit_share "Python pandas is excellent for CSV manipulation"

# Get AI-powered advice
summit_advice "Best practices for database optimization"
```

## CI/CD Pipeline

Summit features a robust CI/CD pipeline that ensures code quality and reliability:

### Automated Quality Checks
- **Test Coverage**: Minimum 70% coverage required (currently 71.9%)
- **Code Formatting**: Automatic Black formatting with 79-character line length
- **Import Sorting**: Automatic isort for consistent import organization
- **Syntax Validation**: Python syntax checking for all modified files
- **Emoji Linting**: Professional code standards (no emojis in codebase)

### Pre-commit Hooks
Our enhanced pre-commit hooks automatically:
1. **Auto-format code** with Black and isort
2. **Run full test suite** with parallel execution
3. **Check code syntax** and debugging statements
4. **Validate commit messages** for professional standards
5. **Enforce quality standards** before any commit

### GitHub Actions Workflow
```yaml
# Automated on every push and PR
- Checkout code
- Setup Python 3.12
- Install dependencies
- Run comprehensive test suite
- Generate coverage reports
- Validate code quality
- Auto-merge if all checks pass
```

### Test Suite
- **104+ Tests**: Comprehensive coverage across all components
- **Parallel Execution**: Fast test runs using pytest-xdist
- **Coverage Reporting**: Detailed coverage analysis with XML output
- **Quality Gates**: Automatic failure if coverage drops below 70%

### Development Workflow
```
Analysis → Implementation → Testing → Quality Checks → Commit → Deploy
    ↑                                                              ↓
    ←←←← Continuous Integration & Deployment Pipeline ←←←←←←←←←←←←←←
```

### Docker Build Optimization
Summit features **optimized Docker builds** that reduce build time from 20+ minutes to under 5 minutes:

**Key Optimizations:**
- **Lightweight Dependencies**: Removed heavy ML libraries (PyTorch, transformers) from production builds
- **Multi-layer Caching**: Registry cache + GitHub Actions cache for faster rebuilds  
- **Optimized .dockerignore**: Excludes unnecessary files from build context
- **Development Split**: Heavy dependencies moved to `dev-requirements.txt` for local development

**Build Performance:**
```bash
# Test optimized build locally
./scripts/test-docker-build.sh

# Development setup (full dependencies)
pip install -r requirements.txt -r dev-requirements.txt

# Production build (lightweight)
docker build -f deployment/docker/Dockerfile.summit-api .
```

## Core Capabilities

### Learning System
- **Request-Driven Learning**: Learns new capabilities based on user requests
- **Self-Modification**: Modifies its own source code to add functionality
- **Capability Building**: Combines simple skills into complex ones
- **Knowledge Accumulation**: Every interaction makes it more capable

### Autonomous Development
- **PR-Based Workflow**: Creates pull requests for autonomous development
- **Multi-Role Code Review**: AI-powered code reviews from multiple perspectives
- **GitHub Codespaces Integration**: Isolated development environments
- **Version Control**: All changes tracked and reversible

### Safety & Quality
- **Cost Controls**: Daily ($10) and hourly ($2) budget limits
- **Quality Assurance**: Comprehensive testing before any deployment
- **Professional Standards**: Clean code without visual clutter
- **Error Handling**: Graceful fallbacks and error recovery

## Architecture

```
summit/
 src/                    # Core source code
    fastmcp_server.py  # FastMCP server implementation
    summit_client.py   # FastMCP client for connecting to server
    cost_tracker.py    # Budget management
    pr_reviewers.py    # AI code review system
    agent_git_api.py   # Git automation wrapper
    task_manager.py    # Task orchestration
 tests/                 # Comprehensive test suite (104+ tests)
 bin/                   # Executable scripts (start_web.py, run_summit.py)
 scripts/               # Development and automation scripts
 examples/              # Demo and example scripts
 utilities/             # Utility and testing scripts
 deployment/            # Deployment configurations
    docker/            # Docker files and configurations
    runpod/            # RunPod deployment scripts
    render/            # Render deployment configurations
    kubernetes/        # Kubernetes configurations
 .github/workflows/     # CI/CD automation
 .githooks/             # Enhanced pre-commit hooks
 docs/                  # Detailed documentation
 config/                # Configuration files
```

## Development Standards

### Mandatory Development Process
Summit enforces a strict 5-phase development workflow:

1. **Analysis Phase**: Understand requirements and examine codebase
2. **Implementation Phase**: Write clean, tested code
3. **Quality Assurance Phase**: Run coverage, linting, formatting
4. **Git Operations Phase**: Proper commit workflow with validation
5. **Verification Phase**: Confirm all tests pass and quality gates met

### Code Quality Rules
- **No Emojis**: Professional documentation and code only
- **Test Coverage**: Minimum 70% coverage on all changes
- **Black Formatting**: Consistent code style with 79-character lines
- **Clean Commits**: Descriptive commit messages, no debugging code
- **Quality Gates**: All tests must pass before merge

### Git Workflow
```bash
# Use the agent git wrapper for all operations
from src.agent_git_api import save_work

# Automatically validates, tests, and pushes
save_work("commit message")
```

## Key Features

### Voice-Driven Development
- **Speech Recognition**: Natural language task assignment
- **Real-time Monitoring**: Live progress tracking
- **Interactive Terminal**: Browser-based development environment

### AI-Powered Code Review
- **Multi-Perspective Reviews**: Security, architecture, testing, UX viewpoints
- **Automated Quality Checks**: Code analysis and improvement suggestions
- **Review Aggregation**: Consolidated feedback and recommendations

### Knowledge Management
- **Semantic Search**: Vector-based knowledge retrieval
- **Learning Analytics**: Track knowledge gaps and growth patterns
- **Experience Sharing**: Collaborative knowledge building

## Configuration

### Required Environment Variables
```bash
ANTHROPIC_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_key_here  # For embeddings
```

### Optional Configuration
```bash
DAILY_BUDGET=10.0           # Daily spending limit
HOURLY_BUDGET=2.0           # Hourly spending limit
MAX_RECURSION_DEPTH=3       # Learning recursion limit
```

## Testing

### Run Tests Locally
```bash
# Full test suite with coverage
python bin/run_coverage.py

# Specific test file
pytest tests/test_summit_basic.py -v

# Parallel execution
pytest tests/ -n auto
```

### Coverage Requirements
- **Minimum 70% overall coverage**
- **New code must maintain or improve coverage**
- **Coverage reports generated automatically**

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow development standards**: All tests must pass, coverage ≥70%
4. **Use the agent git API**: `save_work("descriptive commit message")`
5. **Create Pull Request**: Automated review and quality checks

### Pre-commit Setup
```bash
# Install pre-commit hooks
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Monitoring & Observability

### Health Checks
- **System Status**: `summit_status` for health monitoring
- **Cost Tracking**: Real-time budget usage and projections
- **Performance Metrics**: Search analytics and response times

### Logging
- **Structured Logging**: JSON format for easy parsing
- **Error Tracking**: Comprehensive error reporting and debugging
- **Audit Trail**: All learning activities tracked and logged

## Security

### Safe Development Practices
- **Container Isolation**: All development in isolated environments
- **Budget Controls**: Automatic spending limits and circuit breakers
- **Code Review**: AI-powered security analysis
- **Version Control**: All changes tracked and reversible

### Access Control
- **GitHub Token Scoping**: Minimal required permissions
- **API Key Management**: Secure credential handling
- **Environment Isolation**: Separate dev/test/prod environments

## Support & Documentation

- **Detailed Documentation**: See [docs/README.md](docs/README.md) for complete system overview
- **Project Status**: See [docs/project_status.md](docs/project_status.md) for current capabilities
- **Coding Standards**: See [docs/coding_standards.md](docs/coding_standards.md) for development guidelines
- **Architecture Vision**: See [docs/future_architecture.md](docs/future_architecture.md) for roadmap
- **Folder Organization**: See [docs/folder_organization.md](docs/folder_organization.md) for directory structure
- **Container Isolation**: See [docs/container_isolation.md](docs/container_isolation.md) for security practices

## License

This project is proprietary software. All rights reserved.

---

**Summit doesn't just answer questions - it learns to do whatever you need, permanently expanding its capabilities to serve you better.** 