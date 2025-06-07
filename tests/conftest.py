"""
Pytest configuration and shared fixtures for Summit AI tests.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Ensure src directory is in path
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set environment variables for testing
os.environ.setdefault("SUMMIT_READONLY_MODE", "true")
os.environ.setdefault("TESTING", "true")
