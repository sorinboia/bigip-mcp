# F5 BIG-IP API Research (2025-11-07)

## Managing iRules via iControl REST
- Base collection: `/mgmt/tm/ltm/rule`; supports GET/POST/PATCH/PUT/DELETE with natural key `(name, partition, subPath)` for CRUD. Docs: APIRef_tm_ltm_rule on clouddocs.f5.com via Context7.
- Payload includes definition metadata (checksum, signature flags) plus `tmPartition`. We'll submit the TCL definition in the `apiAnonymous` body field when creating/updating rules.
- SOAP alternative exposes `create`, `delete_rule`, `modify_rule`, `query_rule`, etc., but REST is preferred for FastMCP tools. Docs: dco_ltm_irule_object reference.

## Attaching iRules to Virtual Servers
- Virtual servers live at `/mgmt/tm/ltm/virtual`. Supported methods: GET/POST/PUT/PATCH/DELETE. Natural key `(name, partition, subPath)`. Docs: APIRef_tm_ltm_virtual.
- To bind iRules, send a `rules` array with full paths (`/Common/my_rule`). Other relevant fields include `destination`, `pool`, `profiles`, persistence settings, etc.

- Direct REST resources for log retrieval are limited; action item is to confirm whether `/mgmt/tm/util/bash` or `/mgmt/tm/util/tail` is supported on the target BIG-IP build for safely tailing `/var/log/ltm`.
- For tuning, log-level knobs exist under `/mgmt/tm/sys/daemon-log-settings/tmm` (controls `iruleLogLevel`, `httpLogLevel`, etc.) and `/mgmt/tm/sys/daemon-log-settings/lind`. Docs: APIRef_tm_sys_daemon-log-settings_tmm and APIRef_tm_sys_daemon-log-settings_lind.
