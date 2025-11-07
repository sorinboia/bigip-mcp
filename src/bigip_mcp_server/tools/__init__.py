"""fastMCP tool registration."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import Settings
from . import irules, logs, virtual_servers


def register_all(mcp: FastMCP, settings: Settings) -> None:
    """Register every tool bundle with the shared settings object."""

    irules.register(mcp, settings)
    virtual_servers.register(mcp, settings)
    logs.register(mcp, settings)
