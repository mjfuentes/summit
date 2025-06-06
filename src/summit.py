#!/usr/bin/env python3

import asyncio
import os
import sys
import time
import subprocess
import json
import requests
from typing import Any, Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from anthropic import Anthropic

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from config import setup_environment, SUMMIT_CONFIG
from cost_tracker import CostTracker
from vector_knowledge_base import EnhancedKnowledgeBase

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
knowledge_base = EnhancedKnowledgeBase()

# Initialize Anthropic client
def get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

# GitHub API configuration for Codespaces
def get_github_headers():
    """Get GitHub API headers with authentication"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def get_github_repo_info():
    """Get GitHub repository information from environment or git config"""
    # Try environment variables first
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    
    if owner and repo:
        return owner, repo
    
    # Try to extract from git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            # Parse GitHub URL (supports both SSH and HTTPS)
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    # SSH format: git@github.com:owner/repo.git
                    parts = remote_url.split(":")[-1].replace(".git", "").split("/")
                    return parts[0], parts[1]
                elif remote_url.startswith("https://"):
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = remote_url.split("/")
                    return parts[-2], parts[-1].replace(".git", "")
    except:
        pass
    
    return None, None

# Track server start time
start_time = time.time()

# Store active codespaces for management
active_codespaces = {}

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
                    "max_results": {
                        "type": "number",
                        "description": "Optional: Maximum number of results to return (default: 5)",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="summit_analytics",
            description="Get search analytics and knowledge base insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_suggestions": {
                        "type": "boolean",
                        "description": "Optional: Include query suggestions (default: false)",
                    },
                },
            },
        ),
        types.Tool(
            name="summit_insights",
            description="Get content insights and knowledge gaps analysis",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_learn_capability",
            description="Learn a new capability by modifying Summit's codebase using GitHub Codespaces",
            inputSchema={
                "type": "object",
                "properties": {
                    "capability_description": {
                        "type": "string",
                        "description": "Detailed description of the new capability to implement",
                    },
                    "requirements": {
                        "type": "string",
                        "description": "Optional: Specific technical requirements or constraints",
                    },
                    "machine_type": {
                        "type": "string",
                        "description": "Optional: Codespace machine type (standardLinux32gb, premiumLinux32gb, etc.)",
                    },
                },
                "required": ["capability_description"],
            },
        ),
        types.Tool(
            name="summit_codespace_status",
            description="Check status of active development environments (codespaces)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_deploy_changes",
            description="Deploy and activate changes from a completed development session",
            inputSchema={
                "type": "object",
                "properties": {
                    "codespace_name": {
                        "type": "string",
                        "description": "Name of the codespace with completed changes",
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message for the changes",
                    },
                },
                "required": ["codespace_name", "commit_message"],
            },
        ),
        types.Tool(
            name="summit_cleanup_environment",
            description="Clean up development environment after learning is complete",
            inputSchema={
                "type": "object",
                "properties": {
                    "codespace_name": {
                        "type": "string",
                        "description": "Name of the codespace to clean up",
                    },
                },
                "required": ["codespace_name"],
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
        max_results = arguments.get("max_results", 5)
        
        if not query:
            raise ValueError("Query is required for learning")
        
        # Perform enhanced semantic search in the knowledge base
        search_results = knowledge_base.search_knowledge(query, max_results=max_results)
        
        if not search_results:
            # Get suggestions for alternative queries
            suggestions = knowledge_base.suggest_related_queries(query)
            suggestion_text = ""
            if suggestions:
                suggestion_text = f"\n\nTry these related queries:\n" + "\n".join(f"• {s}" for s in suggestions)
            
            return [
                types.TextContent(
                    type="text",
                    text=f"No results found for your query '{query}'. Please try a different query or focus.{suggestion_text}"
                )
            ]
        
        # Extract relevant information from the search results with enhanced details
        relevant_information = []
        for i, result in enumerate(search_results, 1):
            score = result['similarity_score']
            relevance = result['relevance']
            
            if result['type'] == 'shared_item':
                item = result['data']
                timestamp = item['timestamp'][:10]  # Just the date
                info_line = f"{i}. {item['content']} (Category: {item['category']}, Date: {timestamp})"
                if score > 1.0:
                    info_line += f" ★ High relevance ({score:.1f})"
                relevant_information.append(info_line)
            elif result['type'] == 'synthesized_insight':
                insight = result['data']
                timestamp = insight['timestamp'][:10]
                info_line = f"{i}. 💡 Insight: {insight['insight']} (Date: {timestamp})"
                if score > 1.0:
                    info_line += f" ★ High relevance ({score:.1f})"
                relevant_information.append(info_line)
        
        # Get additional context if focus is specified
        focus_context = ""
        if focus:
            if focus.lower() in ['patterns', 'trends']:
                insights = knowledge_base.get_content_insights()
                if insights['content_themes']:
                    focus_context = f"\n\nKey themes in the knowledge base: {', '.join(insights['content_themes'])}"
            elif focus.lower() == 'gaps':
                insights = knowledge_base.get_content_insights()
                if insights['knowledge_gaps']:
                    focus_context = f"\n\nKnowledge gaps identified: {', '.join(insights['knowledge_gaps'])}"
        
        # Build the enhanced response
        search_mode = "semantic + keyword" if knowledge_base.embeddings_enabled else "enhanced keyword"
        response = f"""Summit's Knowledge Search Results (using {search_mode} search):

