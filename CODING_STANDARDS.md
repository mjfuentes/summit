# Summit Coding Standards

## Code Comments
- NEVER add obvious/redundant comments like "# Test passed", "# Success", "# End of function"
- Comments should explain WHY, not WHAT the code does
- Avoid stating the obvious - let the code speak for itself
- Only comment when adding genuine value or explaining complex logic

## Documentation Standards
- NO EMOJIS in documentation files - use clear, professional text only
- Keep documentation concise and focused on core capabilities
- Emphasize learning and self-improvement aspects

## Code Quality
- Use meaningful variable and function names
- Keep functions focused on a single responsibility
- Prefer explicit over implicit code
- Write tests for new functionality

## Testing Standards
- Use proper assertions (`assert`) instead of return statements in tests
- Test both success and failure cases
- Include edge case testing
- Maintain test coverage above 70%

## Error Handling
- Provide specific, actionable error messages
- Use appropriate exception types
- Log errors with sufficient context
- Graceful degradation when possible

## Performance
- Avoid premature optimization
- Profile before optimizing
- Consider async/await for I/O operations
- Cache expensive computations when appropriate

These standards ensure code quality and maintainability across all Summit development. 