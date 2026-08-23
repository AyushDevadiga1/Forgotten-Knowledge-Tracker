## Context

`loop.py` imports `pynput` at module level (line 11). Any test that touches `loop` — even indirectly — triggers pynput's X server connection attempt. In headless CI (Docker `python:3.11-slim`), there is no DISPLAY variable and no Xvfb, so the import raises `ImportError`.

The existing pattern in `test_warmup.py` (lines 36-40) already solves this for its own tests by injecting fake modules into `sys.modules` before importing `loop`. This change moves that pattern to `conftest.py` so it applies globally.

## Goals / Non-Goals

**Goals:**
- CI tests pass in headless environments without installing Xvfb
- No production code changes
- Minimal diff — reuse existing `test_warmup.py` pattern

**Non-Goals:**
- Refactoring `loop.py` to lazy-import pynput (would change production behavior)
- Installing Xvfb in CI (fragile, adds Docker complexity)
- Supporting real pynput behavior in tests (tests mock the tracking pipelines anyway)

## Decisions

**Decision 1: Mock via `sys.modules` in `conftest.py`**
- Alternatives: (A) Lazy-import pynput in `loop.py`, (B) Install Xvfb in CI, (C) Mock per-test in each test file
- Rationale: `sys.modules` stubs are set before pytest collects any test module, so pynput never initializes. This is the same approach `test_warmup.py` already uses successfully. Lazy import changes production code. Xvfb adds Docker weight. Per-test mocking duplicates effort.

**Decision 2: Also mock `psutil` at global scope**
- Rationale: `psutil` is also imported at module level in `loop.py`. While psutil doesn't fail in headless environments, it's a C extension that may not be available in minimal CI images. Pre-emptive mocking avoids future breakage.

## Risks / Trade-offs

- **Risk**: Fake pynput modules may not cover all attributes accessed by other code paths. → **Mitigation**: Tests that exercise pynput-specific behavior (listener creation, keyboard callbacks) are not expected to work with fakes; those tests already mock at a higher level. The fake modules only need to satisfy the import.
- **Trade-off**: Tests that actually test pynput integration won't work. → Acceptable: integration tests for pynput should run in a headed environment, not in CI.
