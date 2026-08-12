---
name: audit-patch
description: Minimal, regression-oriented procedure for implementing a confirmed bug fix.
---

Patch only the confirmed defect. Preserve the established contract. Add regression coverage that fails before the patch where practical. Avoid unrelated refactoring. Review callers/consumers and failure paths before declaring the patch complete.

Capture every confirmed fix in an OpenSpec change before editing code: load the `openspec-propose` skill (or run `/opsx-propose`) to scaffold the change (or update it when one already covers the behavior), implement the fix as part of that change, and reference the change name in the finding record. Never silently rewrite requirements.
