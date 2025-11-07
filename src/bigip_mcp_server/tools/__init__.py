"""fastMCP tool registration."""

from __future__ import annotations

from fastmcp import FastMCP

from ..bigip_client import BigIPClient
from ..config import Settings
from . import irules, logs, virtual_servers


def register_all(mcp: FastMCP, settings: Settings, client: BigIPClient | None = None) -> None:
    """Register every tool bundle with the shared settings object."""

    client = client or BigIPClient(settings)
    irules.register(mcp, settings, client)
    virtual_servers.register(mcp, settings, client)
    logs.register(mcp, settings, client)
