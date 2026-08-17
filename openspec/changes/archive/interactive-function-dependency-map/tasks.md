## 1. Build the dependency analyzer

- [x] 1.1 Write `tools/generate_dependency_map.py` (pure stdlib, AST-based): walk `tracker_app/**/*.py` and `setup.py`, collect function/method definitions with module-qualified ids, resolve imports (absolute + relative), and find call edges between project functions
- [x] 1.2 Output `docs/dependency-map/data.json` with `nodes`, `edges`, and metadata (generated_at, counts)

## 2. Build the interactive map page

- [x] 2.1 Write `docs/dependency-map/index.html`: vis-network force layout, module coloring, module filter, search, click-to-inspect panel, legend, and the graph data embedded so it runs offline from `file://`
- [x] 2.2 Verify the page renders and the graph loads without a server

## 3. Document the map in the README

- [x] 3.1 Add a "Interactive function dependency map" section to the README explaining what it is and linking to the map and the JSON
- [x] 3.2 Regenerate the graph data and confirm counts are sane (no duplicate node ids)