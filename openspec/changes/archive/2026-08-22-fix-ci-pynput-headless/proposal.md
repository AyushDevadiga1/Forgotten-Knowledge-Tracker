## Why

CI tests fail on push because `pynput` is imported at module level in `loop.py` and immediately tries to connect to an X server. The CI Docker container (`python:3.11-slim`) is headless — no DISPLAY, no Xvfb — so the import raises `ImportError: this platform is not supported`. This blocks all CI runs.

## What Changes

- Add `pynput` module mocking to `tracker_app/tests/conftest.py` using `sys.modules` stubs, applied before any `tracker_app` imports
- Remove per-test pynput mocking from `test_warmup.py` (now handled globally)
- No production code changes

## Capabilities

### New Capabilities
None — this is a test infrastructure fix, not a behavior change.

### Modified Capabilities
None — no spec-level behavior changes.

## Impact

- `tracker_app/tests/conftest.py`: Add pynput sys.modules stubs at top
- `tracker_app/tests/test_warmup.py`: Remove redundant pynput mocking (now global)
