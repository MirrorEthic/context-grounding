"""
OKF ingest tests — §4b/§4c of CONTEXT_GROUNDING_PROGRAM.md.

Fixture bundle is synthetic OKF v0.1: index.md, log.md with bare-date headings,
one dated human concept, one dateless agent concept carrying every T-class
violation from the §1 incident's ambient field.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hologram.okf import (
    TemporalLintError, annotate, enforce, ingest_bundle, lint_record, lint_text,
    read_bundle,
)
from hologram.okf.report import PROBES_GATED


FIXED_NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / 'sample_bundle'
    root.mkdir()
    (root / 'index.md').write_text(
        '---\ntype: index\n---\n# Sample\n\n'
        '- [dated](concepts/dated.md)\n- [exhaust](concepts/exhaust.md)\n'
        '- [missing](concepts/missing.md)\n'
    )
    (root / 'log.md').write_text(
        '---\ntype: log\n---\n'
        '## 2026-05-22\nAdded dated concept.\n'
        '## 2026-06-01 restructure\nMoved things around.\n'
    )
    concepts = root / 'concepts'
    concepts.mkdir()
    (concepts / 'dated.md').write_text(
        '---\ntype: concept\ntimestamp: 2026-07-01T09:00:00-06:00\n'
        'temporal_reference: past_completed\n---\n'
        'Migration completed 2026-07-01T09:00:00-06:00.\n'
    )
    (concepts / 'exhaust.md').write_text(
        '---\ntype: concept\ngenerated_by: enrichment-agent\n---\n'
        'Auto-generated summary. The probe night run 9h ago spanned '
        '19:45→23:05 and results landed yesterday. See [dated](dated.md).\n'
    )
    return root


# ── lint: the one codepath ───────────────────────────────────────────────────

def test_lint_detects_incident_ambient_field():
    text = 'probe night ran 9h ago, span 19:45→23:05, results yesterday'
    codes = {(f.code, f.kind) for f in lint_text(text)}
    assert ('T2', 'anchorless_relative') in codes      # 9h ago
    assert ('T2', 'relative_word') in codes            # yesterday
    assert ('T1', 'bare_clock') in codes               # 19:45 / 23:05
    assert ('T4', 'ambient_lexical') in codes          # night


def test_full_anchor_passes_and_exempts_nearby_delta():
    text = 'Completed 2026-07-15T23:51:00-06:00 (9h before now).'
    assert lint_text(text) == []
    anchored_delta = 'Started 2026-07-15T23:51:00-06:00, 9h ago.'
    assert not any(f.code == 'T2' for f in lint_text(anchored_delta))


def test_date_only_flags_t1_but_anchors_its_line_for_t4():
    findings = lint_text('2026-07-15 evening session (completed)')
    kinds = {(f.code, f.kind) for f in findings}
    assert ('T1', 'date_without_offset') in kinds
    assert ('T4', 'ambient_lexical') not in kinds      # line carries a date


def test_code_blocks_are_not_temporal_claims():
    fenced = ("Query example:\n```sql\nWHERE ts >= '2023-01-01' AND t < '19:45'\n"
              "-- run 9h ago at night\n```\nProse after.\n")
    assert lint_text(fenced) == []
    inline = "Filter with `block_timestamp >= '2023-01-01'` as shown."
    assert lint_text(inline) == []
    outside = "```\nclean\n```\nBut 9h ago out here still fires."
    assert any(f.code == 'T2' for f in lint_text(outside))


def test_t3_missing_and_invalid_temporal_reference():
    assert any(f.kind == 'missing_temporal_reference'
               for f in lint_record('clean body', {}))
    assert any(f.kind == 'invalid_temporal_reference'
               for f in lint_record('clean body', {'temporal_reference': 'soonish'}))
    assert lint_record('clean body', {'temporal_reference': 'ongoing'}) == []


def test_enforce_rejects_annotate_never_does_same_findings():
    body = 'shipped 3 days ago'
    fm = {'timestamp': '2026-07-14', 'temporal_reference': 'past_completed'}
    with pytest.raises(TemporalLintError) as exc:
        enforce(body, fm)
    ann = annotate(body, fm)
    # I6: identical findings from both modes; annotate just doesn't raise
    assert [f.to_dict() for f in exc.value.findings] == ann['findings']
    assert ann['anchored'] is True and ann['anchor_has_offset'] is False


def test_annotate_dateless_is_unanchored_unknown():
    ann = annotate('no dates here', {})
    assert ann['anchored'] is False
    assert ann['temporal_reference'] == 'unknown'
    assert ann['as_of'] is None


# ── reader: permissive by spec ───────────────────────────────────────────────

def test_reader_walks_bundle_permissively(bundle):
    b = read_bundle(bundle)
    assert set(b.concepts) == {'index.md', 'log.md',
                               'concepts/dated.md', 'concepts/exhaust.md'}
    assert b.index is not None and b.index.is_index
    assert [e.date for e in b.log_entries] == ['2026-05-22', '2026-06-01']
    assert b.log_entries[1].heading == 'restructure'


def test_reader_tolerates_missing_type_and_bad_yaml(tmp_path):
    root = tmp_path / 'broken'
    root.mkdir()
    (root / 'no_type.md').write_text('---\nname: x\n---\nbody\n')
    (root / 'bad_yaml.md').write_text('---\n: [unclosed\n---\nbody\n')
    (root / 'no_fm.md').write_text('just prose\n')
    b = read_bundle(root)
    assert len(b.concepts) == 3
    assert b.concepts['no_type.md'].type is None
    assert any('type' in n for n in b.concepts['no_type.md'].parse_notes)
    assert b.concepts['no_fm.md'].body == 'just prose\n'


def test_reader_marks_broken_links_not_resolved_by_inference(bundle):
    b = read_bundle(bundle)
    index_links = {l.resolved: l.broken for l in b.concepts['index.md'].links}
    assert index_links['concepts/dated.md'] is False
    assert index_links['concepts/missing.md'] is True


# ── overlay: consumer judgments, per-concept keying ──────────────────────────

def test_ingest_writes_overlay_with_i1_defaults(bundle, tmp_path):
    result = ingest_bundle(bundle, project_root=tmp_path, now=FIXED_NOW)
    overlay = Path(result.overlay_dir)
    for name in ('ingest-report.json', 'grounding-profile.yaml',
                 'provenance.json', 'temporal-index.json', 'coactivation.json'):
        assert (overlay / name).exists(), name
    assert (overlay / 'learned-state').is_dir()

    temporal = json.loads((overlay / 'temporal-index.json').read_text())
    dated = temporal['concepts']['concepts/dated.md']
    exhaust = temporal['concepts']['concepts/exhaust.md']
    assert dated['anchored'] is True and dated['servable_as_current'] is True
    assert dated['staleness_days'] > 0
    # I2: dateless (producer-undated) must never be servable as current
    assert exhaust['anchored'] is False and exhaust['servable_as_current'] is False
    # I3: log headings anchored, history not state
    assert all(e['temporal_reference'] == 'past_completed'
               and e['as_of'].endswith('+00:00') for e in temporal['log_entries'])


def test_ingest_types_producer_and_exhaust(bundle, tmp_path):
    result = ingest_bundle(bundle, project_root=tmp_path, now=FIXED_NOW)
    prov = json.loads((Path(result.overlay_dir) / 'provenance.json').read_text())
    assert prov['producers']['concepts/exhaust.md'] == 'agent'
    assert 'concepts/exhaust.md' in prov['exhaust_concepts']
    assert 'concepts/dated.md' not in prov['exhaust_concepts']


def test_source_bundle_untouched_and_keying_survives_log_append(bundle, tmp_path):
    before = {p: p.read_text() for p in bundle.rglob('*.md')}
    r1 = ingest_bundle(bundle, project_root=tmp_path, now=FIXED_NOW)
    assert {p: p.read_text() for p in bundle.rglob('*.md')} == before

    prof1 = json.loads((Path(r1.overlay_dir) / 'temporal-index.json').read_text())
    (bundle / 'log.md').open('a').write('## 2026-07-10\nAppended.\n')
    r2 = ingest_bundle(bundle, project_root=tmp_path, now=FIXED_NOW)
    # §4c: log append lands in the SAME overlay (bundle_id keyed on index
    # identity, not whole-bundle digest) — learned state is not orphaned
    assert r2.bundle_id == r1.bundle_id and r2.overlay_dir == r1.overlay_dir

    prof2 = json.loads((Path(r2.overlay_dir) / 'temporal-index.json').read_text())
    assert prof2['concepts']['concepts/dated.md'] == prof1['concepts']['concepts/dated.md']
    assert len(prof2['log_entries']) == 3


# ── report: lint and probe never mix ─────────────────────────────────────────

def test_report_lint_section_and_gated_probes(bundle, tmp_path):
    result = ingest_bundle(bundle, project_root=tmp_path, now=FIXED_NOW)
    lint = result.report['lint']
    assert lint['concepts'] == 4
    assert lint['dateless_current_risk'] == 3          # only dated.md is anchored
    assert lint['producer_breakdown'].get('agent', 0) >= 1
    assert lint['links']['broken_not_yet_written'] == 1
    assert lint['finding_counts']['T2'] >= 1
    # §7b: no behavioral verdict may exist until the nulls run
    assert result.report['probes'] == {'status': PROBES_GATED}
