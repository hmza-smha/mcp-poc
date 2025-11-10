"""
HTTP-based MCP Client for Remote Server Connection
Connects to MCP servers running on remote hosts via HTTP/SSE

This version can connect to servers running anywhere on the network.
"""

import asyncio
import json
import sys
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPTestClient:
    def __init__(self):
        self.session = None
        self.exit_stack = None
        
    async def connect(self, server_url: str):
        """
        Connect to a remote MCP server via HTTP/SSE
        
        Args:
            server_url: Base URL of the server (e.g., "http://localhost:8000")
        """
        self.exit_stack = AsyncExitStack()
        
        # Construct SSE endpoint
        sse_url = f"{server_url}/sse"
        
        print(f"Connecting to: {sse_url}")
        
        # Connect to server using SSE transport
        sse_transport = await self.exit_stack.enter_async_context(
            sse_client(sse_url)
        )
        self.read, self.write = sse_transport
        
        # Create session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.read, self.write)
        )
        
        # Initialize connection
        await self.session.initialize()
        
        print("✓ Connected to MCP server successfully!\n")
        
    async def disconnect(self):
        """Disconnect from server"""
        if self.exit_stack:
            await self.exit_stack.aclose()
            print("\n✓ Disconnected from server")
    
    async def list_resources(self):
        """List all available resources"""
        print("\n=== LISTING RESOURCES ===")
        response = await self.session.list_resources()
        
        if not response.resources:
            print("No resources available")
            return
        
        for i, resource in enumerate(response.resources, 1):
            print(f"\n{i}. {resource.name}")
            print(f"   URI: {resource.uri}")
            print(f"   Type: {resource.mimeType}")
            print(f"   Description: {resource.description}")
    
    async def read_resource(self, uri: str):
        """Read a specific resource"""
        print(f"\n=== READING RESOURCE: {uri} ===")
        response = await self.session.read_resource(uri)
        
        for content in response.contents:
            if content.text:
                print("\nContent:")
                try:
                    data = json.loads(content.text)
                    print(json.dumps(data, indent=2))
                except:
                    print(content.text)
    
    async def list_tools(self):
        """List all available tools"""
        print("\n=== LISTING TOOLS ===")
        response = await self.session.list_tools()
        
        if not response.tools:
            print("No tools available")
            return
        
        for i, tool in enumerate(response.tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   Description: {tool.description}")
            print(f"   Input Schema:")
            print(f"   {json.dumps(tool.inputSchema, indent=6)}")
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a specific tool"""
        print(f"\n=== CALLING TOOL: {name} ===")
        print(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        response = await self.session.call_tool(name, arguments)
        
        print("\nResponse:")
        for content in response.content:
            if hasattr(content, 'text'):
                print(content.text)
    
    async def list_prompts(self):
        """List all available prompts"""
        print("\n=== LISTING PROMPTS ===")
        response = await self.session.list_prompts()
        
        if not response.prompts:
            print("No prompts available")
            return
        
        for i, prompt in enumerate(response.prompts, 1):
            print(f"\n{i}. {prompt.name}")
            print(f"   Description: {prompt.description}")
            if prompt.arguments:
                print(f"   Arguments:")
                for arg in prompt.arguments:
                    required = " (required)" if arg.required else " (optional)"
                    desc = arg.description if hasattr(arg, 'description') else 'N/A'
                    print(f"     - {arg.name}{required}: {desc}")
    
    async def get_prompt(self, name: str, arguments: dict = None):
        """Get a specific prompt"""
        print(f"\n=== GETTING PROMPT: {name} ===")
        if arguments:
            print(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        response = await self.session.get_prompt(name, arguments)
        
        print(f"\nDescription: {response.description}")
        print("\nMessages:")
        for i, message in enumerate(response.messages, 1):
            print(f"\n{i}. Role: {message.role}")
            if hasattr(message.content, 'text'):
                print(f"   Content: {message.content.text}")


async def interactive_menu(client: MCPTestClient):
    """Interactive menu for testing MCP features"""
    
    while True:
        print("\n" + "="*60)
        print("MCP TEST CLIENT - MAIN MENU (HTTP/SSE)")
        print("="*60)
        print("RESOURCES:")
        print("  1. List all resources")
        print("  2. Read a resource")
        print("\nTOOLS:")
        print("  3. List all tools")
        print("  4. Call a tool")
        print("\nPROMPTS:")
        print("  5. List all prompts")
        print("  6. Get a prompt")
        print("\nOTHER:")
        print("  7. Quick test - Create a task")
        print("  8. Quick test - View all tasks")
        print("  9. Quick test - Complete workflow")
        print("  0. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice: ").strip()
        
        try:
            if choice == "1":
                await client.list_resources()
                
            elif choice == "2":
                uri = input("Enter resource URI (e.g., task://all): ").strip()
                await client.read_resource(uri)
                
            elif choice == "3":
                await client.list_tools()
                
            elif choice == "4":
                print("\nAvailable tools:")
                print("  - create_task")
                print("  - complete_task")
                print("  - delete_task")
                print("  - search_tasks")
                
                tool_name = input("\nEnter tool name: ").strip()
                print("\nEnter arguments as JSON (e.g., {\"title\": \"My task\"})")
                args_str = input("Arguments: ").strip()
                arguments = json.loads(args_str) if args_str else {}
                
                await client.call_tool(tool_name, arguments)
                
            elif choice == "5":
                await client.list_prompts()
                
            elif choice == "6":
                prompt_name = input("Enter prompt name: ").strip()
                args_str = input("Enter arguments as JSON (or press Enter for none): ").strip()
                arguments = json.loads(args_str) if args_str else None
                
                await client.get_prompt(prompt_name, arguments)
                
            elif choice == "7":
                print("\n--- Quick Test: Create Task ---")
                title = input("Task title: ").strip()
                description = input("Description (optional): ").strip()
                priority = input("Priority (low/medium/high, default=medium): ").strip() or "medium"
                
                args = {"title": title}
                if description:
                    args["description"] = description
                args["priority"] = priority
                
                await client.call_tool("create_task", args)
                
            elif choice == "8":
                print("\n--- Quick Test: View All Tasks ---")
                await client.read_resource("task://all")
                
            elif choice == "9":
                print("\n--- Quick Test: Complete Workflow ---")
                print("This will: create 2 tasks, list them, complete one, search, and view results")
                
                print("\n1. Creating tasks...")
                await client.call_tool("create_task", {
                    "title": "Write documentation",
                    "description": "Complete API documentation",
                    "priority": "high"
                })
                await client.call_tool("create_task", {
                    "title": "Review pull requests",
                    "description": "Review pending PRs",
                    "priority": "medium"
                })
                
                print("\n2. Listing all tasks...")
                await client.read_resource("task://all")
                
                print("\n3. Completing first task...")
                await client.call_tool("complete_task", {"task_id": 1})
                
                print("\n4. Searching for 'documentation'...")
                await client.call_tool("search_tasks", {"keyword": "documentation"})
                
                print("\n5. Final status...")
                await client.read_resource("task://all")
                
            elif choice == "0":
                print("\nExiting...")
                break
                
            else:
                print("\nInvalid choice. Please try again.")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        input("\nPress Enter to continue...")


async def main():
    """Main entry point"""
    print("="*60)
    print("MCP TEST CLIENT (HTTP/SSE)")
    print("Remote server connection tool for MCP servers")
    print("="*60)
    
    # Get server URL from command line or use default
    if len(sys.argv) >= 2:
        server_url = sys.argv[1]
    else:
        print("\nUsage: python mcp_client_http.py <server_url>")
        print("Example: python mcp_client_http.py http://localhost:8000")
        print("\nNo server URL provided. Using default: http://localhost:8000")
        server_url = "http://localhost:8000"
    
    client = MCPTestClient()
    
    try:
        # Connect to server
        print(f"\nConnecting to server: {server_url}")
        await client.connect(server_url)
        
        # Run interactive menu
        await interactive_menu(client)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
