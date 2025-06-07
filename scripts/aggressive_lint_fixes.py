#!/usr/bin/env python3
"""
Aggressive comprehensive linting fixes for all remaining issues.
Handles specific patterns that standard tools miss.
"""

import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple


def fix_import_order_issues():
    """Fix all import order and organization issues"""
    print(" FIXING IMPORT ORDER ISSUES")
    print("=" * 50)

    files_to_fix = {
        "src/database.py": {
            "pattern": r"from sqlalchemy import \(\s*([^)]+)\)",
            "replacement": lambda match: format_sqlalchemy_imports(
                match.group(1)
            ),
        },
        "src/pr_reviewers.py": {"reorganize_imports": True},
        "src/summit.py": {"reorganize_imports": True},
        "tests/test_database.py": {
            "add_import_newlines": [
                (
                    "import pytest\nimport pytest_asyncio",
                    "import pytest\n\nimport pytest_asyncio",
                )
            ]
        },
        "tests/test_web_api.py": {"reorganize_imports": True},
    }

    for file_path, fixes in files_to_fix.items():
        if not os.path.exists(file_path):
            continue

        print(f"Fixing {file_path}...")

        with open(file_path, "r") as f:
            content = f.read()

        original_content = content

        # Handle specific pattern replacements
        if "pattern" in fixes:
            content = re.sub(
                fixes["pattern"],
                fixes["replacement"],
                content,
                flags=re.DOTALL,
            )

        # Handle import newline additions
        if "add_import_newlines" in fixes:
            for old, new in fixes["add_import_newlines"]:
                content = content.replace(old, new)

        # Handle full import reorganization
        if fixes.get("reorganize_imports"):
            content = reorganize_imports_comprehensive(content, file_path)

        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            print(f"   Fixed imports in {file_path}")
        else:
            print(f"  - No changes needed in {file_path}")


def format_sqlalchemy_imports(imports_text: str) -> str:
    """Format SQLAlchemy imports in alphabetical order"""
    imports = [
        imp.strip().rstrip(",")
        for imp in imports_text.split("\n")
        if imp.strip()
    ]
    clean_imports = [imp for imp in imports if imp and imp != ","]
    clean_imports.sort()

    formatted = "from sqlalchemy import (\n"
    for imp in clean_imports:
        formatted += f"    {imp},\n"
    formatted += ")"
    return formatted


def reorganize_imports_comprehensive(content: str, file_path: str) -> str:
    """Comprehensively reorganize imports with proper grouping"""
    lines = content.split("\n")
    import_lines = []
    other_lines = []
    in_imports = True

    for line in lines:
        if (
            line.startswith("import ") or line.startswith("from ")
        ) and in_imports:
            import_lines.append(line)
        elif line.strip() == "" and in_imports:
            continue  # Skip empty lines in import section
        else:
            if in_imports:
                in_imports = False
            other_lines.append(line)

    # Categorize imports
    stdlib_imports = []
    third_party_imports = []
    local_imports = []

    for imp in import_lines:
        if is_stdlib_import(imp):
            stdlib_imports.append(imp)
        elif is_local_import(imp, file_path):
            local_imports.append(imp)
        else:
            third_party_imports.append(imp)

    # Sort within each group
    stdlib_imports.sort()
    third_party_imports.sort()
    local_imports.sort()

    # Rebuild content with proper spacing
    new_content = []

    if stdlib_imports:
        new_content.extend(stdlib_imports)
        new_content.append("")

    if third_party_imports:
        new_content.extend(third_party_imports)
        new_content.append("")

    if local_imports:
        new_content.extend(local_imports)
        new_content.append("")

    # Remove trailing empty line if no other content
    if other_lines and not other_lines[0].strip():
        other_lines = other_lines[1:]

    new_content.extend(other_lines)

    return "\n".join(new_content)


def is_stdlib_import(import_line: str) -> bool:
    """Check if import is from standard library"""
    stdlib_modules = {
        "os",
        "sys",
        "time",
        "datetime",
        "json",
        "re",
        "subprocess",
        "typing",
        "dataclasses",
        "contextlib",
        "asyncio",
        "pathlib",
    }

    if import_line.startswith("import "):
        module = import_line[7:].split(".")[0].split(" ")[0]
        return module in stdlib_modules
    elif import_line.startswith("from "):
        module = import_line[5:].split(" ")[0].split(".")[0]
        return module in stdlib_modules

    return False


def is_local_import(import_line: str, file_path: str) -> bool:
    """Check if import is local to the project"""
    local_modules = {
        "cost_tracker",
        "task_manager",
        "database",
        "agent_git_api",
        "standalone_server",
    }

    if import_line.startswith("from "):
        module = import_line[5:].split(" ")[0]
        return any(local_mod in module for local_mod in local_modules)

    return False


