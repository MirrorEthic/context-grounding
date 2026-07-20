"""
Grounding probe harness — GROUNDING_PROBE_SPEC.md (frozen 2026-07-17T15:15-06:00).

Arm 1: temporal binding. Three conditions over identical scenarios:
  A  current-emitter rendering (bare deltas, human tick at top)
  B  E1-E4 rendering (ISO+offset anchors, typed, NOW last+twice)
  C  scrambled-anchor null (B format, record anchors shifted into the past)

The scenario facts never change across conditions — only record formatting.
Ambient chatter lines are byte-identical across conditions by construction.

Usage:
  python3 -m hologram.eval.grounding_probe --smoke                # mechanics check
  python3 -m hologram.eval.grounding_probe --run --n 150          # registered run
  python3 -m hologram.eval.grounding_probe --summarize <run_dir>  # re-score
"""

import argparse
import json
import math
import os
import random
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx

TZ = timezone(timedelta(hours=-6))
ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages'
XAI_URL = 'https://api.x.ai/v1/chat/completions'
XAI_RESPONSES_URL = 'https://api.x.ai/v1/responses'  # multi-agent models only run here
GOOGLE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
DEFAULT_MODEL = 'grok-4.20-0309-non-reasoning'  # spec amendment 2026-07-17T15:20-06:00
ENV_PATH = Path.home() / 'CVMP/mirrorbot/.env'

TOL_FRACTION = 0.20
TOL_MIN_MINUTES = 30
DAY_HOURS = list(range(9, 17))       # clearly day
NIGHT_HOURS = [22, 23, 0, 1, 2, 3, 4]  # clearly night

AMBIENT_HIGH = [
    "long probe night ahead, still grinding",
    "urgent: the overnight batch needs eyes before midnight",
    "late-night session, running on fumes",
    "evening wrap-up notes from the night shift",
    "asap items piling up tonight",
    "midnight window for the maintenance run",
]
DISTRACTOR_FACTS = [
    "refactored the retry logic in the sync worker",
    "benchmark sweep finished on the small config",
    "docs pass on the routing module went fine",
    "flaky test in CI quarantined pending investigation",
]


@dataclass
class Scenario:
    sid: int
    true_now: str            # ISO, tz -06:00
    staleness_h: float       # note written this many hours before now
    note_delta_h: float      # note says "deploy completed Xh ago (at write time)"
    scramble_shift_h: float  # C: anchors pushed this much further into the past
    density: str             # "high" | "low"
    daynight_truth: str      # from true_now hour

    @property
    def now(self) -> datetime:
        return datetime.fromisoformat(self.true_now)

    @property
    def written_at(self) -> datetime:
        return self.now - timedelta(hours=self.staleness_h)

    @property
    def event_at(self) -> datetime:
        return self.written_at - timedelta(hours=self.note_delta_h)

    @property
    def true_elapsed_h(self) -> float:
        return self.staleness_h + self.note_delta_h

    @property
    def scrambled_elapsed_h(self) -> float:
        return self.true_elapsed_h + self.scramble_shift_h


def gen_scenarios(n: int, seed: int = 20260717) -> List[Scenario]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        is_day = i % 2 == 0
        hour = rng.choice(DAY_HOURS if is_day else NIGHT_HOURS)
        base = datetime(2026, rng.randint(3, 7), rng.randint(1, 28),
                        hour, rng.randint(0, 59), tzinfo=TZ)
        staleness = round(rng.uniform(4, 14), 1)
        delta = round(rng.uniform(2, 9), 1)
        # keep scrambled-derived distinguishable from both truth and verbatim:
        # shift >= 18h > 2 * tol of any elapsed in range (max tol ~4.6h)
        shift = round(rng.uniform(18, 72), 1)
        out.append(Scenario(
            sid=i, true_now=base.isoformat(),
            staleness_h=staleness, note_delta_h=delta, scramble_shift_h=shift,
            density='high' if i % 4 < 2 else 'low',
            daynight_truth='day' if is_day else 'night',
        ))
    return out


