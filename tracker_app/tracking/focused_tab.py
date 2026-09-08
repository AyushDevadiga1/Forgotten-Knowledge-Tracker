"""Focused browser tab capture via Windows UI Automation (Windows only).

Reads the foreground browser window's focused tab (title + URL) using
pywinauto's UIA backend, gated by process name because the
`Chrome_WidgetWin_1` window class is shared with Electron apps. Firefox does
not expose a tab strip via UIA, so it degrades to window-title parsing.

Every failure (non-Windows, non-browser foreground, UIA unavailable, odd tree
shape) degrades to `None` without raising, so the tracking loop never blocks
or crashes on capture problems.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("FocusedTab")

# Browsers whose address bar / tab strip are reachable through UIA.
_UIA_BROWSER_PROCESSES = frozenset({"chrome.exe", "msedge.exe"})
# Firefox exposes no UIA tab strip; use the window title only.
_TITLE_FALLBACK_PROCESSES = frozenset({"firefox.exe"})
_ALL_BROWSER_PROCESSES = _UIA_BROWSER_PROCESSES | _TITLE_FALLBACK_PROCESSES

# Cap the stored snapshot age to bound staleness when tabs change inside a
# window that keeps the same HWND (e.g. switching tabs in Chrome).
_MAX_SNAPSHOT_AGE_S = 5.0

# pywinauto must not be imported at module load: non-Windows installs (CI,
# Linux dev machines) must import this module safely.
_pywinauto = None


def _lazy_pywinauto():
    global _pywinauto
    if _pywinauto is None:
        from pywinauto import Desktop

        _pywinauto = Desktop
    return _pywinauto


@dataclass(frozen=True)
class FocusedTab:
    """Focused browser tab as exposed to the intent gate."""

    title: str
    url: Optional[str] = None


_CACHE: dict = {"hwnd": None, "pid": None, "tab": None, "ts": 0.0}


def _foreground_window() -> Optional[Tuple[int, int]]:
    """Return (hwnd, pid) of the foreground window, or None on any failure."""
    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return hwnd, pid
    except Exception as e:
        logger.debug("foreground window lookup failed: %s", e)
        return None


def _process_name(pid: int) -> Optional[str]:
    try:
        import psutil

        return str(psutil.Process(pid).name()).lower()
    except Exception as e:
        logger.debug("process name lookup failed for pid %s: %s", pid, e)
        return None


def _window_title(hwnd: int) -> Optional[str]:
    try:
        import win32gui

        return str(win32gui.GetWindowText(hwnd) or "").strip() or None
    except Exception as e:
        logger.debug("window title lookup failed for hwnd %s: %s", hwnd, e)
        return None


def _url_from_uia(window) -> Optional[str]:
    """Best-effort focused URL from the address-bar Edit (Chrome/Edge)."""
    try:
        edits = [c for c in window.descendants(control_type="Edit")]
    except Exception as e:
        logger.debug("edit enumeration failed: %s", e)
        return None
    if not edits:
        return None

    for edit in edits:
        try:
            value = edit.get_value() or ""
        except Exception:
            value = ""
        if not isinstance(value, str):
            continue
        value = value.strip()
        if "://" in value:
            return value

    # Chrome renders the address bar with the name "Address and search bar"
    # even when empty; use its WHOLE value only if it still looks like a URL.
    for edit in edits:
        try:
            name = str(edit.window_text() or "").strip().lower()
        except Exception:
            continue
        if name in ("address and search bar", "address bar"):
            try:
                value = (edit.get_value() or "").strip()
            except Exception:
                continue
            if "://" in value:
                return value
    return None


def _selected_tab_title(window, hwnd: int) -> Optional[str]:
    """Selected tab title via UIA TabItem, falling back to the window title."""
    try:
        tabs = [c for c in window.descendants(control_type="TabItem")]
    except Exception as e:
        logger.debug("tab enumeration failed: %s", e)
        tabs = []
    for tab in tabs:
        try:
            if tab.is_selected():
                name = str(tab.window_text() or "").strip()
                if name:
                    return name
        except Exception as e:
            logger.debug("tab probe failed: %s", e)
            continue
    return _window_title(hwnd)


def _resolve_from_uia(hwnd: int) -> Optional[FocusedTab]:
    try:
        Desktop = _lazy_pywinauto()
        window = Desktop(backend="uia").window(handle=hwnd)
    except Exception as e:
        logger.debug("UIA attach failed for hwnd %s: %s", hwnd, e)
        return None

    title = _selected_tab_title(window, hwnd)
    if not title:
        return None
    return FocusedTab(title=title, url=_url_from_uia(window))


def _resolve_from_title(hwnd: int) -> Optional[FocusedTab]:
    title = _window_title(hwnd)
    if not title:
        return None
    return FocusedTab(title=title, url=None)


def _resolve(pid: int, hwnd: int, proc: str) -> Optional[FocusedTab]:
    if proc in _UIA_BROWSER_PROCESSES:
        return _resolve_from_uia(hwnd)
    if proc in _TITLE_FALLBACK_PROCESSES:
        return _resolve_from_title(hwnd)
    return None


def get_focused_tab(fallback_ok: bool = True) -> Optional[FocusedTab]:
    """Return the focused browser tab (title + URL) or None.

    The foreground window is resolved to its process name; only supported
    browsers are inspected (the Chrome_WidgetWin_1 class alone is not proof of
    Chrome - Electron apps share it). Results are memoized per foreground
    HWND/pid to avoid per-cycle UIA cost; the snapshot is refreshed when the
    HWND changes or when it is older than _MAX_SNAPSHOT_AGE_S.

    `fallback_ok` additionally permits the window-title fallback (Firefox, or
    a UIA shape that hides the selected tab). Returns None - never raises -
    for non-browsers and on any capture failure.
    """
    try:
        fg = _foreground_window()
        if fg is None:
            return None
        hwnd, pid = fg

        now = time.time()
        if (
            _CACHE["hwnd"] == hwnd
            and _CACHE["pid"] == pid
            and _CACHE["tab"] is not None
            and now - _CACHE["ts"] < _MAX_SNAPSHOT_AGE_S
        ):
            return _CACHE["tab"]

        proc = _process_name(pid)
        if proc not in _ALL_BROWSER_PROCESSES:
            _CACHE.update({"hwnd": hwnd, "pid": pid, "tab": None, "ts": now})
            return None

        tab = _resolve(pid, hwnd, proc)
        if tab is None and fallback_ok:
            # Last resort: a browser whose tab strip UIA does not expose (or a
            # hiccup in the walk) still degrades to its window title.
            tab = _resolve_from_title(hwnd)
        _CACHE.update({"hwnd": hwnd, "pid": pid, "tab": tab, "ts": now})
        return tab
    except Exception as e:
        # Never raise into the tracking loop - a capture hiccup degrades to None.
        logger.debug("focused-tab capture failed: %s", e)
        return None


def clear_cache() -> None:
    """Reset the memoized snapshot (test hook)."""
    _CACHE.update({"hwnd": None, "pid": None, "tab": None, "ts": 0.0})
