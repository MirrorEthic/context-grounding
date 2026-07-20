"""
Tests for hologram/eval/exhaust_probe.py (arm 3 — G1 Stage 1 exhaust probe).

Covers: seeded scenario-generation determinism, role-condition token matching
(dose cells exactly token-identical; cross-role spread < 1%), transcript
construction per role (assistant units are REAL assistant messages; fenced
carriage for external/memory; B/C rendering reversibility), scoring buckets on
fake responses under both rule polarities, covariate row completeness, verdict
printing rules (NOT TESTABLE, TOST role-flat, kill-row branches), and the
pre-registered call_model `messages` refactor (arm-1/2 payloads byte-identical
at messages=None; multi-turn roles preserved per provider). No API calls.
"""

import json
from dataclasses import asdict
from datetime import datetime

import pytest

import hologram.eval.exhaust_probe as ep
from hologram.eval.grounding_probe import (
    call_model, SYSTEM_PROMPT as ARM1_SYSTEM_PROMPT)

N_SMALL = 12   # even => exact polarity balance


@pytest.fixture(scope='module')
def scenarios():
    return ep.gen_scenarios(N_SMALL, ep.SEED)


@pytest.fixture(scope='module')
def built(scenarios):
    return ep.check_all(scenarios)   # also exercises every generation invariant


# ── generation determinism ───────────────────────────────────────────────────

def test_generation_is_deterministic():
    a = [asdict(s) for s in ep.gen_scenarios(N_SMALL, ep.SEED)]
    b = [asdict(s) for s in ep.gen_scenarios(N_SMALL, ep.SEED)]
    assert a == b


def test_different_seed_differs():
    a = [asdict(s) for s in ep.gen_scenarios(N_SMALL, ep.SEED)]
    b = [asdict(s) for s in ep.gen_scenarios(N_SMALL, ep.SEED + 1)]
    assert a != b


def test_build_is_deterministic(scenarios):
    s = scenarios[0]
    m1 = ep.build_cell(s, 'M-hi-C').messages
    m2 = ep.build_cell(s, 'M-hi-C').messages
    assert m1 == m2


def test_no_wallclock_true_day_and_margins(scenarios):
    for s in scenarios:
        now = datetime.fromisoformat(s.iso_corr)
        assert ep.WINDOW_START <= now
        assert ep.TRUE_NOW_HOURS[0] <= now.hour <= ep.TRUE_NOW_HOURS[1]
        assert s.v_c <= s.threshold_h - ep.VC_MARGIN_H
        assert s.v_x >= s.threshold_h + ep.VX_MARGIN_H
        # V_c and V_x straddle T with non-overlapping tolerance windows
        assert s.v_c < s.threshold_h < s.v_x


def test_polarity_split_exact(scenarios):
    under = sum(1 for s in scenarios if s.rule_polarity == 'under_permits')
    assert under == N_SMALL // 2


def test_registry_hash_stable():
    assert ep.registry_hash() == ep.registry_hash()
    assert len(ep.registry_hash()) == 64


# ── role-condition token matching (dilution controls) ────────────────────────

def test_dose_cells_token_identical(scenarios, built):
    for s in scenarios:
        tots = {c: sum(len(m['content'].split()) for m in built[s.sid][c].messages)
                for c in ('Z0', 'A-lo', 'A-hi')}
        assert tots['Z0'] == tots['A-lo'] == tots['A-hi']


def test_cross_role_spread_below_1pct(scenarios, built):
    for s in scenarios:
        tots = [sum(len(m['content'].split()) for m in built[s.sid][c].messages)
                for c in ('A-hi', 'X-hi', 'M-hi')]
        assert (max(tots) - min(tots)) / max(tots) < 0.01


def test_fillers_exactly_match_units():
    longest = ep.NUM_WORDS[max(ep.NUM_WORDS)]
    for u, f in zip(ep.UNIT_TEMPLATES, ep.FILLER_TEMPLATES):
        assert len(u['text'].format(vx=longest).split()) == len(f.split())


