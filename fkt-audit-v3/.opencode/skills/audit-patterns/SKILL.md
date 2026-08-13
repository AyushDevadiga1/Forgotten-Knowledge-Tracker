---
name: Audit Patterns
metadata:
  purpose: Recursively search for graph-adjacent sibling defects after confirmation
---

From a confirmed finding, derive the smallest root-cause pattern.

Search in this order:
1. same function/module
2. direct graph neighbors
3. same abstraction/helper pattern
4. same module family
5. repository-wide only when the pattern is clearly systemic

Classify candidates as confirmed-candidate / false-positive / requires-proof. Never patch candidates directly. Send them to the independent proof gate.

Persist reusable patterns in `.audit/patterns/` so future audits can reuse them without repeating discovery.
