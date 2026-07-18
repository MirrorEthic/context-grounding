"""
Ingest audit report — §7b. Two sections that never mix:

  lint  — deterministic static analysis over I1–I5 output. Shippable.
  probe — behavioral (Binding/Enforcement) verdicts. GATED: prints no verdict
          until the scrambled-anchor and ingest-annotation nulls have run and
          each verdict line can state its resolving power. Until then the
          section is exactly {'status': PROBES_GATED}.

A conformance verdict the probe cannot resolve, printed next to a broken-link
count, is the failure §7 exists to prevent. Do not add fields to the probe
section from this module; the gate lifts in the probe harness, not here.
"""

from collections import Counter
from typing import Dict

from .reader import Bundle

PROBES_GATED = 'not run (gated on §7 nulls)'


def build_report(bundle_id: str, bundle: Bundle, records: Dict[str, Dict]) -> Dict:
    total = len(records)
    anchored = sum(1 for r in records.values() if r['temporal']['anchored'])
    finding_counts: Counter = Counter()
    for r in records.values():
        for f in r['lint_findings']:
            finding_counts[f['code']] += 1
    producer_counts = Counter(r['producer'] for r in records.values())
    broken = sum(1 for c in bundle.concepts.values() for l in c.links if l.broken)
    total_links = sum(len(c.links) for c in bundle.concepts.values())

    return {
        'bundle_id': bundle_id,
        'lint': {
            'concepts': total,
            'temporal_coverage_pct': round(100.0 * anchored / total, 1) if total else 0.0,
            'dateless_current_risk': total - anchored,
            'producer_breakdown': dict(producer_counts),
            'agent_produced_pct': round(
                100.0 * producer_counts.get('agent', 0) / total, 1) if total else 0.0,
            'links': {'total': total_links, 'broken_not_yet_written': broken},
            'finding_counts': {code: finding_counts.get(code, 0)
                               for code in ('T1', 'T2', 'T3', 'T4')},
            'log_entries': len(bundle.log_entries),
            'parse_notes': len(bundle.parse_notes)
                + sum(len(c.parse_notes) for c in bundle.concepts.values()),
        },
        'probes': {'status': PROBES_GATED},
    }


def render_text(report: Dict) -> str:
    lint = report['lint']
    fc = lint['finding_counts']
    lines = [
        f"Bundle: {report['bundle_id']}",
        '',
        '── lint (deterministic) ──────────────────────',
        f"  concepts:               {lint['concepts']}",
        f"  temporal coverage:      {lint['temporal_coverage_pct']}%",
        f"  dateless-current risk:  {lint['dateless_current_risk']} concepts",
        f"  producers:              {lint['producer_breakdown']}"
        f"  (agent {lint['agent_produced_pct']}%)",
        f"  links:                  {lint['links']['total']} total, "
        f"{lint['links']['broken_not_yet_written']} not_yet_written",
        f"  findings:               T1={fc['T1']} T2={fc['T2']} T3={fc['T3']} T4={fc['T4']}",
        f"  log entries:            {lint['log_entries']}",
        '',
        '── probes (behavioral) ───────────────────────',
        f"  {report['probes']['status']}",
    ]
    return '\n'.join(lines)
