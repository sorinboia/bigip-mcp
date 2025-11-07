# BIG-IP Tool Validation (2025-11-07)

## Environment
- Target: `BIGIP_HOST` from `.env` (F5 UDF lab, v17)
- Partition: `Common`
- Auth: username/password flow minting temporary token via `/mgmt/shared/authn/login`
- Virtual server exercised: `/Common/TestVs`

## Validation Steps
1. Loaded `.env`, instantiated `Settings`, and confirmed token issuance (`_ensure_token` returned 26-char token).
2. Instantiated the FastMCP server via `create_server()` and invoked tools directly using their registered coroutines.
3. Sequence executed:
   - `irules.list` (baseline count 15 system rules).
   - `irules.create` for `codex_validation_<epoch>` with a basic logging TCL body.
   - `irules.update` swapped the log string to a "v2" marker.
   - `virtuals.attach_irule` bound the rule to `/Common/TestVs`.
   - `logs.tail_ltm` fetched 5 lines filtered on `mcpd`, confirming `/mgmt/tm/util/bash` pipeline works.
   - `virtuals.detach_irule` removed the test rule.
   - `irules.delete` cleaned up the rule.

## Observations & Outputs
```
- irules.create -> /Common/codex_validation_1762528425 (generation 134)
- irules.update -> generation 135
- virtuals.attach_irule -> rules now ['/Common/codex_validation_1762528425']
- logs.tail_ltm -> repeated mcpd MTU warnings (legacy VE NIC) + clock skew notice
- virtuals.detach_irule -> rules []
- irules.delete -> status deleted
```

## Issues Found
- DELETE responses advertise `application/json` but return an empty body, causing `BigIPClient.request()` to raise `JSONDecodeError`. Fixed by tolerating empty JSON payloads and falling back to text (see 2025-11-07 update to `bigip_client.py` + tests `test_request_handles_empty_json_success` / `test_request_falls_back_to_text_on_invalid_json`).

## Follow-Ups
- Consider capturing server/virtual metadata snapshots (pool, profiles) to ensure attaching rules does not disturb existing bindings.
- Add integration harness using `fastmcp.Client` over stdio for future regression tests.
