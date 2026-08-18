# -*- coding: utf-8 -*-
"""Engine-shim + best-effort guard helpers shared across the adapter/bridge layers.

`debug_utils` is a game symbol: it exists in the running client but not under the
Python 3.13 test interpreter. Rather than copy-paste the guarded fallback import in
every module, they import `LOG_CURRENT_EXCEPTION` / `LOG_NOTE` / `LOG_PROD` from here
-- one place that resolves the real thing in-client and degrades to a no-op out of
client (so the engine-free helper modules still import under pytest).

`_safe` / `_safe_int` are the read-side guard idiom (run a getter, log + fall back to a
default on any failure) lifted here so more than one module can share them.

Adapter/bridge only -- the engine-free `domain/` layer must NOT import this. 2/3-compatible.
"""
import re
import traceback

# Dev-trace gate. LOG_CURRENT_EXCEPTION always fires (real errors, in `except` blocks
# only); LOG_NOTE is informational chatter that runs on the normal path (every refresh,
# hangar mount, listener re-arm and click) and would otherwise spam a player's
# python.log. So LOG_NOTE is routed through a gate that is a no-op unless _DEBUG -- flip
# _DEBUG to True only for a local dev build; the shipped mod stays quiet. LOG_PROD is a
# separate, always-on tier for a small curated set of low-volume diagnostics (boot
# marker, settings lifecycle, mount/placement) that ARE worth shipping.
_DEBUG = False

try:
    from debug_utils import LOG_NOTE as _LOG_NOTE
except Exception:
    def _LOG_NOTE(*args, **kwargs):
        pass

try:
    from debug_utils import LOG_ERROR as _LOG_ERROR
except Exception:
    def _LOG_ERROR(*args, **kwargs):
        pass


def LOG_NOTE(*args, **kwargs):
    """Informational trace -- suppressed unless _DEBUG so a shipped build never writes
    dev chatter to the player's python.log. Callers keep using LOG_NOTE unchanged."""
    if _DEBUG:
        _LOG_NOTE(*args, **kwargs)


def LOG_PROD(*args, **kwargs):
    """Production diagnostic -- always logged. Must stay low-volume and free of
    filesystem paths, usernames, and install dirs."""
    _LOG_NOTE(*args, **kwargs)


# Anchors a `File "<...>scripts\client\<rest>"` (or /-separated, or packed inside a
# .wotmod zip) traceback line down to the mod-relative tail, so a scrubbed traceback
# never carries this machine's username / install directory. Prefix-agnostic, so this
# already handles a UNC-rooted (`\\host\share\...`) path that happens to hit the anchor.
_SCRIPTS_CLIENT_RE = re.compile(r'File "[^"]*?([Ss]cripts[\\/][Cc]lient[\\/][^"]*)"')
# Whatever is left that's still a drive-rooted Windows path (`C:\...`) with no
# scripts/client anchor -- strip the drive+dirs, keep only the filename. Requires the
# drive-letter prefix so this can't re-match the mod-relative tail _SCRIPTS_CLIENT_RE
# just produced (which has no drive letter).
_WIN_ABS_PATH_RE = re.compile(r'[A-Za-z]:[\\/](?:[^\\/\r\n"]+[\\/])*([^\\/\r\n"]+)')
# Same for a UNC-rooted path (`\\host\share\...`) with no scripts/client anchor --
# requires the leading `\\` so it can't re-match the anchored tail (which has none).
_UNC_ABS_PATH_RE = re.compile(r'\\\\(?:[^\\/\r\n"]+[\\/])*([^\\/\r\n"]+)')
# Same for a POSIX-rooted path (`/...`). The negative lookbehind requires the leading
# `/` to start a fresh token (string/quote/whitespace start) so it can't fire mid a
# relative path like the "scripts/client/..." tail (whose slashes are preceded by a
# word character).
_POSIX_ABS_PATH_RE = re.compile(r'(?<![\w./\\])/(?:[^/\r\n"]+/)*([^/\r\n"]+)')


def _scrub_paths(text):
    """Trim absolute filesystem paths out of `text` (a traceback) down to a
    mod-relative or bare-filename tail. Pure stdlib (`re`), no game imports -- unit
    tests game-closed."""
    if not text:
        return text
    text = _SCRIPTS_CLIENT_RE.sub(lambda m: 'File "' + m.group(1) + '"', text)
    text = _WIN_ABS_PATH_RE.sub(lambda m: m.group(1), text)
    text = _UNC_ABS_PATH_RE.sub(lambda m: m.group(1), text)
    text = _POSIX_ABS_PATH_RE.sub(lambda m: m.group(1), text)
    return text


def LOG_CURRENT_EXCEPTION():
    """Log the currently-handled exception's traceback, scrubbed of absolute
    filesystem paths (no install dir / username in the player's python.log). Same
    zero-arg call form as debug_utils.LOG_CURRENT_EXCEPTION."""
    try:
        _LOG_ERROR(_scrub_paths(traceback.format_exc()))
    except Exception:
        pass


def _safe(fn, default):
    """Call `fn`; return its value, or `default` on None / any exception (logged)."""
    try:
        value = fn()
        return default if value is None else value
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return default


def _safe_int(fn, default):
    return int(_safe(fn, default))
