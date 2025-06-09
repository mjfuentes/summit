#!/usr/bin/env python3
"""
Summit FastMCP Client - Interact with Summit MCP Server

This client provides a simple way to interact with the Summit MCP server,
allowing users to register agents, get tasks, and mark tasks as complete.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastmcp import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SummitClient:
    """Client for interacting with the Summit MCP server"""

    def __init__(
        self,
        server_url: Optional[str] = None,
        server_path: Optional[str] = None,
    ):
        """
        Initialize the Summit client

        Args:
            server_url: URL to the Summit MCP server (defaults to environment variable)
            server_path: Path to a local server script (defaults to environment variable)
        """
        # Determine server connection details
        self.server_url = server_url or os.environ.get("SUMMIT_MCP_URL")
        self.server_path = server_path or os.environ.get("SUMMIT_MCP_PATH")

        # Choose connection method based on provided details
        if self.server_url:
            # Connect to remote server via URL
            self.client = Client(self.server_url)
        elif self.server_path:
            # Connect to local server via script
            self.client = Client(self.server_path)
        else:
            # Default to localhost SSE connection
            self.client = Client("http://localhost:8080/sse")

        self._is_connected = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Connect to the Summit MCP server"""
        if not self._is_connected:
            await self.client.connect()
            self._is_connected = True
            logger.info("Connected to Summit MCP server")

            # List available tools
            tools = await self.client.list_tools()
            logger.info(
                f"Available tools: {', '.join(tool.name for tool in tools)}"
            )

    async def disconnect(self):
        """Disconnect from the Summit MCP server"""
        if self._is_connected:
            await self.client.disconnect()
            self._is_connected = False
            logger.info("Disconnected from Summit MCP server")

    async def register_agent(
        self,
        agent_id: str,
        role: str,
        agent_type: str = "autonomous",
        capabilities: Optional[List[str]] = None,
        model: str = "unknown",
        system_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register an agent with the Summit platform

        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent (e.g., "engineering", "testing")
            agent_type: Type of agent (default: "autonomous")
            capabilities: List of agent capabilities
            model: Model used by the agent
            system_info: Additional system information

        Returns:
            Registration response
        """
        if not self._is_connected:
            await self.connect()

        # Prepare request
        request = {
            "agent_id": agent_id,
            "role": role,
            "agent_type": agent_type,
            "capabilities": capabilities or [],
            "model": model,
            "system_info": system_info or {},
        }

        # Call the registration tool
        response = await self.client.call_tool(
            "summit_register_agent", request
        )

        # Parse and return response
        if response and response.text:
            return (
                response.json() if response.json() else {"text": response.text}
            )
        return {"error": "No response from server"}

    async def get_next_task(self, agent_id: str, role: str) -> Dict[str, Any]:
        """
        Get the next available task for an agent

        Args:
            agent_id: ID of the agent requesting a task
            role: Role the agent wants to fulfill

        Returns:
            Task information or status message
        """
        if not self._is_connected:
            await self.connect()

        # Prepare request
        request = {
            "agent_id": agent_id,
            "role": role,
        }

        # Call the get_next_task tool
        response = await self.client.call_tool("summit_get_next_task", request)

        # Parse and return response
        if response and response.text:
            return (
                response.json() if response.json() else {"text": response.text}
            )
        return {"error": "No response from server"}

    async def complete_task(
        self,
        task_id: str,
        agent_id: str,
        success: bool = True,
        result: Optional[Dict[str, Any]] = None,
        summary: str = "",
        files_modified: Optional[List[str]] = None,
        error_message: str = "",
    ) -> Dict[str, Any]:
        """
        Mark a task as completed or failed

        Args:
            task_id: ID of the task being completed
            agent_id: ID of the agent completing the task
            success: Whether the task completed successfully
            result: Result data as a dictionary
            summary: Brief summary of work completed
            files_modified: List of files modified
            error_message: Error message if task failed

        Returns:
            Status message
        """
        if not self._is_connected:
            await self.connect()

        # Prepare request
        request = {
            "task_id": task_id,
            "agent_id": agent_id,
            "success": success,
            "result": result or {},
            "summary": summary,
            "files_modified": files_modified or [],
            "error_message": error_message,
        }

        # Call the complete_task tool
        response = await self.client.call_tool("summit_complete_task", request)

        # Parse and return response
        if response and response.text:
            return (
                response.json() if response.json() else {"text": response.text}
            )
        return {"error": "No response from server"}

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the Summit MCP server

        Returns:
            Health status information
        """
        if not self._is_connected:
            await self.connect()

        # Call the health check tool
        response = await self.client.call_tool("summit_health", {})

        # Parse and return response
        if response and response.text:
            return (
                response.json() if response.json() else {"text": response.text}
            )
        return {"error": "No response from server"}

    async def get_agent_guide(self) -> str:
        """
        Get the agent guide documentation

        Returns:
            Agent guide markdown content
        """
        if not self._is_connected:
            await self.connect()

        # Read the agent guide resource
        resource = await self.client.read_resource("/docs/agent-guide")
        return resource.content


async def main():
    """Example usage of the Summit client"""
    # Create agent ID with timestamp to ensure uniqueness
    agent_id = f"example-agent-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    async with SummitClient() as client:
        # Check server health
        health = await client.check_health()
        print(f"Server health: {health}")

        # Get the agent guide
        try:
            guide = await client.get_agent_guide()
            print("\nAgent Guide:")
            print(guide)
        except Exception as e:
            print(f"Error getting agent guide: {e}")

        # Register an agent
        register_response = await client.register_agent(
            agent_id=agent_id,
            role="engineering",
            capabilities=["coding", "testing", "deployment"],
        )
        print(f"\nRegistration response: {register_response}")

        # Get a task
        task_response = await client.get_next_task(
            agent_id=agent_id, role="engineering"
        )
        print(f"\nTask response: {task_response}")

        # Complete a task (example - will likely fail without valid task_id)
        if (
            task_response.get("status") == "success"
            and "task" in task_response
        ):
            task_id = task_response["task"]["id"]
            complete_response = await client.complete_task(
                task_id=task_id,
                agent_id=agent_id,
                summary="Task completed successfully",
                files_modified=["example.py"],
            )
            print(f"\nTask completion response: {complete_response}")


if __name__ == "__main__":
    asyncio.run(main())
