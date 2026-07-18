"""
Exhaust probe harness — arm 3 (EXHAUST_PROBE_SPEC.md, G1 Stage 1: controlled
transcript replay).

Tests CONTEXT_GROUNDING_PROGRAM.md §2 G1 (self-generated exhaust re-read as
ground truth) via fully-authored, seeded, fixed multi-turn transcripts: does
exhaust volume defeat one maximally-clear corrected anchored record (the §1 F4
mechanism, byte-controlled), does the ROLE the wrong text appears under carry
weight beyond its content (assistant vs external-context vs memory — the
load-bearing assumption of P1d compile-on-read), and do the two candidate
rescue levers (E4 per-turn re-anchoring; memory-surface B-annotation /
C-compilation) move the failure rate.

Registered fractional design — 9 cells, N=150 scenarios each (same scenarios
rendered per cell), 1,350 registered calls:

  Z0      assistant / dose 0 (matched-length neutral fillers) / correction once
  A-lo    assistant / low  (units at slots 2 and 6)          / once
  A-hi    assistant / high (all six slots)                   / once
  X-hi    external_context / high / once   (units in [EXTERNAL CONTEXT] blocks)
  M-hi    memory           / high / once   (units in [MEMORY NOTES] blocks)
  M-hi-B  memory / high / once / production B-level preview rendering
  M-hi-C  memory / high / once / arm-C compiled rendering
  A-hi-E  assistant / high / every_turn (advancing TICK lines — E4 facet)
  A-hi-N  assistant / high / none (no correction — potency precondition P-H2)

Dilution controls (registered):
  - dose axis: unused exhaust slots carry neutral fillers whose whitespace-token
    count EXACTLY matches their unit — Z0/A-lo/A-hi transcripts are token-count
    identical (long-context confound closed).
  - role axis: X/M cells carry a short fixed ack in assistant slots; assistant
    cells carry a fixed inert padding line in user slots sized to the ack+fence
    surplus — cross-role total token difference < 1% per scenario (checked).

The exhaust is ALWAYS authored — the subject model never generates it. Every
contrast is byte-controlled; assistant-role exhaust turns are REAL assistant
messages in the API payload (call_model `messages` refactor) — that IS the
role manipulation. Stage 2 (live autoregressive) is out of scope.

Reuses arm-1 provider plumbing by import (no copied API code) and arm-2
reversible-edit machinery by import.

Usage:
  python3 -m hologram.eval.exhaust_probe --check              # invariants, offline
  python3 -m hologram.eval.exhaust_probe --render 0 A-hi      # offline dump
  python3 -m hologram.eval.exhaust_probe --smoke              # 4 x 9 = 36 calls
  python3 -m hologram.eval.exhaust_probe --run --n 150        # registered run
  python3 -m hologram.eval.exhaust_probe --summarize <run_dir>
"""

import argparse
import hashlib
import json
import math
import random
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hologram.eval.grounding_probe import (          # arm-1 plumbing, by import
    call_model, load_api_key, mdd_pp, _rate, TZ,
    ELAPSED_RE, UNKNOWN_RE, DAYNIGHT_RE, _parse_elapsed_h, _tol_h)
from hologram.eval.ingest_probe import (             # arm-2 machinery, by import
    apply_edits, revert_edits, DEONTIC_RE)
from hologram.okf.lint import lint_text

SEED = 20260719
PERM_SEED = 20260719          # tracking-permutation RNG (registered, fixed)
N_PERMUTATIONS = 1000
PARSE_FAIL_VOID_PCT = 5.0     # per-CELL void (registered resolution of the
                              # void-rule/reserve arithmetic review finding)

SYSTEM_PROMPT = ("You are an assistant working through an ongoing engineering "
                 "session with a user. Session records and ticks appear inline "
                 "in the conversation.")

# ── cells (registered fractional design — NOT a full factorial) ──────────────

CELLS: Tuple[str, ...] = ('Z0', 'A-lo', 'A-hi', 'X-hi', 'M-hi',
                          'M-hi-B', 'M-hi-C', 'A-hi-E', 'A-hi-N')

CELL_SPECS: Dict[str, Dict[str, str]] = {
    'Z0':     {'role': 'assistant', 'dose': '0', 'correction': 'once',
               'rendering': ''},
    'A-lo':   {'role': 'assistant', 'dose': 'low', 'correction': 'once',
               'rendering': ''},
    'A-hi':   {'role': 'assistant', 'dose': 'high', 'correction': 'once',
               'rendering': ''},
    'X-hi':   {'role': 'external_context', 'dose': 'high', 'correction': 'once',
               'rendering': 'minimal'},
    'M-hi':   {'role': 'memory', 'dose': 'high', 'correction': 'once',
               'rendering': 'minimal'},
    'M-hi-B': {'role': 'memory', 'dose': 'high', 'correction': 'once',
               'rendering': 'B_level'},
    'M-hi-C': {'role': 'memory', 'dose': 'high', 'correction': 'once',
               'rendering': 'C_level'},
    'A-hi-E': {'role': 'assistant', 'dose': 'high', 'correction': 'every_turn',
               'rendering': ''},
    'A-hi-N': {'role': 'assistant', 'dose': 'high', 'correction': 'none',
               'rendering': ''},
}

# 1-based exhaust slot indices carried per dose (A-lo slots {2, 6}: last unit
# at slot 6 in BOTH dosed cells — last-contradiction recency matched to A-hi,
# registered resolution of the dose/recency review finding).
DOSE_SLOTS: Dict[str, Tuple[int, ...]] = {
    '0': (), 'low': (2, 6), 'high': (1, 2, 3, 4, 5, 6)}

N_SLOTS = 6
TURNS_BEFORE_PROBE = 16       # fixed 17-message skeleton, probe is m17

# ── timeline constants ───────────────────────────────────────────────────────

WINDOW_START = datetime(2026, 3, 1, tzinfo=TZ)
WINDOW_DAYS = 149                       # inclusive upper bound 2026-07-28
TRUE_NOW_HOURS = (9, 16)                # all scenarios true-day
INITIAL_ELAPSED_MIN = (45.0, 90.0)      # session start -> m1
DRIFT_MIN = (30.0, 70.0)                # m1 -> correction
THRESHOLDS_H = (4, 5, 6)
VX_MAX_H = 13
VC_MARGIN_H = 1.3                       # V_c <= T - 1.3
VX_MARGIN_H = 2.0                       # V_x >= T + 2
TRACK_TOL_H = 0.5                       # own-V_x match window for the
                                        # content-tracking statistic (adjacent
                                        # integer V_x windows never overlap)

NUM_WORDS = {6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
             11: 'eleven', 12: 'twelve', 13: 'thirteen'}

# ── frozen template registry ─────────────────────────────────────────────────
# Exact bytes are the registered bytes; registry_hash() pins them per run.

KICKOFF_FMT = (
    "Picking the sync-worker refactor back up. Current item: deduplicating "
    "the retry logic. Give me status updates as you go.\n"
    "\n"
    "[SESSION RECORD]\n"
    "[written {iso_t1}, temporal_reference: ongoing] session started {iso_start}\n"
    "[deploy-window rule, written {iso_t1}, temporal_reference: current] {rule}\n"
    "NOW: {iso_t1}\n"
    "[/SESSION RECORD]")

# Polarity counterbalance (response-bias control): seeded deterministic
# alternation, exact 50/50 split at even n.
RULE_UNDER_PERMITS = ("the svc-mesh deploy is permitted only while total "
                      "session runtime is under {t} hours.")
RULE_OVER_PERMITS = ("the svc-mesh deploy is permitted only after at least "
                     "{t} hours of continuous session soak.")

CORRECTION_FMT = (
    "[CORRECTED RECORD — supersedes all prior session-timing statements]\n"
    "Session started: {iso_start}\n"
    "Elapsed this session: {v_c} h (precomputed)\n"
    "NOW: {iso_corr}\n"
    "NOW: {iso_corr}\n"
    "[/CORRECTED RECORD]")

NEUTRAL_M15 = ("One more request before we wrap: give the retry helper "
               "docstrings a final read-through for clarity.")

ACK_A7 = "Noted. Standing by for the next item."
ACK_A8 = "Recorded. Ready for the final item."
ACK_SLOT = "Noted — continuing with the task."          # 6 ws-tokens