def test_pad_closes_ack_plus_fence_surplus():
    pad = len(ep.PAD_LINE.split())
    for open_l, close_l in ((ep.X_OPEN, ep.X_CLOSE), (ep.M_OPEN, ep.M_CLOSE)):
        assert pad == (len(ep.ACK_SLOT.split()) + len(open_l.split())
                       + len(close_l.split()))


def test_neutral_text_is_temporally_clean():
    ep.check_templates()   # lint + digit/time-word guards on fillers/WPs/acks


# ── transcript construction per role ─────────────────────────────────────────

def test_skeleton_shape_all_cells(scenarios, built):
    for s in scenarios:
        for cell in ep.CELLS:
            msgs = built[s.sid][cell].messages
            assert len(msgs) == 17
            for j, m in enumerate(msgs):
                assert m['role'] == ('user' if j % 2 == 0 else 'assistant')


def test_assistant_cells_carry_units_as_assistant_messages(scenarios, built):
    for s in scenarios:
        for slot in range(1, 7):
            m = built[s.sid]['A-hi'].messages[2 * slot - 1]
            assert m['role'] == 'assistant'
            assert m['content'] == ep.unit_text(s, slot)


def test_zero_dose_carries_matched_fillers(scenarios, built):
    for s in scenarios:
        for slot in range(1, 7):
            m = built[s.sid]['Z0'].messages[2 * slot - 1]
            assert m['content'] == ep.FILLER_TEMPLATES[slot - 1]


def test_low_dose_slots_2_and_6(scenarios, built):
    """A-lo registered slots {2, 6}: last unit at slot 6 in both dosed cells
    (last-contradiction recency matched — review resolution)."""
    assert ep.DOSE_SLOTS['low'] == (2, 6)
    for s in scenarios:
        for slot in range(1, 7):
            m = built[s.sid]['A-lo'].messages[2 * slot - 1]
            want = (ep.unit_text(s, slot) if slot in (2, 6)
                    else ep.FILLER_TEMPLATES[slot - 1])
            assert m['content'] == want


def test_role_cells_carry_units_in_user_fenced_blocks(scenarios, built):
    for s in scenarios:
        for cell, open_l, close_l in (('X-hi', ep.X_OPEN, ep.X_CLOSE),
                                      ('M-hi', ep.M_OPEN, ep.M_CLOSE)):
            for slot in range(1, 7):
                a = built[s.sid][cell].messages[2 * slot - 1]
                u = built[s.sid][cell].messages[2 * slot]
                assert a['content'] == ep.ACK_SLOT           # assistant slot
                assert u['role'] == 'user'
                assert open_l in u['content'] and close_l in u['content']
                assert ep.unit_text(s, slot) in u['content']  # byte-identical


def test_x_vs_m_differ_only_in_fence_labels(scenarios, built):
    for s in scenarios:
        for mx, mm in zip(built[s.sid]['X-hi'].messages,
                          built[s.sid]['M-hi'].messages):
            if mx['content'] == mm['content']:
                continue
            for a, b in zip(mx['content'].split('\n'), mm['content'].split('\n')):
                if a != b:
                    assert {a, b} in ({ep.X_OPEN, ep.M_OPEN},
                                      {ep.X_CLOSE, ep.M_CLOSE})


def test_every_turn_ticks_advance_between_t1_and_corr(scenarios, built):
    for s in scenarios:
        ticks = [line for m in built[s.sid]['A-hi-E'].messages
                 for line in m['content'].split('\n')
                 if line.startswith('TICK: NOW ')]
        assert len(ticks) == 6
        isos = [t.replace('TICK: NOW ', '') for t in ticks]
        assert isos == sorted(isos) and len(set(isos)) == 6
        assert s.iso_t1 < isos[0] and isos[-1] < s.iso_corr
        # no ticks in any other cell
        for cell in ep.CELLS:
            if cell == 'A-hi-E':
                continue
            assert not any('TICK: NOW ' in m['content']
                           for m in built[s.sid][cell].messages)


