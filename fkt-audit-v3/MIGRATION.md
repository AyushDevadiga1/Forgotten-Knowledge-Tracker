# v2 → v3 migration

1. Back up/commit current work.
2. Keep OpenSpec-generated files under `.opencode/skills/openspec-*` and `.opencode/commands/opsx-*`.
3. Add the v3 agents, audit skills, `/audit` command, and `.audit/` state folders.
4. Replace the duplicated old audit methodology in `AGENTS.md` with the short project rules from `AGENTS.v3.md`, preserving any real FKT-specific instructions.
5. Retire the old monolithic `adversarial-debugger.md` after the first successful v3 smoke test.
6. Start a fresh OpenCode session.
7. Select `audit-orchestrator` and run `/audit quick` on a small subsystem first.

Do not start with `/audit full`.
