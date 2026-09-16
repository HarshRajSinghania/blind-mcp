"""Seniority inferred from a job title, and what that implies about a band.

Reporting one range for "forward deployed" at Databricks gives USD
140,400-320,200 -- a 2.3x spread covering five different jobs, and a number
nobody is ever offered. Split by seniority it resolves into bands people are
actually hired against, the largest of which (Sr. FDE, 182,000-250,208) carries
48 of the postings.

Titles are messy and this is a heuristic. It keys off explicit seniority
markers only and returns `unspecified` rather than guessing, and every result
carries the titles it was derived from so a caller can check the work.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Ordered: the first match wins, so compound markers ("Sr. Manager") must be
# tested before their parts ("Manager").
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("intern", re.compile(r"\b(intern|internship|co-?op)\b", re.I)),
    ("vp", re.compile(r"\b(vp|vice[- ]president|svp|evp)\b", re.I)),
    ("director", re.compile(r"\b(sr\.?|senior)[\s,]+director\b|\bdirector\b", re.I)),
    ("senior_manager", re.compile(r"\b(sr\.?|senior)[\s,]+(manager|mgr)\b", re.I)),
    ("principal", re.compile(r"\bprincipal\b", re.I)),
    ("distinguished", re.compile(r"\b(distinguished|fellow)\b", re.I)),
    ("staff", re.compile(r"\b(sr\.?|senior)[\s,]+staff\b|\bstaff\b", re.I)),
    ("lead", re.compile(r"\b(lead|tech lead|tl)\b", re.I)),
    ("manager", re.compile(r"\b(manager|mgr|head of)\b", re.I)),
    ("senior", re.compile(r"\b(sr\.?|senior)\b|\b(iii|3)\b", re.I)),
    ("junior", re.compile(r"\b(jr\.?|junior|associate|entry[- ]level|\bi\b|\b1\b)\b", re.I)),
]

# Rough ascending order, for reporting steps between adjacent levels. Titles
# that mean different things at different companies (lead vs staff vs manager)
# are inherently unordered against each other; this is a reporting convenience,
# not a claim about any company's ladder.
ORDER = [
    "intern", "junior", "mid", "senior", "staff", "lead", "principal",
    "distinguished", "manager", "senior_manager", "director", "vp",
    "unspecified",
]


def classify(title: str) -> str:
    """Seniority marker in a title, or 'mid' when a title carries none.

    Caveat worth passing on to whoever reads the output: some IC titles
    contain a seniority word that is really part of the role name --
    "Engagement Manager" is an individual contributor at most consultancies
    but classifies as `manager` here. The titles are always returned
    alongside, so the mistake is visible rather than silent.
    """
    if not title:
        return "unspecified"
    for level, pattern in _RULES:
        if pattern.search(title):
            return level
    return "mid"


def _round(value: float) -> float:
    return round(value, 2)


def summarise(postings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Collapse postings that share a pay band into the band itself.

    Databricks posts the identical Sr. FDE band across 48 listings, one per
    industry vertical. Counting postings makes that look like 48 data points;
    it is one band, advertised 48 times. Both numbers are reported so the
    difference is visible.
    """
    priced = [p for p in postings if p.get("pay")]
    if not priced:
        return None

    tally: dict[tuple[float, float], int] = {}
    for p in priced:
        key = (p["pay"]["min"], p["pay"]["max"])
        tally[key] = tally.get(key, 0) + 1

    modal_key, modal_count = max(tally.items(), key=lambda kv: (kv[1], -kv[0][0]))
    lows = sorted(k[0] for k in tally)
    highs = sorted(k[1] for k in tally)

    spread = _round(modal_key[1] / modal_key[0]) if modal_key[0] else None
    return {
        "low": lows[0],
        "high": highs[-1],
        "typical": {"min": modal_key[0], "max": modal_key[1]},
        # How much the band actually narrows things down. Employers differ
        # wildly: Databricks posts tight per-level bands (x1.37), Figma posts
        # one x2.5 band spanning its whole ladder, and Anthropic sometimes
        # posts a single figure. A wide band is a real published range, not a
        # parse error -- it just carries little information.
        "spread": spread,
        "precision": (
            "point" if spread == 1.0
            else "tight" if spread and spread < 1.5
            else "wide" if spread and spread >= 1.8
            else "normal"
        ),
        "typical_seen_in_postings": modal_count,
        "distinct_bands": len(tally),
        "postings": len(priced),
        "currency": priced[0]["pay"]["currency"],
        "titles": sorted({p["title"] for p in priced})[:6],
    }


def band_width_ratio(bands: Iterable[dict[str, Any]]) -> float | None:
    """The ceiling-to-floor ratio, when a company applies one consistently.

    Databricks builds every band as floor x 1.375, so a quoted floor already
    determines the ceiling -- useful to know before treating the top of a
    range as negotiable. Returns None when the ratios disagree, which is the
    more common case and means the company has no single rule.
    """
    ratios = [
        b["typical"]["max"] / b["typical"]["min"]
        for b in bands
        if b and b["typical"]["min"]
    ]
    if len(ratios) < 2:
        return None
    if max(ratios) - min(ratios) > 0.02:  # not a consistent rule
        return None
    return _round(sum(ratios) / len(ratios))


def level_steps(by_level: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Midpoint increase between adjacent levels that both have a band.

    Ratios travel between markets far better than absolute figures do: a US
    senior-over-mid step is a reasonable prior for the same company's step in
    a market that publishes nothing.
    """
    present = [lvl for lvl in ORDER if lvl in by_level and by_level[lvl]]
    steps = []
    for lower, upper in zip(present, present[1:]):
        a, b = by_level[lower]["typical"], by_level[upper]["typical"]
        mid_a, mid_b = (a["min"] + a["max"]) / 2, (b["min"] + b["max"]) / 2
        if mid_a:
            steps.append({
                "from": lower,
                "to": upper,
                "midpoint_increase_pct": _round(100 * (mid_b - mid_a) / mid_a),
            })
    return steps
