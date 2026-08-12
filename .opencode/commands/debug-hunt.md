---
description: Run a recursive adversarial bug hunt over the repository
agent: adversarial-debugger
subtask: false
---

Audit the repository using the adversarial-debugger protocol.

Start by understanding the architecture and actual verification commands. Hunt for correctness failures across logic, data flow, contracts, edge cases, state transitions, concurrency/asynchrony, failures, and integration boundaries.

For every confirmed bug:
- prove it,
- fix it,
- add regression coverage where practical,
- identify the root-cause pattern,
- search the repository for sibling instances,
- re-audit affected callers and consumers,
- perform an adversarial second pass.

Do not weaken tests or perform unrelated refactors.

Continue until the stop condition in the agent instructions is satisfied.

Finish with an evidence-backed report and exact verification results.
