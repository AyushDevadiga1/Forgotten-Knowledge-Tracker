---
name: audit-recon
description: Build a factual, bounded repository model before bug discovery.
---

Establish only what the repository evidence supports.

Read project instructions first. Identify architecture, entry points, critical paths, state/data flow, dependencies, tests, and verification commands. Inspect OpenSpec specs/changes if relevant. Record uncertainty explicitly.

Do not infer intended behavior solely from names. Prefer implementation, tests, schemas, runtime observations, and explicit docs.

Persist findings through the repository-recon agent to `.audit/context/recon.md`.
