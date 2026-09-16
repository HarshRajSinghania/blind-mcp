"""Polite HTTP layer for teamblind.com.

Three things happen here and nowhere else: robots.txt is enforced, responses are
cached on disk, and requests are spaced out. Everything above this module can
assume a fetch is cheap and allowed.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import httpx

from . import __version__

BASE = "https://www.teamblind.com"


def env(name: str, default: str | None = None) -> str | None:
    """Read PAYBAND_<name>, honouring the BLIND_MCP_ prefix it used to have.

    The project was called blind-mcp until the pay tools became the point of
    it. Renaming the variables without a fallback would silently ignore a
    cache directory or a throttle someone had already set, which is the kind
    of breakage that looks like the tool misbehaving rather than like a
    rename.
    """
    return os.environ.get(f"PAYBAND_{name}") or os.environ.get(
        f"BLIND_MCP_{name}", default
    )


USER_AGENT = env(
    "USER_AGENT",
    f"payband-mcp/{__version__} (+https://github.com/dheerajjha/payband-mcp)",
)
CACHE_DIR = Path(env("CACHE_DIR") or Path.home() / ".cache" / "payband-mcp")
CACHE_TTL = int(env("CACHE_TTL", str(6 * 3600)))
MIN_INTERVAL = float(env("MIN_INTERVAL", "1.5"))

# Opt-in only. Blind's bot detection reacts badly to automated authenticated
# traffic (it fires an "automatic logout, code 2009" and invalidates the
# session), and every read path this server uses works fine anonymously.
# See README "Do I need to log in?" before setting this.
SESSION_COOKIE = os.environ.get("BLIND_COOKIE", "").strip()


class BlindBlocked(RuntimeError):
    """Blind's bot protection refused the request.

    Distinct from a 404: the company exists, we are simply not allowed in.
    Callers must not report this as "no results", which would read as an
    answer when it is an outage.
    """


class RobotsDenied(RuntimeError):
    """Raised when robots.txt disallows the path. Not caught anywhere: a denied
    path is a bug in the caller, not a runtime condition to recover from."""


class _Throttle:
    def __init__(self, min_interval: float) -> None:
        self._min = min_interval
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            gap = time.monotonic() - self._last
            if gap < self._min:
                time.sleep(self._min - gap)
            self._last = time.monotonic()


_throttle = _Throttle(MIN_INTERVAL)
_robots: urllib.robotparser.RobotFileParser | None = None
_robots_lock = threading.Lock()


def _robots_parser() -> urllib.robotparser.RobotFileParser:
    global _robots
    with _robots_lock:
        if _robots is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{BASE}/robots.txt")
            try:
                with httpx.Client(timeout=15, headers={"User-Agent": USER_AGENT}) as c:
                    rp.parse(c.get(f"{BASE}/robots.txt").text.splitlines())
            except httpx.HTTPError:
                # Unreachable robots.txt means we do not get to assume consent.
                rp.disallow_all = True
            _robots = rp
        return _robots


def allowed(url: str) -> bool:
    return _robots_parser().can_fetch(USER_AGENT, url)


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode()).hexdigest()[:20]
    host = urlparse(url).netloc.replace(":", "_")
    # Authenticated and anonymous responses must not share an entry, or setting
    # BLIND_COOKIE would silently replay logged-out HTML (and vice versa).
    scope = "auth" if SESSION_COOKIE else "anon"
    return CACHE_DIR / host / scope / f"{digest}.html"


_purged_this_process = False


def _purge_expired(force: bool = False) -> int:
    """Remove cache entries older than CACHE_TTL. Returns the number removed.

    Runs once per process: it walks the whole cache tree, which is far too
    expensive to repeat on every request.
    """
    global _purged_this_process
    if _purged_this_process and not force:
        return 0
    _purged_this_process = True
    if not CACHE_DIR.exists():
        return 0
    cutoff = time.time() - CACHE_TTL
    removed = 0
    for path in CACHE_DIR.rglob("*.html"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def fetch(path_or_url: str, *, force: bool = False) -> str:
    """GET a Blind page, honouring robots.txt, the disk cache and the throttle."""
    _purge_expired()
    url = path_or_url if path_or_url.startswith("http") else BASE + path_or_url

    if not allowed(url):
        raise RobotsDenied(
            f"robots.txt disallows {url}. Blind disallows /search/ for every "
            f"user-agent; use company topic pages or channels instead."
        )

    cached = _cache_path(url)
    if not force and cached.exists():
        if time.time() - cached.stat().st_mtime < CACHE_TTL:
            return cached.read_text(encoding="utf-8")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE

    _throttle.wait()
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)

    if resp.status_code == 403:
        raise BlindBlocked(
            "Blind returned 403 to an automated request. Since ~Sept 2026 it "
            "rejects every non-browser User-Agent site-wide -- curl and an "
            "empty UA are refused too, so this is not specific to this client. "
            "We do not spoof a browser to get around it. The ATS-backed pay "
            "tools (job_openings, pay_bands) are unaffected."
        )
    if "/session-out" in str(resp.url):
        raise RuntimeError(
            "Blind invalidated the session (code 2009). Unset BLIND_COOKIE — "
            "every read path here works anonymously."
        )
    resp.raise_for_status()

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(resp.text, encoding="utf-8")
    return resp.text