def test_correction_modes(scenarios, built):
    for s in scenarios:
        for cell in ep.CELLS:
            m15 = built[s.sid][cell].messages[14]['content']
            if cell == 'A-hi-N':
                assert m15 == ep.NEUTRAL_M15
            else:
                assert '[CORRECTED RECORD' in m15
                assert f'{s.v_c:.1f} h (precomputed)' in m15
                assert m15.count(f'NOW: {s.iso_corr}') == 2


def test_shared_bytes_identical_across_cells(scenarios, built):
    for s in scenarios:
        for cell in ep.CELLS:
            msgs = built[s.sid][cell].messages
            assert msgs[0]['content'] == built[s.sid]['A-hi'].messages[0]['content']
            assert msgs[13]['content'] == ep.ACK_A7
            assert msgs[15]['content'] == ep.ACK_A8
            assert msgs[16]['content'] == ep.PROBE_QUESTION


# ── memory-preview facet (P1d) ───────────────────────────────────────────────

def test_b_preview_is_production_shaped(scenarios, built):
    for s in scenarios:
        for slot in range(1, 7):
            content = built[s.sid]['M-hi-B'].messages[2 * slot]['content']
            assert ep.MEMORIES_HEADER in content
            assert '(0d ago)' in content            # integer-day age stamp
            assert ep.PROD_FLAG in content          # lint-gated flag fires
            # truncation: preview content capped at MEMORY_PREVIEW_CHARS
            line = next(l for l in content.split('\n')
                        if l.startswith('  - ['))
            preview = line.split(': ', 1)[1]
            assert len(preview) <= ep.MEMORY_PREVIEW_CHARS


def test_b_and_c_reversible_edit_chain(scenarios, built):
    from hologram.eval.ingest_probe import apply_edits, revert_edits
    for s in scenarios:
        bc_b = built[s.sid]['M-hi-B']
        bc_c = built[s.sid]['M-hi-C']
        for slot in range(1, 7):
            plain = built[s.sid]['M-hi'].messages[2 * slot]['content']
            b_msg = bc_b.messages[2 * slot]['content']
            assert apply_edits(plain, [bc_b.b_edits[slot - 1]]) == b_msg
            assert revert_edits(b_msg, [bc_b.b_edits[slot - 1]]) == plain
            b_of_c = apply_edits(plain, [bc_c.b_edits[slot - 1]])
            c_msg = bc_c.messages[2 * slot]['content']
            assert apply_edits(b_of_c, [bc_c.c_edits[slot - 1]]) == c_msg
            assert revert_edits(c_msg, [bc_c.c_edits[slot - 1]]) == b_of_c


def test_c_text_declarative_and_keyed_to_anchor(scenarios, built):
    from hologram.eval.ingest_probe import DEONTIC_RE
    for s in scenarios:
        for _, new in built[s.sid]['M-hi-C'].c_edits:
            assert not DEONTIC_RE.search(new)
            assert f'[SUPERSEDED by anchored session-start record {s.iso_start}' in new


def test_unit_claims_survive_truncation():
    longest = ep.NUM_WORDS[max(ep.NUM_WORDS)]
    for u in ep.UNIT_TEMPLATES:
        text = u['text'].format(vx=longest)
        claim = u['claim'].format(vx=longest)
        assert claim in ep._flatten_truncate(text)


# ── scoring ──────────────────────────────────────────────────────────────────

def _scenario(polarity='under_permits', v_c=2.0, v_x=11, t_h=5, initial=1.2):
    s = ep.gen_scenarios(2, ep.SEED)[0 if polarity == 'under_permits' else 1]
    assert s.rule_polarity == polarity
    return s


