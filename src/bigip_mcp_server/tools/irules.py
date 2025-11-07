"""iRule-related fastMCP tools."""

from __future__ import annotations

from fastmcp import FastMCP
import httpx

from ..bigip_client import BigIPClient
from ..config import Settings


def register(mcp: FastMCP, settings: Settings, client: BigIPClient) -> None:
    """Register iRule tools backed by /mgmt/tm/ltm/rule."""

    async def _call(func, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as exc:  # pragma: no cover - passthrough wrapper
            detail = exc.response.text.strip()
            message = (
                f"BIG-IP returned {exc.response.status_code} {exc.response.reason_phrase}: {detail or 'no body'}"
            )
            raise RuntimeError(message) from exc

    def _display_path(name: str, partition: str | None = None) -> str:
        if name.startswith("/"):
            return name
        if name.startswith("~"):
            parts = [segment for segment in name.split("~") if segment]
            return "/" + "/".join(parts)
        partition = partition or settings.bigip_partition
        return f"/{partition}/{name}"

    @mcp.tool(
        name="irules_list",
        description="List iRules in the configured partition (GET /mgmt/tm/ltm/rule).",
    )
    async def list_irules(include_definition: bool = False) -> dict:
        """Return metadata for the partition's iRules."""

        items = await _call(client.list_irules, include_definition=include_definition)
        return {
            "partition": settings.bigip_partition,
            "count": len(items),
            "items": items,
        }

    @mcp.tool(
        name="irules_create",
        description="Create a new iRule via POST /mgmt/tm/ltm/rule.",
    )
    async def create_irule(name: str, definition: str, partition: str | None = None) -> dict:
        """Create an iRule; definition should be raw TCL."""

        response = await _call(client.create_irule, name, definition, partition=partition)
        partition = partition or settings.bigip_partition
        return {
            "status": "created",
            "rule": response.get("fullPath", _display_path(name, partition)),
            "generation": response.get("generation"),
        }

    @mcp.tool(
        name="irules_update",
        description="Replace an iRule definition via PATCH /mgmt/tm/ltm/rule/<name>.",
    )
    async def update_irule(name: str, definition: str, partition: str | None = None) -> dict:
        response = await _call(client.update_irule, name, definition, partition=partition)
        partition = partition or settings.bigip_partition
        return {
            "status": "updated",
            "rule": response.get("fullPath", _display_path(name, partition)),
            "generation": response.get("generation"),
        }

    @mcp.tool(
        name="irules_delete",
        description="Delete an iRule via DELETE /mgmt/tm/ltm/rule/<name>.",
    )
    async def delete_irule(name: str, partition: str | None = None) -> dict:
        await _call(client.delete_irule, name, partition=partition)
        return {
            "status": "deleted",
            "rule": _display_path(name, partition),
        }
