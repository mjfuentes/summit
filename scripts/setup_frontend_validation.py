#!/usr/bin/env python3
"""
Setup script for frontend validation with Render.com previews
"""

import os
import sys


def check_requirements():
    """Check if all required secrets and configuration are set"""
    required_secrets = [
        "RENDER_API_KEY",
        "RENDER_SERVICE_ID",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
    ]

    missing = []
    for secret in required_secrets:
        if not os.getenv(secret):
            missing.append(secret)

    if missing:
        print("Missing required environment variables:")
        for secret in missing:
            print(f"  - {secret}")
        print("\nAdd these to your GitHub repository secrets.")
        return False

    print("All required secrets are configured.")
    return True


def validate_render_config():
    """Validate render.yaml configuration"""
    if not os.path.exists("render.yaml"):
        print("render.yaml not found. Please commit the render.yaml file.")
        return False

    print("render.yaml configuration found.")
    return True


def test_api_endpoints():
    """Test that API endpoints return correct format"""
    try:
        import requests

        # Test local server if running
        try:
            response = requests.get(
                "http://localhost:8000/api/tasks", timeout=5
            )
            data = response.json()

            if "tasks" in data and isinstance(data["tasks"], list):
                print("Local API endpoints return correct format.")
            else:
                print("Warning: Local API returns unexpected format.")

        except requests.exceptions.RequestException:
            print("Local server not running - skipping API test.")

    except ImportError:
        print("requests not installed - skipping API test.")


def main():
    print("Frontend Validation Setup")
    print("=" * 40)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Validate configuration
    if not validate_render_config():
        sys.exit(1)

    # Test API endpoints
    test_api_endpoints()

    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Commit and push your changes")
    print("2. Create a PR to test the validation workflow")
    print("3. The workflow will automatically:")
    print("   - Add 'render-preview' label to PR")
    print("   - Wait for Render.com to create preview environment")
    print("   - Run frontend validation tests")
    print("   - Comment results on the PR")
    print("   - Clean up preview environment")


if __name__ == "__main__":
    main()
