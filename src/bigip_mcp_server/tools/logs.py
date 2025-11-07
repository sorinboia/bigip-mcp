"""Log access tools (placeholder)."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import Settings


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(name="logs.tail_ltm", description="Tail /var/log/ltm (scaffolding placeholder)")
    async def tail_ltm(lines: int = 100, contains: str | None = None) -> str:
        filter_msg = f" filtered by '{contains}'" if contains else ""
        return f"Pending implementation: tail {lines} lines{filter_msg} via /mgmt/tm/util/bash"
