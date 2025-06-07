#!/usr/bin/env python3
import requests
import time
import sys
import json

def check_task_status(task_id, max_wait=300):
    """Poll task status until completion or timeout"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"http://localhost:8000/api/tasks/{task_id}")
            data = response.json()
            
            if not data.get('success'):
                print(f"Error: {data.get('message', 'Unknown error')}")
                return None
                
            task = data.get('task', {})
            status = task.get('status', 'unknown')
            
            print(f"[{int(time.time() - start_time)}s] Status: {status}")
            
            if status in ['completed', 'failed', 'timeout', 'stopped']:
                print(f"\nTask {status}!")
                print(f"Is completed: {data.get('is_completed', False)}")
                if 'full_logs' in task:
                    print(f"Full logs available: {len(task['full_logs'])} characters")
                return task
                
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error checking status: {e}")
            time.sleep(5)
    
    print(f"Timeout after {max_wait}s")
    return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 check_task.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    result = check_task_status(task_id)
    
    if result:
        print("\nTask completed successfully!")
    else:
        print("\nTask did not complete or failed")
        sys.exit(1) 