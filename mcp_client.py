import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Parameters to launch your specific server
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"], # Ensure this filename matches exactly
)

async def call_mcp_tool(tool_name: str, arguments: dict):
    """Connects to the Robin MCP server and executes a tool."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            
            # List available tools for debugging
            # tools = await session.list_tools()
            
            # Execute the requested tool
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else "No result."

def run_tool_sync(tool_name, arguments):
    """Synchronous wrapper so LangGraph can call it easily."""
    return asyncio.run(call_mcp_tool(tool_name, arguments))