"""Unit tests for the BigIPClient helpers (pure logic only)."""

from __future__ import annotations

import json

import httpx
import pytest

from bigip_mcp_server.bigip_client import BigIPClient
from bigip_mcp_server.config import Settings


def _make_client(transport: httpx.MockTransport) -> BigIPClient:
    settings = Settings(bigip_host="https://bigip.test", bigip_token="fake-token")
    client = BigIPClient(settings)
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url=client.base_url,
        verify=False,
        headers=client._headers(),
    )
    return client


def _settings_with_creds() -> Settings:
    return Settings(
        bigip_host="https://bigip.test",
        bigip_token=None,
        bigip_username="admin",
        bigip_password="secret",
    )


def test_name_normalization_variants() -> None:
    client = BigIPClient(Settings(bigip_host="https://bigip.test", bigip_token="fake"))
    assert client._normalize_name("foo") == "~Common~foo"
    assert client._normalize_name("/Common/bar") == "~Common~bar"
    assert client._normalize_name("~Tenant~Folder~obj") == "~Tenant~Folder~obj"


def test_full_path_variants() -> None:
    client = BigIPClient(Settings(bigip_host="https://bigip.test", bigip_token="fake"))
    assert client._full_path("foo") == "/Common/foo"
    assert client._full_path("~Tenant~Bar") == "/Tenant/Bar"
    assert client._full_path("/Tenant/Folder/Obj") == "/Tenant/Folder/Obj"


@pytest.mark.asyncio
async def test_list_irules_filters_partition() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/mgmt/tm/ltm/rule"
        return httpx.Response(
            200,
            json={
                "items": [
                    {"name": "keep", "partition": "Common", "fullPath": "/Common/keep"},
                    {"name": "skip", "partition": "Other", "fullPath": "/Other/skip"},
                ]
            },
        )

    client = _make_client(httpx.MockTransport(handler))
    try:
        items = await client.list_irules()
        assert [item["name"] for item in items] == ["keep"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_attach_irule_sets_changed_flag() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json={"fullPath": "/Common/vs", "rules": []})
        if request.method == "PATCH":
            assert json.loads(request.content) == {"rules": ["/Common/rule"]}
            return httpx.Response(200, json={"fullPath": "/Common/vs"})
        raise AssertionError("Unexpected method")

    client = _make_client(httpx.MockTransport(handler))
    try:
        result = await client.attach_irule_to_virtual("vs", "rule")
        assert result["changed"] is True
        assert calls == ["GET", "PATCH"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_detach_irule_noop_when_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json={"fullPath": "/Common/vs", "rules": ["/Common/other"]})

    client = _make_client(httpx.MockTransport(handler))
    try:
        result = await client.detach_irule_from_virtual("vs", "rule")
        assert result["changed"] is False
        assert result["rules"] == ["/Common/other"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tail_ltm_builds_safe_command() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)["utilCmdArgs"]
        return httpx.Response(200, json={"commandResult": "line1\nline2\n"})

    client = _make_client(httpx.MockTransport(handler))
    try:
        log_text = await client.tail_ltm_log(lines=20, grep="ERROR")
        assert "line1" in log_text
        payload = captured["body"]
        assert payload.startswith("-c 'tail -n 20 /var/log/ltm")
        assert "grep -F" in payload
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_request_reauths_on_unauthorized() -> None:
    settings = _settings_with_creds()

    tokens = iter(["first-token", "second-token"])

    class ReauthClient(BigIPClient):
        async def _fetch_token(self) -> str:  # type: ignore[override]
            return next(tokens)

    client = ReauthClient(settings)

    transport_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        transport_calls.append(request.headers.get("X-F5-Auth-Token", ""))
        if len(transport_calls) == 1:
            return httpx.Response(401, request=request)
        return httpx.Response(200, json={"result": "ok"})

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=client.base_url,
        verify=False,
    )

    try:
        response = await client.request("GET", "/tm/ltm/rule")
        assert response == {"result": "ok"}
        assert transport_calls == ["first-token", "second-token"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_fetch_token_hits_login_endpoint() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"token": {"token": "minty"}})

    settings = _settings_with_creds()
    client = BigIPClient(settings, auth_transport=httpx.MockTransport(handler))

    token = await client._fetch_token()
    assert token == "minty"
    assert captured["path"] == "/mgmt/shared/authn/login"
    assert captured["body"]["loginProviderName"] == "tmos"


@pytest.mark.asyncio
async def test_request_handles_empty_json_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "application/json"}, text="")

    client = _make_client(httpx.MockTransport(handler))
    try:
        result = await client.request("DELETE", "/tm/ltm/rule/foo")
        assert result is None
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_request_falls_back_to_text_on_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "application/json"}, text="not-json")

    client = _make_client(httpx.MockTransport(handler))
    try:
        result = await client.request("GET", "/tm/ltm/rule")
        assert result == "not-json"
    finally:
        await client.close()
