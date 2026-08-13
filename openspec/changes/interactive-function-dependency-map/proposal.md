## Why

Understanding FKT currently requires reading code or the architecture tree — nothing shows how the 500+ functions actually relate. An interactive dependency map makes the shape of the codebase visible to both human readers and agents: nodes are functions, edges are call/dependency relations, and the whole thing can be explored visually.

## What Changes

- Add a static-analysis generator (`tools/generate_dependency_map.py`) that walks the Python codebase, resolves imports, and emits the function call graph as JSON.
- Add a self-contained interactive map page (`docs/dependency-map/index.html`) rendered with vis-network, with the graph data embedded so it works offline from `file://`.
- Keep a machine-readable `docs/dependency-map/data.json` so agents can consume the graph programmatically.
- Add a README section explaining the map and linking to it.

## Capabilities

### New Capabilities
None. Docs/tooling-only change; the change opts out of specs (`skip_specs: true`).

### Modified Capabilities
None.

## Impact

- New files: `tools/generate_dependency_map.py`, `docs/dependency-map/index.html`, `docs/dependency-map/data.json`
- Modified: `README.md`
- No runtime behavior, schema, or dependencies change.

## Notes

- The call graph is a static (AST-based) approximation. Calls resolved only by name/import matching within the project; calls into third-party libraries are excluded.
- Scope covers the Python backend (`tracker_app/` + `setup.py`); the React/TypeScript frontend is out of scope for this change.