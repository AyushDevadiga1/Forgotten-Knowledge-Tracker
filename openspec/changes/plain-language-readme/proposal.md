## Why

The README explains FKT to engineers but assumes technical knowledge everywhere. A person with no technical background (a student, a stakeholder, a non-technical collaborator) cannot tell what the app does, whether it is safe to run, or how to try it. Documentation should open with a plain-language explanation and keep the technical content clearly separated.

## What Changes

- Rewrite the README so the top explains, in everyday language, what FKT is, what problem it solves, and how it behaves.
- Explain the app's behavior with simple analogies and a step-by-step story instead of acronyms (OCR, CLE, SM-2, RandomForest).
- Keep the privacy story in plain English near the top.
- Move setup commands and technical detail into a clearly marked "For technical readers" section without losing the quick start, tests, config, and troubleshooting material.

## Capabilities

### New Capabilities
None. Docs-only change; the change opts out of specs (`skip_specs: true`).

### Modified Capabilities
None.

## Impact

- `README.md` (project documentation)
- No code, behavior, or dependencies change.