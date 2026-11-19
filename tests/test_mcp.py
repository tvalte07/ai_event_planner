import asyncio

import pytest


def test_fastmcp_client_discovers_and_invokes_budget_tool():
    pytest.importorskip("fastmcp")
    from fastmcp import Client
    from app.mcp.server import mcp

    async def check():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools}
            assert {"calculate_event_budget", "generate_event_schedule", "manage_guest_list", "get_event_details", "search_event_documents"} <= names
            result = await client.call_tool("calculate_event_budget", {"total_budget": 30000})
            return result.structured_content

    result = asyncio.run(check())
    assert result["total"] == 30000
    assert result["illustrative"] is True
