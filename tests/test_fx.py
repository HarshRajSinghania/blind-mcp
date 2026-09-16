"""Conversion, and what happens when rates cannot be had. No network."""

from payband_mcp import fx, server

TABLE = {"date": "2026-09-15", "rates": {"USD": 1.0, "GBP": 0.74166, "PLN": 3.7612}}


def test_convert_uses_the_table_in_both_directions():
    assert round(fx.convert(340_000, "PLN", "USD", TABLE)) == 90_397
    assert round(fx.convert(100_000, "USD", "GBP", TABLE)) == 74_166
    assert fx.convert(1_000, "USD", "USD", TABLE) == 1_000


def test_convert_refuses_rather_than_guesses():
    assert fx.convert(1_000, "XYZ", "USD", TABLE) is None
    assert fx.convert(1_000, "USD", "XYZ", TABLE) is None
    assert fx.convert(1_000, "PLN", "USD", None) is None


def _priced(currency, low, high, n):
    return [
        {"title": "Engineer", "location": "X", "url": "u",
         "pay": {"min": low, "max": high, "currency": currency, "interval": "year"}}
        for _ in range(n)
    ]


def test_markets_never_compares_currencies_without_a_rate(monkeypatch):
    """340,000 PLN beside 187,200 USD reads as Poland paying more. It is not."""
    monkeypatch.setattr(fx, "rates", lambda *a, **k: None)
    rows, meta = server._by_market(
        _priced("USD", 139_200, 235_200, 38) + _priced("PLN", 272_000, 408_000, 8),
        "USD",
    )
    assert meta is None
    assert all("vs_largest_market" not in r for r in rows)
    assert all(not any(k.startswith("typical_in_") for k in r) for r in rows)


def test_markets_converts_and_dates_the_rate(monkeypatch):
    monkeypatch.setattr(fx, "rates", lambda *a, **k: TABLE)
    rows, meta = server._by_market(
        _priced("USD", 139_200, 235_200, 38) + _priced("PLN", 272_000, 408_000, 8),
        "USD",
    )
    assert meta["rate_date"] == "2026-09-15"
    poland = next(r for r in rows if r["currency"] == "PLN")
    # The published figure survives untouched next to the estimate.
    assert poland["typical"] == {"min": 272_000, "max": 408_000}
    assert poland["typical_in_USD"] == {"min": 72_317, "max": 108_476}
    assert poland["vs_largest_market"] == 0.48


def test_a_single_market_needs_no_rates(monkeypatch):
    monkeypatch.setattr(
        fx, "rates", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fetched"))
    )
    rows, meta = server._by_market(_priced("USD", 1, 2, 3), "USD")
    assert meta is None and len(rows) == 1


def _posting(currency, low, high):
    return {"title": "Senior Engineer", "location": "X", "url": "u",
            "company": "c", "board": "b",
            "pay": {"min": low, "max": high, "currency": currency,
                    "interval": "year", "source": "posting_text"}}


def test_market_rate_ranks_by_pay_not_by_exchange_rate(monkeypatch):
    """340,000 PLN sorts above 187,200 USD numerically and is worth half."""
    from payband_mcp import ats

    boards = {
        "PolandCo": [_posting("PLN", 272_000, 408_000)],
        "USCo": [_posting("USD", 139_200, 235_200)],
    }
    monkeypatch.setattr(fx, "rates", lambda *a, **k: TABLE)
    monkeypatch.setattr(
        ats, "fetch_postings", lambda company, board=None, role="": ("b", boards[company])
    )

    result = server.market_rate("engineer", ["PolandCo", "USCo"], level="senior")

    assert [r["company"] for r in result["rates"]] == ["USCo", "PolandCo"]
    poland = result["rates"][1]
    assert poland["typical"] == {"min": 272_000, "max": 408_000}   # published
    assert poland["typical_in_USD"] == {"min": 72_317, "max": 108_476}
    assert result["fx"]["base"] == "USD"
    assert result["currencies_compared"] == ["PLN", "USD"]


def test_market_rate_needs_no_rates_for_one_currency(monkeypatch):
    from payband_mcp import ats

    boards = {"A": [_posting("USD", 100_000, 200_000)],
              "B": [_posting("USD", 300_000, 400_000)]}
    monkeypatch.setattr(
        fx, "rates", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fetched"))
    )
    monkeypatch.setattr(
        ats, "fetch_postings", lambda company, board=None, role="": ("b", boards[company])
    )
    result = server.market_rate("engineer", ["A", "B"])
    assert [r["company"] for r in result["rates"]] == ["B", "A"]
    assert result["fx"] is None
