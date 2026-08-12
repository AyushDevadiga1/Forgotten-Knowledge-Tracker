---
description: Run the evidence-gated recursive adversarial audit workflow
agent: audit-orchestrator
subtask: false
---

Run a repository correctness audit using the audit-orchestrator.

Scope: $ARGUMENTS

Rules:
- If scope is empty, choose high-risk areas from repository recon rather than blindly scanning everything at once.
- Do not edit during discovery or reproduction.
- Do not patch a candidate until the bug-reproducer marks it CONFIRMED.
- Use OpenSpec artifacts as intent/change evidence when they exist; do not invent requirements.
- Persist durable state in `.audit/`.
- For every confirmed bug, mine the root-cause pattern and search the repository for sibling instances.
- Reproduce each sibling independently before patching it.
- After every patch, run adversarial verification and regression auditing.
- Finish only when the orchestrator stop condition is satisfied.

Return a concise final report with paths to durable audit records.
