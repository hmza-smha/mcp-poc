"""
HTTP-based MCP Server for Remote Deployment
Uses SSE (Server-Sent Events) for communication instead of stdio

This version can run on a separate server and accept connections over HTTP.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    Prompt,
    TextContent,
    PromptMessage,
    GetPromptResult,
)
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
import uvicorn

# In-memory task storage
tasks = {}
task_counter = 0

# Initialize MCP Server
app = Server("task-manager")


# ============================================================================
# RESOURCES
# ============================================================================

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List all available resources."""
    resources = []
    
    resources.append(
        Resource(
            uri="task://all",
            name="All Tasks",
            mimeType="application/json",
            description="Complete list of all tasks in the system"
        )
    )
    
    for task_id, task in tasks.items():
        resources.append(
            Resource(
                uri=f"task://{task_id}",
                name=f"Task {task_id}",
                mimeType="application/json",
                description=f"Details for task: {task['title']}"
            )
        )
    
    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read the content of a specific resource."""
    uri = str(uri)
    if uri == "task://all":
        return json.dumps({
            "tasks": tasks,
            "total_count": len(tasks),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    
    elif uri.startswith("task://"):
        task_id = int(uri.split("//")[1])
        if task_id in tasks:
            return json.dumps(tasks[task_id], indent=2)
        else:
            raise ValueError(f"Task {task_id} not found")
    
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


# ============================================================================
# TOOLS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="create_task",
            description="Create a new task with a title and optional description",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the task"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level of the task"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "number",
                        "description": "The ID of the task to complete"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="delete_task",
            description="Delete a task permanently",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "number",
                        "description": "The ID of the task to delete"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="search_tasks",
            description="Search for tasks by keyword in title or description",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for"
                    }
                },
                "required": ["keyword"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Execute a tool based on its name and arguments."""
    global task_counter
    
    if name == "create_task":
        task_counter += 1
        task_id = task_counter
        
        task = {
            "id": task_id,
            "title": arguments["title"],
            "description": arguments.get("description", ""),
            "priority": arguments.get("priority", "medium"),
            "completed": False,
            "created_at": datetime.now().isoformat()
        }
        
        tasks[task_id] = task
        
        return [
            TextContent(
                type="text",
                text=f"Task created successfully!\n\n{json.dumps(task, indent=2)}"
            )
        ]
    
    elif name == "complete_task":
        task_id = int(arguments["task_id"])
        
        if task_id not in tasks:
            return [TextContent(type="text", text=f"Task {task_id} not found")]
        
        tasks[task_id]["completed"] = True
        tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        return [
            TextContent(
                type="text",
                text=f"Task {task_id} marked as completed!\n\n{json.dumps(tasks[task_id], indent=2)}"
            )
        ]
    
    elif name == "delete_task":
        task_id = int(arguments["task_id"])
        
        if task_id not in tasks:
            return [TextContent(type="text", text=f"Task {task_id} not found")]
        
        deleted_task = tasks.pop(task_id)
        
        return [
            TextContent(
                type="text",
                text=f"Task {task_id} deleted successfully!\n\n{json.dumps(deleted_task, indent=2)}"
            )
        ]
    
    elif name == "search_tasks":
        keyword = arguments["keyword"].lower()
        results = []
        
        for task_id, task in tasks.items():
            if (keyword in task["title"].lower() or 
                keyword in task.get("description", "").lower()):
                results.append(task)
        
        return [
            TextContent(
                type="text",
                text=f"Found {len(results)} task(s) matching '{keyword}':\n\n{json.dumps(results, indent=2)}"
            )
        ]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# PROMPTS
# ============================================================================

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List all available prompts."""
    return [
        Prompt(
            name="daily_summary",
            description="Generate a daily summary of all tasks",
            arguments=[
                {
                    "name": "include_completed",
                    "description": "Whether to include completed tasks",
                    "required": False
                }
            ]
        ),
        Prompt(
            name="task_priorities",
            description="Analyze and suggest task priorities",
            arguments=[]
        ),
        Prompt(
            name="create_task_wizard",
            description="Interactive wizard to create a well-structured task",
            arguments=[
                {
                    "name": "task_type",
                    "description": "Type of task (work, personal, urgent)",
                    "required": True
                }
            ]
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get a specific prompt with its messages."""
    if name == "daily_summary":
        include_completed = arguments.get("include_completed", "true") == "true" if arguments else True
        
        task_list = []
        for task_id, task in tasks.items():
            if not include_completed and task["completed"]:
                continue
            task_list.append(task)
        
        prompt_text = f"""Please provide a daily summary of tasks.

Current tasks ({len(task_list)} total):
{json.dumps(task_list, indent=2)}

Please:
1. Summarize the overall status
2. Highlight high-priority tasks
3. Identify any overdue or urgent items
4. Suggest next actions"""

        return GetPromptResult(
            description="Daily task summary prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )
    
    elif name == "task_priorities":
        prompt_text = f"""Analyze the following tasks and provide priority recommendations:

{json.dumps(list(tasks.values()), indent=2)}

Please:
1. Review each task's current priority
2. Suggest any priority adjustments based on urgency and importance
3. Recommend a focus order for today
4. Identify tasks that could be delegated or eliminated"""

        return GetPromptResult(
            description="Task priority analysis prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )
    
    elif name == "create_task_wizard":
        task_type = arguments.get("task_type", "general") if arguments else "general"
        
        prompt_text = f"""Let's create a well-structured {task_type} task together.

Please help me create a task by asking about:
1. What is the main objective or title?
2. What are the specific details or requirements?
3. What priority level is appropriate (low/medium/high)?
4. Are there any dependencies or blockers?

After gathering this information, use the create_task tool to add it to the system."""

        return GetPromptResult(
            description=f"Interactive wizard for creating a {task_type} task",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# HTTP/SSE TRANSPORT SETUP
# ============================================================================

# Create SSE transport
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """Handle SSE connection from client"""
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options(),
        )
    return Response()

async def handle_messages(request):
    """Handle incoming messages from client"""
    await sse.handle_post_message(request.scope, request.receive, request._send)
    return Response()

# Create Starlette app
starlette_app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ],
)


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("Starting MCP Task Manager Server (HTTP/SSE)")
    print("="*60)
    print("Server will be available at: http://localhost:8000")
    print("SSE endpoint: http://localhost:8000/sse")
    print("Messages endpoint: http://localhost:8000/messages")
    print("="*60)
    print("\nAvailable features:")
    print("  - Resources: Read task data")
    print("  - Tools: Create, complete, delete, and search tasks")
    print("  - Prompts: Pre-built templates for common workflows")
    print("="*60)
    
    # Run the server
    uvicorn.run(
        starlette_app,
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        log_level="info"
    )
