"""Configuration helpers for the fastMCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    bigip_host: str
    bigip_token: str
    bigip_partition: str = "Common"
    bigip_verify_ssl: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.getenv("BIGIP_HOST")
        token = os.getenv("BIGIP_TOKEN")
        if not host or not token:
            missing = [name for name, value in ("BIGIP_HOST", host), ("BIGIP_TOKEN", token) if not value]
            raise RuntimeError(
                "Missing required BIG-IP environment variables: " + ", ".join(missing)
            )

        partition = os.getenv("BIGIP_PARTITION", "Common")
        verify_ssl = os.getenv("BIGIP_VERIFY_SSL", "1") not in {"0", "false", "False"}
        return cls(
            bigip_host=host.rstrip("/"),
            bigip_token=token,
            bigip_partition=partition,
            bigip_verify_ssl=verify_ssl,
        )
