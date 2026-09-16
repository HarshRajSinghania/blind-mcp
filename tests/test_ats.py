"""Job-board parsing tests. Offline: every input here is a literal.

The payloads are shaped like the real ones, including the escaping quirks,
because those quirks are where every bug so far has lived.
"""

from __future__ import annotations

from blind_mcp import ats


def test_greenhouse_double_escaped_pay_element():
    """Greenhouse escapes twice and separates the figures with markup.

    One unescape reveals the tags but leaves `&mdash;` an entity, so the two
    figures are divided by `</span><span class="divider">&mdash;</span><span>`
    rather than by a dash. Both regressions were real.
    """
    content = (
        "&lt;div class=&quot;pay-range&quot;&gt;&lt;span&gt;$152,900&lt;/span&gt;"
        "&lt;span class=&quot;divider&quot;&gt;&amp;mdash;&lt;/span&gt;"
        "&lt;span&gt;$210,155 USD&lt;/span&gt;&lt;/div&gt;"
    )
    pay = ats._pay_from_html(content)
    assert pay == {
        "min": 152900.0,
        "max": 210155.0,
        "currency": "USD",
        "interval": "year",
        "source": "posting_pay_field",
    }


def test_pay_falls_back_to_body_text():
    pay = ats._pay_from_html("<p>The range for this role is $120,000 - $160,000 CAD.</p>")
    assert (pay["min"], pay["max"], pay["currency"]) == (120000.0, 160000.0, "CAD")
    assert pay["source"] == "posting_text"


def test_k_suffixed_and_reversed_ranges_are_normalised():
    assert ats._money("152") == 152000.0     # "$152k"
    assert ats._money("152,900") == 152900.0
    pay = ats._pay_from_html("<p>$210,155 — $152,900 USD</p>")
    assert pay["min"] < pay["max"]


def test_no_pay_returns_none_not_a_guess():
    assert ats._pay_from_html("<p>Competitive salary and equity.</p>") is None
    assert ats._pay_from_html(None) is None


def test_matching_requires_every_word_in_the_title():
    posts = [
        {"title": "AI Engineer - FDE (Forward Deployed Engineer)"},
        {"title": "Forward Deployed Engineer, Public Sector"},
        {"title": "Software Engineer, Deployed Systems"},
        {"title": "Account Executive"},
    ]
    hits = ats.matching(posts, "forward deployed")
    assert len(hits) == 2
    assert all("forward" in h["title"].lower() for h in hits)


def test_board_slugs_are_ordered_and_unique():
    slugs = ats.board_slugs("Goldman Sachs")
    assert slugs[0] == "goldmansachs"
    assert "goldman-sachs" in slugs
    assert len(slugs) == len(set(slugs))


def test_summarise_spans_the_whole_band():
    from blind_mcp import levels
    band = [
        {"title": "Engineer", "pay": {"min": 100.0, "max": 200.0, "currency": "USD"}},
        {"title": "Engineer", "pay": {"min": 150.0, "max": 300.0, "currency": "USD"}},
        {"title": "Engineer", "pay": {"min": 120.0, "max": 250.0, "currency": "USD"}},
    ]
    s = levels.summarise(band)
    assert (s["low"], s["high"]) == (100.0, 300.0)
    assert s["postings"] == 3
    assert s["distinct_bands"] == 3


def test_explicit_board_rejects_unknown_provider():
    import pytest
    with pytest.raises(ValueError, match="Unknown board"):
        ats.fetch_postings("Acme", board="workday:acme")


def test_board_not_found_explains_how_to_recover():
    """A dead end should say what to do next, not just that it failed."""
    try:
        ats._BOARDS_ORIGINAL = ats._BOARDS
        ats._BOARDS = ()               # force every loader to be skipped
        ats.fetch_postings("Nonexistent Co")
    except ats.BoardNotFound as exc:
        msg = str(exc)
        assert "board='greenhouse:<slug>'" in msg   # the recovery path
        assert "self-host" in msg                    # the other explanation
    finally:
        ats._BOARDS = ats._BOARDS_ORIGINAL