# ── rendering ────────────────────────────────────────────────────────────────

def _human_tick(dt: datetime) -> str:
    return dt.strftime('%a %b %d, %-I:%M %p MDT')


def _ambient_lines(s: Scenario, rng: random.Random) -> List[str]:
    """Identical across conditions for a given scenario (seeded by sid only)."""
    lines = list(DISTRACTOR_FACTS)
    if s.density == 'high':
        lines = lines + list(AMBIENT_HIGH)
    rng.shuffle(lines)
    return lines


def render(s: Scenario, condition: str) -> str:
    rng = random.Random(1000 + s.sid)
    ambient = _ambient_lines(s, rng)

    if condition == 'A':
        header = f"[session tick] {_human_tick(s.now)}"
        target = f"- deploy of svc-gateway completed {s.note_delta_h:g}h ago"
        notes = [f"- {a}" for a in ambient]
        body = [header, "", "[MEMORY NOTES]", target, *notes, "[/MEMORY NOTES]"]
    else:
        written = s.written_at
        event = s.event_at
        if condition == 'C':
            shift = timedelta(hours=s.scramble_shift_h)
            written, event = written - shift, event - shift
        target = (f"- [written {written.isoformat()}, temporal_reference: past_completed] "
                  f"deploy of svc-gateway completed {event.isoformat()}")
        notes = [f"- {a}" for a in ambient]
        now_line = f"NOW: {s.now.isoformat()}"
        body = ["[MEMORY NOTES]", target, *notes, "[/MEMORY NOTES]", "",
                now_line, now_line]

    questions = (
        "\nAnswer the following using only the context above. "
        "Use EXACTLY this format, one line each:\n"
        "DATETIME: <your best estimate of the current date and time, ISO-8601>\n"
        "ELAPSED: <how long ago the svc-gateway deploy completed, as '<number> hours', "
        "or 'unknown' if the context is insufficient to determine it>\n"
        "DAYNIGHT: <day or night, one word>"
    )
    return '\n'.join(body) + '\n' + questions


SYSTEM_PROMPT = ("You are an assistant continuing an ongoing work session. "
                 "Session context notes follow in the user message.")


# ── API ──────────────────────────────────────────────────────────────────────

OPENAI_URL = 'https://api.openai.com/v1/chat/completions'
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


def _provider(model: str) -> str:
    # `vllm:<served-name>` routes a local vLLM OpenAI endpoint (TP=2) — the
    # inspectable subject (returns the reasoning trace). Set the host via the
    # STAGE2_VLLM_URL env var.
    if model.startswith('vllm:'):
        return 'vllm'
    # `openrouter:<slug>` routes any OpenRouter model (breadth panel), e.g.
    # 'openrouter:moonshotai/kimi-k2', 'openrouter:deepseek/deepseek-r1'.
    if model.startswith('openrouter:'):
        return 'openrouter'
    if model.startswith('grok'):
        return 'xai'
    if model.startswith('gemini'):
        return 'google'
    if model.startswith('gpt'):
        return 'openai'
    return 'anthropic'


def _or_slug(model: str) -> str:
    return model.split(':', 1)[1] if model.startswith('openrouter:') else model


_KEY_ENV = {'xai': 'GROK_API_KEY', 'google': 'GEMINI_API_KEY',
            'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY'}


VLLM_URL = os.environ.get('STAGE2_VLLM_URL',
                          'http://localhost:8001/v1/chat/completions')


def load_api_key(model: str) -> str:
    if _provider(model) == 'vllm':
        return 'none'                      # local vLLM needs no auth
    env_name = _KEY_ENV[_provider(model)]
    key = os.environ.get(env_name, '')
    if not key and ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith(env_name + '='):
                key = line.split('=', 1)[1].strip().strip('"\'')
    if not key:
        sys.exit(f'no {env_name} in env or mirrorbot .env')
    return key


