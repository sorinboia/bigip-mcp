"""Integration test that drives the MCP server via fastmcp.Client."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport

from .support.fake_bigip import FakeBigIPServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def fake_bigip() -> FakeBigIPServer:
    server = FakeBigIPServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


async def _call_tool(client: Client, tool_name: str, **arguments: Any) -> Any:
    args = {key: value for key, value in arguments.items() if value is not None}
    response = await client.call_tool(tool_name, args or None)
    if response.data is not None:
        return response.data
    if response.structured_content:
        return response.structured_content
    if response.content:
        blocks = []
        for block in response.content:
            if hasattr(block, "text"):
                blocks.append(getattr(block, "text"))
            else:
                blocks.append(str(block))
        return blocks[0] if len(blocks) == 1 else blocks
    return None


@pytest.mark.asyncio
async def test_pool_flow_via_mcp_client(fake_bigip: FakeBigIPServer) -> None:
    env = os.environ.copy()
    env.update(
        {
            "BIGIP_HOST": fake_bigip.url,
            "BIGIP_TOKEN": "test-token",
            "BIGIP_PARTITION": "Common",
            "BIGIP_VERIFY_SSL": "0",
        }
    )

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "bigip_mcp_server"],
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    pool_name = f"pytest_pool_{int(time.time())}"
    members_initial = ["10.0.0.1:80"]
    members_updated = [{"name": "10.0.0.2:80", "ratio": 2}]

    client = Client(transport, name="pytest-mcp-client")
    async with client:
        await client.list_tools()

        virtuals = await _call_tool(client, "virtuals_list")
        assert virtuals["count"] >= 1

        pools_before = await _call_tool(client, "pools_list")
        assert isinstance(pools_before["items"], list)

        created = await _call_tool(
            client,
            "pools_create",
            name=pool_name,
            members=members_initial,
        )
        assert created["status"] == "created"
        assert created["pool"].endswith(pool_name)

        modified = await _call_tool(
            client,
            "pools_modify",
            name=pool_name,
            description="updated via test",
            members=members_updated,
        )
        assert modified["status"] == "modified"
        assert modified["pool"].endswith(pool_name)

        pools_after = await _call_tool(client, "pools_list")
        names = [item.get("name") for item in pools_after["items"]]
        assert pool_name in names
