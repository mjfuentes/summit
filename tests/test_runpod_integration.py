#!/usr/bin/env python3
"""
Tests for RunPod Integration

This module tests the RunPod integration functionality including
configuration, deployment management, and cost calculations.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from runpod_integration import (
    DeploymentInfo,
    RunPodClient,
    RunPodConfig,
    RunPodDeploymentManager,
    create_runpod_config,
)


class TestRunPodConfig:
    """Test RunPod configuration"""

    def test_config_creation(self):
        """Test creating RunPod configuration"""
        config = RunPodConfig(
            api_key="test-key",
            gpu_type="RTX 4090",
            deployment_type="serverless",
        )

        assert config.api_key == "test-key"
        assert config.gpu_type == "RTX 4090"
        assert config.deployment_type == "serverless"
        assert config.workers_min == 0
        assert config.workers_max == 3
        assert config.environment_vars == {}

    def test_config_with_environment_vars(self):
        """Test configuration with environment variables"""
        env_vars = {"TEST_VAR": "test_value"}
        config = RunPodConfig(api_key="test-key", environment_vars=env_vars)

        assert config.environment_vars == env_vars

    def test_create_runpod_config_helper(self):
        """Test the helper function for creating config"""
        config = create_runpod_config(
            api_key="test-key", gpu_type="A100", workers_max=5
        )

        assert config.api_key == "test-key"
        assert config.gpu_type == "A100"
        assert config.workers_max == 5


class TestDeploymentInfo:
    """Test deployment information dataclass"""

    def test_deployment_info_creation(self):
        """Test creating deployment info"""
        deployment = DeploymentInfo(
            deployment_id="test-id",
            deployment_type="serverless",
            gpu_type="RTX 4090",
            status="running",
        )

        assert deployment.deployment_id == "test-id"
        assert deployment.deployment_type == "serverless"
        assert deployment.gpu_type == "RTX 4090"
        assert deployment.status == "running"
        assert deployment.created_at is not None
        assert deployment.cost_per_hour == 0.0

    def test_deployment_info_with_custom_created_at(self):
        """Test deployment info with custom creation time"""
        custom_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        deployment = DeploymentInfo(
            deployment_id="test-id",
            deployment_type="pod",
            gpu_type="A100",
            status="starting",
            created_at=custom_time,
        )

        assert deployment.created_at == custom_time


class TestRunPodClient:
    """Test RunPod client functionality"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return RunPodConfig(
            api_key="test-key",
            gpu_type="RTX 4090",
            deployment_type="serverless",
        )

    @pytest.fixture
    def client(self, config):
        """Create test client"""
        with patch("runpod.api_key"):
            return RunPodClient(config)

    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.config.api_key == "test-key"
        assert "RTX 4090" in client.gpu_pricing
        assert "A100" in client.gpu_pricing

    def test_gpu_pricing_structure(self, client):
        """Test GPU pricing structure"""
        rtx_4090_pricing = client.gpu_pricing["RTX 4090"]

        assert "pod_community" in rtx_4090_pricing
        assert "pod_secure" in rtx_4090_pricing
        assert "serverless_flex" in rtx_4090_pricing
        assert "serverless_active" in rtx_4090_pricing

        # Check pricing values are reasonable
        assert rtx_4090_pricing["pod_community"] > 0
        assert rtx_4090_pricing["serverless_flex"] > 0

    @pytest.mark.asyncio
    async def test_get_available_gpus_success(self, client):
        """Test getting available GPUs successfully"""
        mock_gpus = [
            {"id": "RTX 4090", "displayName": "RTX 4090", "memoryInGb": 24},
            {"id": "A100", "displayName": "A100 80GB", "memoryInGb": 80},
        ]

        with patch("runpod.get_gpus", return_value=mock_gpus):
            gpus = await client.get_available_gpus()

            assert len(gpus) == 2
            assert gpus[0]["displayName"] == "RTX 4090"
            assert gpus[1]["memoryInGb"] == 80

    @pytest.mark.asyncio
    async def test_get_available_gpus_failure(self, client):
        """Test handling GPU retrieval failure"""
        with patch("runpod.get_gpus", side_effect=Exception("API Error")):
            gpus = await client.get_available_gpus()

            assert gpus == []

    @pytest.mark.asyncio
    async def test_get_gpu_info_success(self, client):
        """Test getting specific GPU info"""
        mock_gpu_info = {
            "id": "RTX 4090",
            "displayName": "RTX 4090",
            "memoryInGb": 24,
            "maxGpuCount": 8,
        }

        with patch("runpod.get_gpu", return_value=mock_gpu_info):
            gpu_info = await client.get_gpu_info("RTX 4090")

            assert gpu_info["displayName"] == "RTX 4090"
            assert gpu_info["memoryInGb"] == 24

    @pytest.mark.asyncio
    async def test_get_gpu_info_failure(self, client):
        """Test handling GPU info retrieval failure"""
        with patch("runpod.get_gpu", side_effect=Exception("Not found")):
            gpu_info = await client.get_gpu_info("INVALID_GPU")

            assert gpu_info is None

    @pytest.mark.asyncio
    async def test_create_template_success(self, client):
        """Test creating template successfully"""
        mock_template = {
            "id": "template-123",
            "name": "test-template",
            "imageName": "test-image",
        }

        with patch("runpod.create_template", return_value=mock_template):
            template = await client.create_template(
                name="test-template", image_name="test-image"
            )

            assert template["id"] == "template-123"
            assert template["name"] == "test-template"

    @pytest.mark.asyncio
    async def test_create_template_failure(self, client):
        """Test handling template creation failure"""
        with patch(
            "runpod.create_template", side_effect=Exception("Creation failed")
        ):
            template = await client.create_template(
                name="test-template", image_name="test-image"
            )

            assert template is None

    @pytest.mark.asyncio
    async def test_create_serverless_endpoint_success(self, client):
        """Test creating serverless endpoint"""
        mock_endpoint = {
            "id": "endpoint-123",
            "name": "test-endpoint",
            "templateId": "template-123",
        }

        with patch("runpod.create_endpoint", return_value=mock_endpoint):
            endpoint = await client.create_serverless_endpoint(
                template_id="template-123", name="test-endpoint"
            )

            assert endpoint["id"] == "endpoint-123"
            assert endpoint["name"] == "test-endpoint"

    @pytest.mark.asyncio
    async def test_create_pod_success(self, client):
        """Test creating pod successfully"""
        mock_pod = {"id": "pod-123", "name": "test-pod", "gpuType": "RTX 4090"}

        with patch("runpod.create_pod", return_value=mock_pod):
            pod = await client.create_pod(
                name="test-pod", image_name="test-image"
            )

            assert pod["id"] == "pod-123"
            assert pod["name"] == "test-pod"

    @pytest.mark.asyncio
    async def test_get_pods_success(self, client):
        """Test getting pods successfully"""
        mock_pods = [
            {"id": "pod-1", "name": "pod-1"},
            {"id": "pod-2", "name": "pod-2"},
        ]

        with patch("runpod.get_pods", return_value=mock_pods):
            pods = await client.get_pods()

            assert len(pods) == 2
            assert pods[0]["id"] == "pod-1"

    @pytest.mark.asyncio
    async def test_get_endpoints_success(self, client):
        """Test getting endpoints successfully"""
        mock_endpoints = [
            {"id": "endpoint-1", "name": "endpoint-1"},
            {"id": "endpoint-2", "name": "endpoint-2"},
        ]

        with patch("runpod.get_endpoints", return_value=mock_endpoints):
            endpoints = await client.get_endpoints()

            assert len(endpoints) == 2
            assert endpoints[0]["id"] == "endpoint-1"

    @pytest.mark.asyncio
    async def test_stop_pod_success(self, client):
        """Test stopping pod successfully"""
        with patch("runpod.stop_pod") as mock_stop:
            success = await client.stop_pod("pod-123")

            assert success is True
            mock_stop.assert_called_once_with("pod-123")

    @pytest.mark.asyncio
    async def test_terminate_pod_success(self, client):
        """Test terminating pod successfully"""
        with patch("runpod.terminate_pod") as mock_terminate:
            success = await client.terminate_pod("pod-123")

            assert success is True
            mock_terminate.assert_called_once_with("pod-123")

    def test_calculate_cost_pod(self, client):
        """Test cost calculation for pods"""
        # Test RTX 4090 pod cost
        cost = client.calculate_cost("pod", "RTX 4090", 1.0, "community")
        expected = client.gpu_pricing["RTX 4090"]["pod_community"]
        assert cost == expected

        # Test secure cloud pricing
        cost_secure = client.calculate_cost("pod", "RTX 4090", 1.0, "secure")
        expected_secure = client.gpu_pricing["RTX 4090"]["pod_secure"]
        assert cost_secure == expected_secure

    def test_calculate_cost_serverless(self, client):
        """Test cost calculation for serverless"""
        # Test 1 hour serverless cost
        cost = client.calculate_cost("serverless", "RTX 4090", 1.0)
        expected = client.gpu_pricing["RTX 4090"]["serverless_flex"] * 3600
        assert cost == expected

        # Test 1 minute serverless cost
        cost_minute = client.calculate_cost("serverless", "RTX 4090", 1 / 60)
        expected_minute = (
            client.gpu_pricing["RTX 4090"]["serverless_flex"] * 60
        )
        assert cost_minute == expected_minute

    def test_calculate_cost_unknown_gpu(self, client):
        """Test cost calculation for unknown GPU"""
        cost = client.calculate_cost("pod", "UNKNOWN_GPU", 1.0)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_get_deployment_logs(self, client):
        """Test getting deployment logs"""
        # Test pod logs (not implemented)
        logs = await client.get_deployment_logs("pod-123", "pod")
        assert "Pod logs not yet implemented" in logs[0]

        # Test serverless logs (not implemented)
        logs = await client.get_deployment_logs("endpoint-123", "serverless")
        assert "Serverless logs not yet implemented" in logs[0]


