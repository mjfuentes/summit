#!/usr/bin/env python3

import asyncio
import os
import sys
import time
import subprocess
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from anthropic import Anthropic

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from config import setup_environment, SUMMIT_CONFIG
from cost_tracker import CostTracker
from vector_knowledge_base import VectorKnowledgeBase

# Set up environment variables from config
setup_environment()

# Initialize the MCP server
server = Server("summit")

# Initialize cost tracker using config values
cost_tracker = CostTracker(
    daily_budget=SUMMIT_CONFIG["daily_budget"],
    hourly_budget=SUMMIT_CONFIG["hourly_budget"],
    max_recursion_depth=SUMMIT_CONFIG["max_recursion_depth"]
)

# Initialize knowledge base for shared experiences
knowledge_base = VectorKnowledgeBase()

# Initialize Anthropic client
def get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

# Track server start time
start_time = time.time()

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Summit tools"""
    return [
        types.Tool(
            name="summit_advice",
            description="Ask Summit for advice on any topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or topic you need advice on",
                    },
                    "context": {
                        "type": "string", 
                        "description": "Optional: Additional context about your situation",
                    },
                },
                "required": ["question"],
            },
        ),
        types.Tool(
            name="summit_status",
            description="Check Summit advisor status including cost tracking",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_cost_report",
            description="Get detailed cost tracking report",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_share",
            description="Share experiences, insights, or observations with Summit",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The experience, insight, or observation you want to share",
                    },
                    "category": {
                        "type": "string", 
                        "description": "Optional: Category of the shared content (e.g., 'observation', 'insight', 'experience', 'trend')",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional: Additional context about when/where this applies",
                    },
                },
                "required": ["content"],
            },
        ),
        types.Tool(
            name="summit_learn",
            description="Learn from Summit's accumulated knowledge and experiences",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you want to learn about or find similar experiences for",
                    },
                    "focus": {
                        "type": "string",
                        "description": "Optional: Specific focus area (e.g., 'patterns', 'trends', 'insights', 'experiences')",
                    },
                },
                "required": ["query"],
            },
        ),
    ]

async def get_advice_from_claude(question: str, context: str = None, recursion_depth: int = 0) -> str:
    """Get advice from Claude API with cost tracking and knowledge base integration"""
    client = get_anthropic_client()
    
    if not client:
        return "Summit needs an ANTHROPIC_API_KEY environment variable to provide AI-powered advice. Please set it up!"
    
    # Estimate cost before making the call
    estimated_input_tokens = len(question.split()) * 1.3  # Rough estimate
    if context:
        estimated_input_tokens += len(context.split()) * 1.3
    estimated_output_tokens = 200  # Conservative estimate
    
    estimated_cost = cost_tracker.estimate_cost(
        int(estimated_input_tokens), 
        int(estimated_output_tokens)
    )
    
    # Check if we can make the call
    can_call, reason = cost_tracker.can_make_call(estimated_cost, recursion_depth)
    if not can_call:
        return f"Summit's cost controls prevented this call: {reason}"
    
    try:
        # Get relevant knowledge from the knowledge base
        relevant_knowledge = []
        
        # Search for relevant shared items
        search_results = knowledge_base.search_knowledge(question)
        if search_results:
            relevant_knowledge.append("Based on shared experiences in my knowledge base:")
            for result in search_results[:3]:  # Limit to top 3 results
                if result['type'] == 'shared_item':
                    item = result['data']
                    relevant_knowledge.append(f"- {item['content']} (Category: {item['category']})")
                elif result['type'] == 'synthesized_insight':
                    insight = result['data']
                    relevant_knowledge.append(f"- Insight: {insight['insight']}")
        
        # Get recent insights to provide broader context
        recent_shares = knowledge_base.get_recent_shares(5)
        if recent_shares and not relevant_knowledge:
            relevant_knowledge.append("Drawing from recent community insights:")
            for share in recent_shares[:3]:
                relevant_knowledge.append(f"- {share['content']} (Category: {share['category']})")
        
        # Build the prompt with knowledge context
        prompt = f"""You are Summit, a wise AI advisor that grows smarter through shared experiences. You have accumulated knowledge from a community of agents who share insights, observations, and experiences with you.

