#!/usr/bin/env python3

import asyncio
import json
import subprocess
import sys
from typing import Any

import mcp.client.stdio
import mcp.types as types
from mcp.client import ClientSession

async def test_summit_mcp_server():
    """Test Summit MCP server functionality"""
    
    print("Testing Summit MCP Server")
    print("=" * 40)
    
    # Start Summit as a subprocess
    summit_process = subprocess.Popen([
        sys.executable, "summit.py"
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Connect to Summit MCP server
        async with mcp.client.stdio.stdio_client() as (read_stream, write_stream):
            # Connect streams to the subprocess
            read_stream = summit_process.stdout
            write_stream = summit_process.stdin
            
            async with ClientSession(read_stream, write_stream) as session:
                
                # Initialize the session
                await session.initialize()
                print("Connected to Summit MCP server")
                
                # Test 1: List available tools
                print("\nTest 1: Listing available tools")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Test 2: Check Summit status
                print("\nTest 2: Checking Summit status")
                status_result = await session.call_tool("summit_status", {})
                print("Status response:")
                for content in status_result.content:
                    if content.type == "text":
                        print(content.text)
                
                # Test 3: Get cost report
                print("\nTest 3: Getting cost report")
                cost_result = await session.call_tool("summit_cost_report", {})
                print("Cost report:")
                for content in cost_result.content:
                    if content.type == "text":
                        print(content.text)
                
                # Test 4: Ask for advice (small request to test AI)
                print("\nTest 4: Asking for advice")
                advice_result = await session.call_tool("summit_advice", {
                    "question": "What is the best way to test an MCP server?",
                    "context": "I'm testing Summit's MCP functionality"
                })
                print("Advice response:")
                for content in advice_result.content:
                    if content.type == "text":
                        print(content.text[:200] + "..." if len(content.text) > 200 else content.text)
                
                print("\nAll MCP tests completed successfully")
                
    except Exception as e:
        print(f"ERROR: MCP test failed: {e}")
        
    finally:
        # Clean up subprocess
        summit_process.terminate()
        try:
            summit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            summit_process.kill()

if __name__ == "__main__":
    asyncio.run(test_summit_mcp_server()) 