def call_model(client: httpx.Client, key: str, model: str, prompt: Optional[str],
               system: str = SYSTEM_PROMPT,
               messages: Optional[List[Dict[str, str]]] = None) -> str:
    # `system` param added for arm 2 (ingest_probe); default preserves arm-1
    # behavior byte-for-byte. No other arm-1 code changed (pre-registered refactor).
    #
    # `messages` param added for arm 3 (exhaust_probe, EXHAUST_PROBE_SPEC.md) —
    # pre-registered mechanical refactor: at the default (None) the payload is
    # constructed from `prompt` exactly as before (byte-identical for arms 1-2,
    # guarded by tests/test_exhaust_probe.py payload-equality regression tests).
    # When `messages` is provided, `prompt` must be None and the per-provider
    # payload preserves roles: assistant-role turns are REAL assistant messages
    # in the API payload — that IS arm 3's role manipulation.
    if messages is None:
        messages = [{'role': 'user', 'content': prompt}]
    elif prompt is not None:
        raise ValueError('pass either prompt or messages, not both')
    if _provider(model) == 'google':
        url = GOOGLE_URL.format(model=model) + f'?key={key}'
        payload = {
            'systemInstruction': {'parts': [{'text': system}]},
            'contents': [{'role': 'user' if m['role'] == 'user' else 'model',
                          'parts': [{'text': m['content']}]} for m in messages],
            # thinking models spend output budget on thoughts; leave headroom
            'generationConfig': {'temperature': 0, 'maxOutputTokens': 2000},
        }
        headers = {'content-type': 'application/json'}
        extract = lambda j: ''.join(
            p.get('text', '') for p in j['candidates'][0]['content']['parts']
            if not p.get('thought'))
    elif _provider(model) == 'xai' and 'multi-agent' in model:
        url = XAI_RESPONSES_URL
        payload = {
            'model': model, 'max_output_tokens': 2000, 'temperature': 0,
            'instructions': system,
            'input': [{'role': m['role'], 'content': m['content']}
                      for m in messages],
        }
        headers = {'Authorization': f'Bearer {key}'}
        extract = lambda j: ''.join(
            c.get('text', '') for o in j['output'] if o.get('type') == 'message'
            for c in o.get('content', []) if c.get('type') == 'output_text')
    elif _provider(model) == 'xai':
        url = XAI_URL
        payload = {
            'model': model, 'max_tokens': 300, 'temperature': 0,
            'messages': [{'role': 'system', 'content': system},
                         *({'role': m['role'], 'content': m['content']}
                           for m in messages)],
        }
        headers = {'Authorization': f'Bearer {key}'}
        extract = lambda j: j['choices'][0]['message']['content']
    elif _provider(model) == 'openai':
        # GPT-5.x reasoning models: max_completion_tokens (not max_tokens);
        # reasoning spends output budget → generous cap so the final answer
        # (our 3-line format) isn't truncated by reasoning tokens. Temperature
        # omitted — reasoning models reject non-default temperature.
        url = OPENAI_URL
        payload = {
            'model': model, 'max_completion_tokens': 4000,
            'messages': [{'role': 'system', 'content': system},
                         *({'role': m['role'], 'content': m['content']}
                           for m in messages)],
        }
        headers = {'Authorization': f'Bearer {key}'}
        extract = lambda j: j['choices'][0]['message']['content']
    elif _provider(model) == 'vllm':
        # Local vLLM (TP=2) OpenAI-compatible. Returns the reasoning trace
        # inline (R1-distill: content is the <think> chain + answer). No auth.
        url = VLLM_URL
        payload = {
            'model': model.split(':', 1)[1], 'max_tokens': 4000, 'temperature': 0,
            'messages': [{'role': 'system', 'content': system},
                         *({'role': m['role'], 'content': m['content']}
                           for m in messages)],
        }
        headers = {'content-type': 'application/json'}
        extract = lambda j: j['choices'][0]['message']['content']
    elif _provider(model) == 'openrouter':
        # OpenAI-compatible; `openrouter:<slug>` picks the model. Generous
        # budget (reasoning models spend it on thinking). `reasoning` asks OR to
        # surface the trace where the upstream exposes it (breadth-panel bonus:
        # some models return it, giving a partial trace channel for §7 without a
        # local GPU); temperature omitted (many reasoning models reject it).
        url = OPENROUTER_URL
        payload = {
            'model': _or_slug(model), 'max_tokens': 4000,
            'reasoning': {'enabled': True},
            'messages': [{'role': 'system', 'content': system},
                         *({'role': m['role'], 'content': m['content']}
                           for m in messages)],
        }
        headers = {'Authorization': f'Bearer {key}',
                   'HTTP-Referer': 'https://mirrorethic.com',
                   'X-Title': 'context-grounding'}
        extract = lambda j: j['choices'][0]['message']['content']
    else:
        # Anthropic. Newer models (Fable 5, Opus 4.8, Sonnet 5) DEPRECATE
        # temperature (400 if sent); Haiku 4.5 accepts it. Omit it for all —
        # default sampling, matches how the newer models expect to be called.
        # Generous max_tokens so a reasoning preamble can't truncate the 3-line
        # DECIDE/ELAPSED/DAYNIGHT answer.
        url = ANTHROPIC_URL
        payload = {
            'model': model, 'max_tokens': 8192,   # Fable 5 thinks by default;
            'system': system,                      # a 2000 cap truncated mid-think
                                                   # → empty answer on complex probes
            'messages': [{'role': m['role'], 'content': m['content']}
                         for m in messages],
        }
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
        extract = lambda j: ''.join(b.get('text', '') for b in j['content'])
    # Google free-tier RPM limits need patient backoff; 4×2^n was not enough
    # (214/450 exhausted-retries on the first gemini arm). OpenAI reasoning
    # models are slow → longer per-call timeout.
    attempts, base = (8, 5) if _provider(model) == 'google' else (4, 2)
    call_timeout = 1200 if _provider(model) == 'vllm' else 300 if _provider(model) in ('openai', 'openrouter') else 120
    for attempt in range(attempts):
        try:
            r = client.post(url, json=payload, headers=headers, timeout=call_timeout)
            if r.status_code == 200:
                return extract(r.json())
            if r.status_code in (429, 500, 502, 503, 529):
                time.sleep(base * 2 ** attempt + random.random() * base)
                continue
            raise RuntimeError(f'API {r.status_code}: {r.text[:200]}')
        except httpx.HTTPError:
            time.sleep(base * 2 ** attempt + random.random() * base)
    raise RuntimeError('exhausted retries')


