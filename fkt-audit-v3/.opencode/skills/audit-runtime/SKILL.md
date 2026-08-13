---
name: Audit Runtime
metadata:
  purpose: Validate real behavior instead of relying on green tests alone
---

Trace the supplied path from entry to observable result.

Ask:
- What input entered?
- What state changed?
- What was persisted/emitted/returned?
- Which errors can be swallowed?
- Which external boundaries can disagree?
- Could the system return a plausible but incorrect result?

Prefer the smallest executable reproduction. Reuse existing fixtures and tests; create temporary probes only when needed and do not leave noise behind.
