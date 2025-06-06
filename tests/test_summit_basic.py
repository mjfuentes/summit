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
        # Start Summit process
        process = subprocess.Popen([
            sys.executable, "src/summit.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
          text=True, env=env)
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if process is still running
        poll_result = process.poll()
        if poll_result is None:
            print("SUCCESS: Summit process started and is running")
        else:
            print(f"ERROR: Summit process exited with code {poll_result}")
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"Error output: {stderr_output}")
            assert False, f"Summit process failed to start, exit code: {poll_result}"
        
        print("Test 2: Checking process responsiveness")
        
        # Let it run for a few more seconds
        time.sleep(3)
        
        # Check if still running
        poll_result = process.poll()
        if poll_result is None:
            print("SUCCESS: Summit is stable and responsive")
        else:
            print(f"ERROR: Summit process crashed with code {poll_result}")
            assert False, f"Summit process crashed, exit code: {poll_result}"
        
        print("Test 3: Terminating process")
        process.terminate()
        
        # Wait for clean shutdown
        try:
            process.wait(timeout=5)
            print("SUCCESS: Summit shut down cleanly")
        except subprocess.TimeoutExpired:
            print("WARNING: Had to force kill Summit")
            process.kill()
        
        print("\nBasic functionality test PASSED")
        
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        assert False, f"Test failed with exception: {e}"

if __name__ == "__main__":
    test_summit_basic() 