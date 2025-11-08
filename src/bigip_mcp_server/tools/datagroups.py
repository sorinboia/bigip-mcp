"""Data group fastMCP tools."""

from __future__ import annotations

from typing import Any, Mapping

from fastmcp import FastMCP
import httpx

from ..bigip_client import BigIPClient
from ..config import Settings


def register(mcp: FastMCP, settings: Settings, client: BigIPClient) -> None:
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
        name="datagroups_list",
        description="List internal data groups in the configured partition (GET /mgmt/tm/ltm/data-group/internal).",
    )
    async def list_data_groups(include_records: bool = False) -> dict:
        items = await _call(client.list_data_groups, include_records=include_records)
        return {
            "partition": settings.bigip_partition,
            "count": len(items),
            "items": items,
        }

    @mcp.tool(
        name="datagroups_create",
        description="Create an internal data group via POST /mgmt/tm/ltm/data-group/internal.",
    )
    async def create_data_group(
        name: str,
        type: str,
        partition: str | None = None,
        description: str | None = None,
        records: list[Mapping[str, Any]] | list[str] | None = None,
    ) -> dict:
        response = await _call(
            client.create_data_group,
            name,
            type=type,
            partition=partition,
            description=description,
            records=records,
        )
        partition = partition or settings.bigip_partition
        return {
            "status": "created",
            "data_group": response.get("fullPath", _display_path(name, partition)),
            "generation": response.get("generation"),
        }

    @mcp.tool(
        name="datagroups_update",
        description="Update an internal data group via PATCH /mgmt/tm/ltm/data-group/internal/<name>.",
    )
    async def update_data_group(
        name: str,
        partition: str | None = None,
        type: str | None = None,
        description: str | None = None,
        records: list[Mapping[str, Any]] | list[str] | None = None,
    ) -> dict:
        response = await _call(
            client.update_data_group,
            name,
            partition=partition,
            type=type,
            description=description,
            records=records,
        )
        partition = partition or settings.bigip_partition
        return {
            "status": "updated",
            "data_group": response.get("fullPath", _display_path(name, partition)),
            "generation": response.get("generation"),
        }

    @mcp.tool(
        name="datagroups_delete",
        description="Delete an internal data group via DELETE /mgmt/tm/ltm/data-group/internal/<name>.",
    )
    async def delete_data_group(name: str, partition: str | None = None) -> dict:
        await _call(client.delete_data_group, name, partition=partition)
        return {
            "status": "deleted",
            "data_group": _display_path(name, partition),
        }
