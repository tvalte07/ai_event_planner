"""Example MCP client: discover server tools and invoke one over MCP."""

import asyncio
from fastmcp import Client
from app.mcp.server import mcp


async def discover_and_call() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Discovered tools:", ", ".join(tool.name for tool in tools))
        result = await client.call_tool("calculate_event_budget", {"total_budget": 30000})
        print("Budget tool result:", result.structured_content or result.content)


if __name__ == "__main__":
    asyncio.run(discover_and_call())
