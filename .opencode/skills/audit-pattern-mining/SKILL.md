---
name: audit-pattern-mining
description: Recursive root-cause procedure for finding sibling instances of a confirmed defect pattern.
---

Convert the confirmed defect into an abstract failure pattern that does not depend on one variable name or file.

Search for semantic equivalents, copied logic, sibling implementations, shared helpers, alternate branches, and older versions. Do not mark siblings confirmed from similarity alone; send each through reproduction.

Persist the pattern under `.audit/patterns/`.
