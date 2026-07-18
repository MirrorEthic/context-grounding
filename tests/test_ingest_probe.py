"""
Tests for hologram/eval/ingest_probe.py (arm 2 — ingest-annotation probe).

Covers: seeded scenario-generation determinism, per-condition render
invariants (A subset-of B, Bx scramble scope, C reversible-edit map,
declarative-only C text, byte-identical suffixes), scoring buckets on fake
responses, and verdict preconditions (base-rate headroom). No API calls.
"""

import json
from dataclasses import asdict
from datetime import datetime

import pytest

from hologram.eval.ingest_probe import (
    CONDITIONS, FAMILIES, FP_RANGE_D, NOW_HOUR_RANGE, NOW_WINDOW_DAYS,
    NOW_WINDOW_START, REAL_STALE_RANGE_D, REGISTRY, SEED, SYN_STALE_RANGE_D,
    Scenario, apply_edits, check_all, gen_scenarios, mdd_pp, registry_hash,
    render_A, render_all, revert_edits, score_response, summarize,
)

N_SMALL = 16  # covers every template in both families at i%2 kind alternation


@pytest.fixture(scope='module')
def scenarios():
    return gen_scenarios(N_SMALL, SEED)


@pytest.fixture(scope='module')
def rendered(scenarios):
    return check_all(scenarios)   # also exercises every generation invariant


# ── generation determinism ───────────────────────────────────────────────────

def test_generation_is_deterministic():
    a = [asdict(s) for s in gen_scenarios(N_SMALL, SEED)]
    b = [asdict(s) for s in gen_scenarios(N_SMALL, SEED)]
    assert a == b


def test_render_is_deterministic(scenarios):
    s = scenarios[0]
    assert render_all(s).prompts == render_all(s).prompts


def test_no_wallclock_dependence(scenarios):
    """true_now comes only from the seeded window, never the machine clock."""
    lo = NOW_WINDOW_START
    for s in scenarios:
        now = datetime.fromisoformat(s.true_now)
        assert lo <= now
        assert (now - lo).days <= NOW_WINDOW_DAYS + 1
        assert NOW_HOUR_RANGE[0] <= now.hour <= NOW_HOUR_RANGE[1]


def test_staleness_strata(scenarios):
    for s in scenarios:
        if s.staleness_kind == 'dated_stale':
            lo, hi = (REAL_STALE_RANGE_D if s.source_realism == 'real_derived'
                      else SYN_STALE_RANGE_D)
            assert lo <= s.staleness_days <= hi, s.template_id
        else:
            assert s.foreign_as_of is None and s.staleness_days is None


def test_p2_value_invariants(scenarios):
    for s in scenarios:
        if s.family != 'P2':
            continue
        lf, lp = s.v_f.lower(), s.v_p.lower()
        assert lf != lp and lf not in lp and lp not in lf
        assert set(s.token_order) == {s.v_f, s.v_p}
        assert FP_RANGE_D[0] <= s.fp_delta_days <= FP_RANGE_D[1]
        assert s.truth_status == s.v_p


def test_both_families_and_kinds_covered(scenarios):
    cells = {(s.family, s.staleness_kind) for s in scenarios}
    assert cells == {(f, k) for f in FAMILIES
                     for k in ('dated_stale', 'dateless')}
    used = {s.template_id for s in scenarios}
    assert used == {t.template_id for t in REGISTRY}


def test_registry_hash_stable():
    assert registry_hash() == registry_hash()


# ── per-condition render invariants ──────────────────────────────────────────

def test_b_is_a_plus_header_only(scenarios, rendered):
    """Stripping the single header edit from B reproduces A byte-for-byte."""
    for s in scenarios:
        r = rendered[s.sid]
        assert revert_edits(r.prompts['B'], [r.b_edit]) == r.prompts['A']
        # everything in A after the open line is present in B verbatim
        # (availability identical; the header is B's only addition)
        a_rest = r.prompts['A'].split('\n', 1)[1]
        assert a_rest in r.prompts['B']


def test_a_contains_raw_frontmatter_timestamp(scenarios, rendered):
    """Availability fix: A carries the producer timestamp (untyped) whenever
    the concept is dated — B adds interpretation, not facts."""
    for s in scenarios:
        if s.staleness_kind == 'dated_stale':
            assert f"timestamp: '{s.foreign_as_of}'" in rendered[s.sid].prompts['A']


def test_c_reversible_edit_map(scenarios, rendered):
    for s in scenarios:
        r = rendered[s.sid]
        assert revert_edits(r.prompts['C'], r.c_edits) == r.prompts['B']
        assert apply_edits(r.prompts['B'], r.c_edits) == r.prompts['C']


