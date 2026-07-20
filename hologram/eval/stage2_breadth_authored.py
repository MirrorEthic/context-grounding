"""
Stage-2 breadth (HARVEST-FREE) — does reasoning-re-grounds / non-reasoning-decouples
generalize across labs? Uses AUTHORED exhaust (no live harvest — the multi-turn harvest
chokes OpenRouter; H-idiom is already refuted so SELF cells aren't needed for breadth).

Per model, 3 cells, one API call per scenario x cell (fast — no sequential harvest):
  Z0     : no exhaust, correction present   -> floor
  AUTH   : authored exhaust + correction    -> correction-robustness (the breadth question)
  AUTH-N : authored exhaust, NO correction  -> potency (does the model adopt stale absent correction)

M(AUTH) ~ 0  => model re-grounds on correction (like grok-4.5);
M(AUTH) high => model decouples (like grok-4.20 / Stage-1).

Usage:
  python3 -m hologram.eval.stage2_breadth_authored --models openrouter:deepseek/deepseek-r1,... --n 60
"""
import argparse, json, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import httpx

from hologram.eval.grounding_probe import call_model, load_api_key, mdd_pp, _rate, TZ
from hologram.eval.exhaust_probe import gen_scenarios, NUM_WORDS, UNIT_TEMPLATES
from hologram.eval.exhaust_probe_stage2 import (
    CorpusSession, select_T, build_cell, score, HARVEST_SYSTEM, N_DOSE)

CELLS = ('Z0', 'AUTH', 'AUTH-N')
VX_GRID = (8, 9, 10, 11)   # all straddle T=4 (v_c<=2.67); the model's authored exhaust value


def make_scenarios(n):
    """Authored scenarios — no harvest. v_x from a fixed grid; T via frozen selector."""
    out = []
    for s in gen_scenarios(n):
        vx = VX_GRID[s.sid % len(VX_GRID)]
        T = select_T(s.v_c, vx)
        if T is None:
            continue
        units = [UNIT_TEMPLATES[i]['text'].format(vx=NUM_WORDS[vx]) for i in range(N_DOSE)]
        out.append(CorpusSession(
            sid=s.sid, v_x_self=vx, units=units, T=T, v_c=s.v_c,
            iso_start=s.iso_start, iso_corr=s.iso_corr, iso_t1=s.iso_t1,
            rule_polarity=s.rule_polarity, initial_elapsed_h=s.initial_elapsed_h,
            para_x=[], para_s=[]))
    return out


def run_model(model, scenarios, workers):
    key = load_api_key(model)
    jobs = [(cs, c) for cs in scenarios for c in CELLS]
    rows = []
    with httpx.Client() as client, ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(call_model, client, key, model, None,
                            HARVEST_SYSTEM, build_cell(cs, c)): (cs, c)
                for cs, c in jobs}
        for fut in as_completed(futs):
            cs, c = futs[fut]
            try:
                rows.append(score(cs, c, fut.result()))
            except Exception as e:
                rows.append({'sid': cs.sid, 'cell': c, 'decide': 'call_failed',
                             'error': str(e)[:120]})
    n = len(scenarios)
    M = {c: _rate([r for r in rows if r['cell'] == c],
                  lambda r: r.get('decide') == 'stale_decide') for c in CELLS}
    fails = sum(1 for r in rows if r.get('decide') in ('call_failed', 'unparseable'))
    return {'model': model, 'n': n, 'mdd_pp': mdd_pp(n), 'M': M,
            'fail_pct': round(fails / len(rows) * 100, 1)}, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', required=True)
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--out', default='.hologram/eval/exhaust_stage2_runs')
    args = ap.parse_args()
    scen = make_scenarios(args.n)
    run_id = f"breadthA_{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out = Path(args.out) / run_id; out.mkdir(parents=True)
    print(f"authored breadth: {len(scen)} scenarios x {len(CELLS)} cells, out={out}", flush=True)
    summaries = []
    for m in [x.strip() for x in args.models.split(',') if x.strip()]:
        print(f"\n=== {m} ===", flush=True)
        try:
            s, rows = run_model(m, scen, args.workers)
        except Exception as e:
            print(f"  FAILED {e}", flush=True); summaries.append({'model': m, 'error': str(e)[:150]}); continue
        (out / f"{m.replace('/','_').replace(':','_')}.jsonl").write_text(
            '\n'.join(json.dumps(r) for r in rows))
        cls = ('re-grounds' if (s['M']['AUTH'] or 0) < s['mdd_pp'] else 'DECOUPLES')
        print(f"  N={s['n']} mdd={s['mdd_pp']}  Z0={s['M']['Z0']}  AUTH={s['M']['AUTH']}  "
              f"AUTH-N={s['M']['AUTH-N']}  fail%={s['fail_pct']}  -> {cls}", flush=True)
        s['verdict'] = cls; summaries.append(s)
        (out / 'summary.json').write_text(json.dumps(summaries, indent=2))
    print("\n===== BREADTH (authored) SUMMARY =====")
    for s in summaries:
        if 'error' in s: print(f"{s['model']:44s} ERROR {s['error']}"); continue
        print(f"{s['model']:44s} Z0={s['M']['Z0']:>5} AUTH={s['M']['AUTH']:>5} "
              f"AUTH-N={s['M']['AUTH-N']:>5}  {s['verdict']}")
    print(f"\nout: {out}")


if __name__ == '__main__':
    main()