{chr(10).join(relevant_information)}

Found {len(search_results)} relevant items from {knowledge_base.get_knowledge_summary()['total_shares']} total shared experiences.{focus_context}"""
        
        return [
            types.TextContent(
                type="text",
                text=response
            )
        ]
    
    elif name == "summit_analytics":
        include_suggestions = arguments.get("include_suggestions", False)
        
        # Get comprehensive analytics
        analytics = knowledge_base.get_search_analytics()
        summary = knowledge_base.get_knowledge_summary()
        
        response = f"""Summit Search Analytics & Performance

Search Statistics:
• Total searches performed: {analytics['total_searches']}
• Semantic searches: {analytics['semantic_searches']} ({analytics['semantic_percentage']:.1f}%)
• Keyword searches: {analytics['keyword_searches']} ({analytics['keyword_percentage']:.1f}%)
• Empty results rate: {analytics['empty_rate']:.1f}%

Query Patterns:
• Question queries: {analytics['query_types'].get('question', 0)}
• Search queries: {analytics['query_types'].get('search', 0)}
• Similarity queries: {analytics['query_types'].get('similarity', 0)}
• Recommendation queries: {analytics['query_types'].get('recommendation', 0)}
• General queries: {analytics['query_types'].get('general', 0)}

Knowledge Base Status:
• Search mode: {summary['search_mode']}
• Total content items: {summary['total_shares']}
• Synthesized insights: {summary['synthesized_insights']}
• Vector embeddings: {summary['total_embeddings']}

Popular Categories (from search results):
{chr(10).join(f"• {cat}: {count} searches" for cat, count in analytics['popular_categories'].items()) if analytics['popular_categories'] else "• No search data yet"}"""

        if include_suggestions and analytics['total_searches'] > 0:
            # Add optimization suggestions
            response += f"""

Performance Insights:
• Search efficiency: {'Good' if analytics['empty_rate'] < 20 else 'Could be improved'}
• Content diversity: {'Good' if len(summary['categories']) > 3 else 'Limited categories'}
• Vector search: {'Active' if summary['search_mode'].startswith('semantic') else 'Consider enabling OPENAI_API_KEY for semantic search'}"""
        
        return [
            types.TextContent(
                type="text",
                text=response
            )
        ]
    
    elif name == "summit_insights":
        insights = knowledge_base.get_content_insights()
        summary = knowledge_base.get_knowledge_summary()
        
        response = f"""Summit Knowledge Base Content Analysis

Content Overview:
• Total shared items: {insights['total_items']}
• Synthesized insights: {insights['total_insights']}
• Active categories: {len(insights['categories_distribution'])}

Category Distribution:
{chr(10).join(f"• {cat}: {count} items" for cat, count in insights['categories_distribution'].items())}