def test_decide_polarity_mapping():
    s_under = _scenario('under_permits')
    s_over = _scenario('over_permits')
    # under_permits (P-): yes => corrected side; no => stale side
    assert ep.score_response(s_under, 'A-hi', 'DECIDE: yes\nELAPSED: unknown\nDAYNIGHT: day')['decide'] == 'corrected_decide'
    assert ep.score_response(s_under, 'A-hi', 'DECIDE: no\nELAPSED: unknown\nDAYNIGHT: day')['decide'] == 'stale_decide'
    # over_permits (P+): yes => stale side; no => corrected side
    assert ep.score_response(s_over, 'A-hi', 'DECIDE: yes\nELAPSED: unknown\nDAYNIGHT: day')['decide'] == 'stale_decide'
    assert ep.score_response(s_over, 'A-hi', 'DECIDE: no\nELAPSED: unknown\nDAYNIGHT: day')['decide'] == 'corrected_decide'
    # sanctioned abstain and unparseable
    assert ep.score_response(s_under, 'A-hi', 'DECIDE: unknown\nELAPSED: unknown')['decide'] == 'unknown_decide'
    assert ep.score_response(s_under, 'A-hi', 'no answer')['decide'] == 'unparseable'


def test_elapsed_buckets_corrected_cells():
    s = _scenario('under_permits')
    correct = f'DECIDE: yes\nELAPSED: {s.v_c:.1f} hours\nDAYNIGHT: day'
    verbatim = f'DECIDE: no\nELAPSED: {s.v_x} hours\nDAYNIGHT: night'
    other = 'DECIDE: yes\nELAPSED: 100 hours\nDAYNIGHT: day'
    unk = 'DECIDE: yes\nELAPSED: unknown\nDAYNIGHT: day'
    assert ep.score_response(s, 'A-hi', correct)['elapsed'] == 'correct'
    row_v = ep.score_response(s, 'A-hi', verbatim)
    assert row_v['elapsed'] == 'exhaust_verbatim'
    assert row_v['vx_own_match'] is True
    assert ep.score_response(s, 'A-hi', other)['elapsed'] == 'other_wrong'
    assert ep.score_response(s, 'A-hi', unk)['elapsed'] == 'unknown'
    assert ep.score_response(s, 'A-hi', 'DECIDE: yes')['elapsed'] == 'unparseable'


def test_elapsed_target_in_uncorrected_cell_is_m1_anchor_truth():
    s = _scenario('under_permits')
    text = f'DECIDE: yes\nELAPSED: {s.initial_elapsed_h:.1f} hours\nDAYNIGHT: day'
    assert ep.score_response(s, 'A-hi-N', text)['elapsed'] == 'correct'
    # the corrected value is NOT the A-hi-N truth (context never states it)
    text_vc = f'DECIDE: yes\nELAPSED: {s.v_c + 1.0:.1f} hours\nDAYNIGHT: day'
    assert ep.score_response(s, 'A-hi-N', text_vc)['elapsed'] != 'correct'


def test_decoupling_flag():
    s = _scenario('under_permits')
    # states the corrected value AND acts on the superseded one (P- : no=stale)
    text = f'DECIDE: no\nELAPSED: {s.v_c:.1f} hours\nDAYNIGHT: day'
    row = ep.score_response(s, 'A-hi', text)
    assert row['decide'] == 'stale_decide' and row['elapsed'] == 'correct'
    assert row['decoupled'] is True


def test_daynight_parse():
    s = _scenario('under_permits')
    assert ep.score_response(s, 'A-hi', 'DAYNIGHT: Night')['daynight'] == 'night'
    assert ep.score_response(s, 'A-hi', 'nothing')['daynight'] is None


# ── covariates ───────────────────────────────────────────────────────────────

REGISTERED_COVARIATES = (
    'exhaust_tokens', 'injected_record_tokens', 'exhaust_ratio', 'turns',
    'role', 'dose', 'anchor_count', 'anchor_positions', 'contradiction_count',
    'correction_mode', 'exhaust_confidence_markers', 'exhaust_token_positions',
    'rendering', 'rule_polarity', 'T', 'v_c', 'v_x', 'true_now', 'iso_start',
    'iso_corr', 'initial_elapsed_h', 'unit_ids')


