#!/usr/bin/env python3
"""Tests for open source models integration"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.open_source_models import (
    ModelConfig,
    OpenSourceModelManager,
    RunPodOpenSourceHandler,
    create_runpod_handler,
    get_advice_from_open_source,
)


class TestModelConfig:
    """Test ModelConfig dataclass"""

    def test_model_config_defaults(self):
        """Test ModelConfig with default values"""
        config = ModelConfig(model_name="test-model")

        assert config.model_name == "test-model"
        assert config.model_type == "llama"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.use_quantization is True
        assert config.device == "auto"
        assert config.trust_remote_code is False

    def test_model_config_custom_values(self):
        """Test ModelConfig with custom values"""
        config = ModelConfig(
            model_name="custom-model",
            model_type="mistral",
            max_tokens=4096,
            temperature=0.5,
            top_p=0.8,
            use_quantization=False,
            device="cuda:0",
            trust_remote_code=True,
        )

        assert config.model_name == "custom-model"
        assert config.model_type == "mistral"
        assert config.max_tokens == 4096
        assert config.temperature == 0.5
        assert config.top_p == 0.8
        assert config.use_quantization is False
        assert config.device == "cuda:0"
        assert config.trust_remote_code is True


class TestOpenSourceModelManager:
    """Test OpenSourceModelManager class"""

    def test_init_valid_model(self):
        """Test initialization with valid model"""
        manager = OpenSourceModelManager("llama-3.1-8b")

        assert manager.model_id == "llama-3.1-8b"
        assert manager.model_info is not None
        assert manager.model_info["model_type"] == "llama"
        assert manager.model is None
        assert manager.tokenizer is None
        assert manager.pipeline is None

    def test_init_invalid_model(self):
        """Test initialization with invalid model"""
        with pytest.raises(ValueError, match="Unsupported model"):
            OpenSourceModelManager("invalid-model")

    def test_supported_models(self):
        """Test that all supported models are accessible"""
        supported = OpenSourceModelManager.SUPPORTED_MODELS

        assert "llama-3.1-8b" in supported
        assert "llama-3.1-70b" in supported
        assert "code-llama-13b" in supported
        assert "code-llama-34b" in supported
        assert "mistral-7b" in supported

    @patch("src.open_source_models.AutoTokenizer")
    @patch("src.open_source_models.AutoModelForCausalLM")
    @patch("src.open_source_models.pipeline")
    @patch("src.open_source_models.torch")
    @patch("src.open_source_models.BitsAndBytesConfig")
    async def test_load_model_success(
        self, mock_bnb, mock_torch, mock_pipeline, mock_model, mock_tokenizer
    ):
        """Test successful model loading"""
        # Setup mocks
        mock_torch.cuda.is_available.return_value = True
        mock_torch.float16 = "float16"  # Mock the dtype

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer_instance.eos_token = "<eos>"
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

        mock_model.from_pretrained.return_value = MagicMock()
        mock_pipeline.return_value = MagicMock()
        mock_bnb.return_value = MagicMock()

        manager = OpenSourceModelManager("llama-3.1-8b")
        result = await manager.load_model()

        assert result is True
        mock_tokenizer.from_pretrained.assert_called_once()
        mock_model.from_pretrained.assert_called_once()
        mock_pipeline.assert_called_once()

    @patch("src.open_source_models.AutoTokenizer")
    async def test_load_model_failure(self, mock_tokenizer):
        """Test model loading failure"""
        mock_tokenizer.from_pretrained.side_effect = Exception(
            "Model not found"
        )

        manager = OpenSourceModelManager("llama-3.1-8b")
        result = await manager.load_model()

        assert result is False

    def test_format_prompt_llama(self):
        """Test prompt formatting for Llama models"""
        manager = OpenSourceModelManager("llama-3.1-8b")

        prompt = manager.format_prompt("Test question")

        assert "Summit" in prompt
        assert "Test question" in prompt
        assert "<|begin_of_text|>" in prompt
        assert "<|start_header_id|>" in prompt

    def test_format_prompt_code_llama(self):
        """Test prompt formatting for Code Llama models"""
        manager = OpenSourceModelManager("code-llama-13b")

        prompt = manager.format_prompt("Write a function")

        assert "Summit" in prompt
        assert "Write a function" in prompt
        assert "[INST]" in prompt
        assert "[/INST]" in prompt

    def test_format_prompt_with_context(self):
        """Test prompt formatting with context"""
        manager = OpenSourceModelManager("llama-3.1-8b")

        prompt = manager.format_prompt("Test question", "Test context")

        assert "Test question" in prompt
        assert "Test context" in prompt

    async def test_generate_response(self):
        """Test response generation"""
        manager = OpenSourceModelManager("llama-3.1-8b")

        # Mock the pipeline, model, and tokenizer to simulate loaded state
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [
            {"generated_text": "Test response from model"}
        ]
        manager.pipeline = mock_pipeline
        manager.model = MagicMock()  # Simulate model is loaded
        manager.tokenizer = MagicMock()  # Simulate tokenizer is loaded
        manager.tokenizer.encode.return_value = [
            1,
            2,
            3,
            4,
            5,
        ]  # Mock token encoding

        response = await manager.generate_response("Test question")

        assert "Test response from model" in response

    async def test_analyze_code(self):
        """Test code analysis"""
        manager = OpenSourceModelManager("code-llama-13b")

        # Mock the generate_response method instead
        with patch.object(
            manager, "generate_response", return_value="Code analysis result"
        ):
            result = await manager.analyze_code("def test(): pass", "python")
            assert "Code analysis result" in result

    async def test_review_pr(self):
        """Test PR review"""
        manager = OpenSourceModelManager("code-llama-13b")

        # Mock the generate_response method instead
        with patch.object(
            manager, "generate_response", return_value="PR review result"
        ):
            pr_data = {"title": "Test PR", "description": "Test description"}
            result = await manager.review_pr(pr_data)
            assert "PR review result" in result

    def test_get_model_info(self):
        """Test getting model info"""
        manager = OpenSourceModelManager("llama-3.1-8b")

        info = manager.get_model_info()

        assert "model_id" in info
        assert "model_name" in info
        assert "model_type" in info
        assert "context_length" in info
        assert "cost_per_token" in info

    def test_list_supported_models(self):
        """Test listing supported models"""
        models = OpenSourceModelManager.list_supported_models()

        assert isinstance(models, list)
        assert "llama-3.1-8b" in models
        assert "code-llama-13b" in models
        assert "mistral-7b" in models


class TestRunPodOpenSourceHandler:
    """Test RunPodOpenSourceHandler class"""

    def test_init(self):
        """Test handler initialization"""
        handler = RunPodOpenSourceHandler("llama-3.1-8b")

        assert handler.model_manager.model_id == "llama-3.1-8b"
        assert handler.model_manager is not None

    @patch("src.open_source_models.OpenSourceModelManager.load_model")
    async def test_initialize_success(self, mock_load):
        """Test successful initialization"""
        mock_load.return_value = True

        handler = RunPodOpenSourceHandler("llama-3.1-8b")
        result = await handler.initialize()

        assert result is True
        mock_load.assert_called_once()

    @patch("src.open_source_models.OpenSourceModelManager.load_model")
    async def test_initialize_failure(self, mock_load):
        """Test initialization failure"""
        mock_load.return_value = False

        handler = RunPodOpenSourceHandler("llama-3.1-8b")
        result = await handler.initialize()

        assert result is False
        mock_load.assert_called_once()

    @patch("src.open_source_models.OpenSourceModelManager.generate_response")
    async def test_handle_request_success(self, mock_generate):
        """Test successful request handling"""
        mock_generate.return_value = "Test response"

        handler = RunPodOpenSourceHandler("llama-3.1-8b")
        handler.model_manager.pipeline = MagicMock()  # Simulate loaded model

        job_input = {
            "operation": "get_advice",
            "data": {"question": "Test question", "context": "Test context"},
        }

        result = await handler.handle_request(job_input)

        assert result["success"] is True
        assert "response" in result
        assert "processing_time" in result

    async def test_handle_request_unknown_operation(self):
        """Test request handling with unknown operation"""
        handler = RunPodOpenSourceHandler("llama-3.1-8b")

        job_input = {"operation": "unknown_operation", "data": {}}

        result = await handler.handle_request(job_input)

        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    async def test_handle_request_analyze_code(self):
        """Test code analysis request handling"""
        handler = RunPodOpenSourceHandler("llama-3.1-8b")

        with patch.object(
            handler.model_manager, "analyze_code", return_value="Code analysis"
        ):
            job_input = {
                "operation": "analyze_code",
                "data": {"code": "def test(): pass", "language": "python"},
            }

            result = await handler.handle_request(job_input)

            assert result["success"] is True
            assert "analysis" in result


class TestUtilityFunctions:
    """Test utility functions"""

    @patch("src.open_source_models.OpenSourceModelManager")
    async def test_get_advice_from_open_source(self, mock_manager_class):
        """Test getting advice from open source model"""
        mock_manager = AsyncMock()
        mock_manager.load_model.return_value = True
        mock_manager.generate_response.return_value = "Test advice"
        mock_manager_class.return_value = mock_manager

        advice = await get_advice_from_open_source("Test question")

        assert advice == "Test advice"
        mock_manager.load_model.assert_called_once()
        mock_manager.generate_response.assert_called_once_with(
            "Test question", None
        )

    def test_create_runpod_handler(self):
        """Test creating RunPod handler"""
        handler = create_runpod_handler("llama-3.1-8b")

        assert isinstance(handler, RunPodOpenSourceHandler)
        assert handler.model_manager.model_id == "llama-3.1-8b"
