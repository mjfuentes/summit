#!/usr/bin/env python3
"""
Open Source Model Integration for Summit AI

This module provides integration with open source models like Llama 3.1,
Code Llama, and Mistral for cost-effective AI operations on RunPod or local GPU.

Features:
- Llama 3.1 8B/70B support
- Code Llama specialized models
- Mistral 7B integration
- RunPod serverless deployment
- Local GPU inference
- Cost tracking and optimization
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
)

from cost_tracker import CostTracker


@dataclass
class ModelConfig:
    """Configuration for open source model"""

    model_name: str
    model_type: str = "llama"  # llama, code_llama, mistral
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    use_quantization: bool = True
    device: str = "auto"
    trust_remote_code: bool = False


class OpenSourceModelManager:
    """Manager for open source model inference"""

    # Supported models with their configurations
    SUPPORTED_MODELS = {
        "llama-3.1-8b": {
            "model_name": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "model_type": "llama",
            "context_length": 128000,
            "cost_per_token": 0.0000001,  # Much cheaper than Claude
        },
        "llama-3.1-70b": {
            "model_name": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "model_type": "llama",
            "context_length": 128000,
            "cost_per_token": 0.0000005,
        },
        "code-llama-13b": {
            "model_name": "codellama/CodeLlama-13b-Instruct-hf",
            "model_type": "code_llama",
            "context_length": 16384,
            "cost_per_token": 0.0000002,
        },
        "code-llama-34b": {
            "model_name": "codellama/CodeLlama-34b-Instruct-hf",
            "model_type": "code_llama",
            "context_length": 16384,
            "cost_per_token": 0.0000004,
        },
        "mistral-7b": {
            "model_name": "mistralai/Mistral-7B-Instruct-v0.3",
            "model_type": "mistral",
            "context_length": 32768,
            "cost_per_token": 0.0000001,
        },
    }

    def __init__(self, model_id: str = "llama-3.1-8b"):
        self.model_id = model_id
        self.model_info = self.SUPPORTED_MODELS.get(model_id)
        if not self.model_info:
            raise ValueError(f"Unsupported model: {model_id}")

        self.logger = logging.getLogger(__name__)
        self.cost_tracker = CostTracker()
        self.model = None
        self.tokenizer = None
        self.pipeline = None

    async def load_model(self, config: Optional[ModelConfig] = None) -> bool:
        """Load the model and tokenizer"""
        try:
            if config is None:
                config = ModelConfig(
                    model_name=self.model_info["model_name"],
                    model_type=self.model_info["model_type"],
                )

            self.logger.info(f"Loading model: {config.model_name}")

            # Configure quantization for memory efficiency
            quantization_config = None
            if config.use_quantization and torch.cuda.is_available():
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                config.model_name,
                trust_remote_code=config.trust_remote_code,
                padding_side="left",
            )

            # Add pad token if missing
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                config.model_name,
                quantization_config=quantization_config,
                device_map=config.device,
                torch_dtype=torch.float16,
                trust_remote_code=config.trust_remote_code,
                low_cpu_mem_usage=True,
            )

            # Create pipeline for easier inference
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

            self.logger.info(f"Model loaded successfully: {config.model_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False

    def format_prompt(
        self, question: str, context: Optional[str] = None
    ) -> str:
        """Format prompt for the specific model type"""
        if self.model_info["model_type"] == "llama":
            # Llama 3.1 chat format
            system_prompt = (
                "You are Summit, a sophisticated AI advisor specializing in "
                "autonomous development and programming assistance. Provide "
                "thoughtful, practical advice. Be concise but thorough."
            )

            if context:
                user_content = f"Context: {context}\n\nQuestion: {question}"
            else:
                user_content = question

            prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user_content}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

Summit's Advice: """

        elif self.model_info["model_type"] == "code_llama":
            # Code Llama format optimized for code tasks
            if context:
                prompt = f"""[INST] You are Summit, an AI coding assistant. 

Context: {context}

Task: {question}

Provide practical coding advice and solutions. [/INST]

Summit's Advice: """
            else:
                prompt = f"""[INST] You are Summit, an AI coding assistant. 

Task: {question}

Provide practical coding advice and solutions. [/INST]

Summit's Advice: """

        elif self.model_info["model_type"] == "mistral":
            # Mistral format
            if context:
                prompt = f"""<s>[INST] You are Summit, an AI advisor.

Context: {context}

Question: {question} [/INST]

Summit's Advice: """
            else:
                prompt = f"""<s>[INST] You are Summit, an AI advisor.

Question: {question} [/INST]

Summit's Advice: """

        else:
            # Generic format
            prompt = f"Question: {question}\n"
            if context:
                prompt += f"Context: {context}\n"
            prompt += "Summit's Advice: "

        return prompt

    async def generate_response(
        self, question: str, context: Optional[str] = None
    ) -> str:
        """Generate response using the loaded model"""
        if not self.model or not self.tokenizer:
            return "Model not loaded. Please call load_model() first."

        try:
            start_time = time.time()

            # Format the prompt
            prompt = self.format_prompt(question, context)

            # Count input tokens
            input_tokens = len(self.tokenizer.encode(prompt))

            # Generate response
            outputs = self.pipeline(
                prompt,
                return_full_text=False,
                clean_up_tokenization_spaces=True,
            )

            response = outputs[0]["generated_text"].strip()

            # Count output tokens
            output_tokens = len(self.tokenizer.encode(response))

            # Calculate processing time and cost
            processing_time = time.time() - start_time
            cost = (input_tokens + output_tokens) * self.model_info[
                "cost_per_token"
            ]

            # Track cost
            self.cost_tracker.record_call(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=f"open_source_{self.model_id}",
                call_type="advice",
            )

            # Add cost info to response
            response += f"\n\n[Model: {self.model_id} | Cost: ${cost:.6f} | Time: {processing_time:.2f}s | Daily spent: ${self.cost_tracker.get_daily_spent():.4f}]"

            self.logger.info(
                f"Generated response in {processing_time:.2f}s "
                f"({input_tokens} + {output_tokens} tokens, ${cost:.6f})"
            )

            return response

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return f"Summit encountered an error: {e}"

    async def analyze_code(self, code: str, language: str = "python") -> str:
        """Analyze code quality and suggest improvements"""
        analysis_prompt = f"""Analyze this {language} code and provide:
1. Code quality assessment
2. Potential bugs or issues  
3. Performance improvements
4. Best practices recommendations

Code:
```{language}
{code}
```"""

        return await self.generate_response(analysis_prompt)

    async def review_pr(self, pr_data: Dict[str, Any]) -> str:
        """Review a pull request"""
        files_changed = pr_data.get("files_changed", [])
        description = pr_data.get("description", "")

        review_prompt = f"""Review this pull request:

Description: {description}

Files changed: {len(files_changed)}

Provide:
1. Overall assessment
2. Code quality review
3. Potential issues
4. Recommendations

Focus on code quality, security, and best practices."""

        return await self.generate_response(review_prompt)

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_id": self.model_id,
            "model_name": self.model_info["model_name"],
            "model_type": self.model_info["model_type"],
            "context_length": self.model_info["context_length"],
            "cost_per_token": self.model_info["cost_per_token"],
            "loaded": self.model is not None,
            "gpu_available": torch.cuda.is_available(),
            "gpu_count": (
                torch.cuda.device_count() if torch.cuda.is_available() else 0
            ),
        }

    @classmethod
    def list_supported_models(cls) -> List[str]:
        """List all supported model IDs"""
        return list(cls.SUPPORTED_MODELS.keys())


