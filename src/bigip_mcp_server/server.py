"""fastMCP server factory."""

from __future__ import annotations

from fastmcp import FastMCP

from .bigip_client import BigIPClient
from .config import Settings
from .tools import register_all


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or Settings.from_env()
    mcp = FastMCP(name="bigip-mcp-server")
    client = BigIPClient(settings)

    @mcp.tool(name="server_info", description="Show server configuration context")
    def server_info() -> dict:
        return {
            "bigip_host": settings.bigip_host,
            "partition": settings.bigip_partition,
            "verify_ssl": settings.bigip_verify_ssl,
        }

    register_all(mcp, settings, client)
    return mcp
