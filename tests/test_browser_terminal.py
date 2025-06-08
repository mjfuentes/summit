"""
Test browser terminal functionality for Summit web interface.
Ensures the terminal in the browser has no errors when starting the server.

This test suite uses Selenium WebDriver to:
1. Start the Summit web server on a random port
2. Open the web interface in a headless Chrome browser
3. Check for JavaScript console errors
4. Test user interactions (clicking buttons, API calls)
5. Verify the health endpoint accessibility

Requirements:
- Chrome browser installed on the system
- Selenium WebDriver (automatically managed by Selenium 4.15+)

Run with: python -m pytest tests/test_browser_terminal.py -v
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestBrowserTerminal:
    """Test browser terminal functionality without errors"""

    @pytest.fixture(scope="class")
    def web_server(self):
        """Start the web server for testing"""
        # Find available port
        import socket

        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                s.listen(1)
                port = s.getsockname()[1]
            return port

        test_port = find_free_port()

        # Get project root and web directory
        project_root = Path(__file__).parent.parent
        web_dir = project_root / "web"

        # Start server process
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)

        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, "{web_dir}")
import uvicorn
from standalone_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={test_port}, log_level="error")
""",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(project_root),
        )

        # Wait for server to start
        server_url = f"http://127.0.0.1:{test_port}"
        startup_timeout = 15

        for _ in range(startup_timeout * 10):
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(
                    f"Server failed to start. STDOUT: {stdout.decode()}, "
                    f"STDERR: {stderr.decode()}"
                )

            try:
                import urllib.request

                response = urllib.request.urlopen(
                    f"{server_url}/health", timeout=1
                )
                if response.status == 200:
                    break
            except BaseException:
                pass

            time.sleep(0.1)
        else:
            process.terminate()
            pytest.fail("Server failed to start within timeout")

        yield server_url

        # Cleanup
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    @pytest.fixture(scope="class")
    def chrome_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")

        # Enable logging to capture console errors
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        try:
            # Use Selenium's automatic driver management
            service = Service()
            driver = webdriver.Chrome(service=service, options=chrome_options)
            yield driver
            driver.quit()
        except WebDriverException as e:
            pytest.skip(f"Chrome WebDriver not available: {e}")

    def test_browser_loads_without_errors(self, web_server, chrome_driver):
        """Test that the browser interface loads without JavaScript errors"""
        try:
            # Navigate to the web interface
            chrome_driver.get(web_server)

            # Wait for page to load
            WebDriverWait(chrome_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check for JavaScript errors in browser console
            logs = chrome_driver.get_log("browser")

            # Filter out non-critical errors and warnings
            critical_errors = []
            for log_entry in logs:
                level = log_entry["level"]
                message = log_entry["message"]

                # Skip only truly non-critical warnings
                if any(
                    skip_pattern in message.lower()
                    for skip_pattern in [
                        "favicon.ico",  # Missing favicon is cosmetic
                        "chrome-extension",  # Browser extension issues
                        "devtools",  # Developer tools related
                        "metamask extension not found",  # MetaMask extension
                    ]
                ):
                    continue

                # Check for critical issues that affect functionality
                is_critical = False

                # SEVERE level errors are always critical
                if level == "SEVERE":
                    is_critical = True

                # 404 errors for resources are critical (missing JS/CSS files)
                if "404" in message and any(
                    resource in message.lower()
                    for resource in ["script.js", "style.css", ".js", ".css"]
                ):
                    is_critical = True

                # Network errors for essential resources
                if "failed to load resource" in message.lower() and any(
                    resource in message.lower()
                    for resource in ["script.js", "style.css", ".js", ".css"]
                ):
                    is_critical = True

                # JavaScript syntax and reference errors
                if any(
                    error_type in message.lower()
                    for error_type in [
                        "syntaxerror",
                        "referenceerror",
                        "typeerror",
                        "uncaught",
                    ]
                ):
                    is_critical = True

                if is_critical:
                    critical_errors.append(log_entry)

            # Assert no critical JavaScript errors
            assert len(critical_errors) == 0, (
                f"Critical JavaScript/resource errors found: "
                f"{[f'{error['level']}: {error['message']}' for error in critical_errors]}"
            )

        except TimeoutException:
            pytest.fail("Page failed to load within timeout")

    def test_page_title_and_content(self, web_server, chrome_driver):
        """Test that the page has correct title and expected content"""
        chrome_driver.get(web_server)

        # Wait for page to load
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "title"))
        )

        # Check page title
        assert "Summit AI" in chrome_driver.title

        # Check for expected content
        page_source = chrome_driver.page_source
        assert "Summit AI Web Interface" in page_source
        assert "Standalone web interface" in page_source

    def test_api_status_functionality(self, web_server, chrome_driver):
        """Test that the status API functionality works in browser"""
        chrome_driver.get(web_server)

        # Wait for page to load
        WebDriverWait(chrome_driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Get Status')]")
            )
        )

        # Click the Get Status button
        status_button = chrome_driver.find_element(
            By.XPATH, "//button[contains(text(), 'Get Status')]"
        )
        status_button.click()

        # Wait for response to appear
        try:
            WebDriverWait(chrome_driver, 10).until(
                EC.presence_of_element_located((By.ID, "status-response"))
            )

            # Check that response is visible and contains expected content
            response_element = chrome_driver.find_element(
                By.ID, "status-response"
            )
            assert response_element.is_displayed()

            # Wait a bit for the response to be populated
            time.sleep(2)

            response_text = response_element.text
            assert "Summit" in response_text or "Loading" in response_text

        except TimeoutException:
            pytest.fail("Status API response did not appear within timeout")

    def test_no_console_errors_during_interaction(
        self, web_server, chrome_driver
    ):
        """Test that no console errors occur during user interactions"""
        chrome_driver.get(web_server)

        # Wait for page to load
        WebDriverWait(chrome_driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Get Status')]")
            )
        )

        # Clear any initial logs
        chrome_driver.get_log("browser")

        # Perform user interactions
        status_button = chrome_driver.find_element(
            By.XPATH, "//button[contains(text(), 'Get Status')]"
        )
        status_button.click()

        # Wait for interaction to complete
        time.sleep(3)

        # Check for new JavaScript errors after interaction
        logs = chrome_driver.get_log("browser")

        # Filter critical errors using the same logic as main test
        critical_errors = []
        for log_entry in logs:
            level = log_entry["level"]
            message = log_entry["message"]

            # Skip only truly non-critical warnings
            if any(
                skip_pattern in message.lower()
                for skip_pattern in [
                    "favicon.ico",  # Missing favicon is cosmetic
                    "chrome-extension",  # Browser extension issues
                    "devtools",  # Developer tools related
                    "metamask extension not found",  # MetaMask extension
                ]
            ):
                continue

            # Check for critical issues that affect functionality
            is_critical = False

            # SEVERE level errors are always critical
            if level == "SEVERE":
                is_critical = True

            # 404 errors for resources are critical (missing JS/CSS files)
            if "404" in message and any(
                resource in message.lower()
                for resource in ["script.js", "style.css", ".js", ".css"]
            ):
                is_critical = True

            # Network errors for essential resources
            if "failed to load resource" in message.lower() and any(
                resource in message.lower()
                for resource in ["script.js", "style.css", ".js", ".css"]
            ):
                is_critical = True

            # JavaScript syntax and reference errors
            if any(
                error_type in message.lower()
                for error_type in [
                    "syntaxerror",
                    "referenceerror",
                    "typeerror",
                    "uncaught",
                ]
            ):
                is_critical = True

            if is_critical:
                critical_errors.append(log_entry)

        # Assert no critical errors during interaction
        assert len(critical_errors) == 0, (
            f"Critical JavaScript/resource errors during interaction: "
            f"{[f'{error['level']}: {error['message']}' for error in critical_errors]}"
        )

    def test_health_endpoint_accessibility(self, web_server, chrome_driver):
        """Test that the health endpoint is accessible from browser"""
        health_url = f"{web_server}/health"
        chrome_driver.get(health_url)

        # Wait for page to load
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check that health endpoint returns valid JSON
        page_source = chrome_driver.page_source
        assert "healthy" in page_source or "status" in page_source

        # Verify no JavaScript errors on health endpoint
        logs = chrome_driver.get_log("browser")
        critical_errors = []
        for log_entry in logs:
            level = log_entry["level"]
            message = log_entry["message"]

            # Skip only truly non-critical warnings
            if any(
                skip_pattern in message.lower()
                for skip_pattern in [
                    "favicon.ico",  # Missing favicon is cosmetic
                    "chrome-extension",  # Browser extension issues
                    "devtools",  # Developer tools related
                    "metamask extension not found",  # MetaMask extension
                ]
            ):
                continue

            # Check for critical issues that affect functionality
            is_critical = False

            # SEVERE level errors are always critical
            if level == "SEVERE":
                is_critical = True

            # 404 errors for resources are critical (missing JS/CSS files)
            if "404" in message and any(
                resource in message.lower()
                for resource in ["script.js", "style.css", ".js", ".css"]
            ):
                is_critical = True

            # Network errors for essential resources
            if "failed to load resource" in message.lower() and any(
                resource in message.lower()
                for resource in ["script.js", "style.css", ".js", ".css"]
            ):
                is_critical = True

            if is_critical:
                critical_errors.append(log_entry)

        assert len(critical_errors) == 0, (
            f"JavaScript/resource errors on health endpoint: "
            f"{[f'{error['level']}: {error['message']}' for error in critical_errors]}"
        )

    def test_web_interface_terminal_elements(self, web_server, chrome_driver):
        """Test that web interface has proper terminal-like elements"""
        chrome_driver.get(web_server)

        # Wait for page to load
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for terminal-like interface elements
        page_source = chrome_driver.page_source

        # Verify the interface has interactive elements
        assert "button" in page_source.lower()
        assert "response" in page_source.lower()

        # Check for proper styling that indicates a terminal-like interface
        assert "background" in page_source.lower()
        assert "font-family" in page_source.lower()

        # Verify no broken JavaScript that would affect terminal functionality
        logs = chrome_driver.get_log("browser")
        syntax_errors = [
            log
            for log in logs
            if log["level"] == "SEVERE"
            and any(
                error_type in log["message"].lower()
                for error_type in [
                    "syntaxerror",
                    "referenceerror",
                    "typeerror",
                ]
            )
        ]

        assert len(syntax_errors) == 0, (
            f"JavaScript syntax/reference errors that could break terminal: "
            f"{[error['message'] for error in syntax_errors]}"
        )

    def test_debug_all_console_messages(self, web_server, chrome_driver):
        """Debug test to log all console messages and identify issues"""
        chrome_driver.get(web_server)

        # Wait for page to load
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Retrieve browser console messages for analysis
        logs = chrome_driver.get_log("browser")

        print("\n=== ALL CONSOLE MESSAGES ===")
        for i, log_entry in enumerate(logs):
            level = log_entry["level"]
            message = log_entry["message"]
            timestamp = log_entry["timestamp"]
            print(f"{i+1}. [{level}] {message}")

        print(f"\n=== TOTAL: {len(logs)} console messages ===")

        # Also check what the page source looks like
        page_source = chrome_driver.page_source
        print(f"\n=== PAGE SOURCE LENGTH: {len(page_source)} characters ===")

        # Check if there are any external resource references
        external_resources = []
        if 'src="' in page_source and not 'src="data:' in page_source:
            import re

            src_matches = re.findall(r'src="([^"]*)"', page_source)
            external_resources.extend(
                [src for src in src_matches if not src.startswith("data:")]
            )

        if 'href="' in page_source and not 'href="data:' in page_source:
            import re

            href_matches = re.findall(r'href="([^"]*)"', page_source)
            external_resources.extend(
                [
                    href
                    for href in href_matches
                    if not href.startswith("data:")
                    and not href.startswith("#")
                ]
            )

        if external_resources:
            print(f"\n=== EXTERNAL RESOURCES FOUND ===")
            for resource in external_resources:
                print(f"- {resource}")
        else:
            print(f"\n=== NO EXTERNAL RESOURCES FOUND ===")

        # This test always passes - it's just for debugging
        assert True

    def test_error_detection_with_missing_resources(self, chrome_driver):
        """Test that our error detection catches missing CSS/JS resources"""
        import socket
        import subprocess
        import sys
        import time
        from pathlib import Path

        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                s.listen(1)
                port = s.getsockname()[1]
            return port

        test_port = find_free_port()

        # Start test server with missing resources
        project_root = Path(__file__).parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)

        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Test Server with Missing Resources</title>
    <link rel="stylesheet" href="/style.css">
    <script src="/script.js"></script>
