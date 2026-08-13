#!/usr/bin/env python3
"""Generate the interactive function dependency map for FKT.

Static (AST-based) call-graph analysis of the Python backend. Emits:
  docs/dependency-map/data.json   - machine-readable graph (nodes + edges + meta)
  docs/dependency-map/index.html  - self-contained interactive map (data embedded)

Usage:
    python tools/generate_dependency_map.py
"""
from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [ROOT / "tracker_app", ROOT / "setup.py"]
OUT_DIR = ROOT / "docs" / "dependency-map"
SKIP_PARTS = {"venv", "__pycache__", ".git", "node_modules", "logs", "data", "test_data", "training_data", "models"}

GROUP_COLORS = {
    "tracking": "#4f8cff",
    "learning": "#22c55e",
    "db": "#eab308",
    "web": "#a855f7",
    "scripts": "#f97316",
    "tools": "#06b6d4",
    "tests": "#64748b",
    "docs": "#ec4899",
    "other": "#94a3b8",
    "root": "#f472b6",
}


class ModuleInfo:
    def __init__(self, rel: Path):
        self.rel = rel
        self.module = module_id(rel)
        self.funcs: dict[str, str] = {}        # module-level name -> node id
        self.classes: dict[str, str] = {}      # class name -> class id
        self.methods: dict[tuple[str, str], str] = {}  # (class, method) -> node id
        self.imports: dict[str, tuple[str | None, str | None]] = {}  # local name -> (module, name)
        self.def_nodes: dict[str, tuple[str | None, ast.FunctionDef, bool]] = {}  # node id -> (class, node, is_nested)


class Scope:
    def __init__(self, func_id: str, class_name: str | None, func_name: str):
        self.func_id = func_id
        self.class_name = class_name
        self.func_name = func_name
        self.locals: set[str] = set()
        self.defs: dict[str, str] = {}


def module_id(rel: Path) -> str:
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    if not parts:
        return ""
    return ".".join(parts)


def group_for(rel: Path) -> str:
    parts = rel.parts
    if parts and parts[0] == "tracker_app":
        if len(parts) > 1 and parts[1] in GROUP_COLORS:
            return parts[1]
        return "other"
    return "root"


def iter_py_files():
    for src in SOURCES:
        if src.is_dir():
            for p in sorted(src.rglob("*.py")):
                rel = p.relative_to(ROOT)
                if any(part in SKIP_PARTS for part in rel.parts):
                    continue
                yield rel
        elif src.is_file():
            yield Path(src.name)


def relative_base(module: str, level: int) -> str:
    parts = module.split(".")
    if level <= 0:
        return ""
    return ".".join(parts[:-level])


def register_func(info: ModuleInfo, node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: str | None) -> None:
    if class_name is None:
        fid = f"{info.module}.{node.name}"
        info.funcs[node.name] = fid
    else:
        fid = f"{info.module}.{class_name}.{node.name}"
        info.methods[(class_name, node.name)] = fid
    info.def_nodes[fid] = (class_name, node, False)


