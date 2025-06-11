#!/usr/bin/env python3
"""Simple demo of the agent git wrapper"""

import sys
from pathlib import Path

from agent_git_api import save_work

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


# Save just the git wrapper files we created
files_to_save = [
    "scripts/agent_git.py",
    "src/agent_git_api.py",
    ".github/agent_prompt.md",
    ".cursorrules",
    "CODING_STANDARDS.md",
    "tests/test_pr_reviewers.py",
]

print(" Demonstrating Agent Git Wrapper")
print("=" * 60)
print(f"Saving {len(files_to_save)} files with automated validation\n")

result = save_work(
    "Implement automated Git wrapper for agent operations", files_to_save
)

if result:
    print("\n Success! Changes have been validated, committed and pushed.")
else:
    print("\n Failed. Please check the errors above.")
