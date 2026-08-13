# FKT Audit v3 State

This directory is durable audit memory, separate from OpenSpec.

- `topology/` — cached dependency-map data and component summaries
- `context/` — compact subsystem knowledge reused across sessions
- `queue/` — bounded hypotheses/work items
- `findings/` — confirmed/rejected findings
- `evidence/` — reproductions and proof records
- `verification/` — patch and adversarial verification records

Do not treat generated topology as runtime truth; it is a routing cache derived from `docs/dependency-map/index.html`.
