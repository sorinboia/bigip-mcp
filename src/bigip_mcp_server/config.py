"""Configuration helpers for the fastMCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load environment variables from .env files when present."""

    # Respect an explicit path first.
    explicit_env = os.getenv("BIGIP_ENV_FILE")
    load_dotenv(override=False)
    if explicit_env:
        load_dotenv(explicit_env, override=False)
    else:
        repo_env = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(repo_env, override=False)


_load_env()


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    bigip_host: str
    bigip_token: str | None = None
    bigip_partition: str = "Common"
    bigip_verify_ssl: bool = True
    bigip_username: str | None = None
    bigip_password: str | None = None
    bigip_login_provider: str = "tmos"

    @classmethod
    def from_env(cls) -> "Settings":
        host = os.getenv("BIGIP_HOST")
        token = cls._clean(os.getenv("BIGIP_TOKEN"))
        username = cls._clean(os.getenv("BIGIP_USERNAME"))
        password = cls._clean(os.getenv("BIGIP_PASSWORD"))
        login_provider = os.getenv("BIGIP_LOGIN_PROVIDER", "tmos")

        if not host:
            raise RuntimeError("Missing required BIG-IP environment variables: BIGIP_HOST")

        if not token and not (username and password):
            raise RuntimeError(
                "Missing BIG-IP authentication. Provide BIGIP_TOKEN or BIGIP_USERNAME/BIGIP_PASSWORD."
            )

        partition = os.getenv("BIGIP_PARTITION", "Common")
        verify_ssl = os.getenv("BIGIP_VERIFY_SSL", "1") not in {"0", "false", "False"}
        return cls(
            bigip_host=host.rstrip("/"),
            bigip_token=token,
            bigip_partition=partition,
            bigip_verify_ssl=verify_ssl,
            bigip_username=username,
            bigip_password=password,
            bigip_login_provider=login_provider,
        )

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
