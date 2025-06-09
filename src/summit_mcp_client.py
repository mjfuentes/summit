#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import socket
from typing import Any, Dict, List, Optional

import mcp

logger = logging.getLogger(__name__)


class SummitMCPClient:
    """Client for communicating with Summit MCP Server"""

    def __init__(
        self,
        server_host: str = "summit-mcp-service.summit.svc.cluster.local",
        server_port: int = 8080,
        agent_id: str = None,
        agent_role: str = None,
    ):
        self.server_host = server_host
        self.server_port = server_port
        self.agent_id = agent_id or self._get_default_agent_id()
        self.agent_role = agent_role
        self.client = None
        self._connected = False

    def _get_default_agent_id(self) -> str:
        """Generate a default agent ID from hostname and environment"""
        hostname = socket.gethostname()
        pod_name = os.getenv("HOSTNAME", hostname)
        return pod_name.replace("-", "_")

    async def connect(self) -> bool:
        """Connect to the Summit MCP server"""
        try:
            # For TCP-based MCP connection
            import mcp.client.stdio

            # Create TCP connection to MCP server
            reader, writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )

            self.client = mcp.client.stdio.StdioClientSession(reader, writer)
            await self.client.initialize()

            self._connected = True
            logger.info(
                f"Connected to Summit MCP server at {self.server_host}:{self.server_port}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Summit MCP server: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.client:
            try:
                await self.client.close()
                self._connected = False
                logger.info("Disconnected from Summit MCP server")
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server: {e}")

    async def register_agent(
        self,
        role: str,
        capabilities: List[str],
        status: str = "active",
        version: str = "1.0.0",
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Register this agent with the Summit system"""
        if not self._connected:
            if not await self.connect():
                return False

        try:
            result = await self.client.call_tool(
                "summit_register_agent",
                {
                    "agent_id": self.agent_id,
                    "role": role,
                    "capabilities": capabilities,
                    "status": status,
                    "version": version,
                    "metadata": metadata or {},
                },
            )

            logger.info(
                f"Agent {self.agent_id} registered successfully with role {role}"
            )
            self.agent_role = role
            return True

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    async def update_status(
        self,
        status: str,
        current_task: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Update agent status and send heartbeat"""
        if not self._connected:
            logger.warning("Not connected to MCP server, cannot update status")
            return False

        try:
            result = await self.client.call_tool(
                "summit_update_agent_status",
                {
                    "agent_id": self.agent_id,
                    "status": status,
                    "current_task": current_task,
                    "metadata": metadata or {},
                },
            )

            logger.debug(f"Status updated to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False

    async def get_tasks(
        self, role: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict]:
        """Get tasks assigned to this agent or role"""
        if not self._connected:
            logger.warning("Not connected to MCP server, cannot get tasks")
            return []

        try:
            result = await self.client.call_tool(
                "summit_list_tasks",
                {
                    "role": role or self.agent_role,
                    "status": status,
                    "limit": 50,
                },
            )

            # Parse the response to extract task data
            # (This would need to be adapted based on actual MCP response format)
            return []

        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update the status of a task"""
        if not self._connected:
            logger.warning("Not connected to MCP server, cannot update task")
            return False

        try:
            await self.client.call_tool(
                "summit_update_task_status",
                {
                    "task_id": task_id,
                    "status": status,
                    "agent_id": self.agent_id,
                    "result": result,
                    "error": error,
                },
            )

            logger.info(f"Task {task_id} status updated to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False

    async def add_task_comment(
        self,
        task_id: str,
        comment_type: str,
        content: str,
        approval_status: Optional[str] = None,
        rating: Optional[int] = None,
        is_internal: bool = False,
    ) -> bool:
        """Add a comment to a task"""
        if not self._connected:
            logger.warning("Not connected to MCP server, cannot add comment")
            return False

        try:
            await self.client.call_tool(
                "summit_add_task_comment",
                {
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "comment_type": comment_type,
                    "content": content,
                    "approval_status": approval_status,
                    "rating": rating,
                    "is_internal": is_internal,
                },
            )

            logger.info(f"Comment added to task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return False

    async def unregister(self) -> bool:
        """Unregister this agent from the Summit system"""
        if not self._connected:
            return True  # Already disconnected

        try:
            await self.client.call_tool(
                "summit_unregister_agent", {"agent_id": self.agent_id}
            )

            logger.info(f"Agent {self.agent_id} unregistered successfully")
            await self.disconnect()
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to MCP server"""
        return self._connected

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Convenience functions for agent registration and management


async def register_agent_with_summit(
    agent_id: str,
    role: str,
    capabilities: List[str],
    server_host: str = "summit-mcp-service.summit.svc.cluster.local",
    server_port: int = 8080,
) -> Optional[SummitMCPClient]:
    """Register an agent with Summit and return the client for further use"""
    client = SummitMCPClient(
        server_host=server_host,
        server_port=server_port,
        agent_id=agent_id,
        agent_role=role,
    )

    if await client.register_agent(role, capabilities):
        return client
    else:
        await client.disconnect()
        return None


async def get_summit_mcp_client(
    agent_id: str = None,
    server_host: str = "summit-mcp-service.summit.svc.cluster.local",
    server_port: int = 8080,
) -> Optional[SummitMCPClient]:
    """Get a connected Summit MCP client"""
    client = SummitMCPClient(
        server_host=server_host, server_port=server_port, agent_id=agent_id
    )

    if await client.connect():
        return client
    else:
        return None


# For backward compatibility with database-based agent lifecycle
class MCPAgentLifecycleManager:
    """Manages agent lifecycle using MCP instead of direct database access"""

    def __init__(self, database_url: str = None):
        # database_url is ignored, included for compatibility
        self.mcp_client = None
        self._agent_id = None
        self._role = None

    async def initialize(
        self, agent_id: str, role: str, capabilities: List[str]
    ):
        """Initialize the agent with MCP registration"""
        self._agent_id = agent_id
        self._role = role

        self.mcp_client = await register_agent_with_summit(
            agent_id, role, capabilities
        )

        if self.mcp_client:
            logger.info(f"Agent {agent_id} initialized with MCP registration")
            return True
        else:
            logger.error(f"Failed to initialize agent {agent_id} with MCP")
            return False

    async def update_status(self, status: str, current_task: str = None):
        """Update agent status"""
        if self.mcp_client:
            return await self.mcp_client.update_status(status, current_task)
        return False

    async def heartbeat(self):
        """Send heartbeat to maintain agent registration"""
        if self.mcp_client:
            return await self.mcp_client.update_status(
                "active", metadata={"heartbeat": True}
            )
        return False

    async def cleanup(self):
        """Clean up agent registration"""
        if self.mcp_client:
            await self.mcp_client.unregister()
            self.mcp_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
