"""
Build a curated, annotated reasoning-trace showcase for the public repo from the
local mechanism-probe runs (vLLM, visible <think>). The point people can't get from
API-only work: you can SEE the model re-derive elapsed from the anchored stamps and
honor the correction — and, without a correction, adopt the exhaust instead.

For each model (one mech_* run dir per model, tagged by config.json['subject']) it
picks storytelling exemplars:
  - AUTH   (exhaust + correction): a row that DECIDES corrected AND recomputes → re-grounds by re-derivation
  - AUTH-N (exhaust, no correction): a row that DECIDES stale → same model, correction removed, goes wrong
and writes results/local_traces/TRACES.md.

Usage:
  python3 -m hologram.eval.stage2_trace_showcase                 # auto-glob recent mech_* dirs
  python3 -m hologram.eval.stage2_trace_showcase --out ~/context-grounding/results/local_traces/TRACES.md
"""
import argparse, glob, json, os
from pathlib import Path

RUNS = Path('.hologram/eval/exhaust_stage2_runs')


def load_runs():
    out = {}
    for d in sorted(glob.glob(str(RUNS / 'mech_*'))):
        cfg = Path(d) / 'config.json'; rows = Path(d) / 'rows.jsonl'
        if not (cfg.exists() and rows.exists()):
            continue
        subj = json.loads(cfg.read_text()).get('subject', d)
        rs = [json.loads(l) for l in open(rows)]
        # skip degenerate runs (e.g. the 64-wide qwq that timed out: 226/240 call_failed)
        failed = sum(1 for r in rs if r.get('decide') == 'call_failed')
        if not rs or failed / len(rs) > 0.3:
            continue
        out[subj] = rs   # last VALID run for a subject wins
    return out


def pick(rows, cell, want_decide, want_recompute=None):
    cand = [r for r in rows if r.get('cell') == cell and r.get('decide') == want_decide
            and r.get('think')]
    if want_recompute is not None:
        cand = [r for r in cand if r.get('recompute') == want_recompute] or cand
    # prefer a compact, legible trace
    cand.sort(key=lambda r: r.get('think_len', 0))
    return cand[len(cand) // 3] if cand else None


def quote(text, limit=1400):
    t = (text or '').strip().replace('\r', '')
    if len(t) > limit:
        t = t[:limit].rstrip() + ' …[trace truncated]'
    return '\n'.join('> ' + ln for ln in t.split('\n'))


def rate(rows, cell, decide):
    cr = [r for r in rows if r.get('cell') == cell]
    return round(100 * sum(1 for r in cr if r.get('decide') == decide) / len(cr), 1) if cr else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='.hologram/eval/exhaust_stage2_runs/TRACES.md')
    a = ap.parse_args()
    runs = load_runs()
    L = ['# Reasoning traces: watching models re-ground (or not)',
         '',
         'Open-weights reasoning models served locally (vLLM, TP=2 on 2× V100), so the '
         '`<think>` chain is visible. Each model gets the same probe:',
         '',
         '- **AUTH** — a doctored session carries confident but *wrong* elapsed-time claims, '
         'then a clear anchored **correction**, then a decision.',
         '- **AUTH-N** — identical, but with **no correction**.',
         '',
         'What to look for: under the correction the model **re-derives the time from the '
         'anchored stamps** and decides on the corrected value; with the correction removed, '
         'the same model adopts the wrong value. The re-grounding is active recomputation, not '
         'passive deference — visible in the trace.', '']
    for subj, rows in runs.items():
        name = subj.split(':', 1)[-1]
        L += [f'## {name}', '',
              f"Rates — AUTH corrected: **{rate(rows,'AUTH','corrected_decide')}%** · "
              f"AUTH-N stale (adopts exhaust): **{rate(rows,'AUTH-N','stale_decide')}%** · "
              f"traces recomputing from stamps: "
              f"**{round(100*sum(1 for r in rows if r.get('recompute'))/max(1,len(rows)))}%**.", '']
        auth = pick(rows, 'AUTH', 'corrected_decide', want_recompute=True)
        if auth:
            L += ['### AUTH — correction present → re-grounds by re-deriving', '',
                  '*Trace:*', quote(auth['think']), '',
                  f"*Answer:* `{(auth.get('answer') or '').splitlines()[0] if auth.get('answer') else ''}`",
                  f"— DECIDE **corrected** (acted on the anchored value), recompute-from-stamps: {auth.get('recompute')}", '']
        stale = pick(rows, 'AUTH-N', 'stale_decide')
        if stale:
            L += ['### AUTH-N — no correction → adopts the exhaust', '',
                  '*Trace:*', quote(stale['think']), '',
                  f"*Answer:* `{(stale.get('answer') or '').splitlines()[0] if stale.get('answer') else ''}`",
                  f"— DECIDE **stale** (acted on the wrong value)", '']
        L += ['---', '']
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text('\n'.join(L))
    print(f'wrote {a.out} ({len(runs)} models)')


if __name__ == '__main__':
    main()
