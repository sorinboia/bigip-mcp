"""fastMCP server for F5 BIG-IP."""

from importlib import metadata

__all__ = ["__version__"]

try:  # pragma: no cover - metadata only available in installed envs
    __version__ = metadata.version("bigip-mcp-server")
except metadata.PackageNotFoundError:  # pragma: no cover - dev editable installs
    __version__ = "0.1.0"
