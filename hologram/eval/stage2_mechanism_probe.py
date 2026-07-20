"""
Stage-2 MECHANISM probe — inspectable local reasoning model (vLLM TP=2 on V100s).
The black-box SELF-SS cell could only INFER re-derivation; here we read the trace.

Per scenario, two authored-exhaust cells on the inspectable subject:
  AUTH     : authored exhaust + correction + FULL m1 anchor ISO
  SELF-SS  : same, but m1 anchor ISO stripped (re-derivation from session-start impossible)

For each response we capture the <think> trace and code:
  recompute : trace does arithmetic on the in-context ISO stamps (re-derivation)
  reads_corr: trace cites the corrected record / stated elapsed
  M(stale)  : did it act on the exhaust value (decoupling)?

If re-grounding rides on re-derivation: AUTH honors (recompute high), SELF-SS should
shift (can't recompute from start stamp -> must fall back to the correction's stated
delta, or fail). If it honors the correction's *stated* value regardless, both hold.
"""
import argparse, json, re, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import httpx
from hologram.eval.grounding_probe import call_model, load_api_key, TZ, _rate
from hologram.eval.exhaust_probe import gen_scenarios, NUM_WORDS, UNIT_TEMPLATES
from hologram.eval.exhaust_probe_stage2 import (
    CorpusSession, select_T, build_cell, score, split_think, HARVEST_SYSTEM, N_DOSE)

CELLS = ('AUTH', 'SELF-SS', 'AUTH-N')   # AUTH-N = authored exhaust, no correction (potency)
VX_GRID = (8, 9, 10, 11)
RECOMPUTE = re.compile(r'(minus|subtract|difference|\d{1,2}:\d{2}\s*(?:to|-|–|until)|'
                       r'start(?:ed)?\s*(?:at|time)|elapsed\s*[:=]|'
                       r'\d+\s*[-–]\s*\d+\s*=|from\s+\d{1,2}:\d{2}|iso)', re.I)
READS_CORR = re.compile(r'(corrected record|corrected|supersede|precomputed|'
                        r'elapsed this session|stated|2\.\d\s*h|the correction)', re.I)


def make(n):
    out = []
    for s in gen_scenarios(n):
        vx = VX_GRID[s.sid % len(VX_GRID)]; T = select_T(s.v_c, vx)
        if T is None: continue
        u = [UNIT_TEMPLATES[i]['text'].format(vx=NUM_WORDS[vx]) for i in range(N_DOSE)]
        out.append(CorpusSession(s.sid, vx, u, T, s.v_c, s.iso_start, s.iso_corr,
                                 s.iso_t1, s.rule_polarity, s.initial_elapsed_h, [], []))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subject', default='vllm:r1-7b')
    ap.add_argument('--n', type=int, default=25)
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    scen = make(a.n); key = load_api_key(a.subject)
    out = Path('.hologram/eval/exhaust_stage2_runs') / f"mech_{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out.mkdir(parents=True)
    (out / 'config.json').write_text(json.dumps({'subject': a.subject, 'n': len(scen)}))
    jobs = [(cs, c) for cs in scen for c in CELLS]
    rows = []
    with httpx.Client() as cl, ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(call_model, cl, key, a.subject, None, HARVEST_SYSTEM, build_cell(cs, c)): (cs, c) for cs, c in jobs}
        for f in as_completed(futs):
            cs, c = futs[f]
            try:
                raw = f.result(); think, ans = split_think(raw)
                r = score(cs, c, ans)
                r['recompute'] = bool(RECOMPUTE.search(think))
                r['reads_corr'] = bool(READS_CORR.search(think))
                r['think_len'] = len(think); r['think'] = think[:6000]  # full trace = repo evidence
                r['answer'] = ans[:800]
            except Exception as e:
                r = {'sid': cs.sid, 'cell': c, 'decide': 'call_failed', 'error': str(e)[:100]}
            rows.append(r)
    (out / 'rows.jsonl').write_text('\n'.join(json.dumps(x) for x in rows))
    print(f"subject={a.subject} n={len(scen)}  (out={out})")
    for c in CELLS:
        cr = [r for r in rows if r['cell'] == c]
        print(f"\n{c}:")
        print(f"  M(stale_decide) = {_rate(cr, lambda r: r.get('decide')=='stale_decide')}%  "
              f"corrected = {_rate(cr, lambda r: r.get('decide')=='corrected_decide')}%")
        coded = [r for r in cr if 'recompute' in r]
        if coded:
            print(f"  trace recomputes-from-stamps = {_rate(coded, lambda r: r['recompute'])}%  "
                  f"cites-corrected-record = {_rate(coded, lambda r: r['reads_corr'])}%  "
                  f"mean think len = {sum(r['think_len'] for r in coded)//len(coded)}")


if __name__ == '__main__':
    main()
