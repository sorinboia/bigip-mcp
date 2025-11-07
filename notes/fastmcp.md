# FastMCP Research (2025-11-07)

## Transport + Server Basics
- `FastMCP(...).run()` defaults to STDIO; explicitly applying `transport="stdio"` is optional but documents our intent. Source: /jlowin/fastmcp README via Context7.
- STDIO is ideal for local CLIs and Claude Desktop integrations because the server runs per session without network exposure. Source: /jlowin/fastmcp docs/deployment/running-server.mdx.
- We can still switch to HTTP/SSE transports later by passing `transport`, `host`, `port`, etc. Source: /jlowin/fastmcp docs/servers/server.mdx.

## Tool Definition Pattern
- Define functions with `@mcp.tool` decorator; each tool receives typed parameters and returns structured responses. Source: /jlowin/fastmcp README.
- `FastMCP.as_proxy` + `ProxyClient` can bridge remote SSE servers to local STDIO endpoints, useful if we need to wrap an upstream BIG-IP proxy. Source: /jlowin/fastmcp docs/servers/proxy.mdx.

## Client Considerations
- `fastmcp.Client` can talk to STDIO servers by launching `python my_server.py`; this is handy for local integration tests. Source: /jlowin/fastmcp README.
- `StdioTransport` exposes knobs (`command`, `args`, `env`, `cwd`) to control how the client spawns our server for testing. Source: /jlowin/fastmcp docs/clients/transports.mdx.

## CLI Factory Hooks
- `fastmcp run server.py:create_server` supports async factory functions so we can perform auth handshakes before returning the FastMCP instance. Source: /jlowin/fastmcp docs/patterns/cli.mdx.

## Tool Metadata & Management
- Tools can be toggled at runtime: after `@mcp.tool` registration we can call `.disable()` / `.enable()` on the decorated function, or remove it entirely via `FastMCP.remove_tool(name)` which automatically emits `notifications/tools/list_changed` to clients. Source: /jlowin/fastmcp docs/servers/tools.mdx (Context7).
- Tool transformations (e.g., tagging, allowlists) are controlled through `tool_transformations` on the transport/client config so we can expose only the BIG-IP scopes we want. Source: /jlowin/fastmcp docs/clients/transports.mdx (Context7).
