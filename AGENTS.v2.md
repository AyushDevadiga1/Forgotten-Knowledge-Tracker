# FKT Project Rules — v2

- Treat repository behavior and explicit project artifacts as evidence; do not invent requirements.
- Keep changes scoped; no unrelated refactors.
- Never weaken tests or assertions just to make checks pass.
- Discover the repository's actual test/build/lint/type-check commands before changing code.
- For audit work, hypotheses are not facts. Confirmation requires concrete evidence.
- Confirmed root causes must trigger a search for semantically related sibling instances.
- Use `.audit/` for durable debugging evidence and `openspec/` for intent/change artifacts.
- Require an OpenSpec change for every modification: features, bug fixes, tooling, and docs. Never edit code without one; never silently rewrite intended behavior.
- Do not place the detailed audit methodology in this file; use the dedicated audit agents/skills.
