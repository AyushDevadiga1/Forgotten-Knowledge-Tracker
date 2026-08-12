---
name: audit-patch
description: Minimal, regression-oriented procedure for implementing a confirmed bug fix.
---

Patch only the confirmed defect. Preserve the established contract. Add regression coverage that fails before the patch where practical. Avoid unrelated refactoring. Review callers/consumers and failure paths before declaring the patch complete.

If behavior changes intentionally, use the relevant OpenSpec change workflow rather than silently rewriting requirements.
