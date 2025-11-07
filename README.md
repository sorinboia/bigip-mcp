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

The server reads its settings from environment variables and automatically loads a `.env` file (either the default in the repo root or the path you set in `BIGIP_ENV_FILE`). Put your BIG-IP connection details there and they will be loaded before `Settings.from_env()` runs.

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `BIGIP_HOST` | yes | Management hostname or IP (e.g. `https://10.0.0.10`). |
| `BIGIP_TOKEN` | conditional | Pre-issued iControl REST token. Optional if username/password are supplied. |
| `BIGIP_USERNAME` / `BIGIP_PASSWORD` | conditional | BIG-IP credentials used to mint a token automatically when `BIGIP_TOKEN` is absent. |
| `BIGIP_LOGIN_PROVIDER` | no | Auth provider passed to `/mgmt/shared/authn/login` (default `tmos`). |
| `BIGIP_PARTITION` | no | Administrative partition to operate in (default `Common`). |
| `BIGIP_VERIFY_SSL` | no | Set to `0` to skip TLS verification during development. |
| `BIGIP_ENV_FILE` | no | Path to an alternate `.env` file if you do not want to use the repo root file. |

Example `.env` snippet:

```dotenv
BIGIP_HOST=https://10.0.0.10
BIGIP_USERNAME=admin
BIGIP_PASSWORD=super-secret
BIGIP_PARTITION=Common
BIGIP_VERIFY_SSL=0
```

## Running the MCP server

```bash
python -m bigip_mcp_server
```

By default fastMCP runs over stdio so it can be spawned per session by the MCP client.

If you only supply `BIGIP_USERNAME`/`BIGIP_PASSWORD`, the server will authenticate lazily by calling `POST /mgmt/shared/authn/login` and cache the returned token, retrying when it receives 401/403 responses.

## Stdio validation harness

Run the scripted end-to-end flow (iRules CRUD, attach/detach, log tail) via the included harness. It launches the stdio server with your current environment variables, calls each tool through `fastmcp.Client`, and prints a JSON summary.

```bash
bigip-mcp-harness --virtual /Common/TestVs --log-lines 5 --log-filter mcpd
```

Key options:

- `--virtual` – fully-qualified virtual server to exercise (default `/Common/TestVs`).
- `--rule-prefix` – prefix for temporary validation iRules.
- `--server-command` – override the arguments passed after the Python interpreter if you need a custom server entrypoint (defaults to `-m bigip_mcp_server`).
- `--env KEY=VALUE` – inject additional environment variables for the server process; repeat as needed.

Use `--output validation.json` to capture the JSON blob on disk for later auditing.

## Available tools

| Tool name | Description |
| --------- | ----------- |
| `server_info` | Echoes the server's configuration context (host, partition, TLS verification). |
| `irules_list` | Lists iRules scoped to the configured partition, optionally returning the TCL body. |
| `irules_create` / `irules_update` / `irules_delete` | CRUD helpers that wrap `POST/PATCH/DELETE /mgmt/tm/ltm/rule`. |
| `virtuals_attach_irule` / `virtuals_detach_irule` | Appends or removes fully-qualified iRules on LTM virtual servers by manipulating the `rules` array. |
| `logs_tail_ltm` | Tails `/var/log/ltm` safely via `POST /mgmt/tm/util/bash` with optional substring filtering. |

All tools automatically scope to the partition in `BIGIP_PARTITION` unless you override the optional partition arguments per call.

## Testing

Install the project (editable) along with the dev extras, then run the async unit tests:

```bash
python3 -m pip install --break-system-packages -e .[dev]
python3 -m pytest
```

## Next Steps

- Validate the implemented tools against a real BIG-IP v17 instance (esp. auth/token lifecycle).
- Harden the `/mgmt/tm/util/bash` execution path with rate limiting and audit logging.
- Add integration tests that run against a dev BIG-IP or a mock harness.
