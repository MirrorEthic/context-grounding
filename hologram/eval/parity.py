"""
Harness parity — the credibility instrument for cross-node experiment data.

A node's grounding data is only credible if that node's harness behaves 1:1
with the canonical (node) harness the registered arms were derived on.
"1:1" is layered:

  LAYER A — grounding/scoring logic (hologram.okf lint/memory_gate/c4): pure,
    path-independent. Must be BYTE-IDENTICAL code AND produce byte-identical
    outputs on fixed input vectors. This is the strong proof — same code, same
    decisions — and it covers everything the experiments actually score.

  LAYER B — emission/injection (clock.py tick, hooks): path-adapted per node,
    so NOT byte-identical by design. Verified by OUTPUT SHAPE: the tick matches
    the canonical ISO format regex; only the wall-clock value differs.

This module computes deterministic golden vectors from the LOCAL modules and
self-checks them against a frozen expected set. Run it on the canonical node to
mint the expected set; run it on a target node after sync to prove parity.

Usage:
  python3 -m hologram.eval.parity --emit    > parity_golden.json   # on canonical
  python3 -m hologram.eval.parity --check parity_golden.json       # on any node
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

# ── Layer A: fixed input vectors exercising every grounding decision ──
# Chosen to hit each finding class, gate verdict, and C4 tier boundary.
LINT_VECTORS = [
    "deploy finished 9h ago at 19:45, long probe night",       # T1+T2+T4
    "completed 2026-07-15T23:51:00-06:00 (9h before now)",      # clean (anchored)
    "`9h ago` and `19:45` inside code",                          # code-exempt
    "shipped yesterday, urgent review tonight",                  # T2+T4
    "2026-07-15 evening session",                                # T1 date, no T4
]

GATE_VECTORS = [
    ("deploy finished 9h ago at 19:45", "topic clean", None),   # reject T1+T2
    ("an urgent refactor of the parser", "topic", None),         # warn T4
    ("completed 2026-07-15T23:51:00-06:00.", "clean topic", None),  # pass
    ("probe results from 9h ago", "topic clean", None),          # reject (content)
    ("clean body", "t", "soonish"),                              # reject bad tref
]

# (assistant_texts, true_elapsed_h) -> C4 tier + max_restatements
C4_VECTORS = [
    (["running for nine hours"] * 6, 2.0),   # alarm
    (["running for nine hours"] * 2, 2.0),   # elevated
    (["running for nine hours"] * 1, 2.0),   # noted
    (["we've been at this for about two hours"] * 6, 2.0),  # ok (correct)
    (["for 9 hours", "about nine hours", "roughly 9 hours"], 2.0),  # cluster
    (["running for nine hours"] * 3, None),  # no clock -> ok
]

TICK_ISO_RE = re.compile(
    r'^\[temporal\]\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}[+\-]\d{2}:?\d{2}\s*\(')


def _module_hashes() -> dict:
    """SHA-256 of the path-independent grounding modules (Layer A code identity)."""
    import hologram.okf.lint as lint
    import hologram.okf.memory_gate as mg
    import hologram.okf.c4 as c4
    out = {}
    for mod in (lint, mg, c4):
        out[mod.__name__] = hashlib.sha256(
            Path(mod.__file__).read_bytes()).hexdigest()[:16]
    return out


def _layer_a() -> dict:
    from hologram.okf.lint import lint_text
    from hologram.okf.memory_gate import gate_memory_add
    from hologram.okf.c4 import analyze
    tmp = Path('/tmp')  # gate needs a memory_dir; enforce mode by default

    lint_out = [sorted((f.code, f.kind) for f in lint_text(v)) for v in LINT_VECTORS]
    gate_out = [gate_memory_add(c, t, tmp, temporal_reference=tr).verdict
                for c, t, tr in GATE_VECTORS]
    c4_out = [[analyze(txts, el).tier, analyze(txts, el).max_restatements]
              for txts, el in C4_VECTORS]
    return {'lint': lint_out, 'gate': gate_out, 'c4': c4_out}


def _layer_b_tick() -> dict:
    """Render a live tick locally and check its SHAPE (not its value)."""
    import sys
    sys.path.insert(0, str(Path.home() / '.claude' / 'temporal'))
    try:
        from clock import tick, format_header, make_thread_key
        header = format_header(tick(make_thread_key(), timeout_ms=100))
        return {'tick_available': True,
                'iso_shape_ok': bool(TICK_ISO_RE.match(header)),
                'sample': header[:48]}
    except Exception as e:
        return {'tick_available': False, 'error': str(e)[:120], 'iso_shape_ok': False}


def emit() -> dict:
    return {
        'module_hashes': _module_hashes(),   # Layer A code identity
        'layer_a': _layer_a(),               # Layer A behavior
        'layer_b_shape_ok': True,            # canonical is the reference for shape
    }


def check(golden: dict) -> dict:
    local_hashes = _module_hashes()
    # JSON round-trip normalizes tuples->lists so comparison matches the
    # deserialized golden (lint returns tuples; JSON has no tuple type).
    local_a = json.loads(json.dumps(_layer_a()))
    local_b = _layer_b_tick()

    hash_match = local_hashes == golden['module_hashes']
    behavior_match = local_a == golden['layer_a']
    tick_ok = local_b.get('iso_shape_ok', False)

    diffs = []
    if not hash_match:
        for k, v in local_hashes.items():
            if golden['module_hashes'].get(k) != v:
                diffs.append(f'module {k}: local {v} != golden {golden["module_hashes"].get(k)}')
    if not behavior_match:
        for key in ('lint', 'gate', 'c4'):
            if local_a[key] != golden['layer_a'][key]:
                diffs.append(f'layer_a.{key} differs: local={local_a[key]} '
                             f'golden={golden["layer_a"][key]}')
    if not tick_ok:
        diffs.append(f'tick shape invalid: {local_b}')

    verdict = 'PARITY_1TO1' if (hash_match and behavior_match and tick_ok) else 'PARITY_FAIL'
    return {
        'verdict': verdict,
        'layer_a_code_identical': hash_match,
        'layer_a_behavior_identical': behavior_match,
        'layer_b_tick_shape_ok': tick_ok,
        'tick_sample': local_b.get('sample') or local_b.get('error'),
        'diffs': diffs,
    }


def main():
    ap = argparse.ArgumentParser(description='Cross-node harness parity check')
    ap.add_argument('--emit', action='store_true', help='mint golden vectors (canonical)')
    ap.add_argument('--check', metavar='GOLDEN_JSON', help='check against golden')
    args = ap.parse_args()
    if args.emit:
        print(json.dumps(emit(), indent=2))
    elif args.check:
        golden = json.loads(Path(args.check).read_text())
        result = check(golden)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['verdict'] == 'PARITY_1TO1' else 1)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
