"""
C4 exhaust-monitor tests — hologram/okf/c4.py.

Pins the G1-calibrated tiering (restatement count of a CONTRADICTED value)
and the decoupling-aware design: correct claims never alarm, contradicted
ones tier by dose. Detection regexes are imported from lint (I6).
"""

import pytest

from hologram.okf.c4 import (
    analyze, extract_temporal_claims, C4Report, TIER_THRESHOLDS,
)


def test_extracts_delta_and_duration_claims():
    claims = extract_temporal_claims("we've been running for nine hours now", 0)
    assert any(abs(c.value_h - 9) < 0.01 and c.kind == 'duration' for c in claims)
    claims = extract_temporal_claims("the deploy finished 9h ago", 1)
    assert any(abs(c.value_h - 9) < 0.01 and c.kind == 'delta_ago' for c in claims)


def test_minutes_normalize_to_hours():
    claims = extract_temporal_claims("about 90 minutes ago", 0)
    assert any(abs(c.value_h - 1.5) < 0.01 for c in claims)


def test_correct_claims_never_alarm():
    # true elapsed 2h; six assistant turns all restating ~2h -> no contradiction
    texts = ["we've been at this for about two hours"] * 6
    rep = analyze(texts, true_elapsed_h=2.0)
    assert rep.tier == 'ok'
    assert rep.max_restatements == 0


def test_contradicted_restatements_tier_by_dose():
    # true elapsed ~2h; the wrong "nine hours" restated N times
    def rep_for(n):
        return analyze(["running for nine hours"] * n, true_elapsed_h=2.0)
    assert rep_for(0).tier == 'ok'
    assert rep_for(1).tier == 'noted'
    assert rep_for(2).tier == 'elevated'
    assert rep_for(6).tier == 'alarm'
    assert rep_for(6).max_restatements == 6


def test_clusters_are_half_hour_grained():
    texts = ["for 9 hours", "about nine hours", "roughly 9 hours"]
    rep = analyze(texts, true_elapsed_h=2.0)
    # all three collapse to one contradicted cluster with 3 restatements
    assert rep.max_restatements == 3
    assert len(rep.contradicted_clusters) == 1


def test_no_truth_disables_contradiction_but_counts_claims():
    rep = analyze(["running for nine hours"] * 3, true_elapsed_h=None)
    assert rep.tier == 'ok'                 # can't call it a contradiction
    assert len(rep.claims) == 3            # but the claims are recorded
    assert rep.contradicted_clusters == {}


def test_calibration_note_present_on_contradiction():
    rep = analyze(["running for nine hours"] * 6, true_elapsed_h=2.0)
    assert '55%' in rep.calibration_note and '20260717T183226' in rep.calibration_note


def test_report_serializes():
    rep = analyze(["for nine hours"] * 2, true_elapsed_h=2.0)
    d = rep.to_dict()
    assert d['tier'] == 'elevated' and d['max_restatements'] == 2
    assert 'contradicted_clusters' in d


def test_no_token_ratio_threshold_exposed():
    # lock L4b: Stage-1 licenses no token-denominated numerator
    import hologram.okf.c4 as c4
    src = open(c4.__file__).read()
    assert 'token' not in src.lower() or 'no token' in src.lower() or 'token-denominated' in src.lower()
