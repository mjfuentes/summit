"""
Test scenarios for integration testing
"""

from typing import Any, Dict, List


class TestScenarios:
    """Collection of test scenarios for the integration tests"""

    def basic_chat_request(self) -> Dict[str, Any]:
        """Basic chat completion request without tools"""
        return {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello! Please respond with a brief greeting and confirm you can assist me.",
                }
            ],
            "max_tokens": 100,
            "temperature": 0.7,
        }

    def function_calling_request(self) -> Dict[str, Any]:
        """Chat request with function calling capabilities"""
        return {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "What's the weather like in New York? Please use the weather function to check.",
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather for a specific location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state/country",
                                },
                                "units": {
                                    "type": "string",
                                    "enum": ["celsius", "fahrenheit"],
                                    "description": "Temperature units",
                                },
                            },
                            "required": ["location"],
                        },
                    },
                }
            ],
            "max_tokens": 200,
            "temperature": 0.7,
        }

    def multi_tool_request(self) -> Dict[str, Any]:
        """Chat request with multiple available tools"""
        return {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "I need to check the weather in Paris and also get the current time. Can you help?",
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather for a specific location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state/country",
                                }
                            },
                            "required": ["location"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "description": "Get the current time in a specific timezone",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "timezone": {
                                    "type": "string",
                                    "description": "Timezone (e.g., 'America/New_York', 'Europe/London')",
                                }
                            },
                            "required": ["timezone"],
                        },
                    },
                },
            ],
            "max_tokens": 300,
            "temperature": 0.7,
        }

    def code_generation_request(self) -> Dict[str, Any]:
        """Request for code generation (testing reasoning capabilities)"""
        return {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "Write a simple Python function that calculates the factorial of a number. Include error handling for negative numbers.",
                }
            ],
            "max_tokens": 300,
            "temperature": 0.3,
        }

    def tool_result_followup(
        self, tool_call_id: str = "call_123"
    ) -> Dict[str, Any]:
        """Follow-up request with tool execution results"""
        return {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "What's the weather like in New York?",
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "New York, NY", "units": "fahrenheit"}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": '{"temperature": 72, "condition": "sunny", "humidity": 65, "wind_speed": 8}',
                },
            ],
            "max_tokens": 150,
            "temperature": 0.7,
        }

    def error_handling_request(self) -> Dict[str, Any]:
        """Request designed to test error handling"""
        return {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "This is a very long prompt designed to test token limits and error handling. "
                    * 100,
                }
            ],
            "max_tokens": 1,  # Intentionally low to trigger potential issues
            "temperature": 0.7,
        }
