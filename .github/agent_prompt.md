# Summit AI Agent - System Prompt Configuration

## CRITICAL: Git Operations Protocol

**YOU MUST NEVER USE DIRECT GIT COMMANDS**. The Summit project has a mandatory Git wrapper that enforces all quality standards. This is non-negotiable.

### Required Git Workflow

1. **Import the Git API at the start of any session where you'll save work:**
   ```python
   from src.agent_git_api import save_work, create_pr, status, pull
   ```

2. **For saving work (replaces git add/commit/push):**
   ```python
   # Save all changes with automatic validation, testing, and push
   save_work("Your single-line commit message here")
   
   # Or save specific files
   save_work("Update specific files", ["file1.py", "file2.py"])
   ```

3. **For creating pull requests:**
   ```python
   create_pr("Commit message", "PR Title", "Optional PR description")
   ```

4. **For checking status:**
   ```python
   status()  # Shows git status
   ```

5. **For updating from remote:**
   ```python
   pull()  # Updates from remote
   ```

### What the Git Wrapper Does Automatically

When you use `save_work()`, it:
1. Validates your commit message (single line, no emojis, proper length)
2. Runs all tests with pytest (streaming output so you see progress)
3. Checks coverage is >70%
4. Runs flake8 linting (if available)
5. Runs pre-commit hooks (if configured)
6. Commits your changes if everything passes
7. Pushes to remote immediately
8. Returns success/failure status

**Important**: The wrapper focuses on local validation. CI/CD runs asynchronously on GitHub after push. This approach:
- Provides faster feedback (no waiting for remote CI)
- Allows the agent to continue with other tasks
- Relies on comprehensive local tests to catch issues early
- Avoids context loss if CI fails later

### Git Wrapper Rules

- **NEVER** use `git`, `git add`, `git commit`, `git push` commands directly
- **NEVER** use subprocess or os.system to run git commands
- **NEVER** try to bypass the wrapper with --no-verify or similar flags
- **ALWAYS** use the provided Python API functions
- **ALWAYS** ensure your commit messages are single-line (no \n characters)
- **ALWAYS** write clear, descriptive commit messages without emojis

### Example Workflows

#### After making code changes:
```python
from src.agent_git_api import save_work

# After implementing a feature
save_work("Implement user authentication with JWT tokens")
```

#### Creating a feature and PR:
```python
from src.agent_git_api import save_work, create_pr

# Make your changes...
# Then create a PR
create_pr(
    "Add comprehensive test coverage for auth module",
    "Feature: Enhanced Authentication Testing",
    "This PR adds unit and integration tests for the authentication module, achieving 95% coverage."
)
```

## Other Summit Standards

### Testing
- Write tests for all new functionality
- Maintain >70% code coverage in src/
- Use pytest for all testing
- No ad-hoc testing with curl/sleep commands

### Code Quality
- Follow PEP 8 style guide
- Add meaningful comments for complex logic
- Avoid obvious comments
- Keep functions focused and small

### Development Process
1. Understand the task
2. Plan the implementation
3. Write tests first (TDD when possible)
4. Implement the feature
5. Run tests locally
6. Use `save_work()` to commit and push
7. Monitor CI/CD results

## Remember

The Git wrapper is your friend. It ensures code quality, prevents broken builds, and maintains project standards. Trust it, use it, and never try to bypass it. This is the Summit way. 