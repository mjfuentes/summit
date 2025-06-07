#!/usr/bin/env python3
"""Test script for the interactive git wrapper"""

import unittest
from pathlib import Path
import sys
import os

# Get repo root
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Import the wrapper
from scripts.agent_git import AgentGitWrapper


def main():

    """Test the git wrapper"""

    print(" Testing the Agent Git Wrapper")

    print("=" * 60)



    # Show current status

    print("\n1. Checking current status:")

    status()



    # Run the save workflow

    print("\n2. Running automated save workflow:")

    print("This will validate, test, and push if everything passes.\n")



    result = save_work(

        "Implement automated agent Git wrapper with local validation"

    )



    print(f"\n{'='*60}")

    print(f"FINAL RESULT: {' SUCCESS' if result else ' FAILED'}")

    print(f"{'='*60}")



    if result:

        print("\nYour changes have been committed and pushed!")

        print("CI/CD will run asynchronously on GitHub.")

    else:

        print("\nPlease fix the issues above and try again.")





if __name__ == "__main__":

    main()

