---
description: Fast graph-aware correctness audit. Use quick by default; deep/full are explicit.
agent: audit-orchestrator
---

Audit mode: $ARGUMENTS

Rules:
- Default to QUICK if no mode is supplied.
- QUICK = target/fault-neighborhood audit; avoid whole-repo scans.
- DEEP = broader neighborhood + recursive sibling search after confirmation.
- FULL = whole-repository risk-driven audit.

Start with the user's scope or the provided target. Reuse `.audit/` and `docs/dependency-map/index.html` before rediscovering architecture. Do not ask the user for routine commands. Do not modify product code unless a confirmed defect reaches patch-engineer.
