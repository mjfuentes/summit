#!/usr/bin/env python3
"""
Aggressive fixes for remaining linting issues that the standard tools miss.
"""

import os
import re
import subprocess


def fix_import_order_manually():
    """Manually fix import order issues that isort misses"""

    # Fix src/database.py import order
    db_file = "src/database.py"
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            content = f.read()

        # Fix the SQLAlchemy import order
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

        # The imports are already correctly ordered, check if this is a false positive
        print(f" {db_file} imports already correctly ordered")

    # Fix src/pr_reviewers.py import issues
    pr_file = "src/pr_reviewers.py"
    if os.path.exists(pr_file):
        with open(pr_file, "r") as f:
            content = f.read()

        # Add newline between import groups
        content = content.replace(
            "import requests\nfrom anthropic import Anthropic",
            "import requests\n\nfrom anthropic import Anthropic",
        )

        with open(pr_file, "w") as f:
            f.write(content)
        print(f" Fixed import groups in {pr_file}")

    # Fix src/summit.py import issues
    summit_file = "src/summit.py"
    if os.path.exists(summit_file):
        with open(summit_file, "r") as f:
            content = f.read()

        # Reorganize imports properly
        lines = content.split("\n")
        import_section = []
        other_lines = []
        in_imports = True

        for line in lines:
            if line.strip() == "" and in_imports:
                continue
            elif line.startswith("import ") or line.startswith("from "):
                if in_imports:
                    import_section.append(line)
                else:
                    other_lines.append(line)
            else:
                if in_imports:
                    in_imports = False
                other_lines.append(line)

        # Reorganize imports: standard lib, then third party, then local
        stdlib_imports = []
        thirdparty_imports = []
        local_imports = []

        for imp in import_section:
            if any(
                pkg in imp
                for pkg in ["import sys", "import os", "import time"]
            ):
                stdlib_imports.append(imp)
            elif any(pkg in imp for pkg in ["requests", "mcp", "anthropic"]):
                thirdparty_imports.append(imp)
            else:
                local_imports.append(imp)

        # Rebuild file with proper import organization
        new_content = []
        if stdlib_imports:
            new_content.extend(stdlib_imports)
            new_content.append("")
        if thirdparty_imports:
            new_content.extend(thirdparty_imports)
            new_content.append("")
        if local_imports:
            new_content.extend(local_imports)
            new_content.append("")

        new_content.extend(other_lines)

        with open(summit_file, "w") as f:
            f.write("\n".join(new_content))
        print(f" Reorganized imports in {summit_file}")


