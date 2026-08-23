import os
import sys
import types

# pynput requires an X display; psutil is a C extension that may be absent in
# minimal CI images. Both are imported at module level in loop.py, so any test
# that touches loop fails in headless environments. Stub them globally before
# any tracker_app code is loaded.  (Pattern from test_warmup.py lines 36-40.)


def _fake_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


sys.modules.setdefault("psutil", _fake_module("psutil"))
sys.modules.setdefault("pynput", _fake_module("pynput"))
sys.modules.setdefault("pynput.keyboard", _fake_module("pynput.keyboard", Listener=object))
sys.modules.setdefault("pynput.mouse", _fake_module("pynput.mouse", Listener=object))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DEBUG", "true")

# Import config before pinning the auth state so first-run SECRET_KEY/API_KEY
# auto-generation happens exactly once and deterministically.
import tracker_app.config  # noqa: F401

# The API tests exercise endpoints without credentials. Force an empty API_KEY
# for this process (load_dotenv never overrides existing vars), which disables
# both auth gates regardless of what a developer's real .env contains.
os.environ["API_KEY"] = ""
