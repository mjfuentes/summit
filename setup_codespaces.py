#!/usr/bin/env python3
"""
Setup script for Summit's GitHub Codespaces integration.

This script helps configure the environment variables needed for
Summit's self-modification capabilities using GitHub Codespaces.
"""

import os
import subprocess
import sys

def check_git_repo():
    """Check if we're in a git repository and get remote info"""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            print(f"✅ Git repository detected: {remote_url}")
            
            # Extract owner and repo from URL
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    # SSH format: git@github.com:owner/repo.git
                    parts = remote_url.split(":")[-1].replace(".git", "").split("/")
                    return parts[0], parts[1]
                elif remote_url.startswith("https://"):
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = remote_url.split("/")
                    return parts[-2], parts[-1].replace(".git", "")
            
            print("⚠️  Repository is not hosted on GitHub")
            return None, None
        else:
            print("❌ Not a git repository")
            return None, None
    except FileNotFoundError:
        print("❌ Git not found")
        return None, None

def check_environment_variables():
    """Check current environment variable status"""
    print("\n📋 Environment Variables Status:")
    
    vars_to_check = [
        ("GITHUB_TOKEN", "GitHub Personal Access Token for API access"),
        ("GITHUB_OWNER", "GitHub repository owner/organization"),
        ("GITHUB_REPO", "GitHub repository name"),
        ("ANTHROPIC_API_KEY", "Anthropic API key for AI capabilities")
    ]
    
    missing_vars = []
    
    for var_name, description in vars_to_check:
        value = os.getenv(var_name)
        if value:
            # Show first/last few characters for security
            masked_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            print(f"✅ {var_name}: {masked_value}")
        else:
            print(f"❌ {var_name}: Not set")
            missing_vars.append((var_name, description))
    
    return missing_vars

def generate_setup_instructions(owner, repo, missing_vars):
    """Generate setup instructions for missing configuration"""
    
    print("\n🔧 Setup Instructions:")
    print("=" * 50)
    
    if missing_vars:
        print("\nMissing environment variables:")
        
        for var_name, description in missing_vars:
            print(f"\n{var_name}:")
            print(f"  Description: {description}")
            
            if var_name == "GITHUB_TOKEN":
                print("  How to get:")
                print("  1. Go to https://github.com/settings/tokens")
                print("  2. Click 'Generate new token (classic)'")
                print("  3. Give it a name like 'Summit Codespaces'")
                print("  4. Select scopes: 'repo', 'codespace'")
                print("  5. Generate and copy the token")
                print("  Set with: export GITHUB_TOKEN='your_token_here'")
                
            elif var_name == "GITHUB_OWNER" and owner:
                print(f"  Set with: export GITHUB_OWNER='{owner}'")
                
            elif var_name == "GITHUB_REPO" and repo:
                print(f"  Set with: export GITHUB_REPO='{repo}'")
                
            elif var_name == "ANTHROPIC_API_KEY":
                print("  How to get:")
                print("  1. Go to https://console.anthropic.com/")
                print("  2. Create an account or sign in")
                print("  3. Generate an API key")
                print("  Set with: export ANTHROPIC_API_KEY='your_key_here'")

def main():
    print("🚀 Summit GitHub Codespaces Setup")
    print("=" * 40)
    
    # Check git repository
    owner, repo = check_git_repo()
    
    # Check environment variables
    missing_vars = check_environment_variables()
    
    # Auto-set repo info if detected
    if owner and repo:
        if not os.getenv("GITHUB_OWNER"):
            os.environ["GITHUB_OWNER"] = owner
            print(f"📝 Auto-set GITHUB_OWNER to '{owner}'")
            
        if not os.getenv("GITHUB_REPO"):
            os.environ["GITHUB_REPO"] = repo
            print(f"📝 Auto-set GITHUB_REPO to '{repo}'")
    
    # Generate instructions
    generate_setup_instructions(owner, repo, missing_vars)
    
    # Check if ready
    if not missing_vars or (len(missing_vars) <= 2 and owner and repo):
        print("\n🎉 Setup complete! Summit is ready for self-modification.")
        print("\nNew capabilities available:")
        print("- summit_learn_capability: Learn new skills via Codespaces")
        print("- summit_codespace_status: Check development environments")
        print("- summit_deploy_changes: Deploy completed changes")
        print("- summit_cleanup_environment: Clean up resources")
    else:
        print(f"\n⚠️  Please set {len(missing_vars)} environment variables to enable self-modification.")
    
    print("\n💡 Tip: Add these exports to your ~/.bashrc or ~/.zshrc for persistence")

if __name__ == "__main__":
    main() 