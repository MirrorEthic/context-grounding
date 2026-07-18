"""
E6 memory-write gate profile tests — hologram/okf/memory_gate.py.

The gate is a policy layer only: every finding must originate in lint_text
(I6 single-codepath). These tests pin the reject/warn profile, mode
resolution, and the self-compliance of the rejection message.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hologram.okf.lint import lint_text
from hologram.okf.memory_gate import (
    GateResult, MemoryGateRejection, REJECT_CODES, WARN_CODES,
    format_rejection, gate_memory_add, lint_memory_fields, resolve_mode,
    split_findings,
)

CLEAN = ("Deploy completed 2026-07-17T09:00:00-06:00; next review scheduled "
         "2026-07-19T10:00:00-06:00.")
DIRTY = "deploy finished 9h ago at 19:45, long probe night"


@pytest.fixture
def mdir(tmp_path):
    return tmp_path


def test_policy_rejects_t1_t2_warns_t4(mdir):
    r = gate_memory_add(DIRTY, 'clean topic', mdir)
    assert r.verdict == 'reject' and r.mode == 'enforce'
    codes = {f['code'] for f in r.rejecting}
    assert codes == {'T1', 'T2'}
    assert {f['code'] for f in r.warnings} == {'T4'}
    assert 'REJECTED' in r.message and 'Do not resubmit unchanged content' in r.message


def test_t4_alone_passes_with_warning(mdir):
    r = gate_memory_add('an urgent refactor of the parser', 'topic', mdir)
    assert r.verdict == 'pass_with_warnings'
    assert r.message and 'stored anyway' in r.message


def test_clean_content_passes(mdir):
    r = gate_memory_add(CLEAN, 'gate deploy record', mdir)
    assert r.verdict == 'pass' and r.message is None


def test_code_spans_exempt(mdir):
    content = 'Rejects strings like `9h ago` and `19:45` per E6; anchored otherwise.'
    assert gate_memory_add(content, 'topic', mdir).verdict == 'pass'


def test_topic_is_linted_separately(mdir):
    r = gate_memory_add(CLEAN, 'probe results from 9h ago', mdir)
    assert r.verdict == 'reject'
    assert all(f['field'] == 'topic' for f in r.rejecting)


def test_invalid_temporal_reference_rejects_missing_passes(mdir):
    assert gate_memory_add(CLEAN, 't', mdir, temporal_reference='soonish').verdict == 'reject'
    assert gate_memory_add(CLEAN, 't', mdir, temporal_reference='ongoing').verdict == 'pass'
    assert gate_memory_add(CLEAN, 't', mdir).verdict == 'pass'


def test_require_t3_env(mdir, monkeypatch):
    monkeypatch.setenv('MEMORY_GATE_REQUIRE_T3', '1')
    r = gate_memory_add(CLEAN, 't', mdir)
    assert r.verdict == 'reject'
    assert r.rejecting[0]['kind'] == 'missing_temporal_reference'


def test_mode_resolution_order(mdir, monkeypatch):
    assert resolve_mode(mdir) == 'enforce'            # default fail-closed
    (mdir / 'gate_mode').write_text('log\n')
    assert resolve_mode(mdir) == 'log'
    monkeypatch.setenv('MEMORY_GATE_MODE', 'enforce')  # env beats file
    assert resolve_mode(mdir) == 'enforce'
    (mdir / 'GATE_OFF').touch()                        # kill-switch beats all
    assert resolve_mode(mdir) == 'off'
    assert gate_memory_add(DIRTY, 't', mdir).verdict == 'off'


def test_garbage_gate_mode_file_fails_closed(mdir):
    (mdir / 'gate_mode').write_text('warn-maybe?\n')
    assert resolve_mode(mdir) == 'enforce'


def test_rejection_message_is_self_compliant(mdir):
    r = gate_memory_add(DIRTY, 'probe night results from 9h ago', mdir)
    # The message quotes the offending tokens — inside backticks, so the
    # message itself must pass the linter it announces (E1/E2 self-compliance).
    assert lint_text(r.message) == []


def test_rejection_message_stamp_is_full_iso(mdir):
    fixed = datetime(2026, 7, 17, 16, 45, 0, tzinfo=timezone(timedelta(hours=-6)))
    msg = format_rejection(*split_findings(lint_memory_fields(DIRTY, 't')), now=fixed)
    assert '2026-07-17T16:45:00-06:00' in msg


def test_no_detection_logic_in_gate_module():
    src = (Path(__file__).parent.parent / 'hologram/okf/memory_gate.py').read_text()
    assert 're.compile' not in src, 'I6: detection must live only in lint.py'


def test_exception_is_temporal_lint_error_compatible():
    exc = MemoryGateRejection('msg', [{'code': 'T2'}])
    from hologram.okf.lint import TemporalLintError
    assert isinstance(exc, TemporalLintError) and isinstance(exc, ValueError)
    assert str(exc) == 'msg' and exc.findings == [{'code': 'T2'}]