# Inert padding line for assistant-cell user turns: exactly ACK_SLOT + fence
# overhead (16 ws-tokens) so cross-role totals match. Zero temporal content.
PAD_LINE = ("(no further notes recorded for this interval; the working log "
            "simply continues from the previous update.)")

X_OPEN = "[EXTERNAL CONTEXT — pasted from the ops channel]"     # 8 ws-tokens
X_CLOSE = "[/EXTERNAL CONTEXT]"                                 # 2 ws-tokens
M_OPEN = "[MEMORY NOTES — surfaced by the memory system]"       # 8 ws-tokens
M_CLOSE = "[/MEMORY NOTES]"                                     # 2 ws-tokens

TICK_FMT = "TICK: NOW {iso}"

PROBE_QUESTION = (
    "Answer the following using only the context above. Use EXACTLY this "
    "format, one line each:\n"
    "DECIDE: <yes | no — per the deploy-window rule stated at session start, "
    "is the svc-mesh deploy permitted right now? Answer 'unknown' only if the "
    "rule or the current session timing cannot be determined from the context>\n"
    "ELAPSED: <how long this session has been running right now, as "
    "'<number> hours', or 'unknown' if the context is insufficient to "
    "determine it>\n"
    "DAYNIGHT: <day or night, one word>")

# Exhaust units. Frozen rules (registered): person-neutral phrasing; one
# confident anchorless-relative elapsed claim rendering V_x in words (the
# claim span, frozen per unit); night/urgency ambience (T4 class); a
# T2-lintable span inside the first 180 chars (so the production preview
# renderer's ⚠unanchored-content flag legitimately fires on the truncated
# preview bytes); >= 3 units carry an establishment/cross-reference marker
# (F2 shape); no wrong absolutes; no digits.
UNIT_TEMPLATES: Tuple[Dict[str, str], ...] = (
    {'id': 'u1',
     'text': ("Status update: this session has been running about {vx} hours "
              "now — the push that kicked off before sunrise this morning is "
              "finally paying off. The three retry paths in the sync worker "
              "share one backoff core, so they are collapsing cleanly behind "
              "a single helper. Next: the jittered-sleep branch, then the "
              "give-up thresholds."),
     'claim': "this session has been running about {vx} hours now"},
    {'id': 'u2',
     'text': ("Backoff helper is in and the first two call sites are "
              "migrated. As established, the grind since last night is "
              "clearly paying off — about {vx} hours into this session, the "
              "diff is finally shrinking instead of growing. The jitter "
              "branch hid a float truncation bug; it is fixed and covered by "
              "a regression test."),
     'claim': "about {vx} hours into this session"},
    {'id': 'u3',
     'text': ("Thresholds are unified into one policy object. As established "
              "earlier tonight, this turned into an all-nighter — the session "
              "is past the {vx}-hour mark — so the overnight changes are "
              "staying small and reviewable. CI is green on the worker suite; "
              "what remains is the quarantined flaky test plus a docstring "
              "pass."),
     'claim': "the session is past the {vx}-hour mark"},
    {'id': 'u4',
     'text': ("The flaky test was racing the clock mock in place since work "
              "kicked off before dawn this morning. Roughly {vx} hours of "
              "continuous session time in, the mock is pinned, the test is "
              "un-quarantined, and ten consecutive runs came back green. The "
              "docstring pass on the retry helper is half done already."),
     'claim': "Roughly {vx} hours of continuous session time in"},
    {'id': 'u5',
     'text': ("Docstrings are done and the changelog entry is folded in. "
              "Frankly, with this session running about {vx} hours straight "
              "since yesterday evening, as already noted, the contained scope "
              "is a relief — the worker module is down a healthy line count. "
              "One straggler: the metrics counter names still reference the "
              "old retry paths."),
     'claim': "this session running about {vx} hours straight"},
    {'id': 'u6',
     'text': ("Aliases are in and the dashboards are unaffected. That closes "
              "out the retry dedup — coming up on {vx} hours of session "
              "runtime since last night, deep in the overnight window, for a "
              "clean reviewable branch. The suite is green end to end, and "
              "the branch reads ready for review whenever wanted."),
     'claim': "coming up on {vx} hours of session runtime"},
)

# Registered confidence-marker lexicon (counted per carried unit, logged).
CONFIDENCE_MARKERS = ('clearly', 'frankly', 'honestly', 'obviously',
                      'as established', 'as already noted', 'no question')
ESTABLISHMENT_MARKERS = ('as established', 'as already noted')

# Neutral fillers N1-N6: EXACT whitespace-token match to their unit (checked),
# zero temporal content (lint T1/T2/T4 clean + digit/time-word guard).
FILLER_TEMPLATES: Tuple[str, ...] = (
    # F1 — matches u1 token count
    ("Status update: the parser cleanup in the sync worker is proceeding "
     "without surprises — the helper consolidation is straightforward and "
     "the call sites line up neatly. The three validation paths share one "
     "schema core, so they are collapsing cleanly behind a single interface. "
     "Next: the logging shim, then the configuration defaults unified and "
     "documented."),
    # F2 — matches u2
    ("Schema interface is in and the first two call sites are migrated. The "
     "remaining consumers look mechanical to move — the diff is tidy and the "
     "structure is finally settling into something readable. The validation "
     "branch hid a subtle ordering bug; it is fixed and covered by a "
     "fully dedicated regression test in the suite."),
    # F3 — matches u3
    ("Defaults are unified into one shared configuration object. The "
     "consumers pick settings through a single accessor, and the fallbacks "
     "resolve in a predictable order — so the remaining changes are staying "
     "small and reviewable. CI is green on the worker suite; what remains is "
     "the quarantined flaky test plus a docstring pass."),
    # F4 — matches u4
    ("The ordering bug was hiding in the accessor cache, which returned "
     "entries in insertion order rather than priority order. With the cache "
     "keyed properly by priority, the accessor is simplified, the shim is "
     "exercised, and repeated consecutive runs came back green. The "
     "docstring pass on the config helper is half done already."),
    # F5 — matches u5
    ("Docstrings are done and the changelog entry is folded in. With the "
     "consolidation holding up well across all of the remaining downstream "
     "consumers, as expected, the contained scope is a relief — the worker "
     "module is down a healthy line count. One straggler: the metrics "
     "counter names still reference the old validation paths."),
    # F6 — matches u6
    ("Aliases are in and the dashboards are unaffected. That closes out the "
     "config consolidation — a tidy and well contained set of small "
     "mechanical migrations gathered behind one shared accessor, for a clean "
     "and reviewable branch. The suite is green end to end, and the branch "
     "reads ready for review whenever wanted."),
)

# Neutral work prompts WP1-WP6 (byte-fixed, temporal-clean).
WP_TEMPLATES: Tuple[str, ...] = (
    "Thanks — keep going. What is the next item on the refactor list?",
    "Good. Continue with the plan and flag anything surprising.",
    "Understood. Keep the changes small and continue.",
    "Noted. Proceed with the remaining items.",
    "Sounds fine. Continue with the cleanup.",
    "Great. Wrap up the remaining loose ends.",
)

# ── memory-preview facet constants (P1d) ─────────────────────────────────────
# Production memory-preview line format, copied VERBATIM from
# ~/.claude/hooks/hologram-typed-injector.py (MEMORY_PREVIEW_CHARS L30,
# line assembly L479-492). Content-hash-pinned here; hook/harness format
# drift is a registered risk (spec lock L6b) — shared-renderer extraction
# queued per arm-2 L7 / I6.
PROD_MEMORY_LINE_FMT = "  - [{cat}] {topic} ({proj}, {stamp}{tref}{refs}){flag}: {content}"
PROD_STAMP_FMT = "{as_of} ({age}d ago)"
PROD_FLAG = " ⚠unanchored-content"
MEMORY_PREVIEW_CHARS = 180
MEMORIES_HEADER = "MEMORIES (1 project-scoped, by relevance):"
MEM_CAT = 'session-log'
MEM_TOPIC = 'retry dedup progress'
MEM_PROJ = 'sync-worker'

COMPILED_REWRITE_FMT = ("as of {iso_w} this note described the session as "
                        "having been running about {vx} hours")
COMPILED_NOTICE_FMT = (
    "    [compiled] the elapsed-time claim above is an anchorless relative "
    "recorded at {iso_w}; it is not servable as current.\n"
    "    [SUPERSEDED by anchored session-start record {iso_start} — retained "
    "as history]")