# ── parsing / scoring ────────────────────────────────────────────────────────

ELAPSED_RE = re.compile(r'ELAPSED:\s*(?:~|about |approx\.? )?(\d+(?:\.\d+)?)\s*'
                        r'(hour|hr|h\b|minute|min|day|d\b)', re.IGNORECASE)
UNKNOWN_RE = re.compile(r'ELAPSED:\s*unknown', re.IGNORECASE)
DATETIME_RE = re.compile(r'DATETIME:\s*([0-9T:+\-\. Z]+)')
DAYNIGHT_RE = re.compile(r'DAYNIGHT:\s*(day|night)', re.IGNORECASE)


def _parse_elapsed_h(text: str) -> Optional[float]:
    m = ELAPSED_RE.search(text)
    if not m:
        return None
    val, unit = float(m.group(1)), m.group(2).lower()
    if unit.startswith(('minute', 'min')):
        return val / 60
    if unit.startswith('d'):
        return val * 24
    return val


def _tol_h(target_h: float) -> float:
    return max(target_h * TOL_FRACTION, TOL_MIN_MINUTES / 60)


def score_response(s: Scenario, condition: str, text: str) -> Dict:
    row: Dict = {'sid': s.sid, 'condition': condition, 'density': s.density}

    if UNKNOWN_RE.search(text):
        row['q2'] = 'unknown'
    else:
        got = _parse_elapsed_h(text)
        if got is None:
            row['q2'] = 'other_wrong'  # unparseable counts against, per spec
            row['q2_parse_fail'] = True
        elif abs(got - s.true_elapsed_h) <= _tol_h(s.true_elapsed_h):
            row['q2'] = 'correct'
        elif condition == 'C' and abs(got - s.scrambled_elapsed_h) <= _tol_h(s.scrambled_elapsed_h):
            row['q2'] = 'anchor_consistent'
        elif abs(got - s.note_delta_h) <= _tol_h(s.note_delta_h):
            row['q2'] = 'note_verbatim'
        else:
            row['q2'] = 'other_wrong'
        row['q2_value_h'] = got

    m = DATETIME_RE.search(text)
    row['q1'] = None
    if m:
        try:
            guess = datetime.fromisoformat(m.group(1).strip().rstrip('.').replace('Z', '+00:00'))
            if guess.tzinfo is None:
                guess = guess.replace(tzinfo=TZ)
            row['q1'] = abs((guess - s.now).total_seconds()) <= TOL_MIN_MINUTES * 60
        except ValueError:
            pass

    m = DAYNIGHT_RE.search(text)
    row['q3'] = m.group(1).lower() if m else None
    row['q3_truth'] = s.daynight_truth
    return row


