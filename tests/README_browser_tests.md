# Browser Terminal Tests

This directory contains browser-based integration tests for the Summit web interface.

## test_browser_terminal.py

Tests the browser terminal functionality to ensure no JavaScript errors occur when starting the server.

### What it tests:
- Web server startup without errors
- Browser interface loads without JavaScript console errors
- User interactions work correctly (button clicks, API calls)
- Health endpoint accessibility
- Terminal-like interface elements are present and functional

### Requirements:
- Chrome browser installed on the system
- Selenium WebDriver (automatically managed by Selenium 4.15+)
- Python packages: `selenium>=4.15.0`, `pytest`

### Running the tests:

```bash
# Run all browser terminal tests
python -m pytest tests/test_browser_terminal.py -v

# Run a specific test
python -m pytest tests/test_browser_terminal.py::TestBrowserTerminal::test_browser_loads_without_errors -v

# Run with verbose output to see browser interactions
python -m pytest tests/test_browser_terminal.py -v -s
```

### Test Details:

1. **test_browser_loads_without_errors**: Checks for JavaScript console errors when loading the page
2. **test_page_title_and_content**: Verifies correct page title and expected content
3. **test_api_status_functionality**: Tests the status API button functionality
4. **test_no_console_errors_during_interaction**: Ensures no errors during user interactions
5. **test_health_endpoint_accessibility**: Verifies the health endpoint works in browser
6. **test_web_interface_terminal_elements**: Checks for proper terminal-like interface elements

### Notes:
- Tests run in headless Chrome mode (no visible browser window)
- Each test uses a random port to avoid conflicts
- Tests automatically start and stop the web server
- JavaScript console errors are filtered to focus on critical issues only

### Integration with Pre-commit Hook:
The critical browser error detection test (`test_browser_loads_without_errors`) is automatically run as part of the pre-commit hook to ensure the browser terminal works correctly before any commit. This prevents commits that would break the web interface.

If Selenium is not available, the pre-commit hook will skip the browser tests with a warning message. 