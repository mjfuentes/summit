#!/usr/bin/env python3

import os
import requests
from datetime import datetime, timezone
import json

def monitor_agent_actions():
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print(' No GITHUB_TOKEN found')
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    print(" AGENT WORKFLOW MONITOR")
    print("=" * 50)

    # First, get our specific PR details
    pr_url = 'https://api.github.com/repos/mjfuentes/summit/pulls/1'
    pr_response = requests.get(pr_url, headers=headers)
    
    if pr_response.status_code != 200:
        print(f' Cannot access PR #1: {pr_response.status_code}')
        return
    
    pr_data = pr_response.json()
    pr_branch = pr_data['head']['ref']  # feature/pr-workflow
    pr_sha = pr_data['head']['sha']
    pr_created = datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00'))
    
    print(f" AGENT'S PR STATUS")
    print(f"   PR #1: {pr_data['title']}")
    print(f"   Branch: {pr_branch}")
    print(f"   State: {pr_data['state']} | Mergeable: {pr_data.get('mergeable', 'unknown')}")
    print(f"   Created: {pr_created.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    # Get workflow runs and filter for agent-related ones
    runs_url = 'https://api.github.com/repos/mjfuentes/summit/actions/runs'
    runs_response = requests.get(runs_url, headers=headers, params={'per_page': 20})
    
    if runs_response.status_code != 200:
        print(f' Cannot access workflow runs: {runs_response.status_code}')
        return
    
    runs_data = runs_response.json()
    
    # Filter runs related to our agent's work
    agent_runs = []
    for run in runs_data['workflow_runs']:
        run_created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
        
        # Include if:
        # 1. It's on our feature branch
        # 2. It's a PR event for our PR
        # 3. It was created after our PR (and is main branch - could be auto-merge)
        is_agent_related = (
            run['head_branch'] == pr_branch or  # Our feature branch
            (run['event'] == 'pull_request' and run_created >= pr_created) or  # PR events since our PR
            (run['head_branch'] == 'main' and run_created >= pr_created and run['event'] == 'push')  # Potential auto-merge
        )
        
        if is_agent_related:
            agent_runs.append(run)
    
    if not agent_runs:
        print(" No workflow runs found for agent's work")
        return
    
    print(f" AGENT'S WORKFLOW RUNS ({len(agent_runs)} found)")
    print()
    
    # Analyze each relevant run
    for i, run in enumerate(agent_runs, 1):
        status = run['status']
        conclusion = run['conclusion']
        
        # Determine emoji and status
        if status == 'completed':
            if conclusion == 'success':
                emoji = ""
                status_text = "SUCCESS"
            elif conclusion == 'failure':
                emoji = ""
                status_text = "FAILED"
            elif conclusion == 'cancelled':
                emoji = ""
                status_text = "CANCELLED"
            else:
                emoji = ""
                status_text = f"COMPLETED ({conclusion})"
        elif status == 'in_progress':
            emoji = ""
            status_text = "RUNNING"
        elif status == 'queued':
            emoji = ""
            status_text = "QUEUED"
        else:
            emoji = ""
            status_text = status.upper()
        
        run_created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
        
        print(f"{emoji} RUN #{i}: {status_text}")
        print(f"   Workflow: {run['name']}")
        print(f"   Branch: {run['head_branch']} | Event: {run['event']}")
        print(f"   Started: {run_created.strftime('%H:%M:%S UTC')}")
        print(f"   URL: {run['html_url']}")
        
        # If failed, try to get more details
        if conclusion == 'failure':
            jobs_url = f"https://api.github.com/repos/mjfuentes/summit/actions/runs/{run['id']}/jobs"
            jobs_response = requests.get(jobs_url, headers=headers)
            if jobs_response.status_code == 200:
                jobs_data = jobs_response.json()
                failed_jobs = [job for job in jobs_data['jobs'] if job['conclusion'] == 'failure']
                if failed_jobs:
                    print(f"    Failed Jobs:")
                    for job in failed_jobs[:3]:  # Show first 3 failed jobs
                        print(f"      - {job['name']}: {job['conclusion']}")
        
        print()
    
    # Summary and recommendations
    print(" SUMMARY")
    
    completed_runs = [r for r in agent_runs if r['status'] == 'completed']
    successful_runs = [r for r in completed_runs if r['conclusion'] == 'success']
    failed_runs = [r for r in completed_runs if r['conclusion'] == 'failure']
    running_runs = [r for r in agent_runs if r['status'] == 'in_progress']
    
    print(f"    Successful: {len(successful_runs)}")
    print(f"    Failed: {len(failed_runs)}")
    print(f"    Running: {len(running_runs)}")
    
    # Determine overall status and next steps
    if running_runs:
        print(f"\n STATUS: Workflow in progress...")
        print(f"   The agent's PR is currently being processed by CI/CD")
        latest_running = running_runs[0]
        print(f"   Monitor: {latest_running['html_url']}")
    elif failed_runs and not successful_runs:
        print(f"\n STATUS: Agent's workflow FAILED")
        print(f"   The PR cannot be auto-merged due to CI failures")
        print(f"   Action needed: Check failed jobs above")
    elif successful_runs:
        latest_success = successful_runs[0]
        if latest_success['head_branch'] == 'main':
            print(f"\n STATUS: Agent's work MERGED to main!")
            print(f"   The PR was successfully auto-merged")
        else:
            print(f"\n STATUS: Agent's CI checks PASSED")
            print(f"   The PR should auto-merge soon if enabled")
    
    # Check if PR is still open when it should have merged
    if pr_data['state'] == 'open' and successful_runs:
        latest_success = successful_runs[0]
        if latest_success['head_branch'] == pr_branch:
            print(f"\n  NOTE: PR still open despite successful CI")
            print(f"   Check if auto-merge is properly configured")

if __name__ == "__main__":
    monitor_agent_actions() 