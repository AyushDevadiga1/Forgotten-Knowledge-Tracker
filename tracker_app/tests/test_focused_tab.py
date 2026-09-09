"""Focused-tab capture unit tests (Windows UIA path behind doubles).

The capture module is pure plumbing: resolve foreground -> process name ->
UIA walk -> FocusedTab, degrading to None on every failure. These tests pin
that contract with fake process-describer / UIA doubles so the module stays
testable on machines without a Windows desktop stack.
"""

import pytest

import tracker_app.tracking.focused_tab as ft


class _FakeEdit:
    def __init__(self, name: str, value: str):
        self._name = name
        self._value = value

    def window_text(self):
        return self._name

    def get_value(self):
        return self._value


class _FakeTab:
    def __init__(self, name: str, selected: bool):
        self._name = name
        self._selected = selected

    def window_text(self):
        return self._name

    def is_selected(self):
        return self._selected


class _FakeWindow:
    def __init__(self, edits=None, tabs=None):
        self._edits = edits or []
        self._tabs = tabs or []

    def descendants(self, control_type: str):
        if control_type == "Edit":
            return list(self._edits)
        if control_type == "TabItem":
            return list(self._tabs)
        return []


def _clear_and(monkeypatch, **fns):
    ft.clear_cache()
    for name, fn in fns.items():
        monkeypatch.setattr(ft, name, fn)


# ---------------------------------------------------------------------------
# get_focused_tab: process gating + degradation
# ---------------------------------------------------------------------------


def test_non_browser_foreground_returns_none_without_uia(monkeypatch):
    _foreground = lambda: (1, 10)
    calls = []
    _clear_and(
        monkeypatch,
        _foreground_window=_foreground,
        _process_name=lambda pid: "cmd.exe",
        _resolve=lambda *a: calls.append(a) or ft.FocusedTab("x", "y"),
    )
    assert ft.get_focused_tab() is None
    assert calls == [], "non-browser must not walk UIA"


def test_chrome_resolves_title_and_url(monkeypatch):
    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (7, 42),
        _process_name=lambda pid: "chrome.exe",
        _resolve=lambda pid, hwnd, proc: ft.FocusedTab("Two Sum - LeetCode", "https://leetcode.com/"),
    )
    tab = ft.get_focused_tab()
    assert tab.title == "Two Sum - LeetCode"
    assert tab.url == "https://leetcode.com/"


def test_firefox_degrades_to_title_only(monkeypatch):
    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (5, 33),
        _process_name=lambda pid: "firefox.exe",
        _resolve=lambda pid, hwnd, proc: ft.FocusedTab("Two Sum - LeetCode", None),
    )
    tab = ft.get_focused_tab()
    assert tab.title == "Two Sum - LeetCode"
    assert tab.url is None


def test_electron_class_is_not_a_browser(monkeypatch):
    # The Chrome_WidgetWin_1 class is shared with Electron apps; the gate must
    # key on process name, not the window class.
    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (9, 99),
        _process_name=lambda pid: "electron.exe",
        _resolve=lambda *a: _raise_(AssertionError("must not resolve non-browser")),
    )
    assert ft.get_focused_tab() is None


def _raise_(exc):
    raise exc


def test_foreground_lookup_exception_returns_none(monkeypatch):
    def boom():
        raise RuntimeError("no desktop")

    _clear_and(monkeypatch, _foreground_window=boom)
    assert ft.get_focused_tab() is None


def test_resolve_exception_returns_none(monkeypatch):
    def boom(pid, hwnd, proc):
        raise RuntimeError("uia dead")

    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (7, 42),
        _process_name=lambda pid: "chrome.exe",
        _resolve=boom,
    )
    assert ft.get_focused_tab() is None


def test_memoizes_same_hwnd_and_refreshes_on_change(monkeypatch):
    ft.clear_cache()
    snow = ft.time.time() - 1.0
    monkeypatch.setattr(ft, "time", type("T", (), {"time": lambda self: snow})())
    monkeypatch.setattr(ft, "_foreground_window", lambda: (1, 10))
    monkeypatch.setattr(ft, "_process_name", lambda pid: "chrome.exe")
    calls = []

    def resolve(pid, hwnd, proc):
        calls.append(hwnd)
        return ft.FocusedTab(f"tab-{hwnd}", None)

    monkeypatch.setattr(ft, "_resolve", resolve)
    assert ft.get_focused_tab().title == "tab-1"
    assert ft.get_focused_tab().title == "tab-1"  # cached, no re-resolve
    assert calls == [1]

    monkeypatch.setattr(ft, "_foreground_window", lambda: (2, 10))
    assert ft.get_focused_tab().title == "tab-2"
    assert calls == [1, 2]


# ---------------------------------------------------------------------------
# UIA walking: address bar URL + selected tab (defensive, never raises)
# ---------------------------------------------------------------------------


def test_url_from_address_bar_with_scheme():
    w = _FakeWindow(edits=[_FakeEdit("search box", ""), _FakeEdit("Address and search bar", "https://leetcode.com/problems/two-sum/")])
    assert ft._url_from_uia(w) == "https://leetcode.com/problems/two-sum/"


def test_url_any_edit_with_scheme():
    w = _FakeWindow(edits=[_FakeEdit("", "https://openai.com/")])
    assert ft._url_from_uia(w) == "https://openai.com/"


def test_url_none_when_no_edit_has_scheme():
    w = _FakeWindow(edits=[_FakeEdit("Address and search bar", ""), _FakeEdit("google search", "hello world")])
    assert ft._url_from_uia(w) is None


