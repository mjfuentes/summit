# Summit Coding Standards & Development Workflow

## MANDATORY DEVELOPMENT PROCESS

Every code change MUST follow this complete workflow:

### 1. Analysis Phase
- **Understand the requirement** - Read and analyze the input thoroughly
- **Examine existing codebase** - Use `grep`, `find`, and code reading to understand current implementation
- **Identify integration points** - Determine where new code fits in the existing architecture
- **Plan the approach** - Design the solution before coding

### 2. Implementation Phase
- **Write clean code** following the standards below
- **Add comprehensive tests** for new functionality
- **Update existing tests** if modifying existing code
- **Document any complex logic** (but avoid obvious comments)

### 3. Quality Assurance Phase
```bash
# REQUIRED: Run these commands before any commit
python run_coverage.py          # Check test coverage
pytest --cov=src --cov-report=term-missing  # Detailed coverage
python -m pylint src/           # Code linting (if available)
python -m black src/ tests/     # Code formatting (if available)
```

### 4. Git Operations Phase - MANDATORY USE OF AGENT GIT WRAPPER
```python
# REQUIRED: Use the Agent Git Wrapper ONLY - NO DIRECT GIT COMMANDS
from src.agent_git_api import save_work, create_pr, status, pull

# Check current status
status()

# Save your work (replaces git add/commit/push)
save_work("Clear, descriptive single-line commit message")

# Or save specific files
save_work("Update specific functionality", ["file1.py", "file2.py"])

# Create a pull request
create_pr("Implement feature X", "Feature: Add X functionality", "Detailed PR description...")
```

**CRITICAL: NEVER USE DIRECT GIT COMMANDS**
- The agent MUST use the `agent_git_api` module for ALL Git operations
- Direct `git` commands are FORBIDDEN and will be rejected
- The wrapper automatically:
  - Validates commit messages (single line, no emojis)
  - Runs all tests and ensures they pass
  - Checks coverage is >70%
  - Runs linting and pre-commit hooks
  - Pushes changes
  - Monitors CI/CD status

**COMMIT MESSAGE REQUIREMENTS:**
- **SINGLE LINE ONLY** - Commit messages must be one line maximum
- **NO MULTI-LINE COMMITS** - Do not use line breaks or multiple paragraphs
- **DESCRIPTIVE BUT CONCISE** - Include essential information in one clear line
- **PROFESSIONAL TONE** - Use clear, technical language without emojis
- **Use proper Git workflow: analyze → implement → test → lint → commit → push**
- **Maintain >70% test coverage on all changes**

**CRITICAL GIT RULE: NEVER USE --no-verify**
- NEVER bypass pre-commit hooks with `git commit --no-verify`
- Pre-commit hooks enforce quality standards (tests, linting, emoji removal)
- If hooks fail, fix the underlying issue instead of bypassing checks
- ALL commits must pass through complete pre-commit validation

**TESTING REQUIREMENTS:**
- **NO AD-HOC TESTING** - Never use `sleep` and `curl` commands for testing
- **FORMAL TEST SUITE ONLY** - All testing must be done through pytest or proper test files
- **AUTOMATED VALIDATION** - Create proper test cases instead of manual command validation

**CRITICAL RULE: NEVER COMMIT WITH FAILING TESTS**
- ALL tests must pass before any commit
- Coverage must be >70% before any commit
- No exceptions to this rule

### 5. Verification Phase
- **Confirm ALL tests pass** - Every single test must be GREEN before commit
- **Verify coverage target** - Must maintain >70% coverage before commit
- **Check for linting issues** - Clean code quality
- **Validate functionality** - Manual testing if needed

**STOP**: If ANY test fails, DO NOT COMMIT. Fix the issue first.

## Code Quality Standards

### Comments
- NEVER add obvious/redundant comments like "# Test passed", "# Success", "# End of function"
- Comments should explain WHY, not WHAT the code does
- Avoid stating the obvious - let the code speak for itself
- Only comment when adding genuine value or explaining complex logic


