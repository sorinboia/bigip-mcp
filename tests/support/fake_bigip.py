"""Minimal HTTP stub that emulates the BIG-IP REST endpoints used in tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


class _State:
    def __init__(self) -> None:
        self.rules: dict[str, dict[str, Any]] = {}
        self.pools: dict[str, dict[str, Any]] = {}
        self.data_groups: dict[str, dict[str, Any]] = {}
        self.virtuals: dict[str, dict[str, Any]] = {
            "/Common/TestVs": {
                "name": "TestVs",
                "partition": "Common",
                "fullPath": "/Common/TestVs",
                "destination": "0.0.0.0:0",
                "rules": [],
            }
        }
        self._generation = 1

    def next_generation(self) -> int:
        self._generation += 1
        return self._generation


class FakeBigIPRequestHandler(BaseHTTPRequestHandler):
    server: "FakeBigIPServer"  # type: ignore[assignment]

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_empty_json(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _not_found(self) -> None:
        self.send_response(404)
        self.end_headers()

    def _parse(self) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    @staticmethod
    def _decode_name(component: str) -> str:
        component = unquote(component)
        if component.startswith("~"):
            parts = [part for part in component.split("~") if part]
            return "/" + "/".join(parts)
        return component

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence test noise
        return

    # -------------------------- HTTP verbs -------------------------- #
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path, _ = self._parse()
        if path == "/mgmt/tm/ltm/rule":
            items = list(self.server.state.rules.values())
            self._send_json({"items": items})
            return
        if path == "/mgmt/tm/ltm/virtual":
            items = list(self.server.state.virtuals.values())
            self._send_json({"items": items})
            return
        if path == "/mgmt/tm/ltm/pool":
            items = list(self.server.state.pools.values())
            self._send_json({"items": items})
            return
        if path == "/mgmt/tm/ltm/data-group/internal":
            items = list(self.server.state.data_groups.values())
            self._send_json({"items": items})
            return

        if path.startswith("/mgmt/tm/ltm/virtual/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            virtual = self.server.state.virtuals.get(identifier)
            if virtual:
                self._send_json(virtual)
                return
            self._not_found()
            return

        if path.startswith("/mgmt/tm/ltm/data-group/internal/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            data_group = self.server.state.data_groups.get(identifier)
            if data_group:
                self._send_json(data_group)
                return
            self._not_found()
            return

        self._not_found()

    def do_POST(self) -> None:  # noqa: N802
        path, _ = self._parse()
        if path == "/mgmt/tm/ltm/rule":
            body = self._json_body()
            name = body.get("name", "rule")
            partition = body.get("partition", "Common")
            full_path = f"/{partition}/{name}"
            rule = {
                "name": name,
                "partition": partition,
                "fullPath": full_path,
                "apiAnonymous": body.get("apiAnonymous", ""),
                "generation": self.server.state.next_generation(),
            }
            self.server.state.rules[full_path] = rule
            self._send_json(rule, status=200)
            return

        if path == "/mgmt/tm/ltm/pool":
            body = self._json_body()
            name = body.get("name", "pool")
            partition = body.get("partition", "Common")
            full_path = f"/{partition}/{name}"
            pool = {
                "name": name,
                "partition": partition,
                "fullPath": full_path,
                "loadBalancingMode": body.get("loadBalancingMode", "round-robin"),
                "monitor": body.get("monitor", "default"),
                "description": body.get("description", ""),
                "members": body.get("members", []),
                "generation": self.server.state.next_generation(),
            }
            self.server.state.pools[full_path] = pool
            self._send_json(pool)
            return

        if path == "/mgmt/tm/ltm/data-group/internal":
            body = self._json_body()
            name = body.get("name", "dg")
            partition = body.get("partition", "Common")
            full_path = f"/{partition}/{name}"
            data_group = {
                "name": name,
                "partition": partition,
                "fullPath": full_path,
                "type": body.get("type", "string"),
                "description": body.get("description", ""),
                "records": body.get("records", []),
                "generation": self.server.state.next_generation(),
            }
            self.server.state.data_groups[full_path] = data_group
            self._send_json(data_group)
            return

        if path in {"/tm/util/bash", "/mgmt/tm/util/bash"}:
            self._send_json({"commandResult": "stub log line"})
            return

        self._not_found()

    def do_PATCH(self) -> None:  # noqa: N802
        path, _ = self._parse()
        if path.startswith("/mgmt/tm/ltm/rule/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            rule = self.server.state.rules.get(identifier)
            if not rule:
                self._not_found()
                return
            body = self._json_body()
            if "apiAnonymous" in body:
                rule["apiAnonymous"] = body["apiAnonymous"]
            rule["generation"] = self.server.state.next_generation()
            self._send_json(rule)
            return

        if path.startswith("/mgmt/tm/ltm/virtual/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            virtual = self.server.state.virtuals.get(identifier)
            if not virtual:
                self._not_found()
                return
            body = self._json_body()
            if "rules" in body:
                virtual["rules"] = body["rules"]
            self._send_json(virtual)
            return

        if path.startswith("/mgmt/tm/ltm/pool/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            pool = self.server.state.pools.get(identifier)
            if not pool:
                self._not_found()
                return
            body = self._json_body()
            pool.update({key: value for key, value in body.items() if value is not None})
            pool["generation"] = self.server.state.next_generation()
            self._send_json(pool)
            return

        if path.startswith("/mgmt/tm/ltm/data-group/internal/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            data_group = self.server.state.data_groups.get(identifier)
            if not data_group:
                self._not_found()
                return
            body = self._json_body()
            for key in ("type", "description", "records"):
                if key in body:
                    data_group[key] = body[key]
            data_group["generation"] = self.server.state.next_generation()
            self._send_json(data_group)
            return

        self._not_found()

    def do_DELETE(self) -> None:  # noqa: N802
        path, _ = self._parse()
        if path.startswith("/mgmt/tm/ltm/rule/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            self.server.state.rules.pop(identifier, None)
            self._send_empty_json(200)
            return

        if path.startswith("/mgmt/tm/ltm/data-group/internal/"):
            identifier = self._decode_name(path.rsplit("/", 1)[-1])
            self.server.state.data_groups.pop(identifier, None)
            self._send_empty_json(200)
            return

        self._not_found()


class FakeBigIPServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), FakeBigIPRequestHandler)
        self.state = _State()
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.shutdown()
        self.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            self._thread = None


__all__ = ["FakeBigIPServer"]
