#!/usr/bin/env python3

import subprocess
import sys
import os
import time

def test_summit_basic():
    """Basic test to verify Summit starts and runs"""
    
    print("Testing Summit Basic Functionality")
    print("=" * 35)
    
    # Set API key
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = "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"
    
    print("Test 1: Starting Summit process")
    
    try:
        # Get the correct path to summit.py
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        summit_path = os.path.join(repo_root, "src", "summit.py")
        
        # Start Summit process
        process = subprocess.Popen([
            sys.executable, summit_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
          text=True, env=env, cwd=repo_root)
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check process result
        poll_result = process.poll()
        
        # Summit is implemented as an MCP server that exits when no input is received
        # In an actual application, it would be run with input/output streams connected
        # For testing purposes, we expect it to exit with code 0 (success)
        if poll_result == 0:
            print("SUCCESS: Summit process started and exited successfully with code 0")
        else:
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"Error output: {stderr_output}")
            assert False, f"Summit process failed with unexpected exit code: {poll_result}"
        
        print("\nBasic functionality test PASSED")
        
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        assert False, f"Test failed with exception: {e}"

if __name__ == "__main__":
    test_summit_basic() 