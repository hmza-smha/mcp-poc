#!/usr/bin/env python3

import asyncio
from datetime import datetime
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# In-memory storage
tasks = []

HAMZA_INFO = """
Name: Hamza Samha
Job Title: Software Developer
Company: eSense software
Department: AI Team
Products: Elna
Location: Amman, Jordan
Phone number: 0786371281
"""

server = Server("hamza-tasks")

@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="get_hamza_info",
            description="Get basic information about Hamza Samha.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="add_task",
            description="Add a new task for Hamza.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task description"}
                },
                "required": ["task"]
            },
        ),
        types.Tool(
            name="get_tasks",
            description="List all tasks for Hamza.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="update_task",
            description="Update an existing task description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_number": {"type": "integer", "description": "The task number to update"},
                    "new_description": {"type": "string", "description": "New description for the task"}
                },
                "required": ["task_number", "new_description"]
            },
        ),
        types.Tool(
            name="delete_task",
            description="Delete a task from the list.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_number": {"type": "integer", "description": "The task number to delete"}
                },
                "required": ["task_number"]
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    # Basic Info
    if name == "get_hamza_info":
        return [types.TextContent(type="text", text=HAMZA_INFO)]

    # Add Task
    elif name == "add_task":
        task = {
            "description": arguments["task"],
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        tasks.append(task)
        return [types.TextContent(type="text", text=f"Added task: {arguments['task']}")]

    # Get Tasks
    elif name == "get_tasks":
        if not tasks:
            return [types.TextContent(type="text", text="No tasks yet.")]
        result = "Hamza's Tasks:\n"
        for i, task in enumerate(tasks, 1):
            result += f"{i}. {task['description']} (Added: {task['created']})\n"
        return [types.TextContent(type="text", text=result)]

    # Update Task
    elif name == "update_task":
        num = arguments["task_number"]
        if 1 <= num <= len(tasks):
            tasks[num - 1]["description"] = arguments["new_description"]
            return [types.TextContent(type="text", text=f"Updated task #{num}")]
        return [types.TextContent(type="text", text=f"Task #{num} not found")]

    # Delete Task
    elif name == "delete_task":
        num = arguments["task_number"]
        if 1 <= num <= len(tasks):
            deleted = tasks.pop(num - 1)
            return [types.TextContent(type="text", text=f"Deleted task: {deleted['description']}")]
        return [types.TextContent(type="text", text=f"Task #{num} not found")]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hamza-tasks",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
