# FKT Audit v3 — Graph-Aware, Evidence-Driven Auditor

This is an overlay for the existing FKT OpenCode + OpenSpec setup.

## What changed from v2

- Quick mode is now the default.
- Audits route through the existing dependency graph instead of rediscovering the repository.
- Agents work inside bounded fault neighborhoods.
- Specialist work is parallelized only within the same neighborhood.
- Existing `.audit/` context is reused.
- Tests are treated as evidence, not unquestionable truth.
- Confirmation uses explicit evidence levels E0–E5.
- Recursive sibling searches begin locally and widen only after confirmation.
- Graph data is cached using its generation metadata and source hash.
- Product edits stay approval-gated in `patch-engineer`.

## Commands

```text
/audit                 # QUICK
/audit quick           # QUICK
/audit deep            # DEEP
/audit full            # FULL
```

Example:

```text
/audit quick tracker_app.db.models
```

Or:

```text
/audit quick

Investigate why feedback persistence can disagree with the API response.
```

## Important

Keep the OpenSpec-generated `.opencode/commands/opsx-*` and `.opencode/skills/openspec-*` files. This package does not replace them.

Keep `.agent/`, `.hermes/`, and `openspec/`.

Use OpenSpec for meaningful behavior changes. Use the audit system for correctness investigation.
