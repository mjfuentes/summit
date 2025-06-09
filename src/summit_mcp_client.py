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

    async def start_task(self, task_id: str) -> bool:
        """Start working on a task"""
        if not self._connected:
            if not await self.connect():
                return False

        try:
            result = await self.client.call_tool(
                "summit_start_task",
                {
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                },
            )

            logger.info(f"Agent {self.agent_id} started task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            return False

    async def end_task(
        self,
        task_id: str,
        success: bool,
        result: Optional[Dict] = None,
        summary: Optional[str] = None,
        files_modified: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        quality_score: float = 5.0,
    ) -> bool:
        """Complete a task with results or mark it as failed"""
        if not self._connected:
            logger.warning("Not connected to MCP server, cannot end task")
            return False

        try:
            await self.client.call_tool(
                "summit_end_task",
                {
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "success": success,
                    "result": result,
                    "summary": summary,
                    "files_modified": files_modified or [],
                    "error_message": error_message,
                    "quality_score": quality_score,
                },
            )

            status = "completed" if success else "failed"
            logger.info(f"Task {task_id} {status} by agent {self.agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to end task {task_id}: {e}")
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


# Convenience functions for simple task management


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


async def start_summit_task(
    task_id: str,
    agent_id: str = None,
    server_host: str = "summit-mcp-service.summit.svc.cluster.local",
    server_port: int = 8080,
) -> bool:
    """Start a task with Summit - convenience function"""
    client = await get_summit_mcp_client(agent_id, server_host, server_port)
    if client:
        try:
            result = await client.start_task(task_id)
            await client.disconnect()
            return result
        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            await client.disconnect()
            return False
    return False


async def complete_summit_task(
    task_id: str,
    success: bool,
    result: Optional[Dict] = None,
    summary: Optional[str] = None,
    files_modified: Optional[List[str]] = None,
    error_message: Optional[str] = None,
    quality_score: float = 5.0,
    agent_id: str = None,
    server_host: str = "summit-mcp-service.summit.svc.cluster.local",
    server_port: int = 8080,
) -> bool:
    """Complete a task with Summit - convenience function"""
    client = await get_summit_mcp_client(agent_id, server_host, server_port)
    if client:
        try:
            result = await client.end_task(
                task_id,
                success,
                result,
                summary,
                files_modified,
                error_message,
                quality_score,
            )
            await client.disconnect()
            return result
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            await client.disconnect()
            return False
    return False


# Simplified agent task manager for containers
class SimpleAgentTaskManager:
    """Simplified task manager for agents using MCP interface"""

    def __init__(
        self,
        agent_id: str = None,
        server_host: str = "summit-mcp-service.summit.svc.cluster.local",
        server_port: int = 8080,
    ):
        self.agent_id = agent_id
        self.server_host = server_host
        self.server_port = server_port
        self.mcp_client = None
        self.current_task_id = None

    async def connect(self) -> bool:
        """Connect to Summit MCP server"""
        self.mcp_client = await get_summit_mcp_client(
            self.agent_id, self.server_host, self.server_port
        )
        return self.mcp_client is not None

    async def start_task(self, task_id: str) -> bool:
        """Start working on a task"""
        if not self.mcp_client:
            if not await self.connect():
                return False

        success = await self.mcp_client.start_task(task_id)
        if success:
            self.current_task_id = task_id
        return success

    async def complete_task(
        self,
        task_id: str = None,
        success: bool = True,
        result: Optional[Dict] = None,
        summary: Optional[str] = None,
        files_modified: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        quality_score: float = 5.0,
    ) -> bool:
        """Complete the current task"""
        task_id = task_id or self.current_task_id
        if not task_id:
            logger.error("No task ID provided and no current task")
            return False

        if not self.mcp_client:
            if not await self.connect():
                return False

        success = await self.mcp_client.end_task(
            task_id,
            success,
            result,
            summary,
            files_modified,
            error_message,
            quality_score,
        )

        if success:
            self.current_task_id = None
        return success

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
            self.mcp_client = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
