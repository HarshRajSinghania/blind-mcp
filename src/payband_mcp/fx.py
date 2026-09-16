"""Currency conversion, so a cross-market comparison is not nonsense.

pay_bands reports the same role in every currency an employer posts it in.
Left as raw numbers that invites a wrong conclusion: GitLab's Polish band is
340,000 PLN against a US band of 187,200 USD, and anyone reading those side by
side sees Poland paying 1.8x. Converted, it is about 45%.

Rates come from the European Central Bank's daily reference rates via
Frankfurter, which needs no key and publishes the date each rate is for. Both
are reported alongside every converted figure, because a converted salary is
an estimate with a timestamp, not a published fact -- the published fact is
the figure in its own currency, which is always kept.

If the rate source cannot be reached, nothing is converted and the caller is
told why. A stale hardcoded table would be worse than no answer.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .http import CACHE_DIR

ENDPOINT = "https://api.frankfurter.dev/v1/latest?base={base}"
TIMEOUT = 15
# Reference rates are published once per working day, so a day of cache costs
# nothing in accuracy and keeps us off someone else's free service.
TTL = 24 * 3600

_memo: dict[str, dict[str, Any]] = {}


def _cache_file(base: str) -> Path:
    return CACHE_DIR / "fx" / f"{base.upper()}.json"


def rates(base: str = "USD", user_agent: str = "") -> dict[str, Any] | None:
    """{"date": ..., "rates": {CUR: multiplier}} for 1 unit of `base`."""
    base = base.upper()
    if base in _memo:
        return _memo[base]

    path = _cache_file(base)
    try:
        if path.exists() and time.time() - path.stat().st_mtime < TTL:
            data = json.loads(path.read_text())
            _memo[base] = data
            return data
    except (OSError, ValueError):
        pass

    req = urllib.request.Request(
        ENDPOINT.format(base=base), headers={"User-Agent": user_agent}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None

    data = {"date": payload.get("date"), "rates": payload.get("rates") or {}}
    data["rates"][base] = 1.0
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    except OSError:
        pass
    _memo[base] = data
    return data


def convert(
    amount: float, frm: str, to: str, table: dict[str, Any] | None
) -> float | None:
    """`amount` in `frm` expressed in `to`, using a table based on some third
    currency. Returns None rather than guessing when either side is missing."""
    if not table or frm == to:
        return amount if frm == to else None
    pair = table.get("rates") or {}
    source, target = pair.get(frm.upper()), pair.get(to.upper())
    if not source or not target:
        return None
    return amount / source * target
