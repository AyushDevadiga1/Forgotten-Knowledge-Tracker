---
name: Audit Proof
metadata:
  purpose: Evidence gate for bug confirmation and adversarial verification
---

Use evidence levels:
E0 suspicion only
E1 static contradiction
E2 invariant/contract violation
E3 deterministic reproduction/observable failure
E4 regression test reproduces and prevents recurrence
E5 runtime + regression + affected-caller verification

Never convert E0-E2 into a code change without a proof step.

A test is not automatically proof. Check whether it exercises the meaningful behavior, observes a real output/side effect, and would fail for the original defect.

For adversarial verification, attempt to break the patch using:
- original reproduction
- adjacent boundaries
- malformed input
- retries / repeated execution
- state transitions
- affected callers
- concurrency/order when relevant
