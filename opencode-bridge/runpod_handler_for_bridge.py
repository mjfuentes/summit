import json
import logging

import runpod
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to persist model across invocations
tokenizer = None
model = None


def load_model():
    """Load model once and reuse across invocations"""
    global tokenizer, model
    if model is None:
        logger.info("Loading Qwen 2.5 model...")
        model_name = "Qwen/Qwen2.5-14B-Instruct"

        tokenizer = AutoTokenizer.from_pretrained(
            model_name, trust_remote_code=True
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        logger.info("Model loaded successfully")


def parse_tool_calls_from_response(response_text):
    """Parse tool calls from Qwen's response text if it follows the expected format"""
    try:
        # Qwen might return tool calls in a structured format
        # This is a simplified parser - adjust based on actual Qwen output
        if (
            "tool_calls:" in response_text.lower()
            or "<tool_call>" in response_text
        ):
            # Extract tool calls using simple parsing
            # You may need to adjust this based on Qwen's actual output format
            import re

            # Look for JSON-like tool call patterns
            tool_call_pattern = (
                r'{"name":\s*"([^"]+)",\s*"arguments":\s*({[^}]*}|"[^"]*")}'
            )
            matches = re.findall(tool_call_pattern, response_text)

            if matches:
                tool_calls = []
                for i, (name, args) in enumerate(matches):
                    try:
                        # Parse arguments
                        if args.startswith("{"):
                            arguments = json.loads(args)
                        else:
                            arguments = json.loads(args.strip('"'))

                        tool_calls.append(
                            {"name": name, "arguments": arguments}
                        )
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse tool call arguments: {args}"
                        )

                return tool_calls
    except Exception as e:
        logger.warning(f"Error parsing tool calls: {e}")

    return None


def format_messages_for_qwen(messages):
    """Format messages for Qwen's chat method"""
    formatted_messages = []

    for msg in messages:
        formatted_msg = {"role": msg["role"], "content": msg["content"]}

        # Handle tool calls in assistant messages
        if msg.get("tool_calls"):
            # Format tool calls for Qwen
            tool_calls_text = "Tool calls needed:\n"
            for call in msg["tool_calls"]:
                tool_calls_text += f"- {call['name']}: {json.dumps(call.get('arguments', {}))}\n"
            formatted_msg["content"] = tool_calls_text

        formatted_messages.append(formatted_msg)

    return formatted_messages


def format_tools_for_qwen(tools):
    """Format tools for Qwen's understanding"""
    if not tools:
        return None

    formatted_tools = []
    for tool in tools:
        if tool.get("type") == "function":
            function = tool.get("function", {})
            formatted_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": function.get("name"),
                        "description": function.get("description"),
                        "parameters": function.get("parameters", {}),
                    },
                }
            )

    return formatted_tools


def handler(event):
    """Main RunPod serverless handler"""
    try:
        input_data = event.get("input", {})
        logger.info(
            f"Received request: {json.dumps(input_data, indent=2)[:500]}..."
        )

        load_model()

        messages = input_data.get("messages", [])
        tools = input_data.get("tools", [])
        tool_outputs = input_data.get("tool_outputs")

        # Format messages for Qwen
        qwen_messages = format_messages_for_qwen(messages)
        qwen_tools = format_tools_for_qwen(tools)

        logger.info(
            f"Processing {len(qwen_messages)} messages with {len(tools) if tools else 0} tools"
        )

        # Create system prompt that explains tool usage if tools are available
        if qwen_tools and not tool_outputs:
            system_msg = {
                "role": "system",
                "content": f"""You are an AI assistant with access to the following tools:

{json.dumps(qwen_tools, indent=2)}

When you need to use a tool, respond with EXACTLY this format:
TOOL_CALL: {{"name": "tool_name", "arguments": {{"param": "value"}}}}

You can make multiple tool calls if needed. Always use the exact tool names and parameter formats provided.""",
            }
            qwen_messages.insert(0, system_msg)

        # Generate response using Qwen's chat method
        try:
            response = model.chat(
                tokenizer, qwen_messages, history=None, system=None
            )

            logger.info(f"Qwen response: {response[:200]}...")

        except Exception as e:
            logger.error(f"Error during model.chat: {e}")
            # Fallback to generate method
            input_text = tokenizer.apply_chat_template(
                qwen_messages, tokenize=False, add_generation_prompt=True
            )

            inputs = tokenizer(input_text, return_tensors="pt").to(
                model.device
            )

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            response = tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )

        # Check if response contains tool calls
        if "TOOL_CALL:" in response and not tool_outputs:
            logger.info("Response contains tool calls")

            # Parse tool calls from response
            tool_calls = []
            lines = response.split("\n")

            for line in lines:
                if "TOOL_CALL:" in line:
                    try:
                        # Extract JSON after TOOL_CALL:
                        json_str = line.split("TOOL_CALL:", 1)[1].strip()
                        tool_call_data = json.loads(json_str)

                        tool_calls.append(
                            {
                                "name": tool_call_data["name"],
                                "arguments": tool_call_data["arguments"],
                            }
                        )
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            f"Failed to parse tool call: {line}, error: {e}"
                        )

            if tool_calls:
                # Convert to OpenCode format
                formatted_tool_calls = []
                for i, call in enumerate(tool_calls):
                    formatted_tool_calls.append(
                        {
                            "id": f"call_{hash(str(call)) % 1000000}",
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call["arguments"]),
                            },
                        }
                    )

                return {
                    "tool_calls": formatted_tool_calls,
                    "content": None,
                    "requires_tool_execution": True,
                }

        # Regular text response
        return {
            "content": response,
            "tool_calls": None,
            "requires_tool_execution": False,
        }

    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {
            "error": str(e),
            "content": f"I encountered an error: {str(e)}",
            "tool_calls": None,
            "requires_tool_execution": False,
        }


# Set the handler for RunPod
runpod.serverless.start({"handler": handler})
