"""Public job-board APIs, for the pay ranges employers are legally made to publish.

Colorado, California, New York, Washington and Illinois require a salary range
on covered postings. Most other markets -- India, Singapore, much of the EU --
require nothing, so the same role at the same company is posted with a range in
Denver and without one in Bengaluru.

These are documented, public, JSON APIs intended to be read by machines. That
matters: everything here is a supported integration, not scraping, and it does
not break when a marketing site is redesigned.
"""

from __future__ import annotations

import html as _html
import json
import re
import urllib.error
import urllib.request
from typing import Any, Iterable

USER_AGENT = "blind-mcp/0.1.0 (+https://github.com/dheerajjha/blind-mcp)"
TIMEOUT = 30

GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
LEVER = "https://api.lever.co/v0/postings/{board}?mode=json"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"

# Greenhouse renders the legally-required range into its own element. Reading
# that is far more reliable than finding two dollar figures in prose.
_PAY_DIV = re.compile(r'<div class="pay-range">(.*?)</div>', re.S)
# Fallback for boards that inline the range in the body text instead.
_PAY_TEXT = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:k\b)?\s*[-–—]{1,2}\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(?:k\b)?",
    re.I,
)
_CURRENCY = re.compile(r"\b(USD|CAD|GBP|EUR|INR|SGD|AUD)\b")
_TAG = re.compile(r"<[^>]+>")


class BoardNotFound(LookupError):
    """No public job board for this company under the name we tried."""


def _get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            # Some boards emit raw control characters inside description HTML.
            return json.loads(resp.read().decode("utf-8"), strict=False)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            raise BoardNotFound(url) from exc
        raise


def _text(content: str | None) -> str:
    """Greenhouse ships HTML-escaped markup: unescape first, then drop tags."""
    return _TAG.sub(" ", _html.unescape(content or ""))


def _money(raw: str) -> float:
    value = float(raw.replace(",", ""))
    return value * 1000 if value < 1000 else value  # "$152k" style


def _pay_from_html(content: str | None) -> dict[str, Any] | None:
    raw = _html.unescape(content or "")
    block = _PAY_DIV.search(raw)
    # Two passes are needed. Greenhouse double-escapes: the first unescape
    # turns &lt;div&gt; into real markup but leaves &mdash; as an entity, and
    # the figures are separated by that entity plus tags, not whitespace.
    region = _html.unescape(_TAG.sub(" ", block.group(1) if block else raw))
    match = _PAY_TEXT.search(region)
    if not match:
        return None
    low, high = _money(match.group(1)), _money(match.group(2))
    if low > high:
        low, high = high, low
    currency = _CURRENCY.search(region)
    return {
        "min": low,
        "max": high,
        "currency": currency.group(1) if currency else "USD",
        "interval": "year",
        "source": "posting_pay_field" if block else "posting_text",
    }


def _posting(title, location, url, pay, company, board) -> dict[str, Any]:
    return {
        "title": title,
        "location": location or "",
        "url": url,
        "pay": pay,
        "company": company,
        "board": board,
    }


def _greenhouse(board: str) -> list[dict[str, Any]]:
    data = _get(GREENHOUSE.format(board=board))
    return [
        _posting(
            j.get("title"),
            (j.get("location") or {}).get("name"),
            j.get("absolute_url"),
            _pay_from_html(j.get("content")),
            j.get("company_name") or board,
            "greenhouse",
        )
        for j in data.get("jobs", [])
    ]


def _lever(board: str) -> list[dict[str, Any]]:
    data = _get(LEVER.format(board=board))
    if not isinstance(data, list):
        raise BoardNotFound(board)
    out = []
    for j in data:
        body = (j.get("descriptionPlain") or "") + " " + (j.get("description") or "")
        out.append(
            _posting(
                j.get("text"),
                (j.get("categories") or {}).get("location"),
                j.get("hostedUrl"),
                _pay_from_html(body),
                board,
                "lever",
            )
        )
    return out


def _ashby(board: str) -> list[dict[str, Any]]:
    data = _get(ASHBY.format(board=board))
    out = []
    for j in data.get("jobs", []):
        pay = None
        # Ashby is the only board that publishes this as real numbers.
        for tier in (j.get("compensation") or {}).get("compensationTiers") or []:
            for comp in tier.get("components") or []:
                if comp.get("compensationType") == "Salary" and comp.get("maxValue"):
                    pay = {
                        "min": float(comp.get("minValue") or comp["maxValue"]),
                        "max": float(comp["maxValue"]),
                        "currency": comp.get("currencyCode") or "USD",
                        "interval": (comp.get("interval") or "year").lower(),
                        "source": "structured",
                    }
                    break
            if pay:
                break
        out.append(
            _posting(
                j.get("title"),
                j.get("location"),
                j.get("jobUrl"),
                pay or _pay_from_html(j.get("descriptionHtml")),
                board,
                "ashby",
            )
        )
    return out


_BOARDS = (("greenhouse", _greenhouse), ("ashby", _ashby), ("lever", _lever))


def board_slugs(company: str) -> list[str]:
    """Plausible job-board tokens for a company name, most likely first."""
    base = company.strip().lower()
    collapsed = re.sub(r"[^a-z0-9]+", "", base)
    hyphen = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    seen: set[str] = set()
    return [s for s in (collapsed, hyphen, base) if s and not (s in seen or seen.add(s))]


def fetch_postings(
    company: str, board: str | None = None
) -> tuple[str, list[dict[str, Any]]]:
    """Find a company's public job board and return every posting on it.

    Tries Greenhouse, then Ashby, then Lever against each plausible slug. Pass
    `board` as "greenhouse:slug" (or ashby:/lever:) to skip the guessing when
    the token does not follow from the company name -- it is visible in the
    careers-page URL, e.g. job-boards.greenhouse.io/<slug>.

    Raises BoardNotFound if nothing answers.
    """
    if board:
        name, _, slug = board.partition(":")
        loader = dict(_BOARDS).get(name)
        if not loader:
            raise ValueError(
                f"Unknown board {name!r}; expected one of "
                f"{', '.join(n for n, _ in _BOARDS)}."
            )
        postings = loader(slug or board_slugs(company)[0])
        if not postings:
            raise BoardNotFound(f"{board} has no postings.")
        return f"{name}:{slug}", postings

    for slug in board_slugs(company):
        for name, loader in _BOARDS:
            try:
                postings = loader(slug)
            except (BoardNotFound, urllib.error.URLError, json.JSONDecodeError):
                continue
            if postings:
                return f"{name}:{slug}", postings
    raise BoardNotFound(
        f"No public Greenhouse, Ashby or Lever board found for {company!r} "
        f"(tried slugs {board_slugs(company)}). Two common reasons: the board "
        f"token differs from the company name -- open their careers page and "
        f"read it out of the URL (job-boards.greenhouse.io/<slug>, "
        f"jobs.ashbyhq.com/<slug>, jobs.lever.co/<slug>), then pass "
        f"board='greenhouse:<slug>' -- or the employer self-hosts and is on "
        f"none of these boards, which is the case for Google, Meta, Amazon "
        f"and Apple."
    )


def matching(postings: Iterable[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    """Postings whose title contains every significant word in `role`."""
    words = [w for w in re.findall(r"[a-z0-9+#]{2,}", role.lower())]
    if not words:
        return list(postings)
    out = []
    for p in postings:
        title = (p.get("title") or "").lower()
        if all(w in title for w in words):
            out.append(p)
    return out