</head>
<body>
    <h1>Test Page</h1>
    <p>This page references missing CSS and JS files.</p>
    <button onclick="testFunction()">Test Button</button>
</body>
</html>
    '''

@app.get("/health")
async def health():
    return {{"status": "healthy"}}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={test_port}, log_level="error")
""",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(project_root),
        )

        # Wait for server to start
        server_url = f"http://127.0.0.1:{test_port}"
        startup_timeout = 10

        for _ in range(startup_timeout * 10):
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(
                    f"Test server failed to start. STDOUT: {stdout.decode()}, "
                    f"STDERR: {stderr.decode()}"
                )

            try:
                import urllib.request

                response = urllib.request.urlopen(
                    f"{server_url}/health", timeout=1
                )
                if response.status == 200:
                    break
            except BaseException:
                pass

            time.sleep(0.1)
        else:
            process.terminate()
            pytest.fail("Test server failed to start within timeout")

        try:
            # Navigate to the test server
            chrome_driver.get(server_url)

            # Wait for page to load
            WebDriverWait(chrome_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait a bit more for all resource loading attempts
            time.sleep(2)

            # Check for JavaScript errors in browser console
            logs = chrome_driver.get_log("browser")

            # Apply our error detection logic
            critical_errors = []
            for log_entry in logs:
                level = log_entry["level"]
                message = log_entry["message"]

                # Skip only truly non-critical warnings
                if any(
                    skip_pattern in message.lower()
                    for skip_pattern in [
                        "favicon.ico",  # Missing favicon is cosmetic
                        "chrome-extension",  # Browser extension issues
                        "devtools",  # Developer tools related
                        "metamask extension not found",  # MetaMask extension
                    ]
                ):
                    continue

                # Check for critical issues that affect functionality
                is_critical = False

                # SEVERE level errors are always critical
                if level == "SEVERE":
                    is_critical = True

                # 404 errors for resources are critical (missing JS/CSS files)
                if "404" in message and any(
                    resource in message.lower()
                    for resource in ["script.js", "style.css", ".js", ".css"]
                ):
                    is_critical = True

                # Network errors for essential resources
                if "failed to load resource" in message.lower() and any(
                    resource in message.lower()
                    for resource in ["script.js", "style.css", ".js", ".css"]
                ):
                    is_critical = True

                # JavaScript syntax and reference errors
                if any(
                    error_type in message.lower()
                    for error_type in [
                        "syntaxerror",
                        "referenceerror",
                        "typeerror",
                        "uncaught",
                    ]
                ):
                    is_critical = True

                if is_critical:
                    critical_errors.append(log_entry)

            # This test should FAIL because we expect to find missing resource
            # errors
            assert len(critical_errors) > 0, (
                f"Expected to find critical errors for missing resources, but found none. "
                f"All logs: {[f'{log['level']}: {log['message']}' for log in logs]}"
            )

            # Verify we caught the specific errors we expect
            missing_css_error = any(
                "style.css" in error["message"] for error in critical_errors
            )
            missing_js_error = any(
                "script.js" in error["message"] for error in critical_errors
            )

            assert missing_css_error, "Should detect missing style.css error"
            assert missing_js_error, "Should detect missing script.js error"

            print(
                f"\n Successfully detected {len(critical_errors)} critical errors:"
            )
            for error in critical_errors:
                print(f"  - [{error['level']}] {error['message']}")

        finally:
            # Cleanup test server
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