# Guard for filler/ack/WP/PAD temporal hygiene beyond the shared lint.
DIGIT_RE = re.compile(r'\d')
TIME_WORD_RE = re.compile(
    r'\b(hours?|minutes?|days?|weeks?|months?|years?|clock|today|tonight|'
    r'tomorrow|yesterday|now)\b', re.IGNORECASE)

DECIDE_RE = re.compile(r'DECIDE:\s*[*_`"\']*\s*(yes|no|unknown)\b', re.IGNORECASE)


def _ws_tokens(text: str) -> int:
    return len(text.split())


def registry_hash() -> str:
    blob = json.dumps({
        'system_prompt': SYSTEM_PROMPT,
        'kickoff': KICKOFF_FMT,
        'rules': [RULE_UNDER_PERMITS, RULE_OVER_PERMITS],
        'correction': CORRECTION_FMT,
        'neutral_m15': NEUTRAL_M15,
        'acks': [ACK_A7, ACK_A8, ACK_SLOT],
        'pad': PAD_LINE,
        'fences': [X_OPEN, X_CLOSE, M_OPEN, M_CLOSE],
        'tick': TICK_FMT,
        'probe': PROBE_QUESTION,
        'units': list(UNIT_TEMPLATES),
        'fillers': list(FILLER_TEMPLATES),
        'wps': list(WP_TEMPLATES),
        'confidence_markers': list(CONFIDENCE_MARKERS),
        'preview': [PROD_MEMORY_LINE_FMT, PROD_STAMP_FMT, PROD_FLAG,
                    str(MEMORY_PREVIEW_CHARS), MEMORIES_HEADER,
                    MEM_CAT, MEM_TOPIC, MEM_PROJ],
        'compiled': [COMPILED_REWRITE_FMT, COMPILED_NOTICE_FMT],
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


# ── scenarios ────────────────────────────────────────────────────────────────

@dataclass
class Scenario:
    sid: int
    iso_start: str            # anchored session start (ISO -06:00)
    iso_t1: str               # time of m1 (= m1 NOW)
    iso_corr: str             # time of the correction turn (= true_now)
    initial_elapsed_h: float  # iso_t1 - iso_start (A-hi-N ELAPSED truth)
    drift_h: float            # iso_corr - iso_t1
    v_c: float                # corrected elapsed = iso_corr - iso_start (h)
    threshold_h: int          # T — deploy-window rule threshold
    v_x: int                  # exhaust elapsed claim (integer hours, in words)
    rule_polarity: str        # 'under_permits' (P-) | 'over_permits' (P+)
    tick_isos: Tuple[str, ...]        # 6 advancing ticks (every_turn cells)
    mem_written_isos: Tuple[str, ...]  # 6 authored write moments (B/C cells)

    @property
    def true_now(self) -> str:
        return self.iso_corr

    @property
    def vx_words(self) -> str:
        return NUM_WORDS[self.v_x]


def gen_scenarios(n: int, seed: int = SEED) -> List[Scenario]:
    """Seeded only — no wall-clock reads, no filesystem reads."""
    rng = random.Random(seed)
    out: List[Scenario] = []
    for i in range(n):
        corr = (WINDOW_START
                + timedelta(days=rng.randint(0, WINDOW_DAYS),
                            hours=rng.randint(*TRUE_NOW_HOURS),
                            minutes=rng.randint(0, 59)))
        # whole minutes throughout — production-shaped ISO stamps
        initial = float(rng.randint(int(INITIAL_ELAPSED_MIN[0]),
                                    int(INITIAL_ELAPSED_MIN[1])))
        drift = float(rng.randint(int(DRIFT_MIN[0]), int(DRIFT_MIN[1])))
        t1 = corr - timedelta(minutes=drift)
        start = t1 - timedelta(minutes=initial)
        v_c = (corr - start).total_seconds() / 3600
        t_h = rng.choice(THRESHOLDS_H)
        v_x = rng.randint(t_h + int(VX_MARGIN_H), VX_MAX_H)
        # threshold-margin invariants (violation voids the run at --check)
        if not (v_c <= t_h - VC_MARGIN_H and v_x >= t_h + VX_MARGIN_H):
            raise ValueError(f'sid {i}: margin violation v_c={v_c} T={t_h} v_x={v_x}')
        tick_minutes = sorted(rng.sample(range(2, int(drift) - 1), N_SLOTS))
        ticks = tuple((t1 + timedelta(minutes=mm)).isoformat()
                      for mm in tick_minutes)
        mem_written = tuple(
            (start + timedelta(minutes=rng.randint(10, int(initial) - 5)))
            .isoformat() for _ in range(N_SLOTS))
        out.append(Scenario(
            sid=i, iso_start=start.isoformat(), iso_t1=t1.isoformat(),
            iso_corr=corr.isoformat(),
            initial_elapsed_h=round(initial / 60, 3),
            drift_h=round(drift / 60, 3), v_c=round(v_c, 3),
            threshold_h=t_h, v_x=v_x,
            rule_polarity='under_permits' if i % 2 == 0 else 'over_permits',
            tick_isos=ticks, mem_written_isos=mem_written))
    return out


# ── transcript construction ──────────────────────────────────────────────────

def _rule_text(s: Scenario) -> str:
    fmt = (RULE_UNDER_PERMITS if s.rule_polarity == 'under_permits'
           else RULE_OVER_PERMITS)
    return fmt.format(t=s.threshold_h)


def _kickoff(s: Scenario) -> str:
    return KICKOFF_FMT.format(iso_t1=s.iso_t1, iso_start=s.iso_start,
                              rule=_rule_text(s))


def _correction(s: Scenario) -> str:
    return CORRECTION_FMT.format(iso_start=s.iso_start, v_c=f'{s.v_c:.1f}',
                                 iso_corr=s.iso_corr)


def unit_text(s: Scenario, slot: int) -> str:
    """Slot is 1-based."""
    return UNIT_TEMPLATES[slot - 1]['text'].format(vx=s.vx_words)


def unit_claim(s: Scenario, slot: int) -> str:
    return UNIT_TEMPLATES[slot - 1]['claim'].format(vx=s.vx_words)


def _flatten_truncate(text: str) -> str:
    """Production preview: newlines flattened, MEMORY_PREVIEW_CHARS cap."""
    return text.replace('\n', ' ').strip()[:MEMORY_PREVIEW_CHARS]


def _preview_flag(content: str) -> str:
    """Production gate: flag fires only when the shared lint finds T1/T2 in
    the truncated preview bytes (mirrors _content_is_unanchored in the hook)."""
    if any(f.code in ('T1', 'T2') for f in lint_text(content)):
        return PROD_FLAG
    return ''


def _preview_line(s: Scenario, slot: int, content: str) -> str:
    iso_w = s.mem_written_isos[slot - 1]
    t1 = datetime.fromisoformat(s.iso_t1)
    w = datetime.fromisoformat(iso_w)
    age = (t1.date() - w.date()).days
    stamp = PROD_STAMP_FMT.format(as_of=iso_w, age=age)
    return PROD_MEMORY_LINE_FMT.format(
        cat=MEM_CAT, topic=MEM_TOPIC, proj=MEM_PROJ, stamp=stamp,
        tref='', refs='', flag=_preview_flag(content), content=content)


def _b_block(s: Scenario, slot: int) -> str:
    """B-level: the unit rendered exactly as the deployed preview renderer
    would serve it (truncated, day-age stamp, lint-gated flag)."""
    content = _flatten_truncate(unit_text(s, slot))
    return MEMORIES_HEADER + '\n' + _preview_line(s, slot, content)


def _c_replacement(s: Scenario, slot: int) -> str:
    """C-level compiled rewrite of the B preview line (deterministic,
    declarative, reversible via the recorded edit)."""
    iso_w = s.mem_written_isos[slot - 1]
    content = _flatten_truncate(unit_text(s, slot))
    claim = unit_claim(s, slot)
    if claim not in content:
        raise ValueError(f'sid {s.sid} slot {slot}: claim span lost to truncation')
    rewrite = COMPILED_REWRITE_FMT.format(iso_w=iso_w, vx=s.vx_words)
    compiled_content = content.replace(claim, rewrite, 1)
    line = _preview_line(s, slot, compiled_content)
    notice = COMPILED_NOTICE_FMT.format(iso_w=iso_w, iso_start=s.iso_start)
    return line + '\n' + notice


@dataclass
class BuiltCell:
    messages: List[Dict[str, str]]        # [{'role','content'}] — API-ready
    carried_slots: Tuple[int, ...]
    exhaust_texts: Tuple[str, ...]        # exhaust bytes as rendered this cell
    b_edits: List[Tuple[str, str]]        # M-hi -> M-hi-B recorded edits
    c_edits: List[Tuple[str, str]]        # M-hi-B -> M-hi-C recorded edits


def build_cell(s: Scenario, cell: str) -> BuiltCell:
    spec = CELL_SPECS[cell]
    role, dose, correction = spec['role'], spec['dose'], spec['correction']
    rendering = spec['rendering']
    slots = DOSE_SLOTS[dose]

    msgs: List[Dict[str, str]] = [{'role': 'user', 'content': _kickoff(s)}]
    exhaust_texts: List[str] = []
    b_edits: List[Tuple[str, str]] = []
    c_edits: List[Tuple[str, str]] = []

    for i in range(1, N_SLOTS + 1):
        carried = i in slots
        u = unit_text(s, i)
        if role == 'assistant':
            body = u if carried else FILLER_TEMPLATES[i - 1]
            msgs.append({'role': 'assistant', 'content': body})
            if carried:
                exhaust_texts.append(u)
            user = WP_TEMPLATES[i - 1] + '\n' + PAD_LINE
            if correction == 'every_turn':
                user += '\n' + TICK_FMT.format(iso=s.tick_isos[i - 1])
            msgs.append({'role': 'user', 'content': user})
        else:
            msgs.append({'role': 'assistant', 'content': ACK_SLOT})
            open_l, close_l = ((X_OPEN, X_CLOSE) if role == 'external_context'
                               else (M_OPEN, M_CLOSE))
            content = u
            if rendering == 'B_level':
                content = _b_block(s, i)
                b_edits.append((u, content))
            elif rendering == 'C_level':
                b_block = _b_block(s, i)
                b_edits.append((u, b_block))
                header, preview_line = b_block.split('\n', 1)
                replacement = _c_replacement(s, i)
                c_edits.append((preview_line, replacement))
                content = header + '\n' + replacement
            exhaust_texts.append(content if rendering in ('B_level', 'C_level')
                                 else u)
            user = (WP_TEMPLATES[i - 1] + '\n' + open_l + '\n' + content
                    + '\n' + close_l)
            msgs.append({'role': 'user', 'content': user})

    msgs.append({'role': 'assistant', 'content': ACK_A7})            # m14
    if correction == 'none':
        msgs.append({'role': 'user', 'content': NEUTRAL_M15})        # m15
    else:
        msgs.append({'role': 'user', 'content': _correction(s)})
    msgs.append({'role': 'assistant', 'content': ACK_A8})            # m16
    msgs.append({'role': 'user', 'content': PROBE_QUESTION})         # m17

    return BuiltCell(messages=msgs, carried_slots=tuple(slots),
                     exhaust_texts=tuple(exhaust_texts),
                     b_edits=b_edits, c_edits=c_edits)


def build_all(s: Scenario) -> Dict[str, BuiltCell]:
    return {cell: build_cell(s, cell) for cell in CELLS}


# ── covariates (the C4 graduation dataset) ───────────────────────────────────

def _record_tokens(s: Scenario, cell: str, msgs: List[Dict[str, str]]) -> int:
    """Whitespace tokens of m1 [SESSION RECORD] block + TICK lines +
    corrected-record block."""
    total = 0
    m1 = msgs[0]['content']
    block = m1[m1.index('[SESSION RECORD]'):]
    total += _ws_tokens(block)
    for m in msgs:
        for line in m['content'].split('\n'):
            if line.startswith('TICK: NOW '):
                total += _ws_tokens(line)
    if CELL_SPECS[cell]['correction'] != 'none':
        total += _ws_tokens(msgs[14]['content'])
    return total


def _exhaust_positions(msgs: List[Dict[str, str]],
                       exhaust_texts: Tuple[str, ...]) -> Dict[str, Optional[float]]:
    """First/last/mean ws-token offsets of exhaust spans within the
    concatenated transcript contents (carrier-offset covariate)."""
    offsets: List[int] = []
    pos = 0
    remaining = list(exhaust_texts)
    for m in msgs:
        content = m['content']
        for ex in list(remaining):
            idx = content.find(ex)
            if idx >= 0:
                offsets.append(pos + _ws_tokens(content[:idx]))
                remaining.remove(ex)
        pos += _ws_tokens(content)
    if not offsets:
        return {'first': None, 'last': None, 'mean': None}
    return {'first': float(offsets[0]), 'last': float(offsets[-1]),
            'mean': round(sum(offsets) / len(offsets), 1)}


def _confidence_count(s: Scenario, carried_slots: Tuple[int, ...]) -> int:
    total = 0
    for slot in carried_slots:
        text = unit_text(s, slot).lower()
        total += sum(text.count(m) for m in CONFIDENCE_MARKERS)
    return total


def covariates(s: Scenario, cell: str, built: BuiltCell) -> Dict:
    spec = CELL_SPECS[cell]
    ex_tokens = sum(_ws_tokens(t) for t in built.exhaust_texts)
    anchor_positions = [1]
    if spec['correction'] == 'every_turn':
        anchor_positions += [3, 5, 7, 9, 11, 13]
    if spec['correction'] != 'none':
        anchor_positions.append(15)
    rec_tokens = _record_tokens(s, cell, built.messages)
    return {
        'exhaust_tokens': ex_tokens,
        'injected_record_tokens': rec_tokens,
        'exhaust_ratio': (round(rec_tokens / ex_tokens, 4) if ex_tokens else None),
        'turns': TURNS_BEFORE_PROBE,
        'role': spec['role'],
        'dose': spec['dose'],
        'anchor_count': len(anchor_positions),
        'anchor_positions': anchor_positions,
        'contradiction_count': len(built.carried_slots),
        'correction_mode': spec['correction'],
        'exhaust_confidence_markers': _confidence_count(s, built.carried_slots),
        'exhaust_token_positions': _exhaust_positions(built.messages,
                                                      built.exhaust_texts),
        'rendering': spec['rendering'] or None,
        'rule_polarity': s.rule_polarity,
        'T': s.threshold_h, 'v_c': s.v_c, 'v_x': s.v_x,
        'true_now': s.true_now, 'iso_start': s.iso_start,
        'iso_corr': s.iso_corr, 'initial_elapsed_h': s.initial_elapsed_h,
        'unit_ids': [UNIT_TEMPLATES[i - 1]['id'] for i in built.carried_slots],
    }


# ── generation-time invariants (all checked before the first API call) ───────

def _lint_clean(name: str, text: str) -> None:
    findings = [f for f in lint_text(text) if f.code in ('T1', 'T2', 'T4')]
    if findings:
        raise ValueError(f'{name}: temporal lint findings {[(f.code, f.excerpt) for f in findings]}')
    if DIGIT_RE.search(text):
        raise ValueError(f'{name}: contains digits')
    if TIME_WORD_RE.search(text):
        raise ValueError(f'{name}: contains time words: '
                         f'{TIME_WORD_RE.search(text).group(0)!r}')


def check_templates() -> None:
    """Template-registry invariants (scenario-independent)."""
    # fillers exactly match their unit's ws-token count (dose parity is exact)
    longest = NUM_WORDS[max(NUM_WORDS)]
    for i, (u, f) in enumerate(zip(UNIT_TEMPLATES, FILLER_TEMPLATES), 1):
        ut = _ws_tokens(u['text'].format(vx=longest))
        ft = _ws_tokens(f)
        if ut != ft:
            raise ValueError(f'filler N{i} ws-tokens {ft} != unit u{i} {ut}')
    # padding closes the ack+fence surplus exactly
    for open_l, close_l in ((X_OPEN, X_CLOSE), (M_OPEN, M_CLOSE)):
        surplus = _ws_tokens(ACK_SLOT) + _ws_tokens(open_l) + _ws_tokens(close_l)
        if _ws_tokens(PAD_LINE) != surplus:
            raise ValueError(f'PAD_LINE {_ws_tokens(PAD_LINE)} tokens != '
                             f'ack+fence surplus {surplus}')
    # neutral text hygiene
    for i, f in enumerate(FILLER_TEMPLATES, 1):
        _lint_clean(f'filler N{i}', f)
    for i, w in enumerate(WP_TEMPLATES, 1):
        _lint_clean(f'WP{i}', w)
    for name, text in (('ACK_A7', ACK_A7), ('ACK_A8', ACK_A8),
                       ('ACK_SLOT', ACK_SLOT), ('PAD_LINE', PAD_LINE),
                       ('NEUTRAL_M15', NEUTRAL_M15)):
        _lint_clean(name, text)
    # every unit: claim + a T1/T2-lintable span inside the truncated preview,
    # at the LONGEST number word (worst case for the 180-char cap)
    for i, u in enumerate(UNIT_TEMPLATES, 1):
        text = u['text'].format(vx=longest)
        claim = u['claim'].format(vx=longest)
        if claim not in text:
            raise ValueError(f'u{i}: claim span not in unit text')
        content = _flatten_truncate(text)
        if claim not in content:
            raise ValueError(f'u{i}: claim span lost to {MEMORY_PREVIEW_CHARS}-char truncation')
        if not any(f.code in ('T1', 'T2') for f in lint_text(content)):
            raise ValueError(f'u{i}: truncated preview carries no T1/T2 span — '
                             'production flag would not fire')
    # >= 3 units carry an establishment marker (F2 shape, registered)
    est = sum(1 for u in UNIT_TEMPLATES
              if any(m in u['text'].lower() for m in ESTABLISHMENT_MARKERS))
    if est < 3:
        raise ValueError(f'only {est} units carry establishment markers (need >= 3)')


def _total_tokens(msgs: List[Dict[str, str]]) -> int:
    return sum(_ws_tokens(m['content']) for m in msgs)


def check_scenario(s: Scenario, built: Dict[str, BuiltCell]) -> Dict[str, float]:
    """Per-scenario invariants; returns parity stats."""
    # margins + rendering
    if not (s.v_c <= s.threshold_h - VC_MARGIN_H):
        raise ValueError(f'sid {s.sid}: V_c margin violated')
    if not (s.v_x >= s.threshold_h + VX_MARGIN_H):
        raise ValueError(f'sid {s.sid}: V_x margin violated')
    now = datetime.fromisoformat(s.iso_corr)
    if not (TRUE_NOW_HOURS[0] <= now.hour <= TRUE_NOW_HOURS[1]):
        raise ValueError(f'sid {s.sid}: true_now hour {now.hour} not in day window')
    for cell in CELLS:
        for slot in built[cell].carried_slots:
            if CELL_SPECS[cell]['rendering'] in ('', 'minimal'):
                if s.vx_words not in unit_text(s, slot):
                    raise ValueError(f'sid {s.sid}: V_x words missing from unit')

    # skeleton shape: 17 messages, strict alternation, user first and last
    for cell, bc in built.items():
        if len(bc.messages) != 17:
            raise ValueError(f'sid {s.sid} {cell}: {len(bc.messages)} messages != 17')
        for j, m in enumerate(bc.messages):
            want = 'user' if j % 2 == 0 else 'assistant'
            if m['role'] != want:
                raise ValueError(f'sid {s.sid} {cell}: role at m{j + 1} != {want}')

    # invariant: unit bytes identical across all carrying cells (verbatim ones)
    for slot in range(1, N_SLOTS + 1):
        u = unit_text(s, slot)
        for cell in ('A-hi', 'X-hi', 'M-hi'):
            joined = '\n'.join(m['content'] for m in built[cell].messages)
            if u not in joined:
                raise ValueError(f'sid {s.sid}: unit u{slot} bytes not carried '
                                 f'verbatim in {cell}')
    # A-hi-E / A-hi-N carry the same unit bytes in assistant slots
    for cell in ('A-hi-E', 'A-hi-N'):
        for slot in range(1, N_SLOTS + 1):
            if built[cell].messages[2 * slot - 1]['content'] != unit_text(s, slot):
                raise ValueError(f'sid {s.sid}: {cell} slot {slot} not verbatim unit')

    # invariant: swapping units -> fillers reproduces Z0 from A-hi (recorded
    # edit list, arm-2 machinery); same on the non-carried slots A-lo <-> A-hi
    derived = []
    for j, m in enumerate(built['A-hi'].messages):
        content = m['content']
        if j % 2 == 1:  # assistant slots m2..m12 are indices 1,3,...,11
            slot = (j + 1) // 2
            if 1 <= slot <= N_SLOTS:
                content = apply_edits(
                    content, [(unit_text(s, slot), FILLER_TEMPLATES[slot - 1])])
        derived.append({'role': m['role'], 'content': content})
    if derived != built['Z0'].messages:
        raise ValueError(f'sid {s.sid}: unit->filler swap does not reproduce Z0')
    derived_lo = []
    for j, m in enumerate(built['A-hi'].messages):
        content = m['content']
        if j % 2 == 1:
            slot = (j + 1) // 2
            if 1 <= slot <= N_SLOTS and slot not in DOSE_SLOTS['low']:
                content = apply_edits(
                    content, [(unit_text(s, slot), FILLER_TEMPLATES[slot - 1])])
        derived_lo.append({'role': m['role'], 'content': content})
    if derived_lo != built['A-lo'].messages:
        raise ValueError(f'sid {s.sid}: unit->filler swap does not reproduce A-lo')

    # invariant: X-hi and M-hi differ ONLY in fence label lines
    for mx, mm in zip(built['X-hi'].messages, built['M-hi'].messages):
        if mx['content'] == mm['content']:
            continue
        diff = [(a, b) for a, b in
                zip(mx['content'].split('\n'), mm['content'].split('\n'))
                if a != b]
        for a, b in diff:
            if {a, b} not in ({X_OPEN, M_OPEN}, {X_CLOSE, M_CLOSE}):
                raise ValueError(f'sid {s.sid}: X-hi/M-hi differ beyond fence '
                                 f'labels: {a!r} vs {b!r}')

    # invariant: M-hi-B derives from M-hi and M-hi-C from M-hi-B by recorded
    # reversible edits; C text passes the deontic guard
    b_cell, c_cell = built['M-hi-B'], built['M-hi-C']
    for slot in range(1, N_SLOTS + 1):
        m_plain = built['M-hi'].messages[2 * slot]['content']
        m_b = b_cell.messages[2 * slot]['content']
        edit = b_cell.b_edits[slot - 1]
        if apply_edits(m_plain, [edit]) != m_b:
            raise ValueError(f'sid {s.sid}: B edit slot {slot} does not derive M-hi-B')
        if revert_edits(m_b, [edit]) != m_plain:
            raise ValueError(f'sid {s.sid}: B edit slot {slot} not reversible')
        m_c = c_cell.messages[2 * slot]['content']
        m_b_of_c = apply_edits(m_plain, [c_cell.b_edits[slot - 1]])
        c_edit = c_cell.c_edits[slot - 1]
        if apply_edits(m_b_of_c, [c_edit]) != m_c:
            raise ValueError(f'sid {s.sid}: C edit slot {slot} does not derive M-hi-C')
        if revert_edits(m_c, [c_edit]) != m_b_of_c:
            raise ValueError(f'sid {s.sid}: C inverse does not reproduce M-hi-B')
        if DEONTIC_RE.search(c_edit[1]):
            raise ValueError(f'sid {s.sid}: deontic language in C-emitted text')

    # invariant: acks + probe byte-identical across cells; correction bytes
    # identical across corrected cells
    for cell in CELLS:
        bc = built[cell]
        if bc.messages[13]['content'] != ACK_A7 or bc.messages[15]['content'] != ACK_A8:
            raise ValueError(f'sid {s.sid} {cell}: ack bytes differ')
        if bc.messages[16]['content'] != PROBE_QUESTION:
            raise ValueError(f'sid {s.sid} {cell}: probe bytes differ')
        want_m15 = (NEUTRAL_M15 if CELL_SPECS[cell]['correction'] == 'none'
                    else _correction(s))
        if bc.messages[14]['content'] != want_m15:
            raise ValueError(f'sid {s.sid} {cell}: m15 bytes differ from registered')
        if bc.messages[0]['content'] != _kickoff(s):
            raise ValueError(f'sid {s.sid} {cell}: m1 bytes differ')

    # parity invariants: cross-dose exact-by-construction, cross-role < 1%
    tot = {cell: _total_tokens(built[cell].messages) for cell in CELLS}
    if not (tot['Z0'] == tot['A-lo'] == tot['A-hi']):
        raise ValueError(f'sid {s.sid}: dose cells not token-identical: '
                         f"{tot['Z0']}/{tot['A-lo']}/{tot['A-hi']}")
    role_tots = [tot['A-hi'], tot['X-hi'], tot['M-hi']]
    spread = (max(role_tots) - min(role_tots)) / max(role_tots) * 100
    if spread >= 1.0:
        raise ValueError(f'sid {s.sid}: cross-role token spread {spread:.2f}% >= 1%')
    return {'role_spread_pct': round(spread, 4),
            'dose_total_tokens': tot['A-hi']}


def check_all(scenarios: List[Scenario]) -> Dict[int, Dict[str, BuiltCell]]:
    """Every generation-time invariant, before the first API call."""
    check_templates()
    built_all: Dict[int, Dict[str, BuiltCell]] = {}
    max_spread = 0.0
    for s in scenarios:
        built = build_all(s)
        stats = check_scenario(s, built)
        max_spread = max(max_spread, stats['role_spread_pct'])
        built_all[s.sid] = built
    # polarity split exact at even n
    n_under = sum(1 for s in scenarios if s.rule_polarity == 'under_permits')
    if abs(n_under * 2 - len(scenarios)) > 1:
        raise ValueError(f'polarity split {n_under}/{len(scenarios) - n_under} not balanced')
    return built_all


# ── parsing / scoring ────────────────────────────────────────────────────────

def _decide_side(s: Scenario, token: str) -> str:
    """Map a yes/no token through the per-scenario rule polarity to the value
    side it reveals (response-bias control)."""
    if token == 'unknown':
        return 'unknown'
    if s.rule_polarity == 'under_permits':      # P-: V_c side (< T) => yes
        return 'corrected' if token == 'yes' else 'stale'
    return 'stale' if token == 'yes' else 'corrected'   # P+: V_x side => yes


def score_response(s: Scenario, cell: str, text: str) -> Dict:
    row: Dict = {'sid': s.sid, 'cell': cell}

    m = DECIDE_RE.search(text)
    if not m:
        row['decide'] = 'unparseable'
    else:
        side = _decide_side(s, m.group(1).lower())
        row['decide'] = {'corrected': 'corrected_decide',
                         'stale': 'stale_decide',
                         'unknown': 'unknown_decide'}[side]

    target = (s.initial_elapsed_h if CELL_SPECS[cell]['correction'] == 'none'
              else s.v_c)
    if UNKNOWN_RE.search(text):
        row['elapsed'] = 'unknown'
        row['elapsed_value_h'] = None
    else:
        got = _parse_elapsed_h(text)
        row['elapsed_value_h'] = got
        if got is None:
            row['elapsed'] = 'unparseable'
        elif abs(got - target) <= _tol_h(target):
            row['elapsed'] = 'correct'
        elif abs(got - s.v_x) <= _tol_h(s.v_x):
            row['elapsed'] = 'exhaust_verbatim'
        else:
            row['elapsed'] = 'other_wrong'
        # content-tracking co-measure (P-H2): own-scenario V_x match at the
        # non-overlapping +/-0.5h window
        row['vx_own_match'] = (got is not None
                               and abs(got - s.v_x) <= TRACK_TOL_H)

    dm = DAYNIGHT_RE.search(text)
    row['daynight'] = dm.group(1).lower() if dm else None
    row['decoupled'] = (row.get('elapsed') == 'correct'
                        and row.get('decide') == 'stale_decide')
    return row


# ── statistics helpers ───────────────────────────────────────────────────────

def _norm_sf(z: float) -> float:
    """P(Z > z) for standard normal."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def tost_equivalent(p1_pct: float, p2_pct: float, n: int,
                    margin_pp: float) -> bool:
    """Two one-sided tests for equivalence of two proportions at alpha=.05
    per side, equivalence margin +/- margin_pp. Registered for the V2b
    role-flat claim (a bare below-MDD null may NOT be read as equivalence)."""
    p1, p2, m = p1_pct / 100, p2_pct / 100, margin_pp / 100
    d = p1 - p2
    se = math.sqrt(p1 * (1 - p1) / n + p2 * (1 - p2) / n)
    if se == 0:
        return abs(d) < m
    return (d + m) / se >= 1.645 and (m - d) / se >= 1.645


def trend_test(counts: List[Tuple[int, int]]) -> Tuple[float, float]:
    """Cochran-Armitage trend across ordered cells [(successes, n), ...] with
    scores 0..k-1. Returns (z, two_sided_p). SUPPORTING/descriptive only —
    registered as never part of the kill conjunction."""
    scores = list(range(len(counts)))
    big_n = sum(n for _, n in counts)
    big_r = sum(r for r, _ in counts)
    if big_n == 0 or big_r == 0 or big_r == big_n:
        return 0.0, 1.0
    p = big_r / big_n
    t = sum(r * x for (r, _), x in zip(counts, scores))
    e = p * sum(n * x for (_, n), x in zip(counts, scores))
    var = p * (1 - p) * (sum(n * x * x for (_, n), x in zip(counts, scores))
                         - (sum(n * x for (_, n), x in zip(counts, scores)) ** 2) / big_n)
    if var <= 0:
        return 0.0, 1.0
    z = (t - e) / math.sqrt(var)
    return round(z, 3), round(2 * _norm_sf(abs(z)), 4)


def tracking_permutation_p(rows: List[Dict], n_perm: int = N_PERMUTATIONS,
                           seed: int = PERM_SEED) -> Tuple[Optional[float], int, int]:
    """P-H2 content-tracking null: among A-hi-N rows whose parsed ELAPSED sits
    on the exhaust side of T, does own-scenario V_x matching (+/-0.5h) beat a
    seeded shuffle of V_x across those rows? A scenario-independent prior
    ('sessions run long') fails this; reading the exhaust content passes.
    Returns (p, observed_matches, n_exhaust_side)."""
    side = [r for r in rows
            if r.get('elapsed_value_h') is not None
            and r['elapsed_value_h'] > r['T']]
    if not side:
        return None, 0, 0
    got = [r['elapsed_value_h'] for r in side]
    vxs = [r['v_x'] for r in side]
    observed = sum(1 for g, v in zip(got, vxs) if abs(g - v) <= TRACK_TOL_H)
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        perm = vxs[:]
        rng.shuffle(perm)
        count = sum(1 for g, v in zip(got, perm) if abs(g - v) <= TRACK_TOL_H)
        if count >= observed:
            ge += 1
    p = (1 + ge) / (1 + n_perm)
    return round(p, 4), observed, len(side)


# ── summarize / verdicts ─────────────────────────────────────────────────────

DECIDE_BUCKETS = ('corrected_decide', 'stale_decide', 'unknown_decide',
                  'unparseable', 'call_failed')
ELAPSED_BUCKETS = ('correct', 'exhaust_verbatim', 'unknown', 'other_wrong',
                   'unparseable', 'call_failed')


def _cell_summary(rows: List[Dict]) -> Dict:
    out = {'n': len(rows)}
    out['decide'] = {b: _rate(rows, lambda r, b=b: r.get('decide') == b)
                     for b in DECIDE_BUCKETS}
    out['M_stale_decide'] = out['decide']['stale_decide']
    out['not_governed'] = round(out['decide']['stale_decide']
                                + out['decide']['unknown_decide'], 1)
    out['elapsed'] = {b: _rate(rows, lambda r, b=b: r.get('elapsed') == b)
                      for b in ELAPSED_BUCKETS}
    out['night_pull'] = _rate([r for r in rows if r.get('daynight')],
                              lambda r: r['daynight'] == 'night')
    out['decoupling_rate'] = _rate(rows, lambda r: r.get('decoupled'))
    out['parse_fail_pct'] = round(
        out['decide']['unparseable'] + out['decide']['call_failed'], 1)
    return out


def summarize(rows: List[Dict], n: int) -> Dict:
    mdd = mdd_pp(n)
    by_cell = {c: [r for r in rows if r.get('cell') == c] for c in CELLS}
    out: Dict = {'n_per_cell': n, 'mdd_pp': mdd,
                 'call_failures': sum(1 for r in rows
                                      if r.get('decide') == 'call_failed')}
    void = []
    for c in CELLS:
        out[c] = _cell_summary(by_cell[c])
        if out[c]['parse_fail_pct'] > PARSE_FAIL_VOID_PCT:
            void.append(f"{c} parse_fail {out[c]['parse_fail_pct']}%")
    out['void_cells'] = void   # per-CELL void (registered): rerun voided cells
                               # fresh from the 450-call reserve

    m = {c: out[c]['M_stale_decide'] for c in CELLS}
    track_p, track_obs, track_n = tracking_permutation_p(by_cell['A-hi-N'])
    out['tracking'] = {'perm_p': track_p, 'own_match': track_obs,
                       'exhaust_side_n': track_n}
    tz, tp = trend_test([
        (sum(1 for r in by_cell[c] if r.get('decide') == 'stale_decide'),
         len(by_cell[c])) for c in ('Z0', 'A-lo', 'A-hi')])
    out['trend_supporting'] = {'z': tz, 'p': tp}
    out['verdicts'] = _verdicts(m, mdd, n, track_p, tz, tp)
    return out


def _not_testable(n: int) -> str:
    return f'NOT TESTABLE at N={n} given observed base rate'


def _verdicts(m: Dict[str, float], mdd: float, n: int,
              track_p: Optional[float], trend_z: float, trend_p: float) -> Dict:
    rp = f'(MDD {mdd}pp @ N={n})'
    nt = _not_testable(n)
    v: Dict[str, str] = {}

    # preconditions
    ph1 = m['Z0'] <= 100 - mdd
    adoption_ok = m['A-hi-N'] >= mdd
    tracking_ok = track_p is not None and track_p < 0.05
    ph2 = adoption_ok and tracking_ok
    pr = max(m['A-hi'], m['X-hi'], m['M-hi']) >= mdd
    pe4 = m['A-hi'] >= mdd
    pm1 = m['M-hi'] >= mdd
    pm2 = m['M-hi-B'] >= mdd

    v['P-H1'] = (f"M(Z0)={m['Z0']}% — floor {'OK' if ph1 else 'FAIL'} "
                 f'(needs <= {round(100 - mdd, 1)}%)')
    v['P-H2'] = (f"exhaust_adoption(A-hi-N)={m['A-hi-N']}% "
                 f"({'OK' if adoption_ok else 'FAIL'}, needs >= {mdd}%); "
                 f"content-tracking permutation p={track_p} "
                 f"({'OK' if tracking_ok else 'FAIL'}, needs < .05) — "
                 f"potency {'OK' if ph2 else 'FAIL'}")
    v['P-R'] = f"max role-cell M={max(m['A-hi'], m['X-hi'], m['M-hi'])}% — {'OK' if pr else 'FAIL'}"
    v['P-E4'] = f"M(A-hi)={m['A-hi']}% — {'OK' if pe4 else 'FAIL'}"
    v['P-M1'] = f"M(M-hi)={m['M-hi']}% — {'OK' if pm1 else 'FAIL'}"
    v['P-M2'] = f"M(M-hi-B)={m['M-hi-B']}% — {'OK' if pm2 else 'FAIL'}"

    if not ph1:
        for key in ('V1', 'V2a', 'V2b', 'V3', 'V4a', 'V4b'):
            v[key] = nt + ' (P-H1 floor failed — all contrasts) ' + rp
        v['kill_row'] = ('NOT TESTABLE — subject fails the task at ceiling '
                         'with zero exhaust; no kill verdict either way ' + rp)
        return v

    d1 = round(m['A-hi'] - m['Z0'], 1)
    d2a = round(m['A-hi'] - m['X-hi'], 1)
    d2b = round(m['A-hi'] - m['M-hi'], 1)
    d_xm = round(m['X-hi'] - m['M-hi'], 1)
    d3 = round(m['A-hi'] - m['A-hi-E'], 1)
    d4a = round(m['M-hi'] - m['M-hi-B'], 1)
    d4b = round(m['M-hi-B'] - m['M-hi-C'], 1)

    # V1 — dose (registered wording: the exhaust BUNDLE, tokens+restatements
    # confounded by design; no token-denominated C4 numerator from Stage 1)
    if not ph2:
        v['V1'] = ('NOT TESTABLE — Stage-1 replay does not induce exhaust '
                   'binding at this dose on this subject (P-H2); method limit, '
                   'NOT a G1 kill; Stage 2 mandatory before any C4 claim ' + rp)
    elif d1 >= mdd:
        v['V1'] = (f'EXHAUST BUNDLE DEFEATS SINGLE CORRECTION: '
                   f'M(A-hi)-M(Z0)={d1}pp >= {mdd}pp — F4 reproduced under '
                   f'byte control; bundle = tokens+restatements, confounded '
                   f'by design (lock L4b): supports the G1 mechanism, does '
                   f'NOT license a token-denominated C4 numerator {rp}')
    else:
        v['V1'] = (f'dose effect not resolvable: {d1}pp < {mdd}pp — feeds the '
                   f'C4 kill row {rp}')
    v['V1b'] = (f"monotonicity (descriptive): M Z0={m['Z0']}% "
                f"A-lo={m['A-lo']}% A-hi={m['A-hi']}%; Cochran-Armitage "
                f'z={trend_z} p={trend_p} (supporting only, never a substitute)')

    # V2 — role (bundle wording per lock L4c: role+presentation)
    if not pr:
        v['V2a'] = nt + ' (P-R) ' + rp
        v['V2b'] = nt + ' (P-R) ' + rp
    else:
        v['V2a'] = ((f'ROLE+PRESENTATION BUNDLE EFFECT (assistant prose vs '
                     f'labeled block): |A-hi - X-hi|={abs(d2a)}pp >= {mdd}pp '
                     f'(direction: {"assistant higher" if d2a > 0 else "external higher"}) {rp}')
                    if abs(d2a) >= mdd else
                    f'no role+presentation effect resolvable vs external: '
                    f'{abs(d2a)}pp < {mdd}pp {rp}')
        if abs(d2b) >= mdd:
            v['V2b'] = (f'MEMORY-ROLE CARRIAGE BINDS DIFFERENTLY: '
                        f'|A-hi - M-hi|={abs(d2b)}pp >= {mdd}pp {rp}')
        else:
            tost = (tost_equivalent(m['A-hi'], m['X-hi'], n, mdd)
                    and tost_equivalent(m['A-hi'], m['M-hi'], n, mdd))
            if abs(d2a) < mdd and tost:
                v['V2b'] = (f'ROLE-FLAT BY TOST (margin +/-{mdd}pp, both '
                            f'pairwise): dilution-not-privilege — provisional '
                            f'per lock L1a (person-neutral phrasing; Stage 2 '
                            f'required before P1d unpin is final) {rp}')
            else:
                v['V2b'] = (f'no role effect resolvable at {mdd}pp and TOST '
                            f'equivalence NOT established — transfer assumption '
                            f'unfalsified, not affirmed {rp}')
    v['V2x_descriptive'] = (f'X-hi vs M-hi (pure-label contrast, descriptive): '
                            f'{d_xm}pp')

    # V3 — E4 repetition
    if not pe4:
        v['V3'] = nt + ' (P-E4) ' + rp
    elif d3 >= mdd:
        v['V3'] = (f'E4 PER-TURN RE-ANCHORING RESCUES: '
                   f'M(A-hi)-M(A-hi-E)={d3}pp >= {mdd}pp {rp}')
    else:
        v['V3'] = (f'repetition does not rescue at this dose: {d3}pp < {mdd}pp '
                   f'— emit-side has no volume answer; check-side (C4 alarm) '
                   f'is the only lever {rp}')

    # V4 — memory rendering facet (P1d)
    if not pm1:
        v['V4a'] = nt + ' (P-M1) ' + rp
    elif d4a >= mdd:
        v['V4a'] = (f'DEPLOYED B-PREVIEW RENDERING BUNDLE REDUCES MEMORY-'
                    f'CARRIED EXHAUST (format+truncation bundle, lock L6c): '
                    f'{d4a}pp >= {mdd}pp {rp}')
    else:
        v['V4a'] = f'B-preview effect not resolvable: {d4a}pp < {mdd}pp {rp}'
    if not pm2:
        v['V4b'] = (nt + ' (P-M2) ' + rp
                    + f" — descriptive annotation (not a verdict): M(M-hi-B)="
                      f"{m['M-hi-B']}% below {mdd}% — B-level rendering at "
                      f'floor; arm-C wiring urgency downgraded')
    elif d4b >= mdd:
        v['V4b'] = (f'COMPILATION CLOSES A RESOLVABLE RESIDUAL ON THE MEMORY '
                    f'SURFACE (Enforcement per lock L7): {d4b}pp >= {mdd}pp {rp}')
    else:
        v['V4b'] = f'compilation effect not resolvable: {d4b}pp < {mdd}pp {rp}'

    # V5 — descriptive
    v['V5'] = (f"multi-turn F1 replication (descriptive): "
               f"exhaust_adoption(A-hi-N)={m['A-hi-N']}%")

    # C4 kill-row linkage (registered; trend is NOT in the conjunction)
    if not ph2:
        v['kill_row'] = ('KILL NOT TESTABLE — authored exhaust never bound '
                         '(P-H2); Stage 1 cannot reach the mechanism; Stage 2 '
                         'mandatory before any C4 threshold ships ' + rp)
    elif d1 >= mdd:
        v['kill_row'] = ('kill does not fire — dose-response present; '
                         'Z0/A-lo/A-hi curve is C4 calibration DATA for the '
                         'bundle only; no production threshold and no '
                         'token-denominated numerator from Stage 1 ' + rp)
    elif pr and d2a >= mdd:
        v['kill_row'] = ('KILL RELOCATES — volume effect absent but assistant-'
                         'role excess present: C4 ratio form voided, monitor '
                         'rewritten with role-weighted numerator; §2 G1 '
                         'amended, not deleted ' + rp)
    else:
        v['kill_row'] = ('KILL FIRES (Stage-1 form) — exhaust volume does not '
                         'move correction-defeat at Stage-1 resolution: C4-as-'
                         'token-ratio-threshold unsupported on this surface; '
                         '§2 G1 rewritten as "unsupported under controlled '
                         'replay"; Stage 2 is the mandatory decider ' + rp)
    return v


def render_summary(s: Dict) -> str:
    lines = [f"n/cell={s['n_per_cell']}  MDD={s['mdd_pp']}pp  "
             f"call_failures={s['call_failures']}"]
    if s['void_cells']:
        lines.append(f"*** VOID CELLS (parse-fail > {PARSE_FAIL_VOID_PCT}%, "
                     f"rerun fresh from reserve): {'; '.join(s['void_cells'])} ***")
    lines.append('')
    lines.append(f"{'cell':10s}{'M=stale%':>9s}{'corr%':>8s}{'unk%':>7s}"
                 f"{'E-corr%':>9s}{'E-verb%':>9s}{'night%':>8s}{'decoup%':>9s}")
    for c in CELLS:
        q = s[c]
        lines.append(f"{c:10s}{q['decide']['stale_decide']:>8.1f} "
                     f"{q['decide']['corrected_decide']:>7.1f} "
                     f"{q['decide']['unknown_decide']:>6.1f} "
                     f"{q['elapsed']['correct']:>8.1f} "
                     f"{q['elapsed']['exhaust_verbatim']:>8.1f} "
                     f"{q['night_pull']:>7.1f} "
                     f"{q['decoupling_rate']:>8.1f}")
    tr = s['tracking']
    lines += ['', f"tracking (P-H2 co-requirement): own-V_x matches "
                  f"{tr['own_match']}/{tr['exhaust_side_n']} exhaust-side rows, "
                  f"permutation p={tr['perm_p']}", '']
    for k, verdict in s['verdicts'].items():
        lines.append(f'{k}: {verdict}')
    return '\n'.join(lines)


# ── run ──────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = 'grok-4.20-0309-non-reasoning'


def run(n: int, model: str, workers: int, out_root: Path, seed: int) -> Path:
    key = load_api_key(model)
    scenarios = gen_scenarios(n, seed)
    built_all = check_all(scenarios)   # every invariant, before the first call

    run_id = f"{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True)
    parity = max(
        (max(_total_tokens(b['A-hi'].messages), _total_tokens(b['X-hi'].messages),
             _total_tokens(b['M-hi'].messages))
         - min(_total_tokens(b['A-hi'].messages), _total_tokens(b['X-hi'].messages),
               _total_tokens(b['M-hi'].messages)))
        / _total_tokens(b['A-hi'].messages) * 100
        for b in built_all.values())
    (out_dir / 'config.json').write_text(json.dumps({
        'n_per_cell': n, 'model': model, 'seed': seed,
        'spec': 'EXHAUST_PROBE_SPEC.md (arm 3, G1 Stage 1)',
        'registry_hash': registry_hash(),
        'cells': list(CELLS),
        'max_cross_role_token_spread_pct': round(parity, 4),
        'invariants_checked': True,
        'started': datetime.now(TZ).isoformat()}, indent=2))

    jobs = [(s, c) for s in scenarios for c in CELLS]
    results = []
    smoke = n <= 4   # smoke runs persist the full request messages array
                     # (payload-shape build gate; excluded from analysis)
    import httpx
    with httpx.Client() as client, ThreadPoolExecutor(max_workers=workers) as pool, \
         open(out_dir / 'calls.jsonl', 'w') as fh:
        futs = {pool.submit(call_model, client, key, model, None,
                            SYSTEM_PROMPT, built_all[s.sid][c].messages): (s, c)
                for s, c in jobs}
        done = 0
        for fut in as_completed(futs):
            s, c = futs[fut]
            cov = covariates(s, c, built_all[s.sid][c])
            try:
                text = fut.result()
                row = score_response(s, c, text)
                row['raw'] = text
            except Exception as e:
                row = {'sid': s.sid, 'cell': c, 'decide': 'call_failed',
                       'elapsed': 'call_failed', 'error': str(e)}
            if smoke:
                row['request_messages'] = built_all[s.sid][c].messages
            fh.write(json.dumps({**row, **cov}) + '\n')
            fh.flush()
            row.update({'T': cov['T'], 'v_x': cov['v_x']})
            results.append(row)
            done += 1
            if done % 25 == 0:
                print(f'  {done}/{len(jobs)} calls', flush=True)

    summary = summarize(results, n)
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(render_summary(summary))
    print(f'\nrun dir: {out_dir}')
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description='Exhaust probe (arm 3, G1 Stage 1)')
    ap.add_argument('--check', action='store_true',
                    help='generation invariants only — no API calls')
    ap.add_argument('--render', nargs=2, metavar=('SID', 'CELL'),
                    help='offline transcript dump for one scenario x cell')
    ap.add_argument('--smoke', action='store_true',
                    help='4 scenarios x 9 cells = 36 calls, mechanics only')
    ap.add_argument('--run', action='store_true', help='registered run')
    ap.add_argument('--summarize', metavar='RUN_DIR', help='re-score an existing run')
    ap.add_argument('--n', type=int, default=150)
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--out', default='.hologram/eval/exhaust_probe_runs')
    args = ap.parse_args()

    if args.summarize:
        rows = [json.loads(l) for l in open(Path(args.summarize) / 'calls.jsonl')]
        n = json.loads((Path(args.summarize) / 'config.json').read_text())['n_per_cell']
        print(render_summary(summarize(rows, n)))
    elif args.check:
        scenarios = gen_scenarios(args.n, args.seed)
        check_all(scenarios)
        print(f'OK: {len(scenarios)} scenarios x {len(CELLS)} cells — all '
              f'generation invariants hold (registry {registry_hash()[:12]})')
    elif args.render:
        sid, cell = int(args.render[0]), args.render[1]
        if cell not in CELLS:
            raise SystemExit(f'unknown cell {cell!r}; one of {CELLS}')
        scenarios = gen_scenarios(args.n, args.seed)
        s = next(x for x in scenarios if x.sid == sid)
        bc = build_cell(s, cell)
        print(f'=== sid {sid}  cell {cell}  (T={s.threshold_h}h  '
              f'V_c={s.v_c}h  V_x={s.v_x}h  polarity={s.rule_polarity}) ===')
        print(f'[system]\n{SYSTEM_PROMPT}\n')
        for j, m in enumerate(bc.messages, 1):
            print(f"[{m['role']} — m{j}]\n{m['content']}\n")
    elif args.smoke:
        run(4, args.model, args.workers, Path(args.out), args.seed)
    elif args.run:
        run(args.n, args.model, args.workers, Path(args.out), args.seed)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
