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

### 4. Git Operations Phase
```bash
# REQUIRED: Complete Git workflow
git add .                       # Stage all changes
git status                      # Verify what's being committed
git commit -m "descriptive message"  # Commit with clear message
git push origin main           # Push to repository
```

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

### Documentation
- NO EMOJIS in documentation files - use clear, professional text only
- Keep documentation concise and focused on core capabilities
- Update relevant documentation when changing functionality

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
- ✅ Proper analysis and understanding
- ✅ Comprehensive testing with ALL tests passing
- ✅ Coverage verification >70%
- ✅ Code quality checks
- ✅ Complete Git workflow
- ✅ Final verification

🚨 **ABSOLUTE REQUIREMENTS:**
- **NEVER COMMIT WITH FAILING TESTS** - Zero tolerance policy
- **NEVER COMMIT WITH <70% COVERAGE** - Quality gate enforced
- **ALWAYS VERIFY BEFORE COMMIT** - No shortcuts allowed

This ensures Summit maintains high code quality and reliability across all development sessions. 