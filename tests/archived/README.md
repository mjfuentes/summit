# Archived Tests

This directory contains test files that have been moved from the main test suite but are preserved for reference and potential future use.

## Purpose

Test files should **never be deleted** from the Summit project as they provide critical validation and documentation of expected behavior. Instead of deletion, obsolete tests are moved here.

## When to Archive Tests

- When test files become obsolete due to major refactoring
- When functionality is completely removed but tests provide valuable documentation
- When tests need to be temporarily disabled but preserved for future reference

## Guidelines

- Maintain the original directory structure when archiving
- Add a comment at the top of archived test files explaining why they were archived
- Include the date of archiving and the commit/PR that archived them
- Consider updating archived tests before reactivating them

## Reactivating Tests

To reactivate an archived test:
1. Review and update the test for current codebase
2. Move it back to the appropriate location in `tests/`
3. Ensure it passes with current code
4. Update any outdated assertions or mocks 