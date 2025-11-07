"""Async helper around BIG-IP iControl REST APIs."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import quote

import httpx

from .config import Settings

MAX_TAIL_LINES = 1000
AUTH_RETRY_CODES = {401, 403}


@dataclass(slots=True)
class BigIPClient:
    """Thin async wrapper for iControl REST requests."""

    settings: Settings
    timeout: float = 30.0
    transport: httpx.BaseTransport | None = None
    auth_transport: httpx.BaseTransport | None = None
    _client: httpx.AsyncClient | None = None
    _token: str | None = None

    def __post_init__(self) -> None:
        self._token = self.settings.bigip_token

    @property
    def base_url(self) -> str:
        return f"{self.settings.bigip_host}/mgmt"

    def _headers(self, token: str | None = None) -> Mapping[str, str]:
        token = token or self._token
        if not token:
            raise RuntimeError("BIG-IP authentication token is not available")
        return {
            "X-F5-Auth-Token": token,
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = self._build_main_client()
        return self._client

    def _build_main_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            verify=self.settings.bigip_verify_ssl,
            timeout=self.timeout,
            transport=self.transport,
        )

    def _build_auth_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.bigip_host,
            verify=self.settings.bigip_verify_ssl,
            timeout=self.timeout,
            transport=self.auth_transport or self.transport,
        )

    async def _ensure_token(self, *, force_refresh: bool = False) -> str:
        if force_refresh:
            self._token = None
        if self._token:
            return self._token
        if self.settings.bigip_token and not force_refresh:
            self._token = self.settings.bigip_token
            return self._token
        if self._can_refresh_token():
            self._token = await self._fetch_token()
            return self._token
        raise RuntimeError("Missing BIG-IP authentication token and no credentials available to obtain one")

    def _can_refresh_token(self) -> bool:
        return bool(self.settings.bigip_username and self.settings.bigip_password)

    async def _fetch_token(self) -> str:
        username = self.settings.bigip_username
        password = self.settings.bigip_password
        if not username or not password:
            raise RuntimeError(
                "BIG-IP credentials are not configured; cannot request authentication token"
            )

        payload = {
            "username": username,
            "password": password,
            "loginProviderName": self.settings.bigip_login_provider,
        }
        client = self._build_auth_client()
        try:
            response = await client.post("/mgmt/shared/authn/login", json=payload)
            response.raise_for_status()
            data = response.json()
        finally:
            await client.aclose()

        token = None
        if isinstance(data, Mapping):
            token = data.get("token", {}).get("token")
        if not token:
            raise RuntimeError("BIG-IP login response did not include a token")
        return token

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> Any:
        client = await self._ensure_client()
        token = await self._ensure_token()
        headers = self._headers(token)
        response = await client.request(method, path, params=params, json=json, headers=headers)

        if response.status_code in AUTH_RETRY_CODES and self._can_refresh_token():
            token = await self._ensure_token(force_refresh=True)
            headers = self._headers(token)
            response = await client.request(method, path, params=params, json=json, headers=headers)

        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            if not response.content.strip():
                return None
            try:
                return response.json()
            except ValueError:
                # Some endpoints claim JSON but return plain text (e.g., DELETE without body).
                return response.text
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

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_name(self, name: str, partition: str | None = None) -> str:
        """Convert a user-specified name into F5's ~Partition~Name format."""

        if not name:
            raise ValueError("Object name must be non-empty")
        if name.startswith("~"):
            return name
        if name.startswith("/"):
            segments = [segment for segment in name.split("/") if segment]
        else:
            partition = partition or self.settings.bigip_partition
            segments = [partition, name]
        return "~" + "~".join(segments)

    def _full_path(self, name: str, partition: str | None = None) -> str:
        """Return /Partition/Name form."""

        if name.startswith("/"):
            return name
        if name.startswith("~"):
            segments = [segment for segment in name.split("~") if segment]
            return "/" + "/".join(segments)
        partition = partition or self.settings.bigip_partition
        return f"/{partition}/{name}"

    def _ltm_path(self, resource: str, *, name: str | None = None, partition: str | None = None) -> str:
        path = f"/tm/ltm/{resource}"
        if name:
            normalized = self._normalize_name(name, partition)
            path = f"{path}/{quote(normalized, safe='~')}"
        return path

    @staticmethod
    def _filter_partition(items: Sequence[Mapping[str, Any]], partition: str) -> list[Mapping[str, Any]]:
        prefix = f"/{partition}/"
        return [
            item
            for item in items
            if item.get("partition") == partition or str(item.get("fullPath", "")).startswith(prefix)
        ]

    @staticmethod
    def _dedupe_fields(fields: Sequence[str] | None) -> list[str]:
        deduped: list[str] = []
        if not fields:
            return deduped
        for field in fields:
            if not field:
                continue
            cleaned = field.strip()
            if cleaned and cleaned not in deduped:
                deduped.append(cleaned)
        return deduped

    @staticmethod
    def _normalize_pool_members(members: Sequence[str | Mapping[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for member in members:
            if isinstance(member, str):
                if not member.strip():
                    raise ValueError("Pool member strings must be non-empty")
                normalized.append({"name": member})
            elif isinstance(member, Mapping):
                if "name" not in member or not str(member["name"]).strip():
                    raise ValueError("Pool member mappings must include a non-empty 'name' key")
                normalized.append(dict(member))
            else:  # pragma: no cover - defensive type guard
                raise TypeError("Pool members must be strings or mappings")
        return normalized

    # ------------------------------------------------------------------ #
    # iRules
    # ------------------------------------------------------------------ #
    async def list_irules(self, include_definition: bool = False) -> list[dict[str, Any]]:
        fields = ["name", "fullPath", "partition", "generation"]
        if include_definition:
            fields.append("apiAnonymous")
        params = {"$select": ",".join(fields)}

        response = await self.request("GET", self._ltm_path("rule"), params=params)
        raw_items: Sequence[Mapping[str, Any]]
        if isinstance(response, Mapping):
            maybe_items = response.get("items", [])
            raw_items = maybe_items if isinstance(maybe_items, Sequence) else []
        elif isinstance(response, Sequence):
            raw_items = response
        else:
            raw_items = []

        filtered = self._filter_partition(raw_items, self.settings.bigip_partition)
        if not include_definition:
            for entry in filtered:
                entry.pop("apiAnonymous", None)
        return list(filtered)

    async def create_irule(
        self,
        name: str,
        definition: str,
        *,
        partition: str | None = None,
    ) -> Any:
        payload = {
            "name": name,
            "partition": partition or self.settings.bigip_partition,
            "apiAnonymous": definition,
        }
        return await self.request("POST", self._ltm_path("rule"), json=payload)

    async def update_irule(
        self,
        name: str,
        definition: str,
        *,
        partition: str | None = None,
    ) -> Any:
        payload = {"apiAnonymous": definition}
        return await self.request(
            "PATCH",
            self._ltm_path("rule", name=name, partition=partition),
            json=payload,
        )

    async def delete_irule(self, name: str, *, partition: str | None = None) -> Any:
        return await self.request("DELETE", self._ltm_path("rule", name=name, partition=partition))

    # ------------------------------------------------------------------ #
    # Virtual servers
    # ------------------------------------------------------------------ #
    async def list_virtuals(self, fields: Sequence[str] | None = None) -> list[dict[str, Any]]:
        params = None
        selected = self._dedupe_fields(fields)
        if selected:
            params = {"$select": ",".join(selected)}

        response = await self.request("GET", self._ltm_path("virtual"), params=params)
        raw_items: Sequence[Mapping[str, Any]]
        if isinstance(response, Mapping):
            maybe_items = response.get("items", [])
            raw_items = maybe_items if isinstance(maybe_items, Sequence) else []
        elif isinstance(response, Sequence):
            raw_items = response
        else:
            raw_items = []

        filtered = self._filter_partition(raw_items, self.settings.bigip_partition)
        return list(filtered)

    async def _get_virtual(self, virtual_name: str, *, partition: str | None = None) -> Mapping[str, Any]:
        path = self._ltm_path("virtual", name=virtual_name, partition=partition)
        response = await self.request("GET", path)
        if isinstance(response, Mapping):
            return response
        raise RuntimeError(f"Unexpected virtual server response type: {type(response)!r}")

    async def attach_irule_to_virtual(
        self,
        virtual_name: str,
        rule_name: str,
        *,
        virtual_partition: str | None = None,
        rule_partition: str | None = None,
    ) -> dict[str, Any]:
        virtual_path = self._ltm_path("virtual", name=virtual_name, partition=virtual_partition)
        current = await self._get_virtual(virtual_name, partition=virtual_partition)
        rules = list(current.get("rules") or [])
        full_rule = self._full_path(rule_name, partition=rule_partition)
        changed = False
        if full_rule not in rules:
            rules.append(full_rule)
            await self.request("PATCH", virtual_path, json={"rules": rules})
            changed = True
        return {
            "virtual": current.get("fullPath", virtual_name),
            "rules": rules,
            "changed": changed,
        }

    async def detach_irule_from_virtual(
        self,
        virtual_name: str,
        rule_name: str,
        *,
        virtual_partition: str | None = None,
        rule_partition: str | None = None,
    ) -> dict[str, Any]:
        virtual_path = self._ltm_path("virtual", name=virtual_name, partition=virtual_partition)
        current = await self._get_virtual(virtual_name, partition=virtual_partition)
        rules = list(current.get("rules") or [])
        full_rule = self._full_path(rule_name, partition=rule_partition)
        new_rules = [rule for rule in rules if rule != full_rule]
        changed = new_rules != rules
        if changed:
            await self.request("PATCH", virtual_path, json={"rules": new_rules})
        return {
            "virtual": current.get("fullPath", virtual_name),
            "rules": new_rules,
            "changed": changed,
        }

    # ------------------------------------------------------------------ #
    # Pools
    # ------------------------------------------------------------------ #
    async def list_pools(self, fields: Sequence[str] | None = None) -> list[dict[str, Any]]:
        params = None
        selected = self._dedupe_fields(fields)
        if selected:
            params = {"$select": ",".join(selected)}

        response = await self.request("GET", self._ltm_path("pool"), params=params)
        raw_items: Sequence[Mapping[str, Any]]
        if isinstance(response, Mapping):
            maybe_items = response.get("items", [])
            raw_items = maybe_items if isinstance(maybe_items, Sequence) else []
        elif isinstance(response, Sequence):
            raw_items = response
        else:
            raw_items = []

        filtered = self._filter_partition(raw_items, self.settings.bigip_partition)
        return list(filtered)

    async def create_pool(
        self,
        name: str,
        *,
        partition: str | None = None,
        load_balancing_mode: str | None = None,
        monitor: str | None = None,
        description: str | None = None,
        members: Sequence[str | Mapping[str, Any]] | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "partition": partition or self.settings.bigip_partition,
        }
        if load_balancing_mode:
            payload["loadBalancingMode"] = load_balancing_mode
        if monitor is not None:
            payload["monitor"] = monitor
        if description is not None:
            payload["description"] = description
        if members is not None:
            payload["members"] = self._normalize_pool_members(members)

        return await self.request("POST", self._ltm_path("pool"), json=payload)

    async def modify_pool(
        self,
        name: str,
        *,
        partition: str | None = None,
        load_balancing_mode: str | None = None,
        monitor: str | None = None,
        description: str | None = None,
        members: Sequence[str | Mapping[str, Any]] | None = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {}
        if load_balancing_mode:
            payload["loadBalancingMode"] = load_balancing_mode
        if monitor is not None:
            payload["monitor"] = monitor
        if description is not None:
            payload["description"] = description
        if members is not None:
            payload["members"] = self._normalize_pool_members(members)

        if not payload:
            raise ValueError("At least one field must be provided to modify a pool")

        path = self._ltm_path("pool", name=name, partition=partition)
        return await self.request("PATCH", path, json=payload)

    # ------------------------------------------------------------------ #
    # Logs
    # ------------------------------------------------------------------ #
    async def tail_ltm_log(self, *, lines: int = 100, grep: str | None = None) -> str:
        lines = max(1, min(lines, MAX_TAIL_LINES))
        if grep and len(grep) > 200:
            raise ValueError("Filter string is too long")

        command = f"tail -n {lines} /var/log/ltm"
        if grep:
            command += f" | grep -F {shlex.quote(grep)}"
        payload = {"command": "run", "utilCmdArgs": f"-c {shlex.quote(command)}"}
        response = await self.request("POST", "/tm/util/bash", json=payload)
        if isinstance(response, Mapping):
            return str(response.get("commandResult", "")).strip()
        return str(response).strip()
