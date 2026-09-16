"""Seniority classification and band summarising. Offline."""

from __future__ import annotations

from payband_mcp import levels


def _p(title, lo, hi, cur="USD"):
    return {"title": title, "pay": {"min": lo, "max": hi, "currency": cur}}


def test_explicit_seniority_markers():
    assert levels.classify("Sr. Forward Deployed Engineer") == "senior"
    assert levels.classify("Staff Software Engineer") == "staff"
    assert levels.classify("Principal Engineer") == "principal"
    assert levels.classify("Software Engineer III") == "senior"
    assert levels.classify("Data Scientist Intern") == "intern"
    assert levels.classify("VP of Sales") == "vp"


def test_compound_markers_beat_their_parts():
    """'Sr. Manager' must not fall through to 'senior' or 'manager'."""
    assert levels.classify("Sr. Manager, FDE") == "senior_manager"
    assert levels.classify("Senior Director, Platform") == "director"
    assert levels.classify("Manager, Forward Deployed Engineering") == "manager"


def test_unmarked_titles_are_mid_not_a_guess():
    assert levels.classify("AI Engineer - FDE (Forward Deployed Engineer)") == "mid"
    assert levels.classify("") == "unspecified"


def test_repeated_band_is_one_data_point_not_many():
    """Databricks posts one Sr. FDE band across dozens of vertical listings."""
    posts = [_p("Sr. FDE - Healthcare", 182000, 250208) for _ in range(9)]
    posts += [_p("Sr. FDE - Public Sector", 182000, 250208)]
    posts += [_p("Sr. FDE - Federal", 211800, 291300)]
    s = levels.summarise(posts)
    assert s["postings"] == 11
    assert s["distinct_bands"] == 2          # not 11
    assert s["typical"] == {"min": 182000, "max": 250208}
    assert s["typical_seen_in_postings"] == 10


def test_band_width_ratio_only_when_consistent():
    consistent = [
        {"typical": {"min": 152900, "max": 210155}},   # x1.374
        {"typical": {"min": 182000, "max": 250208}},   # x1.375
        {"typical": {"min": 211800, "max": 291300}},   # x1.375
    ]
    assert levels.band_width_ratio(consistent) == 1.37

    mixed = [
        {"typical": {"min": 100000, "max": 130000}},   # x1.30
        {"typical": {"min": 100000, "max": 200000}},   # x2.00
    ]
    assert levels.band_width_ratio(mixed) is None


def test_level_steps_follow_the_ladder_order():
    by_level = {
        "mid": {"typical": {"min": 100.0, "max": 200.0}},
        "senior": {"typical": {"min": 150.0, "max": 250.0}},
    }
    steps = levels.level_steps(by_level)
    assert len(steps) == 1
    assert steps[0]["from"] == "mid" and steps[0]["to"] == "senior"
    assert steps[0]["midpoint_increase_pct"] == 33.33


def test_band_precision_is_reported():
    """A 2.5x published band is real data, but it narrows almost nothing."""
    tight = levels.summarise([_p("Sr. Engineer", 182000, 250208)])
    assert tight["spread"] == 1.37 and tight["precision"] == "tight"

    wide = levels.summarise([_p("Forward Deployed Engineer", 153000, 376000)])
    assert wide["spread"] == 2.46 and wide["precision"] == "wide"

    point = levels.summarise([_p("Senior Software Engineer", 320000, 320000)])
    assert point["spread"] == 1.0 and point["precision"] == "point"
