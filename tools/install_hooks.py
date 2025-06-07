#!/usr/bin/env python3

"""
Git Hooks Installer for Summit Project
Sets up pre-commit hooks and development workflow automation.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def setup_git_hooks():
    """Install Git hooks for automated quality checks"""
    print("Setting up Summit AI Git hooks...")

    repo_root = Path(__file__).parent.parent
    hooks_source = repo_root / ".githooks"
    git_hooks_dir = repo_root / ".git" / "hooks"

    # Check if we're in a Git repository
    if not (repo_root / ".git").exists():
        print("Error: Not in a Git repository")
        return False

    # Create hooks directory if it doesn't exist
    git_hooks_dir.mkdir(exist_ok=True)

    # Install pre-commit hook
    pre_commit_source = hooks_source / "pre-commit"
    pre_commit_dest = git_hooks_dir / "pre-commit"

    if pre_commit_source.exists():
        shutil.copy2(pre_commit_source, pre_commit_dest)
        # Make executable
        os.chmod(pre_commit_dest, 0o755)
        print(f"Installed pre-commit hook: {pre_commit_dest}")
    else:
        print(
            f"Warning: Pre-commit hook source not found: {pre_commit_source}"
        )
        return False

    # Configure Git to use hooks
    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".git/hooks"],
            cwd=repo_root,
            check=True,
        )
        print("Configured Git to use hooks")
    except subprocess.CalledProcessError:
        print("Warning: Could not configure Git hooks path")

    return True


def test_emoji_linter():
    """Test the emoji linter functionality"""
    print("Testing emoji linter...")

    repo_root = Path(__file__).parent.parent
    linter_path = repo_root / "tools" / "emoji_linter.py"

    if not linter_path.exists():
        print(f"Error: Emoji linter not found: {linter_path}")
        return False

    # Make executable
    os.chmod(linter_path, 0o755)

    # Test with a simple check
    try:
        result = subprocess.run(
            [sys.executable, str(linter_path), "--help"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )

        if result.returncode == 0:
            print("Emoji linter is working correctly")
            return True
        else:
            print(f"Emoji linter test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error testing emoji linter: {e}")
        return False


def update_coding_standards():
    """Update CODING_STANDARDS.md with emoji linting information"""
    print("Updating coding standards documentation...")

    repo_root = Path(__file__).parent.parent
    standards_file = repo_root / "CODING_STANDARDS.md"

    if not standards_file.exists():
        print("Warning: CODING_STANDARDS.md not found")
        return False

    # Read current content
    with open(standards_file, "r") as f:
        content = f.read()

    # Check if emoji linting section already exists
    if "Emoji Linting" in content:
        print("Emoji linting section already exists in CODING_STANDARDS.md")
        return True

    # Add emoji linting section
    emoji_section = """
### Emoji Linting (Automated)
- **Automatic emoji removal** - Pre-commit hook automatically removes all emoji characters
- **Zero tolerance enforcement** - No emojis can be committed to the repository
- **Manual linting available** - Run `python tools/emoji_linter.py --fix` to clean files manually
- **Comprehensive detection** - Covers all Unicode emoji ranges and symbol categories
- **Professional codebase** - Maintains enterprise-grade documentation standards

#### Emoji Linter Commands:
```bash
# Check for emojis without fixing
python tools/emoji_linter.py

# Automatically remove emojis
python tools/emoji_linter.py --fix

# Check only staged files (used by pre-commit hook)
python tools/emoji_linter.py --staged --fix

# Verbose output showing detection details
python tools/emoji_linter.py --verbose
```
"""

    # Insert after the Documentation section
    if "### Documentation" in content:
        content = content.replace(
            "### Documentation", emoji_section + "\n### Documentation"
        )
    else:
        # Append to end of file
        content += emoji_section

    # Write updated content
    with open(standards_file, "w") as f:
        f.write(content)

    print("Updated CODING_STANDARDS.md with emoji linting section")
    return True


def update_run_coverage():
    """Update run_coverage.py to include emoji linting"""
    print("Updating test coverage script to include emoji linting...")

    repo_root = Path(__file__).parent.parent
    coverage_file = repo_root / "run_coverage.py"

    if not coverage_file.exists():
        print("Warning: run_coverage.py not found")
        return False

    # Read current content
    with open(coverage_file, "r") as f:
        content = f.read()

    # Check if emoji linting is already included
    if "emoji_linter" in content:
        print("Emoji linting already integrated in run_coverage.py")
        return True

    # Add emoji linting before running tests
    emoji_check = """
    print("Checking for emoji violations...")
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "tools/emoji_linter.py", "--fix"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print("Emoji violations found and fixed:")
            print(result.stdout)
            print("Please review changes and re-run tests")
            return
        else:
            print("No emoji violations found")
    except Exception as e:
        print(f"Warning: Could not run emoji linter: {e}")
"""

    # Insert after imports but before test execution
    if "def main():" in content:
        content = content.replace("def main():", f"def main():{emoji_check}")
    elif 'if __name__ == "__main__":' in content:
        content = content.replace(
            'if __name__ == "__main__":',
            f'{emoji_check}\nif __name__ == "__main__":',
        )

    # Write updated content
    with open(coverage_file, "w") as f:
        f.write(content)

    print("Updated run_coverage.py to include emoji linting")
    return True


def main():
    """Main installation function"""
    print("Summit AI Development Environment Setup")
    print("=====================================")

    success = True

    # Install Git hooks
    if not setup_git_hooks():
        success = False

    # Test emoji linter
    if not test_emoji_linter():
        success = False

    # Update documentation
    if not update_coding_standards():
        success = False

    # Update test workflow
    if not update_run_coverage():
        success = False

    if success:
        print("\nSetup completed successfully!")
        print("\nEmoji linting is now active:")
        print("- Pre-commit hook will automatically remove emojis")
        print(
            "- Run 'python tools/emoji_linter.py --fix' to clean existing files"
        )
        print("- All commits are now emoji-free by design")
        print("\nProfessional codebase standards enforced!")
    else:
        print(
            "\nSetup completed with warnings. Please review the messages above."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
