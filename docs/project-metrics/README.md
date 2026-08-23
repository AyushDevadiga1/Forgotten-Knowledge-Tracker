# Project Metrics Tracker

Tracks growing complexity, LOC, KLOC, and structural health of the FKT
codebase over time. Every significant change session produces a snapshot
and a changelog entry so context is never lost.

## Structure

```
docs/project-metrics/
  README.md                    # This file
  CHANGELOG.md                 # Chronological log of all changes
  HEALTH.md                    # Deep-dive analysis of system health
  snapshots/
    2026-08-22.json            # First baseline snapshot
```

## How to use

After each significant change session:
1. Run the snapshot script (or manually count metrics)
2. Append a JSON snapshot to `snapshots/YYYY-MM-DD.json`
3. Add a changelog entry to `CHANGELOG.md`
4. Update `HEALTH.md` if structural concerns change

## Metrics tracked

- **LOC/KLOC** per module and total
- **File count** per module
- **Test count** and test-to-code ratio
- **API endpoint count**
- **Database models** count
- **Dependencies** count
- **Complexity hotspots** (files > 200 LOC)
- **Git commit count**
- **Architectural observations**