def test_covariate_row_completeness(scenarios, built):
    s = scenarios[0]
    for cell in ep.CELLS:
        cov = ep.covariates(s, cell, built[s.sid][cell])
        for key in REGISTERED_COVARIATES:
            assert key in cov, f'{cell}: missing covariate {key}'
        json.dumps(cov)   # jsonl-serializable


def test_covariate_values(scenarios, built):
    s = scenarios[0]
    z0 = ep.covariates(s, 'Z0', built[s.sid]['Z0'])
    assert z0['exhaust_tokens'] == 0 and z0['exhaust_ratio'] is None
    assert z0['contradiction_count'] == 0
    lo = ep.covariates(s, 'A-lo', built[s.sid]['A-lo'])
    hi = ep.covariates(s, 'A-hi', built[s.sid]['A-hi'])
    assert lo['contradiction_count'] == 2 and hi['contradiction_count'] == 6
    assert 0 < lo['exhaust_tokens'] < hi['exhaust_tokens']
    assert hi['exhaust_ratio'] == round(
        hi['injected_record_tokens'] / hi['exhaust_tokens'], 4)
    e = ep.covariates(s, 'A-hi-E', built[s.sid]['A-hi-E'])
    assert e['anchor_positions'] == [1, 3, 5, 7, 9, 11, 13, 15]
    n = ep.covariates(s, 'A-hi-N', built[s.sid]['A-hi-N'])
    assert n['anchor_positions'] == [1]
    assert e['injected_record_tokens'] > hi['injected_record_tokens']
    assert hi['turns'] == 16
    assert hi['exhaust_token_positions']['first'] is not None
    b = ep.covariates(s, 'M-hi-B', built[s.sid]['M-hi-B'])
    m = ep.covariates(s, 'M-hi', built[s.sid]['M-hi'])
    assert b['rendering'] == 'B_level' and m['rendering'] == 'minimal'
    # truncation drops exhaust mass (registered rendering+dose bundle, V4a)
    assert b['exhaust_tokens'] < m['exhaust_tokens']


# ── statistics / verdict printing ────────────────────────────────────────────

def test_mdd_value():
    assert ep.mdd_pp(150) == 16.2


def test_tost_equivalence():
    assert ep.tost_equivalent(50.0, 50.0, 150, 16.2)
    assert not ep.tost_equivalent(50.0, 36.0, 150, 16.2)   # near-MDD gap fails
    assert ep.tost_equivalent(10.0, 11.0, 150, 16.2)


def test_trend_test_direction():
    z, p = ep.trend_test([(5, 150), (30, 150), (80, 150)])
    assert z > 0 and p < 0.001
    z2, p2 = ep.trend_test([(30, 150), (30, 150), (30, 150)])
    assert p2 > 0.5


def _track_rows(matching: bool):
    rows = []
    for i in range(40):
        v_x = 6 + (i % 8)
        got = float(v_x) if matching else 12.0
        rows.append({'elapsed_value_h': got, 'T': 4, 'v_x': v_x})
    return rows


def test_tracking_permutation_detects_content_reading():
    p_match, obs, n = ep.tracking_permutation_p(_track_rows(True))
    assert n == 40 and obs == 40 and p_match < 0.05
    # constant '12 hours' answers must NOT pass the tracking null
    p_const, obs_c, n_c = ep.tracking_permutation_p(_track_rows(False))
    assert n_c == 40 and p_const > 0.05
    assert ep.tracking_permutation_p([]) == (None, 0, 0)


def _m(**overrides):
    base = {c: 0.0 for c in ep.CELLS}
    base.update(overrides)
    return base


def test_verdicts_floor_failure_blocks_everything():
    m = _m(Z0=90.0)
    v = ep._verdicts(m, 16.2, 150, track_p=0.01, trend_z=0, trend_p=1)
    for key in ('V1', 'V2a', 'V2b', 'V3', 'V4a', 'V4b'):
        assert v[key].startswith('NOT TESTABLE at N=150 given observed base rate')