def test_url_none_when_no_edits():
    assert ft._url_from_uia(_FakeWindow()) is None


def test_selected_tab_title_via_is_selected():
    w = _FakeWindow(tabs=[_FakeTab("skills", False), _FakeTab("Two Sum - LeetCode", True)])
    assert ft._selected_tab_title(w, 1) == "Two Sum - LeetCode"


def test_degraded_selection_uses_window_title(monkeypatch):
    monkeypatch.setattr(ft, "_window_title", lambda hwnd: "Two Sum - LeetCode - Google Chrome")
    w = _FakeWindow(tabs=[_FakeTab("x", False), _FakeTab("y", False)])
    assert ft._selected_tab_title(w, 3) == "Two Sum - LeetCode - Google Chrome"


def test_zero_tabs_uses_window_title(monkeypatch):
    monkeypatch.setattr(ft, "_window_title", lambda hwnd: "Kaggle home - Mozilla Firefox")
    assert ft._selected_tab_title(_FakeWindow(), 3) == "Kaggle home - Mozilla Firefox"
def test_resolve_routes_by_process_name(monkeypatch):
    # Dispatch-table proof: chrome -> UIA walk, firefox -> title-only, any
    # other process -> None, and neither resolver may run for non-browsers.
    uia_calls, title_calls = [], []

    def fake_uia(hwnd):
        uia_calls.append(hwnd)
        return ft.FocusedTab("uia", "https://uia/")

    def fake_title(hwnd):
        title_calls.append(hwnd)
        return ft.FocusedTab("title", None)

    monkeypatch.setattr(ft, "_resolve_from_uia", fake_uia)
    monkeypatch.setattr(ft, "_resolve_from_title", fake_title)

    assert ft._resolve(1, 2, "chrome.exe").title == "uia"
    assert ft._resolve(3, 4, "firefox.exe").title == "title"
    assert ft._resolve(5, 6, "youtube.exe") is None
    assert uia_calls == [2]
    assert title_calls == [4]


def test_fallback_ok_disabled_never_uses_window_title(monkeypatch):
    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (7, 42),
        _process_name=lambda pid: "chrome.exe",
        _resolve=lambda pid, hwnd, proc: None,
        _window_title=lambda hwnd: "Two Sum - LeetCode - Google Chrome",
    )
    assert ft.get_focused_tab(fallback_ok=False) is None, \
        "fallback_ok=False must reject the window-title degradation"


def test_fallback_ok_enabled_falls_back_to_window_title(monkeypatch):
    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (7, 42),
        _process_name=lambda pid: "chrome.exe",
        _resolve=lambda pid, hwnd, proc: None,
        _window_title=lambda hwnd: "Two Sum - LeetCode - Google Chrome",
    )
    tab = ft.get_focused_tab()
    assert tab is not None
    assert tab.title == "Two Sum - LeetCode - Google Chrome"
    assert tab.url is None


def test_snapshot_refreshes_after_max_age_on_same_hwnd(monkeypatch):
    # The memoization must capitulate to _MAX_SNAPSHOT_AGE_S: same HWND/pid
    # re-resolves once the snapshot is old enough (fresh tabs in the same
    # window), and the boundary is exclusive (< age, not <=).
    class _Clock:
        def __init__(self, t):
            self.t = t

        def time(self):
            return self.t

    clock = _Clock(100.0)
    ft.clear_cache()
    monkeypatch.setattr(ft, "time", clock)
    monkeypatch.setattr(ft, "_foreground_window", lambda: (1, 10))
    monkeypatch.setattr(ft, "_process_name", lambda pid: "chrome.exe")
    calls = []

    def resolve(pid, hwnd, proc):
        calls.append(clock.t)
        return ft.FocusedTab(f"tab@{clock.t}", None)

    monkeypatch.setattr(ft, "_resolve", resolve)
    assert ft.get_focused_tab().title == "tab@100.0"
    clock.t = 104.9
    assert ft.get_focused_tab().title == "tab@100.0"  # still fresh (< 5s)
    assert calls == [100.0]
    clock.t = 105.0  # exactly _MAX_SNAPSHOT_AGE_S older
    assert ft.get_focused_tab().title == "tab@105.0"
    assert calls == [100.0, 105.0]


class _RaisingTab:
    def window_text(self):
        return "broken tab"

    def is_selected(self):
        raise RuntimeError("UIA probe dead")


def test_tab_probe_exception_falls_back_to_window_title(monkeypatch):
    monkeypatch.setattr(ft, "_window_title", lambda hwnd: "Two Sum - LeetCode - Google Chrome")
    w = _FakeWindow(tabs=[_RaisingTab(), _FakeTab("Two Sum - LeetCode", True)])
    assert ft._selected_tab_title(w, 3) == "Two Sum - LeetCode"


def test_url_edit_value_errors_and_non_str_skipped():
    class _BoomEdit:
        def window_text(self):
            return "broken"

        def get_value(self):
            raise RuntimeError("value dead")

    w = _FakeWindow(
        edits=[_BoomEdit(), _FakeEdit("", 42), _FakeEdit("", "https://leetcode.com/")]
    )
    assert ft._url_from_uia(w) == "https://leetcode.com/"


def test_process_name_failure_returns_none(monkeypatch):
    def boom(pid):
        raise RuntimeError("psutil dead")

    _clear_and(
        monkeypatch,
        _foreground_window=lambda: (7, 42),
        _process_name=boom,
    )
    assert ft.get_focused_tab() is None
