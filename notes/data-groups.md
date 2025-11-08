# BIG-IP Data Group Research (2025-11-08)

## API Surface
- Internal data groups live under `/mgmt/tm/ltm/data-group/internal` (collection) with resource URIs shaped like `/mgmt/tm/ltm/data-group/internal/~Partition~Name`. The API supports GET/POST/PATCH/PUT/DELETE and uses `(name, partition, subPath)` as the natural key. (Source: https://clouddocs.f5.com/api/icontrol-rest/APIRef_tm_ltm_data-group_internal)
- External data groups are exposed at `/mgmt/tm/ltm/data-group/external` with the same HTTP verbs plus properties for referencing files such as `externalFileName`. (Source: https://clouddocs.f5.com/api/icontrol-rest/APIRef_tm_ltm_data-group_external)
- Collections only allow GET/OPTIONS; writes happen against the resource URIs. Both internal and external groups accept the `type` field with values `ip`, `string`, or `integer`.

## Payload Details (Internal)
- Required fields: `name`, `partition` (defaults to `Common` if omitted), and `type`.
- Optional fields: `description`, `appService`, and `records`. Each record entry is shaped as "{"name": "key", "data": "value"}"; `data` may be omitted for pure membership sets.
- PATCH or PUT requests replace only the provided attributes. Supplying the `records` array overwrites the entire list, so we should perform read-modify-write cycles for incremental edits.

## Tooling Considerations
- The API reference notes that `records` is an array structure, so we normalize inputs to the `[{"name": ..., "data": ...}]` form before sending to BIG-IP.
- We continue to rely on token-authenticated iControl REST requests using the headers implemented in `BigIPClient` to avoid duplicating auth logic.

## Next Steps for MCP Server
1. Add CRUD helpers in `BigIPClient` around the internal data group endpoints.
2. Surface fastMCP tools for listing, creating, updating, and deleting data groups, allowing callers to specify type/records/description.
3. Extend the fake BIG-IP harness plus regression tests to emulate `/ltm/data-group/internal` operations so the stdio integration suite can cover the new tools.
