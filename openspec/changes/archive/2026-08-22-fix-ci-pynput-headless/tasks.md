## 1. Mock pynput globally in conftest.py

- [ ] 1.1 Add `_fake_module` helper and `sys.modules` stubs for `pynput`, `pynput.keyboard`, `pynput.mouse` at the top of `tracker_app/tests/conftest.py`, before any `tracker_app` imports
- [ ] 1.2 Also stub `psutil` at module level to prevent C extension import failures in minimal CI images

## 2. Remove redundant per-test mocking

- [ ] 2.1 Remove the `pynput` and `psutil` entries from `test_warmup.py`'s `loop_with_fakes` fixture (keep the tracker_app module fakes, only remove the two hardware dep stubs)

## 3. Verify

- [ ] 3.1 Run full test suite locally to confirm all 377 tests pass
- [ ] 3.2 Verify that `test_warmup.py` still passes after removing its pynput/psutil stubs
