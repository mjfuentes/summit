#!/usr/bin/env python3
"""
OpenCode <-> RunPod Bridge Service

This service translates between OpenCode's OpenAI-compatible API format
and RunPod's custom format, handling function calling translation.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OpenCode-RunPod Bridge", version="1.0.1")

# Configuration
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID:
    logger.error(
        "Missing RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID environment variables"
    )


# Request/Response Models
class ChatMessage(BaseModel):
    role: str
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    tools: Optional[List[Dict]] = None
    functions: Optional[List[Dict]] = None
    function_call: Optional[str] = None
    tool_choice: Optional[str] = None
    stream: Optional[bool] = False
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict]
    usage: Optional[Dict] = None


class RunPodClient:
    """Client for communicating with RunPod"""

    def __init__(self):
        self.session = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json",
        }

    async def call_runpod(self, payload: Dict) -> Dict:
        """Make request to RunPod endpoint"""
        try:
            url = f"{RUNPOD_BASE_URL}/runsync"
            logger.info(f"Calling RunPod: {url}")

            response = await self.session.post(
                url,
                json={"input": payload},
                headers=self.headers,
                timeout=120.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"RunPod error {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"RunPod API error: {response.text}",
                )

            result = response.json()
            logger.info(
                f"RunPod response: {json.dumps(result, indent=2)[:300]}..."
            )
            return result

        except httpx.TimeoutException:
            logger.error("RunPod request timeout")
            raise HTTPException(
                status_code=504, detail="RunPod request timeout"
            )
        except Exception as e:
            logger.error(f"RunPod request failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"RunPod error: {str(e)}"
            )


# Initialize RunPod client
runpod_client = RunPodClient()


class MessageTranslator:
    """Handles translation between OpenCode and RunPod formats"""

    @staticmethod
    def opencode_to_runpod_messages(messages: List[ChatMessage]) -> List[Dict]:
        """Convert OpenCode messages to RunPod format"""
        runpod_messages = []

        for msg in messages:
            runpod_msg = {"role": msg.role, "content": msg.content}

            # Add tool-specific fields if present
            if msg.tool_call_id:
                runpod_msg["tool_call_id"] = msg.tool_call_id

            if msg.tool_calls:
                runpod_msg["tool_calls"] = msg.tool_calls

            runpod_messages.append(runpod_msg)

        return runpod_messages

    @staticmethod
    def opencode_to_runpod_tools(
        tools: Optional[List[Dict]], functions: Optional[List[Dict]]
    ) -> Optional[List[Dict]]:
        """Convert OpenCode tools/functions to RunPod format"""
        # Prefer functions (legacy format) over tools (new format)
        if functions:
            return functions
        elif tools:
            # Convert tools format to functions format
            functions_list = []
            for tool in tools:
                if tool.get("type") == "function" and "function" in tool:
                    functions_list.append(tool["function"])
            return functions_list if functions_list else None
        return None

    @staticmethod
    def runpod_to_opencode_response(
        runpod_response: Dict, request_model: str
    ) -> ChatCompletionResponse:
        """Convert RunPod response to OpenCode format"""

        # Extract RunPod output - handle both dict and list formats
        output = runpod_response.get("output", {})

        # Handle case where output is a list (common RunPod format)
        if isinstance(output, list) and len(output) > 0:
            output = output[0]  # Take the first item

        # Handle error case
        if isinstance(output, dict) and "error" in output:
            error_msg = output["error"]
            logger.error(f"RunPod returned error: {error_msg}")

            choice = {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"I encountered an error: {error_msg}",
                },
                "finish_reason": "stop",
            }

        # Handle function calls (legacy format)
        elif isinstance(output, dict) and output.get("function_call"):
            function_call = output.get("function_call")

            choice = {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "function_call": function_call,
                },
                "finish_reason": "function_call",
            }

        # Handle tool calls (newer format)
        elif isinstance(output, dict) and output.get(
            "requires_tool_execution"
        ):
            tool_calls = output.get("tool_calls", [])

            choice = {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls,
                },
                "finish_reason": "tool_calls",
            }

        # Handle standard RunPod response format with choices
        elif isinstance(output, dict) and "choices" in output:
            choices = output.get("choices", [])
            if choices and len(choices) > 0:
                first_choice = choices[0]

                # Extract text content from tokens or text field
                content = ""
                if "tokens" in first_choice:
                    # Join tokens if it's a list
                    tokens = first_choice["tokens"]
                    if isinstance(tokens, list):
                        content = "".join(tokens)
                    else:
                        content = str(tokens)
                elif "text" in first_choice:
                    content = first_choice["text"]
                elif "message" in first_choice:
                    content = first_choice["message"].get("content", "")

                choice = {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            else:
                # Empty choices array
                choice = {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "No response generated",
                    },
                    "finish_reason": "stop",
                }

        # Handle simple content format
        elif isinstance(output, dict) and "content" in output:
            content = output.get("content", "")

            choice = {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }

        # Handle direct string output
        elif isinstance(output, str):
            choice = {
                "index": 0,
                "message": {"role": "assistant", "content": output},
                "finish_reason": "stop",
            }

        # Fallback for unknown format
        else:
            logger.warning(
                f"Unknown RunPod output format: {type(output)} - {output}"
            )
            choice = {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Received response in unexpected format: {str(output)[:100]}",
                },
                "finish_reason": "stop",
            }

        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request_model,
            choices=[choice],
            usage={
                "prompt_tokens": 0,  # RunPod doesn't provide token counts
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        )


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "OpenCode-RunPod Bridge"}


@app.get("/v1/models")
async def list_models():
    """List available models (for OpenCode compatibility)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen2.5-14b-instruct",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "runpod",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Main endpoint - translate OpenCode chat completion to RunPod"""

    try:
        logger.info(f"Received OpenCode request: {request.model}")
        logger.info(f"Messages: {len(request.messages)}")
        logger.info(f"Tools: {len(request.tools) if request.tools else 0}")

        # Check if this is a follow-up with tool results
        has_tool_results = any(msg.role == "tool" for msg in request.messages)

        # Translate to RunPod format - always use legacy functions format
        runpod_payload = {
            "messages": MessageTranslator.opencode_to_runpod_messages(
                request.messages
            ),
        }

        # Convert tools to functions format (legacy OpenAI format)
        if request.tools:
            functions = []
            for tool in request.tools:
                if tool.get("type") == "function" and "function" in tool:
                    functions.append(tool["function"])
            if functions:
                runpod_payload["functions"] = functions
                runpod_payload["function_call"] = "auto"

        # Add tool outputs if this is a follow-up
        if has_tool_results:
            tool_outputs = []
            for msg in request.messages:
                if msg.role == "tool":
                    tool_outputs.append(
                        {
                            "tool_call_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    )
            runpod_payload["tool_outputs"] = tool_outputs

        # Call RunPod
        runpod_response = await runpod_client.call_runpod(runpod_payload)

        # Translate response back to OpenCode format
        opencode_response = MessageTranslator.runpod_to_opencode_response(
            runpod_response, request.model
        )

        logger.info(
            f"Returning response with finish_reason: {opencode_response.choices[0]['finish_reason']}"
        )

        return opencode_response

    except Exception as e:
        logger.error(f"Bridge error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions/stream")
async def chat_completions_stream(request: ChatCompletionRequest):
    """Streaming endpoint (fallback to non-streaming for now)"""
    logger.info("Streaming requested, falling back to non-streaming")
    response = await chat_completions(request)

    # Convert to streaming format
    chunk = {
        "id": response.id,
        "object": "chat.completion.chunk",
        "created": response.created,
        "model": response.model,
        "choices": [
            {
                "index": 0,
                "delta": response.choices[0]["message"],
                "finish_reason": response.choices[0]["finish_reason"],
            }
        ],
    }

    async def generate():
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/plain")


if __name__ == "__main__":
    logger.info("Starting OpenCode-RunPod Bridge Service")
    logger.info(f"RunPod Endpoint: {RUNPOD_ENDPOINT_ID}")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
