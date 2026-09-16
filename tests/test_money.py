"""Cases taken from postings that were being read wrongly, or not at all."""

import pytest

from blind_mcp.money import parse


def band(text):
    pay = parse(text)
    return None if pay is None else (pay["min"], pay["max"], pay["currency"], pay["interval"])


@pytest.mark.parametrize(
    "text,expected",
    [
        # The shape that worked before, which must keep working.
        ("The pay range is $184,000 - $287,500 USD", (184000, 287500, "USD", "year")),
        ("Salary range: $152k - $200k", (152000, 200000, "USD", "year")),
        # Every one of these returned None before, on real postings.
        ("The base salary range is 184,000 USD - 287,500 USD", (184000, 287500, "USD", "year")),
        ("£85,000 - £110,000 + Incentive Awards", (85000, 110000, "GBP", "year")),
        ("Salary £59,100 to £79,900 + Benefits", (59100, 79900, "GBP", "year")),
        ("Base salary 65.000 - 90.000 EUR annually", (65000, 90000, "EUR", "year")),
        ("Compensation: ₹25,00,000 - ₹40,00,000 per annum", (2500000, 4000000, "INR", "year")),
        ("Poland base salary range: 272,000 PLN – 408,000 PLN", (272000, 408000, "PLN", "year")),
        # Typed by a human, verbatim from Monzo.
        ("\U0001f4b0Base salary £150, 000 - £200, 000 + Equity", (150000, 200000, "GBP", "year")),
    ],
)
def test_published_ranges_are_read(text, expected):
    assert band(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        # Perks and company figures that sit near a number in real postings.
        "Learning budget of €1,200 a year for books, training courses",
        "You get a £500 - £1,000 learning budget every year",
        "We raised $50,000,000 - $80,000,000 in our Series C",
        "Requisition 2024 - 2026 for the platform team",
        "We offer a competitive salary and meaningful equity",
        # Two bare numbers with nothing marking them as money.
        "Between 120,000 and 160,000 lines of code",
    ],
)
def test_figures_that_are_not_salary_are_refused(text):
    assert parse(text) is None


def test_interval_is_read_rather_than_assumed():
    """An hourly rate averaged into annual bands is wrong, not just imprecise."""
    assert band("The hourly pay range is $45.00 - $70.00 per hour") == (45, 70, "USD", "hour")
    assert band("Salary: €4,500 - €6,000 per month") == (4500, 6000, "EUR", "month")


def test_an_explicit_code_beats_an_ambiguous_symbol():
    assert band("Salary range $120,000 - $150,000 CAD") == (120000, 150000, "CAD", "year")


def test_a_single_labelled_figure_is_a_band_of_zero_width():
    assert band("\U0001f4b0 £50,000 base salary + incentive award") == (50000, 50000, "GBP", "year")
    # ...but only when a salary word is adjacent to it.
    assert parse("Trusted by 50,000 businesses across the UK") is None


def test_level_labelled_ranges_are_kept_apart():
    """NVIDIA publishes two bands in one posting; their union is nobody's band."""
    pay = parse(
        "The base salary range is 184,000 USD - 287,500 USD for Level 4, "
        "and 224,000 USD - 356,500 USD for Level 5."
    )
    assert (pay["min"], pay["max"]) == (184000, 287500)
    assert [(b["label"], b["min"], b["max"]) for b in pay["bands"]] == [
        ("Level 4", 184000, 287500),
        ("Level 5", 224000, 356500),
    ]


def test_reversed_and_empty_input():
    assert band("$210,155 — $152,900 USD salary") == (152900, 210155, "USD", "year")
    assert parse(None) is None
    assert parse("") is None