Content Themes (most frequent topics):
{chr(10).join(f"• {theme}" for theme in insights['content_themes']) if insights['content_themes'] else "• Not enough content for theme analysis"}

Knowledge Gaps & Recommendations:
{chr(10).join(f"• {gap}" for gap in insights['knowledge_gaps']) if insights['knowledge_gaps'] else "• Knowledge base appears well-balanced"}

Recent Activity:
{f"• {insights['recent_activity']['count']} recent items in categories: {', '.join(insights['recent_activity']['categories'])}" if insights['recent_activity'] else "• No recent activity"}
{f"• {insights['recent_activity']['timespan']}" if insights['recent_activity'] else ""}

Growth Opportunities:
• Consider adding more content in under-represented categories
• Synthesize insights from existing content to create new knowledge
• Encourage sharing in diverse domains for richer search results"""
        
        return [
            types.TextContent(
                type="text",
                text=response
            )
        ]
    
    elif name == "summit_learn_capability":
        capability_description = arguments.get("capability_description")
        requirements = arguments.get("requirements")
        machine_type = arguments.get("machine_type", "standardLinux32gb")
        
        if not capability_description:
            raise ValueError("Capability description is required")
        
        try:
            # Get repository information
            owner, repo = get_github_repo_info()
            if not owner or not repo:
                return [types.TextContent(type="text", text="Error: Could not determine GitHub repository. Please set GITHUB_OWNER and GITHUB_REPO environment variables.")]
            
            # Plan the implementation
            implementation_plan = await plan_capability_implementation(capability_description, requirements)
            
            # Create a new codespace for development
            codespace_data = await create_codespace(owner, repo, machine_type)
            
            # Start the codespace
            await start_codespace(codespace_data['name'])
            
            # Generate implementation instructions
            instructions = await implement_capability_in_codespace(
                codespace_data['web_url'], 
                implementation_plan, 
                capability_description
            )
            
            # Share this learning session with the knowledge base
            knowledge_base.add_shared_item(
                f"Learning new capability: {capability_description}",
                "capability_development",
                f"Created codespace {codespace_data['name']} for implementation"
            )
            
            response = f"""Summit is learning a new capability! 🚀

Capability: {capability_description}
Development Environment: {codespace_data['name']}
Status: {codespace_data['state']}

{instructions}