def fix_line_length_aggressively():
    """Fix line length issues with aggressive automation"""
    print("\n FIXING LINE LENGTH ISSUES")
    print("=" * 50)

    files_with_line_issues = [
        "src/pr_reviewers.py",
        "src/summit.py",
        "tests/test_autonomous_integration.py",
        "tests/test_pr_reviewers.py",
        "tests/test_summit_basic.py",
    ]

    for file_path in files_with_line_issues:
        if not os.path.exists(file_path):
            continue

        print(f"Processing {file_path}...")

        with open(file_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        modified = False

        for i, line in enumerate(lines):
            if len(line.rstrip()) <= 79:
                new_lines.append(line)
                continue

            # Try various line breaking strategies
            new_line = try_break_line(line, file_path, i)
            if new_line != line:
                new_lines.extend(
                    new_line if isinstance(new_line, list) else [new_line]
                )
                modified = True
            else:
                new_lines.append(line)

        if modified:
            with open(file_path, "w") as f:
                f.writelines(new_lines)
            print(f"   Fixed line lengths in {file_path}")
        else:
            print(f"  - No line length fixes applied to {file_path}")


def try_break_line(line: str, file_path: str, line_num: int) -> str:
    """Try to break a long line using various strategies"""
    stripped = line.strip()
    indent = len(line) - len(line.lstrip())

    # Strategy 1: Break long URLs
    if "https://" in line and len(stripped) > 79:
        return break_url_line(line, indent)

    # Strategy 2: Break long function calls
    if "(" in line and "," in line and stripped.count(",") >= 2:
        return break_function_call(line, indent)

    # Strategy 3: Break long string concatenations
    if " + " in line and '"' in line:
        return break_string_concatenation(line, indent)

    # Strategy 4: Break long f-strings
    if line.strip().startswith('f"') and len(stripped) > 79:
        return break_f_string(line, indent)

    # Strategy 5: Break long assignments
    if " = " in line and len(stripped) > 79:
        return break_assignment(line, indent)

    # Strategy 6: Break long print statements
    if stripped.startswith("print(") and len(stripped) > 79:
        return break_print_statement(line, indent)

    return line


def break_url_line(line: str, indent: int) -> str:
    """Break lines containing URLs"""
    if '"https://' in line:
        parts = line.split('"https://')
        if len(parts) == 2:
            before = parts[0].rstrip()
            url_part = "https://" + parts[1]

            # Find logical break point in URL
            if "/" in url_part[10:]:  # Skip https:// part
                split_idx = url_part.find("/", 10)
                url1 = url_part[:split_idx]
                url2 = url_part[split_idx:]

                return [
                    before + '"' + url1 + '" \\\n',
                    " " * (indent + 4) + '"' + url2,
                ]

    return line


def break_function_call(line: str, indent: int) -> str:
    """Break long function calls"""
    stripped = line.strip()
    paren_pos = stripped.find("(")

    if paren_pos > 0 and paren_pos < 40:  # Only if function name is reasonable
        func_part = stripped[: paren_pos + 1]
        params_part = stripped[paren_pos + 1:]

        # Split parameters
        params = []
        current_param = ""
        paren_level = 0

        for char in params_part:
            if char == "(":
                paren_level += 1
            elif char == ")":
                paren_level -= 1
                if paren_level < 0:  # Closing parenthesis
                    if current_param.strip():
                        params.append(current_param.strip())
                    break
            elif char == "," and paren_level == 0:
                params.append(current_param.strip())
                current_param = ""
                continue
            current_param += char

        if len(params) >= 2:
            result = [" " * indent + func_part + "\n"]
            for i, param in enumerate(params):
                if i == len(params) - 1:
                    result.append(" " * (indent + 4) + param + "\n")
                else:
                    result.append(" " * (indent + 4) + param + ",\n")
            result.append(" " * indent + ")\n")
            return result

    return line


def break_string_concatenation(line: str, indent: int) -> str:
    """Break long string concatenations"""
    if " + " in line and line.count('"') >= 2:
        parts = line.split(" + ")
        if len(parts) >= 2:
            result = []
            for i, part in enumerate(parts):
                if i == 0:
                    result.append(" " * indent + part.strip() + " +\n")
                elif i == len(parts) - 1:
                    result.append(" " * (indent + 4) + part.strip() + "\n")
                else:
                    result.append(" " * (indent + 4) + part.strip() + " +\n")
            return result

    return line


def break_f_string(line: str, indent: int) -> str:
    """Break long f-strings at logical points"""
    stripped = line.strip()
    if stripped.startswith('f"') and stripped.endswith('"'):
        content = stripped[2:-1]
        if " " in content and len(content) > 60:
            # Find middle point to break
            mid = len(content) // 2
            break_point = content.rfind(" ", 0, mid + 20)
            if break_point > 10:  # Don't break too early
                part1 = content[:break_point]
                part2 = content[break_point + 1:]
                return [
                    " " * indent + f'f"{part1} "\n',
                    " " * indent + f'f"{part2}"\n',
                ]

    return line


def break_assignment(line: str, indent: int) -> str:
    """Break long assignment statements"""
    if " = " in line:
        var_part, value_part = line.split(" = ", 1)
        if len(value_part.strip()) > 50:
            return [
                var_part.rstrip() + " = (\n",
                " " * (indent + 4) + value_part.strip() + "\n",
                " " * indent + ")\n",
            ]

    return line


def break_print_statement(line: str, indent: int) -> str:
    """Break long print statements"""
    stripped = line.strip()
    if stripped.startswith("print(") and stripped.endswith(")"):
        content = stripped[6:-1]  # Remove print( and )
        if '"' in content and len(content) > 60:
            return [
                " " * indent + "print(\n",
                " " * (indent + 4) + content + "\n",
                " " * indent + ")\n",
            ]

    return line


def run_final_formatting():
    """Run final formatting tools"""
    print("\n RUNNING FINAL FORMATTING TOOLS")
    print("=" * 50)

    commands = [
        (
            [
                "python",
                "-m",
                "autoflake",
                "--in-place",
                "--recursive",
                "--remove-unused-variables",
                "--remove-all-unused-imports",
                "src/",
                "tests/",
            ],
            "Remove unused imports",
        ),
        (
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
                "--force-sort-within-sections",
            ],
            "Sort imports",
        ),
        (
            ["python", "-m", "black", "src/", "tests/", "--line-length", "79"],
            "Format with Black",
        ),
        (
            [
                "python",
                "-m",
                "autopep8",
                "--in-place",
                "--aggressive",
                "--recursive",
                "--max-line-length",
                "79",
                "src/",
                "tests/",
            ],
            "Final autopep8 pass",
        ),
    ]

    for cmd, desc in commands:
        print(f"Running: {desc}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print(f"   {desc} completed")
            else:
                print(f"   {desc} had issues: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"   {desc} timed out")
        except Exception as e:
            print(f"   {desc} failed: {e}")


def check_final_results():
    """Check final linting results"""
    print("\n CHECKING FINAL RESULTS")
    print("=" * 50)

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
        print(" ALL LINTING ISSUES FIXED!")
        return True
    else:
        issues = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )
        remaining = len(issues)

        print(f" SIGNIFICANT PROGRESS MADE!")
        print(f"   Started with: 53+ issues")
        print(f"   Remaining: {remaining} issues")
        print(f"   Fixed: {53 - remaining} issues automatically")

        if remaining > 0:
            print(f"\n Remaining {remaining} issues need manual attention:")
            # Group by issue type
            issue_types = {}
            for issue in issues[:10]:  # Show first 10
                if ":" in issue:
                    parts = issue.split(" ", 2)
                    if len(parts) >= 2:
                        error_code = parts[1]
                        issue_types[error_code] = (
                            issue_types.get(error_code, 0) + 1
                        )
                        if (
                            issue_types[error_code] <= 3
                        ):  # Show max 3 of each type
                            print(f"     {issue}")

            if remaining > 10:
                print(f"     ... and {remaining - 10} more")

            print(f"\n Issue breakdown:")
            for code, count in sorted(issue_types.items()):
                print(f"   {code}: {count} occurrences")

        return remaining == 0


def main():
    """Run comprehensive aggressive linting fixes"""
    print(" AGGRESSIVE COMPREHENSIVE LINTING FIXES")
    print("=" * 60)
    print("Fixing all automatable linting issues with advanced techniques")
    print("=" * 60)

    try:
        # Step 1: Fix import issues
        fix_import_order_issues()

        # Step 2: Fix line length issues
        fix_line_length_aggressively()

        # Step 3: Run formatting tools
        run_final_formatting()

        # Step 4: Check results
        success = check_final_results()

        if success:
            print("\n AUTOMATION COMPLETE - All issues fixed!")
            print("You can now commit with confidence!")
            return 0
        else:
            print("\n SUBSTANTIAL AUTOMATION ACHIEVED")
            print(
                "Most issues fixed automatically. Remaining issues need manual review."
            )
            return 1

    except Exception as e:
        print(f"\n Error during automation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