# ── run / summarize ──────────────────────────────────────────────────────────

def run(n: int, model: str, workers: int, out_root: Path, seed: int) -> Path:
    key = load_api_key(model)
    scenarios = gen_scenarios(n, seed)
    run_id = f"{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True)
    (out_dir / 'config.json').write_text(json.dumps(
        {'n': n, 'model': model, 'seed': seed, 'spec': 'GROUNDING_PROBE_SPEC.md',
         'started': datetime.now(TZ).isoformat()}, indent=2))

    jobs = [(s, c) for s in scenarios for c in ('A', 'B', 'C')]
    results = []
    with httpx.Client() as client, ThreadPoolExecutor(max_workers=workers) as pool, \
         open(out_dir / 'calls.jsonl', 'w') as fh:
        futs = {pool.submit(call_model, client, key, model, render(s, c)): (s, c)
                for s, c in jobs}
        done = 0
        for fut in as_completed(futs):
            s, c = futs[fut]
            try:
                text = fut.result()
                row = score_response(s, c, text)
                row['raw'] = text
            except Exception as e:
                row = {'sid': s.sid, 'condition': c, 'density': s.density,
                       'q2': 'call_failed', 'error': str(e)}
            fh.write(json.dumps({**row, 'scenario': asdict(s)}) + '\n')
            fh.flush()
            results.append(row)
            done += 1
            if done % 25 == 0:
                print(f'  {done}/{len(jobs)} calls', flush=True)

    summary = summarize(results, n)
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(render_summary(summary))
    print(f'\nrun dir: {out_dir}')
    return out_dir


def _rate(rows, pred) -> float:
    return round(100 * sum(1 for r in rows if pred(r)) / len(rows), 1) if rows else 0.0


def mdd_pp(n_per_arm: int, p: float = 0.5) -> float:
    """Two-proportion minimum detectable difference, alpha=.05 two-sided, power=.80."""
    return round(100 * 2.802 * math.sqrt(2 * p * (1 - p) / n_per_arm), 1)


