# F5 BIG-IP API Research (2025-11-07)

## Managing iRules via iControl REST
- Base collection: `/mgmt/tm/ltm/rule`; supports GET/POST/PATCH/PUT/DELETE with natural key `(name, partition, subPath)` for CRUD. Docs: APIRef_tm_ltm_rule on clouddocs.f5.com via Context7.
- Payload includes definition metadata (checksum, signature flags) plus `tmPartition`. We'll submit the TCL definition in the `apiAnonymous` body field when creating/updating rules.
- SOAP alternative exposes `create`, `delete_rule`, `modify_rule`, `query_rule`, etc., but REST is preferred for FastMCP tools. Docs: dco_ltm_irule_object reference.
- `apiAnonymous` holds the raw TCL definition in JSON bodies for POST/PATCH; sample requests from Telstra's public blueprint confirm the structure and response fields (`kind`, `fullPath`, `generation`). Source: Telstra F5 Blueprint “iControl REST API” page (https://telstra-digital.github.io/f5_blueprint/). 
- DevCentral’s “Adding an iRule via PUT” thread and Google Security Operations’ “F5 BIG-IP iControl API” playbook both show that PATCHing `/mgmt/tm/ltm/rule/<name>` with `{"apiAnonymous": ...}` replaces the entire script, so safe updates must read/merge first. References: https://community.f5.com/kb/technicalarticles/full-examples-of-icontrol-rest-using/272280 and https://cloud.google.com/chronicle/docs/reference/playbooks/f5-big-ip-icontrol.

## Attaching iRules to Virtual Servers
- Virtual servers live at `/mgmt/tm/ltm/virtual`. Supported methods: GET/POST/PUT/PATCH/DELETE. Natural key `(name, partition, subPath)`. Docs: APIRef_tm_ltm_virtual.
- To bind iRules, send a `rules` array with full paths (`/Common/my_rule`). Other relevant fields include `destination`, `pool`, `profiles`, persistence settings, etc.
- API reference reiterates the `rules` property lives on the top-level virtual resource alongside stats (destination, pool, SAT). Source: F5 clouddocs “APIRef_tm_ltm_virtual” (https://clouddocs.f5.com/api/icontrol-rest/APIRef_tm_ltm_virtual.html).
- Practical example: `curl -X PUT ... -d '{"rules":["/Common/out_log","/Common/out_log2"]}' https://<host>/mgmt/tm/ltm/virtual/<vs>` successfully attaches/detaches rules; DevCentral thread covers 11.6+ behavior where the array must contain absolute paths. Source: https://community.f5.com/kb/technicalarticles/full-examples-of-icontrol-rest-using/272280.

- Direct REST resources for log retrieval are limited; action item is to confirm whether `/mgmt/tm/util/bash` or `/mgmt/tm/util/tail` is supported on the target BIG-IP build for safely tailing `/var/log/ltm`.
- For tuning, log-level knobs exist under `/mgmt/tm/sys/daemon-log-settings/tmm` (controls `iruleLogLevel`, `httpLogLevel`, etc.) and `/mgmt/tm/sys/daemon-log-settings/lind`. Docs: APIRef_tm_sys_daemon-log-settings_tmm and APIRef_tm_sys_daemon-log-settings_lind.
- Telemetry Streaming docs show canonical payload for running shell commands via `POST /mgmt/tm/util/bash`—`{"command":"run","utilCmdArgs":"-c \"tail -n 100 /var/log/ltm\""}`—which we can adapt for the log tooling while guarding against injection (wrap args ourselves). Source: F5 Telemetry Streaming poller reference (https://clouddocs.f5.com/products/extensions/f5-telemetry-streaming/latest/userguide/ts_poller.html).
- Security advisories around CVE-2022-1388 stress that `/mgmt/tm/util/bash` is heavily abused; our tooling must enforce allowlists (tail only, limited flags) and optionally refuse execution when `X-F5-Auth-Token` misuse is detected. Sources: https://cyber-91.com/cve-2022-1388-high-critical-rce-vulnerability-exploitation-in-large-scale/ and https://webcache.googleusercontent.com/search?q=GreyNoise+bigip+cve-2022-1388.
