# mcp_client.py
import sys
import os
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")


def get_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=dict(os.environ),
    )


async def execute_tool_via_mcp(tool_name: str, arguments: dict) -> str:
    """Execute a single tool on the FastMCP server and return the text result."""
    server_params = get_server_params()
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            if result.content:
                return result.content[0].text
            return "No content returned from MCP server."


def execute_tool_via_mcp_sync(tool_name: str, arguments: dict) -> str:
    """Synchronous wrapper for execute_tool_via_mcp."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If running inside an event loop (e.g. FastAPI / LangGraph async thread)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, execute_tool_via_mcp(tool_name, arguments))
            return future.result()
    else:
        return asyncio.run(execute_tool_via_mcp(tool_name, arguments))


async def main():
    server_params = get_server_params()

    print(f"Connecting to MCP Server at: {SERVER_SCRIPT}...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover all available tools from the server
            tools_response = await session.list_tools()
            print("\n=== Registered MCP Tools ===")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description.strip().splitlines()[0]}")

            # Example 1: Execute Calculator Tool
            print("\n--- Testing Calculator Tool via MCP ---")
            calc_result = await session.call_tool("calculate", arguments={"expression": "3x + 15 = 45"})
            print("Output:", calc_result.content[0].text)

            # Example 2: Execute Weather Tool
            print("\n--- Testing Weather Tool via MCP ---")
            weather_result = await session.call_tool("fetch_weather", arguments={"location": "Goa and Maredumilli"})
            print("Output:", weather_result.content[0].text)

            # Example 3: Execute Search Tool
            print("\n--- Testing Search Tool via MCP ---")
            search_result = await session.call_tool("google_search", arguments={"query": "latest news on AI"})
            print("Output:", search_result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