I'll track this learning session and help you deploy the changes when ready."""
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error starting learning session: {e}")]
    
    elif name == "summit_codespace_status":
        try:
            # List all codespaces
            all_codespaces = await list_user_codespaces()
            
            # Filter for Summit-related codespaces
            summit_codespaces = [
                cs for cs in all_codespaces 
                if 'Summit' in cs.get('display_name', '') or cs['name'] in active_codespaces
            ]
            
            if not summit_codespaces:
                response = "No active Summit development environments found."
            else:
                response = "Summit Development Environments Status:\n\n"
                for cs in summit_codespaces:
                    status_emoji = "🟢" if cs['state'] == 'Available' else "🟡" if cs['state'] == 'Starting' else "🔴"
                    response += f"{status_emoji} {cs['name']}\n"
                    response += f"   Status: {cs['state']}\n"
                    response += f"   Created: {cs['created_at'][:19].replace('T', ' ')}\n"
                    response += f"   URL: {cs['web_url']}\n\n"
                
                response += f"Total environments: {len(summit_codespaces)}"
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error checking codespace status: {e}")]
    
    elif name == "summit_deploy_changes":
        codespace_name = arguments.get("codespace_name")
        commit_message = arguments.get("commit_message")
        
        if not codespace_name or not commit_message:
            raise ValueError("Codespace name and commit message are required")
        
        try:
            # Get codespace status to verify it exists and is accessible
            codespace_status = await get_codespace_status(codespace_name)
            
            # In a full implementation, this would:
            # 1. Connect to the codespace
            # 2. Run tests to validate changes
            # 3. Commit and push changes
            # 4. Potentially restart the Summit server with new capabilities
            
            # For now, provide instructions for manual deployment
            instructions = f"""
Deployment Instructions for Summit Learning Session:

Codespace: {codespace_name}
Status: {codespace_status['state']}
URL: {codespace_status['web_url']}

Manual Deployment Steps:
1. Ensure all changes are tested and working in the codespace
2. Commit your changes:
   git add .
   git commit -m "{commit_message}"
3. Push to the repository:
   git push origin main
4. The changes will be available for the next Summit restart

Automated deployment capabilities are coming in future versions!
"""

            # Record this deployment in the knowledge base
            knowledge_base.add_shared_item(
                f"Deployed changes from {codespace_name}: {commit_message}",
                "capability_deployment",
                f"Learning session completed and deployed"
            )
            
            # Stop the codespace to save resources (optional)
            await stop_codespace(codespace_name)
            
            response = f"""Deployment initiated for Summit learning session! 🎉

{instructions}

The development environment has been stopped to save resources.
Use summit_cleanup_environment to remove it when no longer needed."""
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error deploying changes: {e}")]
    
    elif name == "summit_cleanup_environment":
        codespace_name = arguments.get("codespace_name")
        
        if not codespace_name:
            raise ValueError("Codespace name is required")
        
        try:
            # Stop the codespace first (if running)
            try:
                await stop_codespace(codespace_name)
            except:
                pass  # Might already be stopped
            
            # Delete the codespace
            await delete_codespace(codespace_name)
            
            # Record cleanup in knowledge base
            knowledge_base.add_shared_item(
                f"Cleaned up development environment: {codespace_name}",
                "environment_management",
                "Learning session complete, resources freed"
            )
            
            response = f"""Development environment cleaned up successfully! ♻️

Codespace '{codespace_name}' has been:
- Stopped (if running)
- Deleted to free resources
- Removed from active tracking

Your learning session data is preserved in Summit's knowledge base.
Ready for the next capability development session!"""
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error cleaning up environment: {e}")]
    
    else:
        raise ValueError(f"Summit doesn't know tool: {name}")

async def create_codespace(owner: str, repo: str, machine_type: str = "standardLinux32gb", ref: str = "main") -> Dict:
    """Create a new GitHub Codespace for development"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required for Codespaces")
    
    url = f"https://api.github.com/repos/{owner}/{repo}/codespaces"
    
    payload = {
        "ref": ref,
        "machine": machine_type,
        "display_name": f"Summit Learning Session - {time.strftime('%Y%m%d-%H%M%S')}",
        "idle_timeout_minutes": 60,
        "retention_period_minutes": 1440  # 24 hours
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        codespace_data = response.json()
        
        # Store in active codespaces
        active_codespaces[codespace_data['name']] = {
            'id': codespace_data['id'],
            'name': codespace_data['name'],
            'state': codespace_data['state'],
            'web_url': codespace_data['web_url'],
            'created_at': codespace_data['created_at'],
            'purpose': 'capability_learning'
        }
        
        return codespace_data
        
    except requests.RequestException as e:
        raise Exception(f"Failed to create codespace: {e}")

async def start_codespace(codespace_name: str) -> Dict:
    """Start an existing codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    url = f"https://api.github.com/user/codespaces/{codespace_name}/start"
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        codespace_data = response.json()
        
        # Update stored info
        if codespace_name in active_codespaces:
            active_codespaces[codespace_name]['state'] = codespace_data['state']
        
        return codespace_data
        
    except requests.RequestException as e:
        raise Exception(f"Failed to start codespace: {e}")

async def stop_codespace(codespace_name: str) -> Dict:
    """Stop a running codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    url = f"https://api.github.com/user/codespaces/{codespace_name}/stop"
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        codespace_data = response.json()
        
        # Update stored info
        if codespace_name in active_codespaces:
            active_codespaces[codespace_name]['state'] = codespace_data['state']
        
        return codespace_data
        
    except requests.RequestException as e:
        raise Exception(f"Failed to stop codespace: {e}")

async def delete_codespace(codespace_name: str) -> bool:
    """Delete a codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    url = f"https://api.github.com/user/codespaces/{codespace_name}"
    
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Remove from active codespaces
        if codespace_name in active_codespaces:
            del active_codespaces[codespace_name]
        
        return True
        
    except requests.RequestException as e:
        raise Exception(f"Failed to delete codespace: {e}")

