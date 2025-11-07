# Project Goals

- Build an MCP server for F5 BIG-IP using fastMCP over stdio.
- Implement CRUD management for iRules plus attaching/detaching iRules to Virtual Servers.
- Provide read access to operational logs such as LTM log files.
- Integrate with the relevant F5 BIG-IP REST APIs to fulfill these capabilities.
- Use Context7 to pull the latest documentation for both fastMCP and F5 BIG-IP APIs.
- Capture research outputs in additional Markdown files stored in this repository.
- Target BIG-IP v17 and authenticate via token-based iControl REST calls.
- Implement log tooling around `/var/log/ltm`, allowing filters while using `/mgmt/tm/util/bash` safely.
- Keep the implementation in Python, configure everything via environment variables, and plan to test against a real BIG-IP where possible.

# Current Plan & Progress

1. Capture detailed requirements, architecture assumptions, and dependencies for the BIG-IP MCP server, using Context7 references where needed. **Status:** completed.
2. Design repo scaffolding (Python fastMCP server, configuration layout, docs) and outline implementation tasks. **Status:** completed.
3. Implement, document, and validate the fastMCP server tools against the BIG-IP APIs. **Status:** in progress (2025-11-07: ran live BIG-IP v17 validation covering iRules CRUD, attach/detach, log tail; added `bigip-mcp-harness` stdio client for repeatable validation; next focus is automated regression coverage).

Reminder: whenever progress changes on any of these steps, update their statuses here **and** in the planning tool so both stay in sync.

# AI general behavious

When finishing a task always consider and if needed update the AGENTS.md file.
Use git to keep track of all changes.
When doing the research make sure you create additinal files and keep the information in there. They need to be in markdown.
Keep the plan/tool statuses synchronized: after completing a step, update the plan tracker and mirror the change in the "Current Plan & Progress" section above. If new tasks are added update the plan.
