"""Log access tools built on /mgmt/tm/util/bash."""

from __future__ import annotations

from fastmcp import FastMCP
import httpx
from typing import TYPE_CHECKING

from ..bigip_client import MAX_TAIL_LINES, BigIPClient


if TYPE_CHECKING:  # pragma: no cover - hints only
    from ..config import Settings


def register(mcp: FastMCP, settings: "Settings", client: BigIPClient) -> None:
    async def _call(func, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as exc:  # pragma: no cover
            detail = exc.response.text.strip()
            message = (
                f"BIG-IP returned {exc.response.status_code} {exc.response.reason_phrase}: {detail or 'no body'}"
            )
            raise RuntimeError(message) from exc

    @mcp.tool(
        name="logs_tail_ltm",
        description="Tail /var/log/ltm with optional substring filtering (POST /mgmt/tm/util/bash).",
    )
    async def tail_ltm(lines: int = 100, contains: str | None = None) -> dict:
        if lines < 1:
            raise ValueError("lines must be >= 1")
        if lines > MAX_TAIL_LINES:
            raise ValueError(f"lines must be <= {MAX_TAIL_LINES}")

        log_text = await _call(client.tail_ltm_log, lines=lines, grep=contains)
        return {
            "lines": lines,
            "filter": contains,
            "log": log_text,
        }