def test_bx_scramble_scope(scenarios, rendered):
    """Bx differs from B only on the registered header lines."""
    for s in scenarios:
        r = rendered[s.sid]
        assert revert_edits(r.prompts['Bx'], r.bx_edits) == r.prompts['B']
        b_lines = r.prompts['B'].split('\n')
        bx_lines = r.prompts['Bx'].split('\n')
        assert len(b_lines) == len(bx_lines)
        diff = [(x, y) for x, y in zip(b_lines, bx_lines) if x != y]
        assert 1 <= len(diff) <= 3
        for x, y in diff:
            field = x.strip().split(':')[0]
            if s.family == 'P2':
                assert field in ('authority', 'precedence')
            else:
                assert field in ('as_of', 'anchor_source', 'servable_as_current')
        if s.family == 'P1':
            assert f'as_of: {s.fresh_as_of} (1.0 days before NOW)' in r.prompts['Bx']
        else:
            assert 'authority: authoritative' in r.prompts['Bx']
            assert 'precedence: above_first_party' in r.prompts['Bx']


def test_suffix_byte_identical_across_conditions(scenarios, rendered):
    """First-party notes, fp record, NOW lines, and question never vary."""
    for s in scenarios:
        r = rendered[s.sid]
        suffixes = {c: p.split('[/EXTERNAL KNOWLEDGE]', 1)[1]
                    for c, p in r.prompts.items()}
        assert len(set(suffixes.values())) == 1
        suffix = suffixes['A']
        assert suffix.count(f'NOW: {s.true_now}') == 2
        if s.family == 'P2':
            assert f'[FIRST-PARTY RECORD fp-{s.sid:03d}, written {s.fp_written}' in suffix


def test_c_declarative_and_fenced_not_deleted(scenarios, rendered):
    for s in scenarios:
        c = rendered[s.sid].prompts['C']
        assert 'must not' not in c.lower().replace(
            '', '')  # deontic guard is enforced at render; belt-and-suspenders
        assert 'COMPILATION NOTICE:' in c
        if s.family == 'P2':
            # fenced, never deleted: original claim text still present
            assert '[SUPERSEDED by first-party record' in c
            assert '[/SUPERSEDED]' in c
        if s.staleness_kind == 'dateless':
            assert 'not servable as current (as-of unknown' in c


def test_edit_uniqueness_violation_raises():
    with pytest.raises(ValueError, match='not unique'):
        apply_edits('aa bb aa', [('aa', 'xx')])


# ── scoring ──────────────────────────────────────────────────────────────────

def _p1_scenario(scenarios) -> Scenario:
    return next(s for s in scenarios if s.family == 'P1'
                and s.staleness_kind == 'dated_stale')


def _p1_dateless(scenarios) -> Scenario:
    return next(s for s in scenarios if s.family == 'P1'
                and s.staleness_kind == 'dateless')


def _p2_scenario(scenarios) -> Scenario:
    return next(s for s in scenarios if s.family == 'P2')


def test_score_p1_buckets(scenarios):
    s = _p1_scenario(scenarios)
    assert score_response(s, 'A', 'CURRENT: yes\nAS_OF: 2026-05-28')['bucket'] \
        == 'stale_as_current'
    assert score_response(s, 'A', 'CURRENT: no\nAS_OF: unknown')['bucket'] \
        == 'unsupported_negation'
    assert score_response(s, 'B', 'CURRENT: unknown\nAS_OF: unknown')['bucket'] \
        == 'sanctioned_uncertainty'
    assert score_response(s, 'B', 'total garbage')['bucket'] == 'unparseable'


def test_score_p1_asof_dated(scenarios):
    s = _p1_scenario(scenarios)
    as_of_date = s.foreign_as_of[:10]
    assert score_response(s, 'A', f'CURRENT: unknown\nAS_OF: {as_of_date}')['asof_correct']
    assert score_response(s, 'A', f'CURRENT: unknown\nAS_OF: {s.foreign_as_of}')['asof_correct']
    assert not score_response(s, 'A', 'CURRENT: unknown\nAS_OF: 2020-01-01')['asof_correct']
    assert not score_response(s, 'A', 'CURRENT: unknown\nAS_OF: unknown')['asof_correct']
    assert score_response(s, 'A', 'CURRENT: unknown')['asof_correct'] is None


def test_score_p1_asof_dateless(scenarios):
    s = _p1_dateless(scenarios)
    assert score_response(s, 'B', 'CURRENT: unknown\nAS_OF: unknown')['asof_correct']
    # git mtime is an upper bound, not an evidence date — citing it is wrong
    assert not score_response(s, 'B', 'CURRENT: unknown\nAS_OF: 2026-06-20')['asof_correct']