### Emoji Linting (Automated)
- **Automatic emoji removal** - Pre-commit hook automatically removes all emoji characters
- **Zero tolerance enforcement** - No emojis can be committed to the repository
- **Manual linting available** - Run `python tools/emoji_linter.py --fix` to clean files manually
- **Comprehensive detection** - Covers all Unicode emoji ranges and symbol categories
- **Professional codebase** - Maintains enterprise-grade documentation standards

#### Emoji Linter Commands:
```bash
# Check for emojis without fixing
python tools/emoji_linter.py

# Automatically remove emojis
python tools/emoji_linter.py --fix

# Check only staged files (used by pre-commit hook)
python tools/emoji_linter.py --staged --fix

# Verbose output showing detection details
python tools/emoji_linter.py --verbose
```

### Documentation  
- **ABSOLUTELY NO EMOJIS** - ZERO tolerance policy for emojis in any code, documentation, logs, or user interface
- Any emoji found in code will result in immediate rejection and rewrite requirement
- Use clear, professional text only - emojis are unprofessional and clutter the codebase
- Keep documentation concise and focused on core capabilities
- Update relevant documentation when changing functionality

### Architecture Documentation
- **Document all major architectural changes** in the `docs/architecture_changes/` directory
- Use the naming convention `YYYYMMDD_descriptive_name.md` with the current date
- Include the following sections in each architecture document:
  1. **Overview**: Brief description of the change
  2. **Motivation**: Why the change was necessary
  3. **Implementation Details**: Key technical components of the change
  4. **Migration Path**: How to migrate from the previous architecture
  5. **Advantages**: Benefits of the new architecture
  6. **Potential Issues**: Known limitations or challenges
  7. **Future Considerations**: Planned improvements or next steps
- Update the main README.md to reflect current architecture
- Keep architecture diagrams up-to-date
- Document backward compatibility considerations

### Code Structure
- Use meaningful variable and function names
- Keep functions focused on a single responsibility
- Prefer explicit over implicit code
- Follow existing code patterns in the repository

### Testing Requirements
- Use proper assertions (`assert`) instead of return statements in tests
- Test both success and failure cases
- Include edge case testing
- Maintain test coverage above 70%
- Add tests BEFORE implementing features (TDD when possible)

### Error Handling
- Provide specific, actionable error messages
- Use appropriate exception types
- Log errors with sufficient context
- Graceful degradation when possible

### Performance
- Avoid premature optimization
- Profile before optimizing
- Consider async/await for I/O operations
- Cache expensive computations when appropriate

## FAILURE TO FOLLOW PROCESS = REJECTION

Any code changes that do not follow this complete workflow will be rejected. 
The agent must demonstrate:
- Proper analysis and understanding
- Comprehensive testing with ALL tests passing
- Coverage verification >70%
- Code quality checks
- Complete Git workflow
- Final verification

**ABSOLUTE REQUIREMENTS:**
- **NEVER COMMIT WITH FAILING TESTS** - Zero tolerance policy
- **NEVER COMMIT WITH <70% COVERAGE** - Quality gate enforced  
- **NEVER USE --no-verify** - All commits must pass pre-commit hooks
- **ALWAYS VERIFY BEFORE COMMIT** - No shortcuts allowed
- **NEVER USE EMOJIS** - Professional code and documentation only
- **NO AD-HOC TESTING** - Never use sleep and curl commands for testing, use formal test suite only
- **NEVER SKIP OR DISABLE FAILING TESTS** - Fix the root cause instead of hiding problems
- **NEVER USE @pytest.mark.skip ON FAILING TESTS** - Skipping tests masks real issues and reduces code quality
- **FIX TESTS, DON'T HIDE THEM** - When tests fail, investigate and fix the underlying problem
- **MAINTAIN TEST INTEGRITY** - All tests must be meaningful and passing to ensure code reliability

This ensures Summit maintains high code quality and reliability across all development sessions. 