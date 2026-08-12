# Durable Audit State

`.audit/` is the investigation memory for the recursive debugging system. It is deliberately separate from `openspec/`, which stores product intent and change artifacts.

## Layout

- `context/` — repository recon and candidate-specific context packs
- `findings/` — candidate and confirmed bug records
- `patterns/` — abstract root-cause patterns and sibling-search results
- `evidence/` — optional command/output artifacts that are too large for finding records
- `verification/` — final verification records

## Evidence rules

- Never mark a bug confirmed without concrete evidence.
- Never treat chat history as authoritative state.
- Do not store secrets, credentials, API keys, or sensitive environment values here.
- Prefer paths, commands, test names, and concise excerpts over giant logs.
