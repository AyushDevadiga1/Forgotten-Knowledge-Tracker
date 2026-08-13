# FKT Project Rules — v3 Audit Layer

Keep this file short. It is always-on context.

- Repository behavior must be established from code, executable evidence, tests, specs, and observed runtime behavior. Do not treat guesses as facts.
- Do not perform unrelated refactors.
- Do not weaken tests to make them pass.
- Preserve existing public behavior unless a confirmed defect or an approved OpenSpec change requires otherwise.
- Use `docs/dependency-map/index.html` as a routing index for static call relationships. It is an approximation, not runtime truth.
- Reuse persisted audit context in `.audit/`; do not repeatedly rediscover already-established architecture.
- Scope investigations to the smallest connected neighborhood that can answer the current question; expand only when evidence requires it.
- Discovery/reproduction/verification agents are read-only. Only the patch agent may modify product code, and edits require approval.
- A suspicious implementation is not a confirmed bug until independently proven.
- For meaningful behavior changes, use the existing OpenSpec workflow. Do not invent repository-wide specs.
