---
name: audit-adversarial-verification
description: Break-the-patch procedure for independent post-fix verification.
---

Assume the patch is wrong. Re-run the original reproduction, then vary inputs and execution conditions around the defect. Inspect the diff and adjacent call paths. Search for sibling implementations of the same root cause.

Fail verification if the original defect remains, if a regression is demonstrated, or if critical evidence is missing.
