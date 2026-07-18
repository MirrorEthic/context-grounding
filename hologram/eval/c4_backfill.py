"""
C4 warmup backfill — score historical Claude Code transcripts offline through
the SAME c4 reader/analyzer the Stop hook uses (hologram.okf.c4), so the
tier/base-rate distribution is available now instead of only from future
sessions.

Honest scope: the contradiction check needs the ISO temporal tick, which only
exists from 2026-07-17T15:19-06:00 onward (the tick fix). Older transcripts
have <2 parseable ticks → elapsed None → claim VOLUME is counted but no
contradiction/tier above 'ok' can fire. The summary separates
clock-available from clock-absent transcripts so the two are never pooled.

Writes to ~/.claude/memory/c4_backfill.jsonl (SEPARATE from the live
c4_log.jsonl — backfill is not forward traffic and must not contaminate the
warmup-flip decision's real-traffic sample).

Usage:
  python3 -m hologram.eval.c4_backfill                 # scan ~/.claude/projects
  python3 -m hologram.eval.c4_backfill --root DIR --glob '*.jsonl'
  python3 -m hologram.eval.c4_backfill --summary-only  # re-summarize the log
"""
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from hologram.okf.c4 import analyze_transcript

DEFAULT_ROOT = Path.home() / '.claude' / 'projects'
OUT = Path.home() / '.claude' / 'memory' / 'c4_backfill.jsonl'
SESSION_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$')


def _transcripts(root: Path, glob: str):
    for p in sorted(root.rglob(glob)):
        # only real session transcripts (uuid.jsonl), not daemon/aux jsonl
        if SESSION_RE.search(p.name):
            yield p


def run(root: Path, glob: str) -> dict:
    rows = []
    for p in _transcripts(root, glob):
        try:
            report, tick_count = analyze_transcript(str(p))
        except Exception as e:
            rows.append({'path': str(p), 'error': str(e)[:200]})
            continue
        rows.append({
            'path': str(p),
            'tick_count': tick_count,
            'clock_available': tick_count >= 2,
            **report.to_dict(),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')
    return summarize(rows)


def summarize(rows) -> dict:
    ok = [r for r in rows if 'error' not in r]
    clock = [r for r in ok if r.get('clock_available')]
    noclock = [r for r in ok if not r.get('clock_available')]
    any_claim = [r for r in ok if r.get('claims')]
    return {
        'transcripts_scanned': len(rows),
        'errors': sum(1 for r in rows if 'error' in r),
        'with_any_temporal_claim': len(any_claim),
        'clock_available': {
            'count': len(clock),
            'tier_distribution': dict(Counter(r['tier'] for r in clock)),
            'contradicted_sessions': sum(1 for r in clock if r['max_restatements']),
            'max_restatements_seen': max((r['max_restatements'] for r in clock), default=0),
        },
        'clock_absent': {
            'count': len(noclock),
            'sessions_with_claims': sum(1 for r in noclock if r.get('claims')),
            'note': 'volume only — pre-tick-fix transcripts, no contradiction possible',
        },
    }


def main():
    ap = argparse.ArgumentParser(description='C4 offline warmup backfill')
    ap.add_argument('--root', default=str(DEFAULT_ROOT))
    ap.add_argument('--glob', default='*.jsonl')
    ap.add_argument('--summary-only', action='store_true')
    args = ap.parse_args()

    if args.summary_only:
        rows = [json.loads(l) for l in open(OUT)]
        s = summarize(rows)
    else:
        s = run(Path(args.root), args.glob)
    print(json.dumps(s, indent=2))
    print(f'\nlog: {OUT}')


if __name__ == '__main__':
    main()
