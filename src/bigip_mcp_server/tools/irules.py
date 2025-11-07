"""iRule-related fastMCP tools."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import Settings


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register iRule tools (placeholder)."""

    @mcp.tool(name="irules.list", description="List available iRules (scaffolding placeholder)")
    async def list_irules() -> str:
        return "Not implemented yet: will call /mgmt/tm/ltm/rule"

    @mcp.tool(name="irules.create", description="Create a new iRule (scaffolding placeholder)")
    async def create_irule(name: str, definition: str) -> str:
        return f"Pending implementation for iRule {name}"

    @mcp.tool(name="irules.delete", description="Delete an iRule (scaffolding placeholder)")
    async def delete_irule(name: str) -> str:
        return f"Pending implementation for deleting {name}"

    @mcp.tool(name="irules.update", description="Update an iRule (scaffolding placeholder)")
    async def update_irule(name: str, definition: str) -> str:
        return f"Pending implementation for updating {name}"
