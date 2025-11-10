"""
Complete MCP (Model Context Protocol) Server Example
Demonstrates Tools, Resources, and Prompts primitives

This is a simple task management MCP server that showcases all MCP features.
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
    ImageContent,
    EmbeddedResource,
    PromptMessage,
    GetPromptResult,
)
from mcp.server.stdio import stdio_server

# In-memory task storage
# In production, this would connect to a real database
tasks = {}
task_counter = 0


# Initialize MCP Server
# The name "task-manager" identifies this server
app = Server("task-manager")


# ============================================================================
# RESOURCES - Expose data that can be read
# ============================================================================
# Resources represent READ-ONLY data sources that Claude can access
# Examples: files, database entries, API responses, configuration

@app.list_resources()
async def list_resources() -> list[Resource]:
    """
    List all available resources.
    
    This is called when Claude wants to know what data is available.
    Each resource has a unique URI (like a URL) that identifies it.
    
    Returns:
        List of Resource objects describing available data
    """
    resources = []
    
    # Resource 1: All tasks as a list
    # URI format: protocol://identifier
    resources.append(
        Resource(
            uri="task://all",  # Unique identifier for this resource
            name="All Tasks",  # Human-readable name
            mimeType="application/json",  # Data format
            description="Complete list of all tasks in the system"
        )
    )
    
    # Resource 2: Each individual task
    # Dynamically create resources for each task
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
    """
    Read the content of a specific resource.
    
    When Claude wants to access data, it calls this function with the
    resource URI. This is where you fetch the actual data.
    
    Args:
        uri: The unique identifier for the resource (from list_resources)
        
    Returns:
        String content of the resource (typically JSON)
        
    Raises:
        ValueError: If the resource URI is invalid or not found
    """
    uri = str(uri)
    if uri == "task://all":
        # Return all tasks with metadata
        return json.dumps({
            "tasks": tasks,
            "total_count": len(tasks),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    
    elif uri.startswith("task://"):
        # Parse the task ID from the URI
        task_id = int(uri.split("//")[1])
        if task_id in tasks:
            return json.dumps(tasks[task_id], indent=2)
        else:
            raise ValueError(f"Task {task_id} not found")
    
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


# ============================================================================
# TOOLS - Functions the AI can call to perform actions
# ============================================================================
# Tools are ACTIONS that Claude can perform
# Examples: creating records, sending emails, making API calls, updating data

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List all available tools.
    
    Tools are functions that Claude can call to perform actions.
    Each tool has a name, description, and JSON schema defining its parameters.
    
    The inputSchema follows JSON Schema specification:
    - type: "object" for structured inputs
    - properties: defines each parameter
    - required: array of mandatory parameter names
    
    Returns:
        List of Tool objects describing available actions
    """
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
                "required": ["title"]  # Only title is mandatory
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
    """
    Execute a tool based on its name and arguments.
    
    When Claude decides to use a tool, this function is called with:
    - name: which tool to execute
    - arguments: the parameters Claude provided
    
    This is where the actual business logic happens.
    
    Args:
        name: The name of the tool to execute
        arguments: Dictionary of arguments matching the tool's inputSchema
        
    Returns:
        List of TextContent objects with the results
        
    Raises:
        ValueError: If the tool name is unknown
    """
    global task_counter
    
    if name == "create_task":
        # Generate a new task ID
        task_counter += 1
        task_id = task_counter
        
        # Create the task object
        task = {
            "id": task_id,
            "title": arguments["title"],
            "description": arguments.get("description", ""),  # Optional field
            "priority": arguments.get("priority", "medium"),  # Default to medium
            "completed": False,
            "created_at": datetime.now().isoformat()
        }
        
        # Store in our "database"
        tasks[task_id] = task
        
        # Return success message
        return [
            TextContent(
                type="text",
                text=f"Task created successfully!\n\n{json.dumps(task, indent=2)}"
            )
        ]
    
    elif name == "complete_task":
        task_id = int(arguments["task_id"])
        
        # Validate task exists
        if task_id not in tasks:
            return [TextContent(type="text", text=f"Task {task_id} not found")]
        
        # Mark as completed
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
        
        # Remove from storage
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
        
        # Search through all tasks
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
# PROMPTS - Pre-defined prompt templates
# ============================================================================
# Prompts are TEMPLATES that help users interact with Claude in specific ways
# They can include context from resources and suggest using specific tools

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """
    List all available prompts.
    
    Prompts are pre-built templates that:
    - Provide context to Claude
    - Guide specific workflows
    - Can include dynamic data from resources
    - Suggest which tools to use
    
    Each prompt can accept arguments to customize its behavior.
    
    Returns:
        List of Prompt objects describing available templates
    """
    return [
        Prompt(
            name="daily_summary",
            description="Generate a daily summary of all tasks",
            arguments=[
                {
                    "name": "include_completed",
                    "description": "Whether to include completed tasks",
                    "required": False  # Optional argument
                }
            ]
        ),
        Prompt(
            name="task_priorities",
            description="Analyze and suggest task priorities",
            arguments=[]  # No arguments needed
        ),
        Prompt(
            name="create_task_wizard",
            description="Interactive wizard to create a well-structured task",
            arguments=[
                {
                    "name": "task_type",
                    "description": "Type of task (work, personal, urgent)",
                    "required": True  # Required argument
                }
            ]
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """
    Get a specific prompt with its messages.
    
    When a user selects a prompt, this function returns the actual prompt
    content that will be sent to Claude. Prompts can:
    - Include current data from your system
    - Provide instructions for Claude
    - Suggest specific tools to use
    
    Args:
        name: The name of the prompt to retrieve
        arguments: Optional dictionary of arguments from the user
        
    Returns:
        GetPromptResult containing the prompt description and messages
        
    Raises:
        ValueError: If the prompt name is unknown
    """
    if name == "daily_summary":
        # Parse optional argument
        include_completed = arguments.get("include_completed", "true") == "true" if arguments else True
        
        # Gather current task data
        task_list = []
        for task_id, task in tasks.items():
            if not include_completed and task["completed"]:
                continue
            task_list.append(task)
        
        # Build the prompt with current data
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
        # Include all task data for analysis
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
        # Use the task_type argument to customize the wizard
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
# SERVER STARTUP
# ============================================================================

async def main():
    """
    Run the MCP server using stdio transport.
    
    MCP servers communicate via standard input/output (stdio).
    This allows them to be launched as subprocesses by MCP clients.
    """
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import sys
    import io
    
    # Fix encoding issues on Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("Starting MCP Task Manager Server...")
    print("Available features:")
    print("  - Resources: Read task data")
    print("  - Tools: Create, complete, delete, and search tasks")
    print("  - Prompts: Pre-built templates for common workflows")
    asyncio.run(main())