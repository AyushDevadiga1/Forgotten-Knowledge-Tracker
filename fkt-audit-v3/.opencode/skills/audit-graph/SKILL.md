---
name: Audit Graph
metadata:
  purpose: Parse and query FKT's static dependency map
---

Read `docs/dependency-map/index.html` and extract the embedded `GRAPH` object.

Important: the map is a static AST call approximation, not runtime truth.

Preferred persistence:
- `.audit/topology/graph-meta.json`
- `.audit/topology/graph-index.json`
- `.audit/topology/component-summary.md`

Cache the graph using its `meta.generated_at`, node count, edge count, and source file hash. Do not rebuild it on every audit if unchanged.

Queries should support:
- node lookup by fully-qualified id, file, module, class, or function
- direct callers/callees
- 1-hop neighborhood
- 2-hop neighborhood only when explicitly requested or needed by evidence
- weakly connected component id/size
- module/group membership
- nearby tests

Do not infer runtime behavior from a missing edge. Use the graph to choose where to inspect.