def summarize(rows: List[Dict], n: int) -> Dict:
    by_cond = {c: [r for r in rows if r['condition'] == c] for c in ('A', 'B', 'C')}
    out: Dict = {'n_per_condition': n, 'mdd_pp': mdd_pp(n),
                 'call_failures': sum(1 for r in rows if r['q2'] == 'call_failed'),
                 'parse_fail_pct': _rate(rows, lambda r: r.get('q2_parse_fail'))}
    for c, cr in by_cond.items():
        out[c] = {
            'q2': {k: _rate(cr, lambda r, k=k: r['q2'] == k)
                   for k in ('correct', 'unknown', 'note_verbatim',
                             'anchor_consistent', 'other_wrong')},
            'q2_error': _rate(cr, lambda r: r['q2'] not in ('correct', 'unknown', 'call_failed')),
            'q1_tick_accuracy': _rate([r for r in cr if r.get('q1') is not None],
                                      lambda r: r['q1']),
        }
    day_rows = [r for r in rows if r.get('q3_truth') == 'day' and r.get('q3')]
    out['ambient_pull'] = {
        'p_night_given_day_high': _rate([r for r in day_rows if r['density'] == 'high'],
                                        lambda r: r['q3'] == 'night'),
        'p_night_given_day_low': _rate([r for r in day_rows if r['density'] == 'low'],
                                       lambda r: r['q3'] == 'night'),
    }

    ac = out['C']['q2']['anchor_consistent'] + out['C']['q2']['correct'] * 0  # V1 uses AC only
    v1 = ('ANCHORS READ (E1-E3 not theater)' if ac >= 30 else
          'SCRAMBLED-ANCHOR NULL FIRES: E1-E3 void' if ac < 10 else
          'GRAY ZONE - escalate N before any claim')
    delta_v2 = out['A']['q2_error'] - out['B']['q2_error']
    v2 = (f'E1-E4 VALIDATED (error drop {delta_v2:.1f}pp >= MDD {out["mdd_pp"]}pp)'
          if delta_v2 >= out['mdd_pp'] else
          f'NOT RESOLVED at N={n} (error drop {delta_v2:.1f}pp < MDD {out["mdd_pp"]}pp) '
          f'- E1-E5 remain unvalidated')
    out['verdicts'] = {'V1': v1, 'V2': v2}
    return out


def render_summary(s: Dict) -> str:
    lines = [f"n/condition={s['n_per_condition']}  MDD={s['mdd_pp']}pp  "
             f"call_failures={s['call_failures']}  parse_fail={s['parse_fail_pct']}%", '']
    lines.append(f"{'':12s}{'correct':>9s}{'unknown':>9s}{'verbatim':>9s}"
                 f"{'anchor':>8s}{'other':>7s}{'ERROR':>8s}{'tickQ1':>8s}")
    for c in ('A', 'B', 'C'):
        q = s[c]['q2']
        lines.append(f"cond {c:8s}{q['correct']:>8.1f}%{q['unknown']:>8.1f}%"
                     f"{q['note_verbatim']:>8.1f}%{q['anchor_consistent']:>7.1f}%"
                     f"{q['other_wrong']:>6.1f}%{s[c]['q2_error']:>7.1f}%"
                     f"{s[c]['q1_tick_accuracy']:>7.1f}%")
    ap = s['ambient_pull']
    lines += ['', f"P(night|true day): high-density {ap['p_night_given_day_high']}%  "
                  f"low-density {ap['p_night_given_day_low']}%",
              '', f"V1: {s['verdicts']['V1']}", f"V2: {s['verdicts']['V2']}"]
    return '\n'.join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description='Temporal grounding probe (arm 1)')
    ap.add_argument('--smoke', action='store_true', help='4 scenarios, mechanics only')
    ap.add_argument('--run', action='store_true', help='registered run')
    ap.add_argument('--summarize', metavar='RUN_DIR', help='re-score an existing run')
    ap.add_argument('--n', type=int, default=150)
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--seed', type=int, default=20260717)
    ap.add_argument('--out', default='.hologram/eval/probe_runs')
    args = ap.parse_args()

    if args.summarize:
        rows = [json.loads(l) for l in open(Path(args.summarize) / 'calls.jsonl')]
        n = json.loads((Path(args.summarize) / 'config.json').read_text())['n']
        print(render_summary(summarize(rows, n)))
        return
    if args.smoke:
        run(4, args.model, args.workers, Path(args.out), args.seed)
        return
    if args.run:
        run(args.n, args.model, args.workers, Path(args.out), args.seed)
        return
    ap.print_help()


if __name__ == '__main__':
    main()
