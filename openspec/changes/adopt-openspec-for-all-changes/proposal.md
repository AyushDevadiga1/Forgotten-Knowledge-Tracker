## Why

Every change and modification the project makes must have a durable OpenSpec record so the intent, design, and tasks of each change survive instead of living only in chat history or commit messages.

## What Changes

- Require an OpenSpec change for every future modification: features, bug fixes, tooling, and documentation.
- Broaden the audit pipeline so `patch-engineer` creates an OpenSpec change before every confirmed fix, not only behavior-changing ones.
- Encode the policy in the project rules (`AGENTS.v2.md`) and the `/audit` command.
- Every finding record references its OpenSpec change through the existing `OPENSPEC_CHANGE` field.

## Capabilities

### New Capabilities
None. This is a tooling/workflow change with no product behavior change, so the change opts out of specs (`skip_specs: true`).

### Modified Capabilities
None.

## Impact

- `.opencode/agents/audit-orchestrator.md` and `.opencode/agents/patch-engineer.md` pipeline rules
- `.opencode/skills/audit-patch/SKILL.md` and `.opencode/commands/audit.md`
- `AGENTS.v2.md` project rules
- All future work now enters OpenSpec first