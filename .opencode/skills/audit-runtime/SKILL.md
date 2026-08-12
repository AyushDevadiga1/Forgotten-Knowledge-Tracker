---
name: audit-runtime
description: Runtime-focused procedure for finding observable failures under hostile scenarios.
---

Prefer small deterministic reproductions. Exercise malformed inputs, dependency failures, timeout/cancellation, retries, partial execution, stale state, and ordering/concurrency when relevant.

Capture command, input, environment assumptions, output, error, and expected result. Do not patch while hunting.
