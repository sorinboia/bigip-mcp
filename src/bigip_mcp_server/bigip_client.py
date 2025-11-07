"""Async helper around BIG-IP iControl REST APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from .config import Settings


@dataclass(slots=True)
class BigIPClient:
    """Thin async wrapper for iControl REST requests."""

    settings: Settings
    timeout: float = 30.0
    _client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        return f"{self.settings.bigip_host}/mgmt"

    def _headers(self) -> Mapping[str, str]:
        return {
            "X-F5-Auth-Token": self.settings.bigip_token,
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                verify=self.settings.bigip_verify_ssl,
                timeout=self.timeout,
                headers=self._headers(),
            )
        return self._client

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> Any:
        client = await self._ensure_client()
        response = await client.request(method, path, params=params, json=json)
        response.raise_for_status()
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "BigIPClient":  # pragma: no cover - context sugar
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc_info: object) -> None:  # pragma: no cover
        await self.close()

    # --- iRules -----------------------------------------------------------
    async def create_irule(self, name: str, definition: str) -> Any:
        """Placeholder for future iRule creation."""

        raise NotImplementedError

    async def update_irule(self, name: str, definition: str) -> Any:
        raise NotImplementedError

    async def delete_irule(self, name: str) -> Any:
        raise NotImplementedError

    async def list_irules(self) -> Any:
        raise NotImplementedError

    # --- Virtual servers --------------------------------------------------
    async def attach_irule_to_virtual(self, virtual_name: str, rule_name: str) -> Any:
        raise NotImplementedError

    async def detach_irule_from_virtual(self, virtual_name: str, rule_name: str) -> Any:
        raise NotImplementedError

    # --- Logs -------------------------------------------------------------
    async def tail_ltm_log(self, *, lines: int = 100, grep: str | None = None) -> str:
        raise NotImplementedError