def parse_file(rel: Path) -> ModuleInfo | None:
    path = ROOT / rel
    try:
        src = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        print(f"  skip (syntax error): {rel}")
        return None

    info = ModuleInfo(rel)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                alias = a.asname or a.name.split(".")[0]
                info.imports[alias] = (a.name, None)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and not node.module:
                continue
            base = relative_base(info.module, node.level)
            module = node.module if base == "" else (base if node.module is None else f"{base}.{node.module}")
            for a in node.names:
                if a.name == "*":
                    continue
                info.imports[a.asname or a.name] = (module, a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            register_func(info, node, None)
        elif isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    register_func(info, stmt, node.name)
    return info


def collect_locals(body) -> set[str]:
    locals_: set[str] = set()

    def visit(n) -> None:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            locals_.add(n.id)
        for c in ast.iter_child_nodes(n):
            visit(c)

    for item in body:
        visit(item)
    return locals_


def iter_calls(node):
    for c in ast.walk(node):
        if isinstance(c, ast.Call):
            yield c


def collect_chain(node) -> list[str]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return parts[::-1]
    return []


def resolve_in_module(mod: str, rest: list[str], mods: dict[str, ModuleInfo]) -> str | None:
    if mod not in mods or not rest:
        return None
    tinfo = mods[mod]
    head, tail = rest[0], rest[1:]
    if head in tinfo.funcs:
        return tinfo.funcs[head] if not tail else None
    if head in tinfo.classes:
        if len(tail) == 1:
            return tinfo.methods.get((head, tail[0]))
        return None
    sub = f"{mod}.{head}"
    if sub in mods:
        return resolve_in_module(sub, tail, mods)
    return None


def resolve_target(tgt: tuple[str | None, str | None], rest: list[str], mods: dict[str, ModuleInfo]) -> str | None:
    mod, name = tgt
    if not mod or mod not in mods:
        return None
    tinfo = mods[mod]
    if name:
        if name in tinfo.funcs:
            return tinfo.funcs[name] if not rest else None
        if name in tinfo.classes:
            if len(rest) == 1:
                return tinfo.methods.get((name, rest[0]))
            return None
        sub = f"{mod}.{name}"
        if sub in mods:
            return resolve_in_module(sub, rest, mods)
        return None
    return resolve_in_module(mod, rest, mods)


def resolve_call(call: ast.Call, scope: Scope, info: ModuleInfo, mods: dict[str, ModuleInfo]) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        name = f.id
        if name in scope.locals:
            return scope.defs.get(name)
        if name in scope.defs:
            return scope.defs[name]
        if name in info.funcs:
            return info.funcs[name]
        if name in info.classes:
            return None
        tgt = info.imports.get(name)
        if tgt is not None:
            return resolve_target(tgt, [], mods)
        return None
    if isinstance(f, ast.Attribute):
        chain = collect_chain(f)
        if not chain:
            return None
        root, rest = chain[0], chain[1:]
        if root in ("self", "cls"):
            if scope.class_name and rest:
                return info.methods.get((scope.class_name, rest[0]))
            return None
        if root in scope.locals:
            return None
        tgt = info.imports.get(root)
        if tgt is not None:
            return resolve_target(tgt, rest, mods)
        return None
    return None


def walk_statements(body, scope: Scope, info: ModuleInfo, mods: dict[str, ModuleInfo], edges: set, known: set) -> None:
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nested_id = f"{scope.func_id}::{stmt.name}"
            child = Scope(nested_id, scope.class_name, stmt.name)
            child.locals = collect_locals(stmt.body)
            scope.defs[stmt.name] = nested_id
            info.def_nodes[nested_id] = (scope.class_name, stmt, True)
            walk_statements(stmt.body, child, info, mods, edges, known)
            continue
        for call in iter_calls(stmt):
            callee = resolve_call(call, scope, info, mods)
            if callee and callee != scope.func_id:
                key = (scope.func_id, callee)
                if key not in known:
                    known.add(key)
                    edges.add(key)


def main() -> None:
    mods: dict[str, ModuleInfo] = {}
    for rel in iter_py_files():
        info = parse_file(rel)
        if info is not None:
            mods[info.module] = info

    known: set = set()
    edges: set = set()
    for info in mods.values():
        for fid, (class_name, func_node, is_nested) in list(info.def_nodes.items()):
            scope = Scope(fid, class_name, func_node.name)
            scope.locals = collect_locals(func_node.body)
            walk_statements(func_node.body, scope, info, mods, edges, known)

    nodes = []
    for info in mods.values():
        for fid, (class_name, func_node, is_nested) in list(info.def_nodes.items()):
            label = func_node.name if (class_name is None or is_nested) else f"{class_name}.{func_node.name}"
            nodes.append({
                "id": fid,
                "label": label,
                "group": group_for(info.rel),
                "file": str(info.rel).replace("\\", "/"),
                "module": info.module,
                "class": class_name,
                "kind": "function" if (is_nested or class_name is None) else "method",
                "line": func_node.lineno,
                "title": f"{fid}\n{info.rel}:{func_node.lineno}",
            })

    nodes.sort(key=lambda n: n["id"])
    edges_list = [{"from": a, "to": b} for a, b in sorted(edges)]
    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": len(mods),
        "nodes": len(nodes),
        "edges": len(edges_list),
        "group_colors": GROUP_COLORS,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "data.json").write_text(json.dumps({"meta": meta, "nodes": nodes, "edges": edges_list}, indent=2), encoding="utf-8")
    payload = json.dumps({"meta": meta, "nodes": nodes, "edges": edges_list})
    html = HTML_TEMPLATE.replace("__DATA__", payload)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"files parsed : {len(mods)}")
    print(f"nodes        : {len(nodes)}")
    print(f"edges        : {len(edges_list)}")
    print(f"wrote        : {OUT_DIR / 'data.json'}")
    print(f"wrote        : {OUT_DIR / 'index.html'}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FKT - Interactive Function Dependency Map</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: "Segoe UI", system-ui, sans-serif; background:#0f172a; color:#e2e8f0; }
  header { padding:12px 18px; border-bottom:1px solid #1e293b; background:#111c33; }
  header h1 { margin:0; font-size:18px; }
  header p { margin:4px 0 0; font-size:12px; color:#94a3b8; }
  #meta { margin-top:6px; font-size:12px; color:#64748b; }
  #controls { display:flex; flex-wrap:wrap; gap:10px; align-items:center; padding:10px 18px; border-bottom:1px solid #1e293b; background:#0d1526; }
  #search { background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:6px; padding:6px 10px; width:260px; font-size:13px; }
  button { background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:6px; padding:6px 12px; font-size:12px; cursor:pointer; }
  button:hover { background:#334155; }
  #groups { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
  #groups label { display:inline-flex; align-items:center; gap:5px; font-size:12px; cursor:pointer; }
  .swatch { width:10px; height:10px; border-radius:2px; display:inline-block; }
  #layout { display:flex; height:calc(100vh - 118px); }
  #network { flex:1; }
  #panel { width:300px; border-left:1px solid #1e293b; background:#111c33; padding:14px; overflow:auto; font-size:13px; }
  #panel h3 { margin:0 0 6px; font-size:14px; word-break:break-all; }
  #panel .kv { color:#94a3b8; font-size:12px; margin:2px 0; word-break:break-all; }
  #panel .kv b { color:#e2e8f0; font-weight:600; }
  #panel .list { margin:8px 0 0; }
  #panel .list h4 { margin:8px 0 4px; font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; }
  #panel .item { display:block; width:100%; text-align:left; background:none; border:none; color:#7dd3fc; font-size:12px; padding:2px 0; cursor:pointer; font-family:Consolas,monospace; word-break:break-all; }
  #panel .item:hover { color:#fbbf24; }
  .empty { color:#64748b; font-style:italic; }
  @media (max-width:800px){ #panel{ display:none; } #layout{ height:calc(100vh - 150px);} }
</style>
</head>
<body>
<header>
  <h1>FKT &mdash; Function Dependency Map</h1>
  <p>Nodes are functions and methods; edges are call dependencies (static AST analysis &mdash; an approximation).</p>
  <div id="meta"></div>
</header>
<div id="controls">
  <input id="search" placeholder="Filter nodes by name or module&hellip;">
  <button id="btn-fit">Fit</button>
  <button id="btn-reset">Reset physics</button>
  <div id="groups"></div>
</div>
<div id="layout">
  <div id="network"></div>
  <aside id="panel">Click a node to inspect what it calls and what calls it.</aside>
</div>
<script>
"use strict";
const GRAPH = __DATA__;
const meta = GRAPH.meta;
const nodeById = Object.fromEntries(GRAPH.nodes.map(n => [n.id, n]));
const colors = meta.group_colors || {};

const groupFilter = {};
GRAPH.nodes.forEach(n => { groupFilter[n.group] = true; });

function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

const nodes = new vis.DataSet(GRAPH.nodes.map(n => ({
  id: n.id,
  label: n.label,
  group: n.group,
  title: n.title,
  hidden: false,
  color: { background: colors[n.group] || "#94a3b8", border: "#1e293b",
           highlight: { background: "#fbbf24", border: "#78350f" } },
  font: { color: "#e2e8f0", face: "Consolas, monospace", size: 12 },
})));
const edges = new vis.DataSet(GRAPH.edges.map(e => ({
  from: e.from, to: e.to,
  color: { color: "#475569", highlight: "#fbbf24", opacity: 0.6 },
  arrows: "to",
  smooth: { enabled: true, type: "dynamic" },
  title: e.from + " -> " + e.to,
})));
const options = {
  nodes: { shape: "dot", size: 12, borderWidth: 1 },
  edges: { width: 1 },
  physics: {
    enabled: true,
    barnesHut: { gravitationalConstant: -30000, centralGravity: 0.3, springLength: 110, springConstant: 0.04, damping: 0.09, avoidOverlap: 0.4 },
    stabilization: { iterations: 800, updateInterval: 25 },
  },
  interaction: { hover: true, tooltipDelay: 150, navigationButtons: true, keyboard: true, multiselect: false },
  groups: Object.fromEntries(Object.entries(colors).map(([g, c]) => [g, {
    color: { background: c, border: "#1e293b", highlight: { background: "#fbbf24", border: "#78350f" } },
    font: { color: "#e2e8f0" },
  }])),
};
const container = document.getElementById("network");
const network = new vis.Network(container, { nodes, edges }, options);
network.once("stabilizationIterationsDone", () => { network.setOptions({ physics: { stabilization: false } }); });

document.getElementById("meta").textContent =
  meta.files + " files  |  " + meta.nodes + " nodes  |  " + meta.edges + " edges  |  generated " + meta.generated_at;

function applyVisibility() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const updates = GRAPH.nodes.map(n => {
    const groupOk = groupFilter[n.group];
    const match = !q || n.label.toLowerCase().includes(q) || n.module.toLowerCase().includes(q);
    return { id: n.id, hidden: !(groupOk && match) };
  });
  nodes.update(updates);
  network.setOptions({ physics: { enabled: true, stabilization: false } });
}
document.getElementById("search").addEventListener("input", applyVisibility);

const groupBoxes = document.getElementById("groups");
Object.keys(colors).forEach(g => {
  const lbl = document.createElement("label");
  lbl.innerHTML = '<span class="swatch" style="background:' + colors[g] + '"></span>' + g + ' <input type="checkbox" checked>';
  const cb = lbl.querySelector("input");
  cb.addEventListener("change", () => { groupFilter[g] = cb.checked; applyVisibility(); });
  groupBoxes.appendChild(lbl);
});

document.getElementById("btn-fit").addEventListener("click", () => network.fit({ animation: true }));
document.getElementById("btn-reset").addEventListener("click", () => network.setOptions({ physics: { enabled: true } }));

function showNode(id) {
  const n = nodeById[id];
  if (!n) return;
  const panel = document.getElementById("panel");
  const out = GRAPH.edges.filter(e => e.from === id).map(e => nodeById[e.to]).filter(Boolean);
  const inc = GRAPH.edges.filter(e => e.to === id).map(e => nodeById[e.from]).filter(Boolean);
  let html = "<h3>" + esc(n.label) + "</h3>";
  html += '<div class="kv"><b>id</b> ' + esc(n.id) + "</div>";
  html += '<div class="kv"><b>module</b> ' + esc(n.module) + "</div>";
  html += '<div class="kv"><b>file</b> ' + esc(n.file) + ":" + n.line + "</div>";
  html += '<div class="kv"><b>kind</b> ' + esc(n.kind) + (n.class ? " of " + esc(n.class) : "") + "</div>";
  html += '<div class="list"><h4>calls (' + out.length + ")</h4>";
  if (!out.length) html += '<div class="empty">none resolved</div>';
  out.forEach(t => { html += '<button class="item" data-id="' + esc(t.id) + '">&#8627; ' + esc(t.label) + "</button>"; });
  html += "</div>";
  html += '<div class="list"><h4>called by (' + inc.length + ")</h4>";
  if (!inc.length) html += '<div class="empty">nothing</div>';
  inc.forEach(t => { html += '<button class="item" data-id="' + esc(t.id) + '">&#8630; ' + esc(t.label) + "</button>"; });
  html += "</div>";
  panel.innerHTML = html;
  panel.querySelectorAll(".item").forEach(btn => {
    btn.addEventListener("click", () => { network.selectNodes([btn.dataset.id]); network.focus(btn.dataset.id, { scale: 1.4 }); showNode(btn.dataset.id); });
  });
}
network.on("click", p => { if (p.nodes.length) showNode(p.nodes[0]); });
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()