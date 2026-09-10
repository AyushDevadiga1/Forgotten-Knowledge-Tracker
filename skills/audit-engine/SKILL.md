---
name: audit-engine
description: Use when running the autonomous code-audit loop over a repository (or continuing one already in progress): "run the audit loop", "continue the audit", "audit the system", "are there bugs". One atomic task per iteration, evidence-gated findings persisted to AUDIT.md, checklist self-mutation, recursion until all tasks are [x]. Not for on-demand single-bug hunts (use /audit freeform debugging instead).
---

# Audit Engine (Ralph's Loop Variant)

## Overview

Run a full autonomous code audit one atomic task at a time. Every iteration completes exactly ONE checklist task, persists any findings, mutates the checklist, and recurses until every task is `[x]`. Findings are evidence-gated: nothing is logged or patched on speculation.

## Loop Constraints (system rules)

1. **Atomic Execution** - Analyze only the code relevant to the first uncompleted `[ ]` task. Do not attempt multiple tasks in one turn.
2. **Persistence** - Append every bug/error/defensive weakness to `AUDIT.md` at the project root as a structured table row, immediately.
3. **Self-Mutation** - Mark the completed task `[x]` in the checklist and update the Current Execution Frame after each iteration.
4. **Recursion** - If any `[ ]` task remains, immediately issue a command to continue scanning. If all are `[x]`, stop and report "Audit Complete".

## When to Use

- A broad sweep of a codebase for unvalidated inputs, auth gaps, crashes, leaks, privilege/query issues is requested ("audit the system").
- An audit loop was started before and must be resumed (continue from the Current Execution Frame).
- A fresh audit needs checkpoints the repo can be interrupted from and resume.

**Do NOT use** for a single named bug - that is a focused hunt, not a loop.

## Dynamic Checklist Template

Copy this into the working checklist file (e.g. `issues/PROMPT.md`) and mark phases off:

```markdown
### Phase 1: Reconnaissance
- [ ] Read root configuration files (package.json, requirements.txt, pyproject.toml, docker-compose.yml) and map data inputs.

### Phase 2: Input Layer & Logic Audit
- [ ] Scan entry points, API routes, and controllers for unvalidated inputs or boundary errors.
- [ ] Check authentication layers, session handling, and token verification.
- [ ] Audit data-processing functions for memory leaks, type-safety exceptions, handled/unhandled crashes.

### Phase 3: Persistence & State
- [ ] Inspect DB query files / storage managers for improper state mutations or query vulnerabilities.
- [ ] Scan env vars, secrets managers, and config-loading scripts.
```

## Execution Frame (per iteration)

Keep a heading in the checklist file:

```markdown
## Current Execution Frame
* **Last Completed Task:** <phase> - <what was scanned> (<FKT-ids appended>)
* **Next Action:** Execute <next phase> - <scope>
```

Update both lines every iteration: the frame is how a resumed/killed loop reboots.

## Persistence Contract (AUDIT.md)

One table per phase. Every row: ID, Subject, Severity, Location, Finding, Evidence, Status.

```markdown
| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-00N | one-line subject | LOW/MED/HIGH | file:line | what + why it matters | reproduction or code proof, not assertion | OPEN/CONFIRMED |
```

- Number IDs `FKT-001..` sequentially across the whole log.
- `CONFIRMED` = runtime-proven OR provable from code the write side and read side both show. `OPEN` = read-only evidence only.

## Evidence Gate (no speculation)

- Inspect the full execution path, not just the suspicious function.
- Reproduce candidates with the narrowest runtime probe (a venv one-liner beats reading).
- Do not log or patch a candidate until it is marked CONFIRMED.
- Post-fix: re-check callers, consumers, failure paths, and regression risk; search for sibling instances of the same root-cause pattern.

## Completion

Only report "Audit Complete" when every checklist task is `[x]`. Leftover unverified candidates are recorded as OPEN, never silently dropped.

## Common Mistakes

- **Evidence-free rows** - storing a finding without a reproduction or two-sided code proof creates noise; gate it.
- **Skipping the frame update** - a loop that dies mid-phase must reboot from the frame, not re-scan.
- **Patch-before-gate** - fixing a candidate that was never reproduced turns discovery into guessing.
- **Multi-tasking per turn** - atomicity is what makes the loop resumable; a turn doing three phases cannot be checkpointed.
- **Log secrets** - AUDIT.md must never contain keys, tokens, or .env values; cite locations only.