class RunPodOpenSourceHandler:
    """Handler for open source models on RunPod"""

    def __init__(self, model_id: str = "llama-3.1-8b"):
        self.model_manager = OpenSourceModelManager(model_id)
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """Initialize the model for RunPod deployment"""
        self.logger.info("Initializing open source model for RunPod...")
        return await self.model_manager.load_model()

    async def handle_request(
        self, job_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle incoming RunPod requests"""
        start_time = time.time()

        try:
            operation = job_input.get("operation", "get_advice")
            data = job_input.get("data", {})

            if operation == "get_advice":
                question = data.get("question", "")
                context = data.get("context")
                response = await self.model_manager.generate_response(
                    question, context
                )

                return {
                    "success": True,
                    "operation": operation,
                    "response": response,
                    "model_info": self.model_manager.get_model_info(),
                    "processing_time": time.time() - start_time,
                }

            elif operation == "analyze_code":
                code = data.get("code", "")
                language = data.get("language", "python")
                analysis = await self.model_manager.analyze_code(
                    code, language
                )

                return {
                    "success": True,
                    "operation": operation,
                    "analysis": analysis,
                    "model_info": self.model_manager.get_model_info(),
                    "processing_time": time.time() - start_time,
                }

            elif operation == "review_pr":
                pr_data = data.get("pr_data", {})
                review = await self.model_manager.review_pr(pr_data)

                return {
                    "success": True,
                    "operation": operation,
                    "review": review,
                    "model_info": self.model_manager.get_model_info(),
                    "processing_time": time.time() - start_time,
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}",
                    "supported_operations": [
                        "get_advice",
                        "analyze_code",
                        "review_pr",
                    ],
                }

        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
            }


# Convenience functions for easy integration
async def get_advice_from_open_source(
    question: str,
    context: Optional[str] = None,
    model_id: str = "llama-3.1-8b",
) -> str:
    """Get advice from open source model (convenience function)"""
    manager = OpenSourceModelManager(model_id)

    if not await manager.load_model():
        return f"Failed to load model: {model_id}"

    return await manager.generate_response(question, context)


def create_runpod_handler(
    model_id: str = "llama-3.1-8b",
) -> RunPodOpenSourceHandler:
    """Create RunPod handler for open source models"""
    return RunPodOpenSourceHandler(model_id)


if __name__ == "__main__":
    # Example usage
    async def main():
        print("Summit AI - Open Source Model Integration")
        print("=" * 50)

        # List supported models
        print("Supported models:")
        for model_id in OpenSourceModelManager.list_supported_models():
            print(f"  - {model_id}")
        print()

        # Test model loading and inference
        model_id = "llama-3.1-8b"
        print(f"Testing {model_id}...")

        manager = OpenSourceModelManager(model_id)

        if await manager.load_model():
            print("Model loaded successfully!")

            # Test inference
            response = await manager.generate_response(
                "How can I optimize Python code for better performance?"
            )
            print(f"Response: {response}")

            # Show model info
            info = manager.get_model_info()
            print(f"Model info: {info}")
        else:
            print("Failed to load model")

    asyncio.run(main())