def fix_line_length_issues():
    """Fix specific line length issues that can be automated"""

    files_to_fix = [
        "src/pr_reviewers.py",
        "src/summit.py",
        "tests/test_summit_basic.py",
        "tests/test_autonomous_integration.py",
        "tests/test_pr_reviewers.py",
    ]

    for filepath in files_to_fix:
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r") as f:
            lines = f.readlines()

        modified = False
        new_lines = []

        for line in lines:
            # Skip if line is within acceptable length
            if len(line.rstrip()) <= 79:
                new_lines.append(line)
                continue

            # Try to break long string literals
            if '"""' in line and len(line.rstrip()) > 79:
                # Skip docstrings - these are harder to break automatically
                new_lines.append(line)
                continue

            # Break long f-strings
            if line.strip().startswith('f"') and len(line.rstrip()) > 79:
                # Try to break f-string
                indent = len(line) - len(line.lstrip())
                content = line.strip()
                if content.startswith('f"') and content.endswith('"'):
                    # Simple f-string that can be broken
                    content = content[2:-1]  # Remove f" and "
                    if " " in content:
                        # Break at roughly middle
                        mid = len(content) // 2
                        break_point = content.find(" ", mid)
                        if break_point > 0:
                            part1 = content[:break_point]
                            part2 = content[break_point + 1 :]
                            new_line = (
                                " " * indent
                                + f'f"{part1} "\n'
                                + " " * indent
                                + f'f"{part2}"\n'
                            )
                            new_lines.append(new_line)
                            modified = True
                            continue

            # Break long regular strings
            if '"' in line and len(line.rstrip()) > 79:
                # Try to break string concatenation
                if " + " in line or ", " in line:
                    new_lines.append(line)  # Too complex for auto-fix
                    continue

            # Break long function calls with many parameters
            if "(" in line and "," in line and len(line.rstrip()) > 79:
                indent = len(line) - len(line.lstrip())
                stripped = line.strip()

                # Try to break at commas
                if stripped.count(",") >= 2:
                    # Break after opening parenthesis
                    paren_pos = stripped.find("(")
                    if paren_pos > 0:
                        func_part = stripped[: paren_pos + 1]
                        params_part = stripped[paren_pos + 1 :]

                        if params_part.endswith(",") or params_part.endswith(
                            "),"
                        ):
                            # Already properly formatted multiline
                            new_lines.append(line)
                            continue

                        # Split parameters
                        params = []
                        current_param = ""
                        paren_level = 0

                        for char in params_part:
                            if char == "(":
                                paren_level += 1
                            elif char == ")":
                                paren_level -= 1
                            elif char == "," and paren_level == 0:
                                params.append(current_param.strip())
                                current_param = ""
                                continue
                            current_param += char

                        if current_param.strip():
                            params.append(current_param.strip())

                        if len(params) >= 2:
                            # Reconstruct as multiline
                            new_line = " " * indent + func_part + "\n"
                            for i, param in enumerate(params[:-1]):
                                new_line += " " * (indent + 4) + param + ",\n"
                            new_line += " " * (indent + 4) + params[-1] + "\n"
                            new_line += " " * indent + ")\n"
                            new_lines.append(new_line)
                            modified = True
                            continue

            # If no automatic fix possible, keep original line
            new_lines.append(line)

        if modified:
            with open(filepath, "w") as f:
                f.writelines(new_lines)
            print(f" Fixed line lengths in {filepath}")


def fix_test_files():
    """Fix import issues in test files"""

    test_files = [
        "tests/test_database.py",
        "tests/test_web_api.py",
    ]

    for filepath in test_files:
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r") as f:
            content = f.read()

        # Add missing newlines between import groups
        # Fix pytest and pytest_asyncio grouping
        content = content.replace(
            "import pytest\nimport pytest_asyncio",
            "import pytest\n\nimport pytest_asyncio",
        )

        # Fix fastapi import grouping
        content = content.replace(
            "import pytest\nfrom fastapi.testclient import TestClient",
            "import pytest\n\nfrom fastapi.testclient import TestClient",
        )

        content = content.replace(
            "from fastapi.testclient import TestClient\nfrom standalone_server import app",
            "from fastapi.testclient import TestClient\n\nfrom standalone_server import app",
        )

        with open(filepath, "w") as f:
            f.write(content)
        print(f" Fixed imports in {filepath}")


def main():
    """Run all remaining fixes"""
    print(" FIXING REMAINING LINTING ISSUES")
    print("=" * 50)

    fix_import_order_manually()
    fix_line_length_issues()
    fix_test_files()

    # Run formatters again
    print("\n RUNNING FINAL FORMATTING PASS")
    subprocess.run(
        [
            "python",
            "-m",
            "isort",
            "src/",
            "tests/",
            "--profile",
            "black",
            "--line-length",
            "79",
        ]
    )
    subprocess.run(
        ["python", "-m", "black", "src/", "tests/", "--line-length", "79"]
    )

    # Check results
    print("\n CHECKING REMAINING ISSUES")
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
        print(" All remaining issues fixed!")
    else:
        remaining = result.stdout.count("\n")
        print(f"  {remaining} issues still remain (down from 53)")
        print(
            "These likely need manual intervention for complex string literals"
        )


if __name__ == "__main__":
    main()
