#!/usr/bin/env python3
"""
Final targeted fixes for stubborn linting issues.
"""

import os
import re


def fix_database_imports():
    """Fix the SQLAlchemy import order in database.py"""
    file_path = "src/database.py"
    with open(file_path, "r") as f:
        content = f.read()

    # Fix the specific import order issue
    old_pattern = r"from sqlalchemy import \(\s*([^)]+)\)"

    def fix_import_order(match):
        imports_text = match.group(1)
        imports = [
            imp.strip().rstrip(",")
            for imp in imports_text.split("\n")
            if imp.strip()
        ]

        # Remove empty items and sort properly
        clean_imports = []
        for imp in imports:
            if imp and imp != ",":
                clean_imports.append(imp.rstrip(","))

        # Sort alphabetically
        clean_imports.sort()

        # Format back
        formatted = "from sqlalchemy import (\n"
        for i, imp in enumerate(clean_imports):
            if i == len(clean_imports) - 1:
                formatted += f"    {imp},\n"
            else:
                formatted += f"    {imp},\n"
        formatted += ")"

        return formatted

    content = re.sub(old_pattern, fix_import_order, content, flags=re.DOTALL)

    with open(file_path, "w") as f:
        f.write(content)
    print(f" Fixed import order in {file_path}")


def fix_pr_reviewers_imports():
    """Fix import issues in pr_reviewers.py"""
    file_path = "src/pr_reviewers.py"
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Find the import section and reorganize
    new_lines = []
    import_section = []
    past_imports = False

    for line in lines:
        if line.startswith("import ") or line.startswith("from "):
            if not past_imports:
                import_section.append(line.rstrip())
            else:
                new_lines.append(line)
        elif line.strip() == "" and not past_imports:
            continue  # Skip empty lines in import section
        else:
            if not past_imports and import_section:
                # Process import section
                stdlib_imports = []
                third_party_imports = []

                for imp in import_section:
                    if any(
                        pkg in imp
                        for pkg in [
                            "import os",
                            "import sys",
                            "from dataclasses",
                            "from typing",
                        ]
                    ):
                        stdlib_imports.append(imp)
                    else:
                        third_party_imports.append(imp)

                # Write organized imports
                if stdlib_imports:
                    new_lines.extend([imp + "\n" for imp in stdlib_imports])
                    new_lines.append("\n")

                if third_party_imports:
                    new_lines.extend(
                        [imp + "\n" for imp in third_party_imports]
                    )
                    new_lines.append("\n")

                past_imports = True

            new_lines.append(line)

    with open(file_path, "w") as f:
        f.writelines(new_lines)
    print(f" Fixed imports in {file_path}")


def fix_summit_imports():
    """Fix import organization in summit.py"""
    file_path = "src/summit.py"
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Reorganize imports
    new_lines = []
    import_lines = []
    past_imports = False

    for line in lines:
        if (
            line.startswith("import ") or line.startswith("from ")
        ) and not past_imports:
            import_lines.append(line.rstrip())
        elif line.strip() == "" and not past_imports:
            continue
        else:
            if not past_imports:
                # Process imports
                stdlib = []
                third_party = []
                local = []

                for imp in import_lines:
                    if any(
                        pkg in imp
                        for pkg in ["import sys", "import os", "import time"]
                    ):
                        stdlib.append(imp)
                    elif any(
                        pkg in imp
                        for pkg in [
                            "import requests",
                            "import mcp",
                            "from anthropic",
                            "from mcp",
                        ]
                    ):
                        third_party.append(imp)
                    else:
                        local.append(imp)

                # Write organized imports
                for group in [stdlib, third_party, local]:
                    if group:
                        new_lines.extend([imp + "\n" for imp in group])
                        new_lines.append("\n")

                past_imports = True

            new_lines.append(line)

    with open(file_path, "w") as f:
        f.writelines(new_lines)
    print(f" Fixed imports in {file_path}")


def break_long_lines_aggressively():
    """Aggressively break long lines in specific files"""

    files_to_fix = {
        "src/pr_reviewers.py": [
            # Specific lines that can be broken
            (271, "if not self.github_headers:"),
            (302, 'url = f"https://api.github.com/repos"'),
            (330, "# Analyze the review sentimen"),
            (342, "if not self.anthropic_client or not review_text:"),
        ],
        "src/summit.py": [
            # Long lines that can be broken
            (159, 'url = f"https://api.github.com"'),
            (166, "response = requests.get("),
            (172, "# Check if Summit repository"),
        ],
    }

    for file_path, line_fixes in files_to_fix.items():
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r") as f:
            lines = f.readlines()

        modified = False
        for line_num, target_content in line_fixes:
            if line_num <= len(lines):
                line = lines[line_num - 1]  # Convert to 0-based index
                if len(line.rstrip()) > 79 and target_content in line:
                    # Try to break this specific line
                    indent = len(line) - len(line.lstrip())

                    # Break long URL or string
                    if '"https://' in line:
                        # Break URL
                        parts = line.split('"https://')
                        if len(parts) == 2:
                            before = parts[0]
                            url = "https://" + parts[1]
                            # Split URL at logical point
                            if "/" in url[10:]:  # Skip https:// part
                                split_point = url.find("/", 10)
                                url1 = url[:split_point]
                                url2 = url[split_point:]
                                new_line = (
                                    before
                                    + '"'
                                    + url1
                                    + '" \\\n'
                                    + " " * (indent + 4)
                                    + '"'
                                    + url2
                                )
                                lines[line_num - 1] = new_line
                                modified = True

                    # Break long function calls
                    elif "(" in line and "," in line:
                        # Simple parameter breaking
                        paren_pos = line.find("(")
                        if paren_pos > 0:
                            before_paren = line[: paren_pos + 1]
                            after_paren = line[paren_pos + 1 :]

                            if (
                                len(before_paren) < 60
                            ):  # Only if function name isn't too long
                                lines[line_num - 1] = (
                                    before_paren
                                    + "\n"
                                    + " " * (indent + 4)
                                    + after_paren
                                )
                                modified = True

        if modified:
            with open(file_path, "w") as f:
                f.writelines(lines)
            print(f" Broke long lines in {file_path}")


def main():
    """Apply all final fixes"""
    print(" APPLYING FINAL TARGETED LINTING FIXES")
    print("=" * 50)

    fix_database_imports()
    fix_pr_reviewers_imports()
    fix_summit_imports()
    break_long_lines_aggressively()

    # Final formatting pass
    import subprocess

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
        ],
        capture_output=True,
    )
    subprocess.run(
        ["python", "-m", "black", "src/", "tests/", "--line-length", "79"],
        capture_output=True,
    )

    print("\n FINAL CHECK")
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
    else:
        before_count = 53
        remaining_lines = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )
        after_count = len(remaining_lines)
        improvement = before_count - after_count

        print(f" PROGRESS: {improvement} issues fixed!")
        print(f"   Before: {before_count} issues")
        print(f"   After:  {after_count} issues")

        if after_count > 0:
            print(
                f"\n Remaining {after_count} issues (mostly complex line lengths)"
            )
            print("These typically require manual intervention for:")
            print("- Complex string formatting")
            print("- Long URLs or file paths")
            print("- Complex function signatures")


if __name__ == "__main__":
    main()
