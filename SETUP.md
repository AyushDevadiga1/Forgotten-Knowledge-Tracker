# OpenCode Adversarial Debugger Setup

## Files

- `AGENTS.md` — short, always-on project rules.
- `.opencode/agents/adversarial-debugger.md` — focused recursive debugging agent.
- `.opencode/commands/debug-hunt.md` — `/debug-hunt` command.

## Install

Copy these files into the root of the repository you want OpenCode to audit:

```text
your-project/
├── AGENTS.md
└── .opencode/
    ├── agents/
    │   └── adversarial-debugger.md
    └── commands/
        └── debug-hunt.md
```

Then start OpenCode from the repository root.

Run:

```text
/debug-hunt
```

You can also invoke the `adversarial-debugger` agent directly from OpenCode's agent picker.

## Important

If your repository already has an `AGENTS.md`, do NOT blindly overwrite it. Merge the short rules into the existing file.

If your repository already has `.opencode/agents/` or `.opencode/commands/`, keep the existing files and add these files.

The command deliberately does not put the full debugging methodology into the command prompt. The methodology lives in the dedicated agent so the task message stays small.

## Recommended workflow

1. Commit/stash your current work.
2. Start OpenCode at the repository root.
3. Run `/debug-hunt`.
4. Let the agent inspect and reproduce issues before editing.
5. Review the final diff and test output.
6. Run the hunt again after major architectural changes.

## Optional: project-specific commands

Add your real commands to `AGENTS.md`, for example:

```md
## Verification commands
- Install: `...`
- Unit tests: `...`
- Integration tests: `...`
- Lint: `...`
- Type-check: `...`
- Build: `...`
```

This gives the debugging agent concrete verification targets without bloating its core instructions.
