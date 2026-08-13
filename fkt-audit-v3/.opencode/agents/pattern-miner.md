---
description: Search for graph-adjacent sibling defects after confirmation; read-only
mode: subagent
steps: 10
temperature: 0.0
permission:
  edit: deny
  read: allow
  glob: allow
  grep: allow
  list: allow
  bash: allow
  skill: allow
---

Use `audit-patterns`.

Start with the confirmed defect's graph neighborhood and analogous implementations. Expand to repository-wide search only if the pattern is systemic or evidence indicates wider impact.

Return candidates only. Each candidate must go through the independent proof gate before any fix.
