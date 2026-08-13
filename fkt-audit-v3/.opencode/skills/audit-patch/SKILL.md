---
name: Audit Patch
metadata:
  purpose: Make minimal changes to confirmed defects
---

Input must be a confirmed finding with evidence and expected behavior.

Patch rules:
- preserve existing contracts unless the confirmed defect requires a change
- minimal diff
- no unrelated refactor
- focused regression test when practical
- run focused verification first
- inspect final diff
- record exact verification evidence in `.audit/verification/`

If expected behavior is ambiguous or would require a new product decision, stop and hand the decision to the user/OpenSpec instead of guessing.