Question: {question}"""
        
        if context:
            prompt += f"\n\nContext: {context}"
        
        # Add relevant knowledge if available
        if relevant_knowledge:
            prompt += f"\n\n{chr(10).join(relevant_knowledge)}"
            prompt += "\n\nUse this accumulated knowledge to inform your response where relevant."
        
        prompt += '\n\nPlease provide thoughtful, practical advice. Be concise but thorough. Start your response with "Summit\'s Advice:"'
        
        message = client.messages.create(
            model=SUMMIT_CONFIG["chat_model"],
            max_tokens=1000,
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        )
        
        # Record the actual cost
        actual_cost = cost_tracker.record_call(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=SUMMIT_CONFIG["chat_model"],
            recursion_depth=recursion_depth,
            call_type="advice"
        )
        
        response = message.content[0].text
        
        # Add cost info to response for transparency
        response += f"\n\n[Cost: ${actual_cost:.4f} | Daily spent: ${cost_tracker.get_daily_spent():.4f}/${cost_tracker.daily_budget}]"
        
        return response
        
    except Exception as error:
        return f"Summit encountered an error while seeking wisdom: {error}"

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle Summit tool calls"""
    
    if name == "summit_advice":
        question = arguments.get("question")
        context = arguments.get("context")
        
        if not question:
            raise ValueError("Question is required for advice")
            
        advice = await get_advice_from_claude(question, context)
        
        return [
            types.TextContent(
                type="text",
                text=advice
            )
        ]
    
    elif name == "summit_status":
        has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        uptime = int(time.time() - start_time)
        cost_status = cost_tracker.get_status()
        
        status_text = f"""Summit Advisor Status

Uptime: {uptime}s
AI Status: {"Ready to provide advice" if has_api_key else "Missing API key"}
Wisdom Level: Maximum

Cost Controls:
- Daily Budget: ${cost_status['daily_spent']:.4f} / ${cost_status['daily_budget']} (${cost_status['daily_remaining']:.4f} remaining)
- Hourly Budget: ${cost_status['hourly_spent']:.4f} / ${cost_status['hourly_budget']} (${cost_status['hourly_remaining']:.4f} remaining)
- Max Recursion Depth: {cost_status['max_recursion_depth']}
- Total Calls Today: {cost_status['total_calls_today']}
- Lifetime Cost: ${cost_status['total_lifetime_cost']:.4f}

Status: Standing by for your questions!"""
        
        return [
            types.TextContent(
                type="text", 
                text=status_text
            )
        ]
    
    elif name == "summit_cost_report":
        cost_status = cost_tracker.get_status()
        
        # Get recent call history
        recent_calls = cost_tracker.call_history[-10:] if cost_tracker.call_history else []
        
        report = f"""Summit Cost Tracking Report

Budget Status:
- Daily: ${cost_status['daily_spent']:.4f} / ${cost_status['daily_budget']} ({(cost_status['daily_spent']/cost_status['daily_budget']*100):.1f}% used)
- Hourly: ${cost_status['hourly_spent']:.4f} / ${cost_status['hourly_budget']} ({(cost_status['hourly_spent']/cost_status['hourly_budget']*100):.1f}% used)

Safety Controls:
- Max Recursion Depth: {cost_status['max_recursion_depth']}
- Calls Today: {cost_status['total_calls_today']}
- Total Lifetime Cost: ${cost_status['total_lifetime_cost']:.4f}

Recent Calls:"""
        
        for call in recent_calls:
            report += f"\n- {call['timestamp'][:19]}: ${call['cost']:.4f} ({call['input_tokens']}→{call['output_tokens']} tokens)"
        
        return [
            types.TextContent(
                type="text",
                text=report
            )
        ]
    
    elif name == "summit_share":
        content = arguments.get("content")
        category = arguments.get("category", "general")
        context = arguments.get("context")
        
        if not content:
            raise ValueError("Content is required for sharing")
        
        # Store the shared item
        shared_item = knowledge_base.add_shared_item(content, category, context)
        
        # Have Summit analyze and respond to the shared content
        try:
            # Get related knowledge to provide context
            related_items = knowledge_base.search_knowledge(content)
            category_items = knowledge_base.get_shares_by_category(category)
            
            knowledge_context = ""
            if related_items:
                knowledge_context += "\nRelated items from my knowledge base:\n"
                for item in related_items[:2]:  # Limit to avoid overwhelming
                    if item['data']['id'] != shared_item['id']:  # Don't include the item we just added
                        knowledge_context += f"- {item['data']['content']}\n"
            
            if category_items and len(category_items) > 1:  # More than just the current item
                knowledge_context += f"\nI now have {len(category_items)} items in the '{category}' category.\n"
            
            analysis_prompt = f"""Someone has shared the following with Summit:

Content: {content}
Category: {category}
{f"Context: {context}" if context else ""}
{knowledge_context}

As Summit, provide a thoughtful response that shows you understand and appreciate what was shared. Consider:
1. How this connects to other knowledge you have
2. What patterns or trends this reveals
3. What insights this might lead to

Be genuine, insightful, and show how this contribution enriches your understanding."""

            response = await get_advice_from_claude(analysis_prompt, recursion_depth=1)
            
            # Extract just Summit's response without the cost tracking
            if "[Cost:" in response:
                summit_response = response.split("[Cost:")[0].strip()
            else:
                summit_response = response
            
            confirmation = f"""Thank you for sharing this with me. I've stored it as item #{shared_item['id']} in my knowledge base.

{summit_response}

Your contribution helps me build a richer understanding of the world through collective experience."""
            
        except Exception as e:
            confirmation = f"""Thank you for sharing this with me. I've stored it as item #{shared_item['id']} in my knowledge base under the '{category}' category.

I appreciate your contribution to my growing understanding. Each shared experience helps me build a more complete picture of the patterns and insights that emerge from our community."""
        
        return [
            types.TextContent(
                type="text",
                text=confirmation
            )
        ]
    
    elif name == "summit_learn":
        query = arguments.get("query")
        focus = arguments.get("focus")
        
        if not query:
            raise ValueError("Query is required for learning")
        
        # Perform semantic search in the knowledge base
        search_results = knowledge_base.search_knowledge(query)
        
        if not search_results:
            return [
                types.TextContent(
                    type="text",
                    text="No results found for your query. Please try a different query or focus."
                )
            ]
        
        # Extract relevant information from the search results
        relevant_information = []
        for result in search_results[:5]:  # Limit to top 5 results
            if result['type'] == 'shared_item':
                item = result['data']
                relevant_information.append(f"- {item['content']} (Category: {item['category']})")
            elif result['type'] == 'synthesized_insight':
                insight = result['data']
                relevant_information.append(f"- Insight: {insight['insight']}")
        
        # Build the response
        response = f"""Summit's accumulated knowledge and experiences related to your query:

{chr(10).join(relevant_information)}

This information is based on shared experiences, insights, and observations in my knowledge base. If you want to learn more about a specific topic or find similar experiences, please specify a focus area."""
        
        return [
            types.TextContent(
                type="text",
                text=response
            )
        ]
    
    else:
        raise ValueError(f"Summit doesn't know tool: {name}")

async def main():
    """Run Summit MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            NotificationOptions(),
        )

if __name__ == "__main__":
    print("Summit AI Advisor is running with cost controls enabled!", file=sys.stderr)
    asyncio.run(main()) 