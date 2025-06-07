#!/usr/bin/env python3
"""
Safe, targeted fixes for the remaining 11 linting issues.
Addresses specific patterns without aggressive automation.
"""

import os
import re
import subprocess


def fix_import_order_simple():
    """Fix simple import order issues without breaking syntax"""

    # Fix src/agent_git_api.py - move sys before pathlib
    file_path = "src/agent_git_api.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        # Simple reordering
        content = content.replace(
            "import subprocess\nfrom pathlib import Path\nimport sys",
            "import subprocess\nimport sys\nfrom pathlib import Path",
        )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed import order in {file_path}")

    # Fix src/cost_tracker.py - move json before datetime import
    file_path = "src/cost_tracker.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        content = content.replace(
            "import os\nfrom datetime import datetime, timedelta\nimport json",
            "import json\nimport os\nfrom datetime import datetime, timedelta",
        )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed import order in {file_path}")

    # Fix src/database.py - move os before datetime import
    file_path = "src/database.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        content = content.replace(
            "from datetime import datetime, timedelta\nfrom typing import Any, Dict, List, Optional\n\nimport os",
            "import os\nfrom datetime import datetime, timedelta\nfrom typing import Any, Dict, List, Optional",
        )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed import order in {file_path}")


def fix_sqlalchemy_imports():
    """Fix SQLAlchemy import order in database.py"""
    file_path = "src/database.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        # Fix alphabetical order
        old_imports = """from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    delete,
    func,
    select,
    update,
)"""

        new_imports = """from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    delete,
    func,
    select,
    update,
)"""

        content = content.replace(old_imports, new_imports)

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed SQLAlchemy imports in {file_path}")


def fix_summit_imports():
    """Fix import organization in summit.py"""
    file_path = "src/summit.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Find import section and reorganize
        import_lines = []
        other_lines = []
        in_imports = True

        for line in lines:
            if (
                line.startswith("import ") or line.startswith("from ")
            ) and in_imports:
                import_lines.append(line.rstrip())
            elif line.strip() == "" and in_imports:
                continue
            else:
                if in_imports:
                    in_imports = False
                other_lines.append(line)

        # Simple reorganization
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for imp in import_lines:
            if any(
                mod in imp
                for mod in [
                    "import sys",
                    "import os",
                    "import time",
                    "import subprocess",
                    "from typing",
                ]
            ):
                stdlib_imports.append(imp)
            elif any(
                mod in imp
                for mod in [
                    "import requests",
                    "import mcp",
                    "from anthropic",
                    "from mcp",
                ]
            ):
                third_party_imports.append(imp)
            else:
                local_imports.append(imp)

        # Sort each group
        stdlib_imports.sort()
        third_party_imports.sort()
        local_imports.sort()

        # Rebuild file
        new_content = []
        new_content.extend([imp + "\n" for imp in stdlib_imports])
        new_content.append("\n")
        new_content.extend([imp + "\n" for imp in third_party_imports])
        new_content.append("\n")
        new_content.extend([imp + "\n" for imp in local_imports])
        new_content.append("\n")
        new_content.extend(other_lines)

        with open(file_path, "w") as f:
            f.writelines(new_content)
        print(f" Fixed imports in {file_path}")


def fix_simple_line_lengths():
    """Fix simple line length issues"""

    fixes = [
        # Fix summit.py line length issues
        (
            "src/summit.py",
            'description="Provide AI-powered advice and guidance for development and coding questions"',
            'description=(\n            "Provide AI-powered advice and guidance for development "\n            "and coding questions"\n        )',
        ),
        (
            "src/summit.py",
            'description="Get current Summit status, uptime, and cost information"',
            'description="Get current Summit status, uptime, and cost info"',
        ),
        (
            "src/summit.py",
            'url = f"https://api.github.com/repos/{owner}/{repo}/codespaces"',
            'url = (\n            f"https://api.github.com/repos/{owner}/{repo}/codespaces"\n        )',
        ),
    ]

    for file_path, old, new in fixes:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()

            if old in content:
                content = content.replace(old, new)
                with open(file_path, "w") as f:
                    f.write(content)
                print(f" Fixed line length in {file_path}")


def fix_bare_except():
    """Fix bare except clause"""
    file_path = "src/summit.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        # Replace bare except with specific exception
        content = content.replace(
            "        except:", "        except Exception:"
        )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed bare except in {file_path}")


def fix_module_level_import():
    """Fix module level import not at top"""
    file_path = "src/summit.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        # Move cost_tracker import to top with other imports
        if "from cost_tracker import CostTracker" in content:
            # Remove from middle
            content = content.replace(
                "from cost_tracker import CostTracker\n", ""
            )
            # Add to imports at top (will be fixed by import reorganization)
            content = content.replace(
                "from typing import Any, Dict, List, Optional",
                "from typing import Any, Dict, List, Optional\nfrom cost_tracker import CostTracker",
            )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed module level import in {file_path}")


def fix_test_files():
    """Fix test file issues"""

    # Fix tests/test_database.py
    file_path = "tests/test_database.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        content = content.replace(
            "import pytest\nimport pytest_asyncio",
            "import pytest\n\nimport pytest_asyncio",
        )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed imports in {file_path}")

    # Fix tests/test_web_api.py
    file_path = "tests/test_web_api.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()

        content = content.replace(
            "import pytest\nfrom fastapi.testclient import TestClient",
            "import pytest\n\nfrom fastapi.testclient import TestClient",
        )

        with open(file_path, "w") as f:
            f.write(content)
        print(f" Fixed imports in {file_path}")


def run_final_check():
    """Check remaining issues"""
    print("\n CHECKING RESULTS")
    print("=" * 30)

    result = subprocess.run(
        [
            "python",
            "-m",
            "flake8",
            "src/",
            "tests/",
            "--select=E501,F401,E402,E712,E722,W291,I100,I101,I201",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(" ALL ISSUES FIXED!")
        return True
    else:
        issues = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )
        remaining = len(issues)

        print(f" PROGRESS: {53 - remaining} issues fixed!")
        print(f"   Remaining: {remaining} issues")

        if remaining <= 10:
            print(f"\n Remaining issues:")
            for issue in issues[:remaining]:
                print(f"   {issue}")

        return remaining == 0


def main():
    """Run safe targeted fixes"""
    print(" SAFE TARGETED LINTING FIXES")
    print("=" * 40)

    fix_import_order_simple()
    fix_sqlalchemy_imports()
    fix_summit_imports()
    fix_simple_line_lengths()
    fix_bare_except()
    fix_module_level_import()
    fix_test_files()

    # Run isort and black for final cleanup
    print("\n RUNNING SAFE FORMATTING")
    subprocess.run(
        ["python", "-m", "isort", "src/", "tests/", "--profile", "black"],
        capture_output=True,
    )
    subprocess.run(
        ["python", "-m", "black", "src/", "tests/", "--line-length", "79"],
        capture_output=True,
    )

    success = run_final_check()

    if success:
        print("\n ALL AUTOMATION COMPLETE!")
        return 0
    else:
        print("\n SIGNIFICANT PROGRESS MADE!")
        return 1


if __name__ == "__main__":
    main()
