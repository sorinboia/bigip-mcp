"""Virtual server tooling for binding/unbinding iRules."""

from __future__ import annotations

from fastmcp import FastMCP
import httpx

from ..bigip_client import BigIPClient
from ..config import Settings


def register(mcp: FastMCP, settings: Settings, client: BigIPClient) -> None:
    async def _call(func, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as exc:  # pragma: no cover
            detail = exc.response.text.strip()
            message = (
                f"BIG-IP returned {exc.response.status_code} {exc.response.reason_phrase}: {detail or 'no body'}"
            )
            raise RuntimeError(message) from exc

    def _display_virtual(name: str, partition: str | None = None) -> str:
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
        name="virtuals_list",
        description="List LTM virtual servers in the configured partition (GET /mgmt/tm/ltm/virtual).",
    )
    async def list_virtuals(select_fields: str | None = None) -> dict:
        fields = _parse_fields(select_fields)
        items = await _call(client.list_virtuals, fields=fields)
        return {
            "partition": settings.bigip_partition,
            "count": len(items),
            "items": items,
        }

    @mcp.tool(
        name="virtuals_attach_irule",
        description="Attach an iRule to a virtual server (PATCH /mgmt/tm/ltm/virtual/<name>).",
    )
    async def attach_irule(
        virtual_name: str,
        rule_name: str,
        virtual_partition: str | None = None,
        rule_partition: str | None = None,
    ) -> dict:
        response = await _call(
            client.attach_irule_to_virtual,
            virtual_name,
            rule_name,
            virtual_partition=virtual_partition,
            rule_partition=rule_partition,
        )
        return {
            "virtual": response.get("virtual", _display_virtual(virtual_name, virtual_partition)),
            "rules": response.get("rules", []),
            "changed": response.get("changed", False),
        }

    @mcp.tool(
        name="virtuals_detach_irule",
        description="Detach an iRule from a virtual server (PATCH /mgmt/tm/ltm/virtual/<name>).",
    )
    async def detach_irule(
        virtual_name: str,
        rule_name: str,
        virtual_partition: str | None = None,
        rule_partition: str | None = None,
    ) -> dict:
        response = await _call(
            client.detach_irule_from_virtual,
            virtual_name,
            rule_name,
            virtual_partition=virtual_partition,
            rule_partition=rule_partition,
        )
        return {
            "virtual": response.get("virtual", _display_virtual(virtual_name, virtual_partition)),
            "rules": response.get("rules", []),
            "changed": response.get("changed", False),
        }
