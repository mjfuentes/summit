# Summit Debugging Session

RUN python -m pytest --tb=short -v
RUN python -m pylint src/ --errors-only

Analyze any errors or failures and:
1. Identify the root cause
2. Propose solutions
3. Implement fixes
4. Verify the fixes work
5. Run tests to ensure no regressions