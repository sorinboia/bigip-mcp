# BIG-IP FastMCP Server

Model Context Protocol (MCP) server that exposes F5 BIG-IP management primitives to LLM clients via [fastMCP](https://github.com/jlowin/fastmcp). The initial feature set focuses on BIG-IP v17:

- Create, delete, update, and inspect iRules.
- Attach/detach iRules on LTM Virtual Servers.
- Query operational logs (e.g., `/var/log/ltm`) with simple filtering controls.

## Project Layout

```
.
├── AGENTS.md              # Working agreements/goals
├── notes/                 # Research captured as markdown
├── src/bigip_mcp_server   # Python package (fastMCP server + BIG-IP client)
└── README.md              # This file
```

## Tooling

- Python ≥ 3.11
- `fastmcp` for MCP server scaffolding
- `httpx` for async iControl REST calls

Install deps (use your preferred venv manager):

```bash
pip install -e .
```

## Configuration

The server uses environment variables so it can run cleanly in CLI contexts like Claude Desktop:

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `BIGIP_HOST` | yes | Management hostname or IP (e.g. `https://10.0.0.10`) |
| `BIGIP_TOKEN` | yes | iControl REST token (generated with `POST /mgmt/shared/authn/login`). |
| `BIGIP_PARTITION` | no | Administrative partition to operate in (default `Common`). |
| `BIGIP_VERIFY_SSL` | no | Set to `0` to skip TLS verification during development. |

## Running the MCP server

```bash
python -m bigip_mcp_server
```

By default fastMCP runs over stdio so it can be spawned per session by the MCP client.

## Next Steps

- Flesh out the BIG-IP client wrapper around iControl REST endpoints.
- Implement fastMCP tools for iRules, virtual server binding, and log access.
- Add integration tests that run against a dev BIG-IP or a mock harness.
