"""Pool management tools exposed via fastMCP."""

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

    def _display_pool(name: str, partition: str | None = None) -> str:
        if name.startswith("/"):
            return name
        if name.startswith("~"):
            parts = [segment for segment in name.split("~") if segment]
            return "/" + "/".join(parts)
        partition = partition or settings.bigip_partition
        return f"/{partition}/{name}"

    def _parse_fields(select_fields: str | None) -> list[str] | None:
        if not select_fields:
            return None
        values = [field.strip() for field in select_fields.split(",") if field.strip()]
        return values or None

    @mcp.tool(
        name="pools_list",
        description="List LTM pools in the configured partition (GET /mgmt/tm/ltm/pool).",
    )
    async def list_pools(select_fields: str | None = None) -> dict:
        fields = _parse_fields(select_fields)
        items = await _call(client.list_pools, fields=fields)
        return {
            "partition": settings.bigip_partition,
            "count": len(items),
            "items": items,
        }

    @mcp.tool(
        name="pools_create",
        description="Create an LTM pool via POST /mgmt/tm/ltm/pool.",
    )
    async def create_pool(
        name: str,
        partition: str | None = None,
        load_balancing_mode: str | None = None,
        monitor: str | None = None,
        description: str | None = None,
        members: list[Mapping[str, Any]] | list[str] | None = None,
    ) -> dict:
        response = await _call(
            client.create_pool,
            name,
            partition=partition,
            load_balancing_mode=load_balancing_mode,
            monitor=monitor,
            description=description,
            members=members,
        )
        partition = partition or settings.bigip_partition
        return {
            "status": "created",
            "pool": response.get("fullPath", _display_pool(name, partition)),
            "generation": response.get("generation"),
        }

    @mcp.tool(
        name="pools_modify",
        description="Modify an LTM pool via PATCH /mgmt/tm/ltm/pool/<name> (full member replacement).",
    )
    async def modify_pool(
        name: str,
        partition: str | None = None,
        load_balancing_mode: str | None = None,
        monitor: str | None = None,
        description: str | None = None,
        members: list[Mapping[str, Any]] | list[str] | None = None,
    ) -> dict:
        response = await _call(
            client.modify_pool,
            name,
            partition=partition,
            load_balancing_mode=load_balancing_mode,
            monitor=monitor,
            description=description,
            members=members,
        )
        partition = partition or settings.bigip_partition
        return {
            "status": "modified",
            "pool": response.get("fullPath", _display_pool(name, partition)),
            "generation": response.get("generation"),
        }
