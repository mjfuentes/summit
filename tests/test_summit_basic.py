#!/usr/bin/env python3

import os
import subprocess
import sys
import time


def test_summit_basic():
    """Basic test to verify Summit starts and runs"""

    print("Testing Summit Basic Functionality")
    print("=" * 35)

    # Set API key
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = (
        "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"
    )

    print("Test 1: Starting Summit process")

    try:
        # Get the correct path to summit.py
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        summit_path = os.path.join(repo_root, "src", "summit.py")

        # Start Summit process
        process = subprocess.Popen(
            [sys.executable, summit_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=repo_root,
        )

        # Give it a moment to start and wait for it to finish
        try:
            # Wait up to 5 seconds for the process to complete
            stdout, stderr = process.communicate(timeout=5)
            exit_code = process.returncode
            killed_by_timeout = False
        except subprocess.TimeoutExpired:
            # If process doesn't finish in 5 seconds, kill it
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            killed_by_timeout = True

        # Summit is implemented as an MCP server that waits for input/output streams
        # It may exit cleanly (code 0) or need to be killed if waiting for streams (code -9)
        # Both cases indicate successful startup

        success_message = (
            "Summit AI Advisor is running with cost controls enabled!"
        )
        startup_successful = success_message in stderr if stderr else False

        if exit_code == 0:
            print(
                "SUCCESS: Summit process started and exited successfully with code 0"
            )
        elif killed_by_timeout and startup_successful:
            print(
                "SUCCESS: Summit process started successfully and was running (killed by timeout as expected)"
            )
        else:
            if stderr:
                print(f"Error output: {stderr}")
            if stdout:
                print(f"Stdout output: {stdout}")
            assert (
                False
            ), f"Summit process failed to start properly. Exit code: {exit_code}, Startup successful: {startup_successful}"

        print("\nBasic functionality test PASSED")

    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        assert False, f"Test failed with exception: {e}"


if __name__ == "__main__":
    test_summit_basic()
