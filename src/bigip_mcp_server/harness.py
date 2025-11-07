"""Stdio harness that exercises the fastMCP server via fastmcp.Client."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVER_ARGS = ["-m", "bigip_mcp_server"]
DEFAULT_RULE_PREFIX = "mcp_harness"
DEFAULT_DEF_V1 = 'when CLIENT_ACCEPTED { log local0. "mcp harness v1" }'
DEFAULT_DEF_V2 = 'when CLIENT_ACCEPTED { log local0. "mcp harness v2" }'


def _parse_env_overrides(pairs: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"Invalid env entry '{item}'. Use KEY=VALUE format.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError(f"Invalid env key in '{item}'.")
        overrides[key] = value
    return overrides


def _serialize_content(block: Any) -> Any:
    if hasattr(block, "text"):
        return getattr(block, "text")
    if is_dataclass(block):
        return asdict(block)
    if isinstance(block, dict):
        return block
    return str(block)


async def _call(
    client: Client,
    tool_name: str,
    **arguments: Any,
) -> Any:
    clean_args = {key: value for key, value in arguments.items() if value is not None}
    result = await client.call_tool(tool_name, clean_args or None)
    if result.data is not None:
        if is_dataclass(result.data):
            return asdict(result.data)
        return result.data
    if result.structured_content:
        return result.structured_content
    if result.content:
        serialized = [_serialize_content(block) for block in result.content]
        if len(serialized) == 1:
            return serialized[0]
        return serialized
    return None


async def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    env = os.environ.copy()
    env_overrides = _parse_env_overrides(args.env or [])
    env.update(env_overrides)

    transport = StdioTransport(
        command=args.python,
        args=args.server_command or DEFAULT_SERVER_ARGS,
        env=env,
        cwd=str(args.server_cwd),
    )

    client = Client(transport, name="bigip-mcp-harness")
    results: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rule_prefix": args.rule_prefix,
        "virtual_server": args.virtual,
    }

    rule_name = f"{args.rule_prefix}_{int(time.time())}"
    definition_v1 = args.definition_v1 or DEFAULT_DEF_V1
    definition_v2 = args.definition_v2 or DEFAULT_DEF_V2

    async with client:
        await client.list_tools()
        results["server.info"] = await _call(client, "server.info")
        results["irules.list_before"] = await _call(client, "irules.list", include_definition=False)
        results["irules.create"] = await _call(client, "irules.create", name=rule_name, definition=definition_v1)
        results["irules.update"] = await _call(client, "irules.update", name=rule_name, definition=definition_v2)
        attach_resp = await _call(
            client,
            "virtuals.attach_irule",
            virtual_name=args.virtual,
            rule_name=rule_name,
        )
        results["virtuals.attach_irule"] = attach_resp
        results["logs.tail_ltm"] = await _call(
            client,
            "logs.tail_ltm",
            lines=args.log_lines,
            contains=args.log_filter,
        )
        detach_resp = await _call(
            client,
            "virtuals.detach_irule",
            virtual_name=args.virtual,
            rule_name=rule_name,
        )
        results["virtuals.detach_irule"] = detach_resp
        results["irules.delete"] = await _call(client, "irules.delete", name=rule_name)

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run BIG-IP validation flows through the fastMCP stdio server."
    )
    parser.add_argument(
        "--virtual",
        default="/Common/TestVs",
        help="Fully-qualified virtual server name to exercise.",
    )
    parser.add_argument(
        "--rule-prefix",
        default=DEFAULT_RULE_PREFIX,
        help="Prefix for generated validation iRules.",
    )
    parser.add_argument(
        "--definition-v1",
        default=DEFAULT_DEF_V1,
        help="Initial iRule definition.",
    )
    parser.add_argument(
        "--definition-v2",
        default=DEFAULT_DEF_V2,
        help="Updated iRule definition used during validation.",
    )
    parser.add_argument(
        "--log-lines",
        type=int,
        default=5,
        help="Number of lines to fetch from logs.tail_ltm.",
    )
    parser.add_argument(
        "--log-filter",
        default=None,
        help="Optional substring filter passed to logs.tail_ltm.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter used to launch the fastMCP server.",
    )
    parser.add_argument(
        "--server-command",
        nargs="+",
        default=None,
        help="Override the arguments passed to the Python interpreter (default: -m bigip_mcp_server).",
    )
    parser.add_argument(
        "--server-cwd",
        default=PROJECT_ROOT,
        type=Path,
        help="Working directory for the server process.",
    )
    parser.add_argument(
        "--env",
        action="append",
        help="Additional KEY=VALUE pairs injected into the server environment (repeatable).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the JSON results.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = asyncio.run(run_validation(args))
    except KeyboardInterrupt:  # pragma: no cover - interactive convenience
        parser.exit(130, "Interrupted by user.\n")

    output = json.dumps(results, indent=2)
    print(output)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