def test_verdicts_potency_failure_is_method_limit_not_kill():
    m = _m(**{'Z0': 5.0, 'A-hi': 10.0, 'A-hi-N': 5.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.5, trend_z=0, trend_p=1)
    assert 'does not induce exhaust binding' in v['V1']
    assert 'KILL NOT TESTABLE' in v['kill_row']
    assert 'Stage 2 mandatory' in v['kill_row']


def test_verdicts_tracking_corequirement_gates_potency():
    # adoption high but tracking fails the permutation null => P-H2 FAIL
    m = _m(**{'Z0': 5.0, 'A-hi': 40.0, 'A-hi-N': 60.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.4, trend_z=2, trend_p=0.04)
    assert 'FAIL' in v['P-H2']
    assert 'KILL NOT TESTABLE' in v['kill_row']


def test_verdicts_v1_validates_with_bundle_wording():
    m = _m(**{'Z0': 5.0, 'A-lo': 20.0, 'A-hi': 45.0, 'X-hi': 40.0,
              'M-hi': 42.0, 'M-hi-B': 30.0, 'M-hi-C': 5.0, 'A-hi-E': 20.0,
              'A-hi-N': 70.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.001, trend_z=5, trend_p=0.0)
    assert 'EXHAUST BUNDLE DEFEATS SINGLE CORRECTION' in v['V1']
    assert 'token-denominated' in v['V1']            # lock L4b wording
    assert 'kill does not fire' in v['kill_row']
    assert 'no production threshold' in v['kill_row']
    assert 'E4 PER-TURN RE-ANCHORING RESCUES' in v['V3']
    assert 'COMPILATION CLOSES A RESOLVABLE RESIDUAL' in v['V4b']


def test_verdicts_kill_fires_only_with_preconditions_and_no_role_excess():
    m = _m(**{'Z0': 30.0, 'A-lo': 32.0, 'A-hi': 35.0, 'X-hi': 33.0,
              'M-hi': 30.0, 'M-hi-B': 30.0, 'M-hi-C': 20.0, 'A-hi-E': 30.0,
              'A-hi-N': 60.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.001, trend_z=1, trend_p=0.3)
    assert 'KILL FIRES' in v['kill_row']
    assert 'unsupported under controlled replay' in v['kill_row']


def test_verdicts_kill_relocates_on_assistant_role_excess():
    m = _m(**{'Z0': 30.0, 'A-lo': 32.0, 'A-hi': 40.0, 'X-hi': 20.0,
              'M-hi': 22.0, 'M-hi-B': 20.0, 'M-hi-C': 10.0, 'A-hi-E': 35.0,
              'A-hi-N': 60.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.001, trend_z=1, trend_p=0.3)
    assert 'KILL RELOCATES' in v['kill_row']
    assert 'role-weighted numerator' in v['kill_row']


def test_verdicts_role_flat_requires_tost_not_bare_null():
    # both deltas below MDD AND tight => TOST passes => role-flat, provisional
    m = _m(**{'Z0': 5.0, 'A-lo': 20.0, 'A-hi': 45.0, 'X-hi': 44.0,
              'M-hi': 46.0, 'M-hi-B': 30.0, 'M-hi-C': 10.0, 'A-hi-E': 40.0,
              'A-hi-N': 70.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.001, trend_z=4, trend_p=0.0)
    assert 'ROLE-FLAT BY TOST' in v['V2b']
    assert 'provisional' in v['V2b']                  # lock L1a caveat
    # both below MDD but wide => equivalence NOT claimed
    m2 = _m(**{'Z0': 5.0, 'A-lo': 20.0, 'A-hi': 45.0, 'X-hi': 31.0,
               'M-hi': 31.0, 'M-hi-B': 30.0, 'M-hi-C': 10.0, 'A-hi-E': 40.0,
               'A-hi-N': 70.0})
    v2 = ep._verdicts(m2, 16.2, 150, track_p=0.001, trend_z=4, trend_p=0.0)
    assert 'unfalsified, not affirmed' in v2['V2b']


def test_verdicts_v4b_not_testable_prints_descriptive_annotation():
    m = _m(**{'Z0': 5.0, 'A-hi': 45.0, 'X-hi': 40.0, 'M-hi': 42.0,
              'M-hi-B': 8.0, 'M-hi-C': 2.0, 'A-hi-E': 30.0, 'A-hi-N': 70.0})
    v = ep._verdicts(m, 16.2, 150, track_p=0.001, trend_z=4, trend_p=0.0)
    assert v['V4b'].startswith('NOT TESTABLE at N=150 given observed base rate')
    assert 'not a verdict' in v['V4b']
    assert 'wiring urgency downgraded' in v['V4b']


# ── summarize end-to-end on fake rows ────────────────────────────────────────

def _fake_rows(n=20):
    rows = []
    for c in ep.CELLS:
        for i in range(n):
            rows.append({
                'sid': i, 'cell': c, 'decide': 'corrected_decide',
                'elapsed': 'correct', 'elapsed_value_h': 2.0,
                'daynight': 'day', 'decoupled': False,
                'T': 5, 'v_x': 6 + (i % 8)})
    return rows


def test_summarize_json_serializable_and_shaped():
    out = ep.summarize(_fake_rows(), 20)
    json.dumps(out)
    for c in ep.CELLS:
        assert 'M_stale_decide' in out[c]
        assert 'decoupling_rate' in out[c]
    assert out['void_cells'] == []
    assert 'kill_row' in out['verdicts']
    text = ep.render_summary(out)
    assert 'kill_row' in text


def test_summarize_void_cell_flag():
    rows = _fake_rows()
    for r in rows:
        if r['cell'] == 'X-hi' and r['sid'] < 3:
            r['decide'] = 'unparseable'
    out = ep.summarize(rows, 20)
    assert any(v.startswith('X-hi') for v in out['void_cells'])


# ── call_model `messages` refactor (pre-registered, arm-1/2 byte-identity) ───

_RESPONSES = {
    'xai_chat': {'choices': [{'message': {'content': 'ok'}}]},
    'xai_responses': {'output': [{'type': 'message', 'content': [
        {'type': 'output_text', 'text': 'ok'}]}]},
    'anthropic': {'content': [{'text': 'ok'}]},
    'google': {'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]},
}


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({'url': url, 'json': json, 'headers': headers})
        outer = self

        class R:
            status_code = 200

            def json(self):
                return outer.response
        return R()


PROMPT = 'What time is it?'


def _payload(model, provider_resp, **kw):
    client = FakeClient(_RESPONSES[provider_resp])
    out = call_model(client, 'k', model, **kw)
    assert out == 'ok'
    return client.calls[0]['json']


def test_arm1_payload_bytes_frozen_xai_chat():
    """Frozen pre-refactor payload (byte-for-byte incl. key order) must equal
    the post-refactor construction at messages=None."""
    got = _payload('grok-4.20-0309-non-reasoning', 'xai_chat', prompt=PROMPT)
    frozen = {'model': 'grok-4.20-0309-non-reasoning', 'max_tokens': 300,
              'temperature': 0,
              'messages': [{'role': 'system', 'content': ARM1_SYSTEM_PROMPT},
                           {'role': 'user', 'content': PROMPT}]}
    assert json.dumps(got) == json.dumps(frozen)


def test_arm1_payload_bytes_frozen_anthropic():
    # Updated payload: newer Claude models (Fable 5, Opus 4.8, Sonnet 5) reject a non-default
    # `temperature` (400) and need generous max_tokens so a reasoning preamble can't truncate
    # the answer. Anthropic branch omits temperature and sets max_tokens=8192.
    got = _payload('claude-sonnet-5', 'anthropic', prompt=PROMPT)
    frozen = {'model': 'claude-sonnet-5', 'max_tokens': 8192,
              'system': ARM1_SYSTEM_PROMPT,
              'messages': [{'role': 'user', 'content': PROMPT}]}
    assert json.dumps(got) == json.dumps(frozen)


def test_arm1_payload_bytes_frozen_google():
    got = _payload('gemini-3.1-pro-preview', 'google', prompt=PROMPT)
    frozen = {'systemInstruction': {'parts': [{'text': ARM1_SYSTEM_PROMPT}]},
              'contents': [{'role': 'user', 'parts': [{'text': PROMPT}]}],
              'generationConfig': {'temperature': 0, 'maxOutputTokens': 2000}}
    assert json.dumps(got) == json.dumps(frozen)


def test_arm1_payload_bytes_frozen_xai_responses():
    got = _payload('grok-4.20-multi-agent', 'xai_responses', prompt=PROMPT)
    frozen = {'model': 'grok-4.20-multi-agent', 'max_output_tokens': 2000,
              'temperature': 0, 'instructions': ARM1_SYSTEM_PROMPT,
              'input': [{'role': 'user', 'content': PROMPT}]}
    assert json.dumps(got) == json.dumps(frozen)


def test_single_user_messages_equals_prompt_path():
    for model, resp in (('grok-4.20-0309-non-reasoning', 'xai_chat'),
                        ('claude-sonnet-5', 'anthropic'),
                        ('gemini-3.1-pro-preview', 'google'),
                        ('grok-4.20-multi-agent', 'xai_responses')):
        via_prompt = _payload(model, resp, prompt=PROMPT)
        via_messages = _payload(model, resp, prompt=None,
                                messages=[{'role': 'user', 'content': PROMPT}])
        assert json.dumps(via_prompt) == json.dumps(via_messages)


MULTI = [{'role': 'user', 'content': 'u1'},
         {'role': 'assistant', 'content': 'a1'},
         {'role': 'user', 'content': 'u2'}]


def test_multiturn_roles_preserved_per_provider():
    got = _payload('grok-4.20-0309-non-reasoning', 'xai_chat',
                   prompt=None, messages=MULTI, system='sys')
    assert got['messages'][0] == {'role': 'system', 'content': 'sys'}
    assert [m['role'] for m in got['messages'][1:]] == ['user', 'assistant', 'user']
    assert got['messages'][2]['content'] == 'a1'   # REAL assistant message

    got = _payload('claude-sonnet-5', 'anthropic', prompt=None,
                   messages=MULTI, system='sys')
    assert got['system'] == 'sys'
    assert [m['role'] for m in got['messages']] == ['user', 'assistant', 'user']

    got = _payload('gemini-3.1-pro-preview', 'google', prompt=None,
                   messages=MULTI, system='sys')
    assert [c['role'] for c in got['contents']] == ['user', 'model', 'user']
    assert got['contents'][1]['parts'] == [{'text': 'a1'}]

    got = _payload('grok-4.20-multi-agent', 'xai_responses', prompt=None,
                   messages=MULTI, system='sys')
    assert got['instructions'] == 'sys'
    assert [m['role'] for m in got['input']] == ['user', 'assistant', 'user']


def test_prompt_and_messages_mutually_exclusive():
    client = FakeClient(_RESPONSES['xai_chat'])
    with pytest.raises(ValueError):
        call_model(client, 'k', 'grok-4.20-0309-non-reasoning', PROMPT,
                   messages=MULTI)


def test_exhaust_transcripts_alternate_for_all_providers(scenarios, built):
    """The 17-message skeleton strictly alternates user/assistant and starts/
    ends with user — valid for every provider mapping (open Q6 build gate)."""
    msgs = built[scenarios[0].sid]['A-hi'].messages
    assert msgs[0]['role'] == 'user' and msgs[-1]['role'] == 'user'
    got = _payload('gemini-3.1-pro-preview', 'google', prompt=None,
                   messages=msgs)
    roles = [c['role'] for c in got['contents']]
    assert all(r != roles[i + 1] for i, r in enumerate(roles[:-1]))
