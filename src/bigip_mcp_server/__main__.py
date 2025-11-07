"""Entrypoint for running the fastMCP server via `python -m`."""

from __future__ import annotations

from .config import Settings
from .server import create_server


def main() -> None:
    settings = Settings.from_env()
    server = create_server(settings)
    server.run()  # stdio transport by default


if __name__ == "__main__":
    main()
