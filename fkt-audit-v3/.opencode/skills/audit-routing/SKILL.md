---
name: Audit Routing
metadata:
  purpose: Build the smallest fault neighborhood and choose specialist coverage
---

Given a target/hypothesis, create a fault neighborhood containing:
1. target node(s)
2. direct callers and callees
3. relevant state/storage boundaries
4. relevant API/external boundaries
5. tests that directly exercise the path
6. relevant OpenSpec artifacts if they exist

Choose specialists by risk:
- pure algorithm/branch/state logic → logic-hunter
- runtime/output/persistence/retry/error behavior → runtime-contract-hunter
- API/schema/storage/module boundary → runtime-contract-hunter
- test confidence concern → runtime-contract-hunter with test-reality focus

Quick mode should normally invoke at most two specialists in parallel. Add a third only when the evidence crosses another boundary.

Never scan disconnected components unless the evidence points there.