async def get_codespace_status(codespace_name: str) -> Dict:
    """Get the current status of a codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    url = f"https://api.github.com/user/codespaces/{codespace_name}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()
        
    except requests.RequestException as e:
        raise Exception(f"Failed to get codespace status: {e}")

async def list_user_codespaces() -> List[Dict]:
    """List all user's codespaces"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    url = "https://api.github.com/user/codespaces"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()['codespaces']
        
    except requests.RequestException as e:
        raise Exception(f"Failed to list codespaces: {e}")

async def plan_capability_implementation(capability_description: str, requirements: str = None) -> str:
    """Use Claude to plan the implementation of a new capability"""
    client = get_anthropic_client()
    
    if not client:
        return "Summit needs an ANTHROPIC_API_KEY to plan capability implementations."
    
    # Get current codebase context
    owner, repo = get_github_repo_info()
    if not owner or not repo:
        codebase_context = "Working with local Summit codebase"
    else:
        codebase_context = f"Working with Summit repository: {owner}/{repo}"
    
    planning_prompt = f"""You are Summit, an AI that can learn new capabilities by modifying its own code. You need to plan how to implement a new capability.

IMPORTANT: Follow Summit's coding standards (available in CODING_STANDARDS.md):
- NEVER add obvious/redundant comments like "# Test passed", "# Success", "# End of function"
- Comments should explain WHY, not WHAT the code does
- Use proper assertions in tests, not return statements
- Keep code clean and readable

Current Context:
- {codebase_context}
- Summit is a Python MCP server with tool handlers
- Current capabilities include: advice, knowledge sharing, search, analytics
- Uses GitHub Codespaces for isolated development environments

New Capability Request:
{capability_description}

{f"Requirements: {requirements}" if requirements else ""}

Please provide a detailed implementation plan including:
1. Files that need to be modified
2. New functions or tools to add
3. Dependencies that might be needed
4. Testing approach
5. Step-by-step implementation strategy
6. Potential risks or challenges

Be specific about the code changes needed. Remember to follow the coding standards and avoid obvious comments."""

    try:
        message = client.messages.create(
            model=SUMMIT_CONFIG["chat_model"],
            max_tokens=1500,
            messages=[{"role": "user", "content": planning_prompt}]
        )
        
        return message.content[0].text
        
    except Exception as e:
        return f"Error planning implementation: {e}"

async def implement_capability_in_codespace(codespace_url: str, implementation_plan: str, capability_description: str) -> str:
    """
    Implement the capability in the codespace environment
    This is a simplified version - in practice, you'd use the Codespaces API
    or VS Code extension API to execute commands and modify files.
    """
    
    # For now, we'll provide detailed instructions for manual implementation
    # In a full implementation, this would use the Codespaces API to:
    # 1. Clone the repository
    # 2. Create/modify files
    # 3. Run tests
    # 4. Validate changes
    
    instructions = f"""
Summit Learning Session Instructions

Codespace URL: {codespace_url}

IMPORTANT: Read CODING_STANDARDS.md first for Summit's coding guidelines.

Capability to Implement:
{capability_description}

Implementation Plan:
{implementation_plan}

Manual Steps:
1. Open the codespace in your browser: {codespace_url}
2. Navigate to the Summit codebase
3. Read CODING_STANDARDS.md to understand code quality expectations
4. Follow the implementation plan above
5. Create/modify the necessary files (following coding standards)
6. Add appropriate tests (use assert, not return statements)
7. Run tests to validate changes
8. Commit changes with descriptive message
9. Use summit_deploy_changes tool when complete

The codespace provides:
- Full Ubuntu development environment
- Python 3.x with all dependencies
- Git access for version control
- VS Code web interface
- Terminal access for commands

Note: This is currently a semi-automated process. Future versions will provide
full automated implementation capabilities.
"""
    
    return instructions

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