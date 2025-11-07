"""Virtual server tooling (placeholder)."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import Settings


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="virtuals.attach_irule",
        description="Attach an iRule to a virtual server (scaffolding placeholder)",
    )
    async def attach_irule(virtual_name: str, rule_name: str) -> str:
        return f"Pending implementation for attaching {rule_name} to {virtual_name}"

    @mcp.tool(
        name="virtuals.detach_irule",
        description="Detach an iRule from a virtual server (scaffolding placeholder)",
    )
    async def detach_irule(virtual_name: str, rule_name: str) -> str:
        return f"Pending implementation for detaching {rule_name} from {virtual_name}"