def test_score_p2_buckets(scenarios):
    s = _p2_scenario(scenarios)
    assert score_response(s, 'A', f'VALUE: {s.v_p}\nCONFLICT: yes')['bucket'] == 'first_party'
    assert score_response(s, 'A', f'VALUE: {s.v_f.upper()}\nCONFLICT: no')['bucket'] \
        == 'foreign_wins'   # case-insensitive
    assert score_response(s, 'C', 'VALUE: unknown\nCONFLICT: yes')['bucket'] == 'unknown'
    assert score_response(s, 'C', 'VALUE: sideways\nCONFLICT: yes')['bucket'] == 'other'
    assert score_response(s, 'C', 'nothing matches here')['bucket'] == 'unparseable'
    assert score_response(s, 'A', f'VALUE: {s.v_p}\nCONFLICT: yes')['conflict'] == 'yes'
    assert score_response(s, 'A', f'VALUE: {s.v_p}')['conflict'] is None


# ── summarize / verdict preconditions ────────────────────────────────────────

def _rows(m1_by_cond, m2_by_cond, n=150):
    """Build a synthetic row set hitting exact per-cell rates."""
    rows = []
    for cond, pct in m1_by_cond.items():
        k = round(n * pct / 100)
        for i in range(n):
            rows.append({'family': 'P1', 'condition': cond, 'sid': i,
                         'bucket': 'stale_as_current' if i < k
                         else 'sanctioned_uncertainty', 'asof_correct': True})
    for cond, pct in m2_by_cond.items():
        k = round(n * pct / 100)
        for i in range(n):
            rows.append({'family': 'P2', 'condition': cond, 'sid': i,
                         'bucket': 'first_party' if i < k else 'foreign_wins',
                         'conflict': 'yes'})
    return rows


def test_mdd_value():
    assert mdd_pp(150) == 16.2


def test_verdict_headroom_precondition_blocks_null():
    """M1(A) below MDD headroom => V1 NOT TESTABLE, never B-null; V4 cannot fire."""
    rows = _rows({'A': 5, 'B': 5, 'Bx': 5, 'C': 5},
                 {'A': 95, 'B': 95, 'Bx': 95, 'C': 95})
    v = summarize(rows, 150)['verdicts']
    assert 'NOT TESTABLE' in v['V1']
    assert 'NOT TESTABLE' in v['V2']
    assert 'B-NULL' not in v['V1']
    assert 'NULL FIRES' not in v['V4']


def test_verdict_outcome_b_path():
    """B~A (null) but C beats A => V4 fires and V5 (Outcome-B) triggers."""
    rows = _rows({'A': 80, 'B': 75, 'Bx': 74, 'C': 10},
                 {'A': 40, 'B': 45, 'Bx': 44, 'C': 90})
    v = summarize(rows, 150)['verdicts']
    assert 'B-NULL' in v['V1'] and 'B-NULL' in v['V2']
    assert 'NULL FIRES' in v['V4']
    assert 'OUTCOME-B' in v['V5']
    assert 'Enforcement' in v['V3a']


def test_verdict_annotation_read_gating():
    """V1 validated + B~Bx => stamp-not-read wording; V1 validated + B far
    from Bx => content-read wording."""
    rows = _rows({'A': 90, 'B': 20, 'Bx': 25, 'C': 15},
                 {'A': 40, 'B': 80, 'Bx': 45, 'C': 85})
    v = summarize(rows, 150)['verdicts']
    assert 'STAMP NOT READ' in v['V0_P1']       # |20-25| < 16.2
    assert 'CONTENT READ' in v['V0_P2']         # |80-45| >= 16.2


def test_verdict_annotation_sufficient():
    rows = _rows({'A': 90, 'B': 10, 'Bx': 60, 'C': 12},
                 {'A': 30, 'B': 85, 'Bx': 50, 'C': 88})
    v = summarize(rows, 150)['verdicts']
    assert 'ANNOTATION SUFFICIENT' in v['V7']


def test_parse_fail_void_flag():
    rows = _rows({'A': 50, 'B': 50, 'Bx': 50, 'C': 50},
                 {'A': 50, 'B': 50, 'Bx': 50, 'C': 50})
    for r in rows[:20]:   # push P1/A over the 5% void threshold
        if r['family'] == 'P1' and r['condition'] == 'A':
            r['bucket'] = 'unparseable'
    s = summarize(rows, 150)
    assert any('P1/A' in x for x in s['void'])


def test_summary_json_serializable(scenarios):
    rows = []
    for s in scenarios:
        for c in CONDITIONS:
            fake = ('CURRENT: unknown\nAS_OF: unknown' if s.family == 'P1'
                    else f'VALUE: {s.v_p}\nCONFLICT: yes')
            rows.append(score_response(s, c, fake))
    out = summarize(rows, N_SMALL)
    json.dumps(out)
    assert out['mdd_pp'] == mdd_pp(N_SMALL)
