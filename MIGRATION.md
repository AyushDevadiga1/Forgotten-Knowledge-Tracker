# FKT Audit v2 Migration

This package is an overlay for the existing FKT repository. It intentionally does not include or replace OpenSpec-generated files.

## Add

Copy these into the project root:

- `.opencode/agents/*` — v2 audit agents
- `.opencode/commands/audit.md` — `/audit` entry point
- `.opencode/skills/audit-*` — on-demand audit procedures
- `.audit/*` — durable audit state structure
- `AGENTS.v2.md` — replacement content for the debugging-specific part of the current `AGENTS.md`

## Preserve

Keep the OpenSpec-generated integrations already installed in:

- `openspec/`
- `.opencode/skills/openspec-*`
- `.opencode/commands/opsx-*`
- `.agent/`
- `.hermes/`

Do not overwrite those with this package.

## Replace

Your current `AGENTS.md` contains the old monolithic debugging protocol. Replace it with a short project-wide rules file by merging the useful repository rules from `AGENTS.v2.md` into your existing file.

Your current `.opencode/agents/adversarial-debugger.md` is the old all-in-one debugger. After the new agents are copied and tested, retire that file to avoid duplicate agent instructions.

Do not delete anything until the new `/audit` command is verified.

## Important permission behavior

Read-only agents intentionally have `edit: deny`. The patcher has `edit: ask`. This is defense-in-depth; do not globally switch the project to unrestricted permissions just to avoid approval prompts.

## First run

1. Start OpenCode from the repository root.
2. Confirm the v2 agents are visible.
3. Run `/audit` with a narrow scope first, for example a subsystem name.
4. Inspect `.audit/context/recon.md` and the first candidate records.
5. Only then run a repository-wide audit.

## OpenSpec interaction

Do not create a giant OpenSpec specification for the existing repository. Use OpenSpec when a behavior/change needs a durable intent artifact. Use `.audit/` for evidence, candidate findings, root-cause patterns, and verification.