class TestRunPodDeploymentManager:
    """Test RunPod deployment manager"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return RunPodConfig(
            api_key="test-key",
            gpu_type="RTX 4090",
            deployment_type="serverless",
        )

    @pytest.fixture
    def manager(self, config):
        """Create test deployment manager"""
        with patch("runpod.api_key"):
            return RunPodDeploymentManager(config)

    def test_manager_initialization(self, manager):
        """Test manager initialization"""
        assert manager.config.api_key == "test-key"
        assert isinstance(manager.client, RunPodClient)
        assert len(manager.deployments) == 0

    @pytest.mark.asyncio
    async def test_deploy_summit_serverless_success(self, manager):
        """Test deploying Summit as serverless successfully"""
        mock_template = {"id": "template-123"}
        mock_endpoint = {"id": "endpoint-123"}

        with patch.object(
            manager.client, "create_template", return_value=mock_template
        ):
            with patch.object(
                manager.client,
                "create_serverless_endpoint",
                return_value=mock_endpoint,
            ):
                with patch.object(manager.client.cost_tracker, "record_call"):
                    deployment = await manager.deploy_summit("test-deployment")

                    assert deployment is not None
                    assert deployment.deployment_id == "endpoint-123"
                    assert deployment.deployment_type == "serverless"
                    assert deployment.gpu_type == "RTX 4090"
                    assert deployment.status == "deploying"
                    assert "endpoint-123" in manager.deployments

    @pytest.mark.asyncio
    async def test_deploy_summit_pod_success(self, manager):
        """Test deploying Summit as pod successfully"""
        manager.config.deployment_type = "pod"

        mock_template = {"id": "template-123"}
        mock_pod = {"id": "pod-123"}

        with patch.object(
            manager.client, "create_template", return_value=mock_template
        ):
            with patch.object(
                manager.client, "create_pod", return_value=mock_pod
            ):
                with patch.object(manager.client.cost_tracker, "record_call"):
                    deployment = await manager.deploy_summit("test-deployment")

                    assert deployment is not None
                    assert deployment.deployment_id == "pod-123"
                    assert deployment.deployment_type == "pod"
                    assert deployment.status == "starting"

    @pytest.mark.asyncio
    async def test_deploy_summit_template_failure(self, manager):
        """Test deployment failure when template creation fails"""
        with patch.object(
            manager.client, "create_template", return_value=None
        ):
            deployment = await manager.deploy_summit("test-deployment")

            assert deployment is None

    @pytest.mark.asyncio
    async def test_get_deployment_status_serverless(self, manager):
        """Test getting serverless deployment status"""
        # Add a test deployment
        deployment = DeploymentInfo(
            deployment_id="endpoint-123",
            deployment_type="serverless",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["endpoint-123"] = deployment

        mock_endpoints = [
            {
                "id": "endpoint-123",
                "workers": 2,
                "requestsCompleted": 100,
                "requestsFailed": 5,
            }
        ]

        with patch.object(
            manager.client, "get_endpoints", return_value=mock_endpoints
        ):
            status = await manager.get_deployment_status("endpoint-123")

            assert status["id"] == "endpoint-123"
            assert status["status"] == "running"
            assert status["workers"] == 2
            assert status["requests_completed"] == 100

    @pytest.mark.asyncio
    async def test_get_deployment_status_pod(self, manager):
        """Test getting pod deployment status"""
        # Add a test deployment
        deployment = DeploymentInfo(
            deployment_id="pod-123",
            deployment_type="pod",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["pod-123"] = deployment

        mock_pods = [
            {
                "id": "pod-123",
                "desiredStatus": "RUNNING",
                "runtime": {"uptimeInSeconds": 3600},
                "gpuCount": 1,
            }
        ]

        with patch.object(manager.client, "get_pods", return_value=mock_pods):
            status = await manager.get_deployment_status("pod-123")

            assert status["id"] == "pod-123"
            assert status["status"] == "RUNNING"
            assert status["gpu_count"] == 1

    @pytest.mark.asyncio
    async def test_get_deployment_status_not_found(self, manager):
        """Test getting status for non-existent deployment"""
        status = await manager.get_deployment_status("non-existent")
        assert status is None

    @pytest.mark.asyncio
    async def test_scale_deployment_success(self, manager):
        """Test scaling deployment successfully"""
        # Add a test serverless deployment
        deployment = DeploymentInfo(
            deployment_id="endpoint-123",
            deployment_type="serverless",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["endpoint-123"] = deployment

        success = await manager.scale_deployment("endpoint-123", 1, 5)
        assert success is True

    @pytest.mark.asyncio
    async def test_scale_deployment_pod_failure(self, manager):
        """Test scaling pod deployment (should fail)"""
        # Add a test pod deployment
        deployment = DeploymentInfo(
            deployment_id="pod-123",
            deployment_type="pod",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["pod-123"] = deployment

        success = await manager.scale_deployment("pod-123", 1, 5)
        assert success is False

    @pytest.mark.asyncio
    async def test_terminate_deployment_pod_success(self, manager):
        """Test terminating pod deployment successfully"""
        # Add a test pod deployment
        deployment = DeploymentInfo(
            deployment_id="pod-123",
            deployment_type="pod",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["pod-123"] = deployment

        with patch.object(manager.client, "terminate_pod", return_value=True):
            with patch.object(manager.client.cost_tracker, "record_call"):
                success = await manager.terminate_deployment("pod-123")

                assert success is True
                assert "pod-123" not in manager.deployments

    @pytest.mark.asyncio
    async def test_terminate_deployment_serverless_success(self, manager):
        """Test terminating serverless deployment successfully"""
        # Add a test serverless deployment
        deployment = DeploymentInfo(
            deployment_id="endpoint-123",
            deployment_type="serverless",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["endpoint-123"] = deployment

        with patch.object(manager.client.cost_tracker, "record_call"):
            success = await manager.terminate_deployment("endpoint-123")

            assert success is True
            assert "endpoint-123" not in manager.deployments

    @pytest.mark.asyncio
    async def test_terminate_deployment_not_found(self, manager):
        """Test terminating non-existent deployment"""
        success = await manager.terminate_deployment("non-existent")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_all_deployments(self, manager):
        """Test getting all deployments"""
        # Add test deployments
        deployment1 = DeploymentInfo(
            deployment_id="test-1",
            deployment_type="serverless",
            gpu_type="RTX 4090",
            status="running",
        )
        deployment2 = DeploymentInfo(
            deployment_id="test-2",
            deployment_type="pod",
            gpu_type="A100",
            status="starting",
        )

        manager.deployments["test-1"] = deployment1
        manager.deployments["test-2"] = deployment2

        deployments = await manager.get_all_deployments()

        assert len(deployments) == 2
        assert deployments[0].deployment_id in ["test-1", "test-2"]
        assert deployments[1].deployment_id in ["test-1", "test-2"]

    @pytest.mark.asyncio
    async def test_get_deployment_logs(self, manager):
        """Test getting deployment logs"""
        # Add a test deployment
        deployment = DeploymentInfo(
            deployment_id="test-123",
            deployment_type="serverless",
            gpu_type="RTX 4090",
            status="running",
        )
        manager.deployments["test-123"] = deployment

        with patch.object(
            manager.client,
            "get_deployment_logs",
            return_value=["log line 1", "log line 2"],
        ):
            logs = await manager.get_deployment_logs("test-123")

            assert len(logs) == 2
            assert "log line 1" in logs

    @pytest.mark.asyncio
    async def test_get_deployment_logs_not_found(self, manager):
        """Test getting logs for non-existent deployment"""
        logs = await manager.get_deployment_logs("non-existent")
        assert logs == ["Deployment not found"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
