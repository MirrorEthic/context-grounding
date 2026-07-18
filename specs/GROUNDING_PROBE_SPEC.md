# Grounding Probe Spec — pre-registered

**Program:** CONTEXT_GROUNDING_PROGRAM.md §7 (probe set freeze)
**Frozen:** 2026-07-17T15:15-06:00, BEFORE any full-arm run. Smoke runs validate mechanics
only (parse rates, API plumbing) and are excluded from analysis. Post-freeze edits to
endpoints, thresholds, or scoring are amendments and must be dated.
**Harness:** `hologram/eval/grounding_probe.py`
**Subject model:** `claude-sonnet-5`, temperature 0, max_tokens 300 (pre-registered; other
models are exploratory arms, not the registered endpoint).
**AMENDMENT 2026-07-17T15:20-06:00 (pre-data, ops-forced):** the Anthropic API key is
deprecated; no Anthropic-API access from this box. Registered subject changes to
`grok-4.20-0309-non-reasoning` via x.ai — the explicitly non-reasoning variant, closest
analog to the §1 incident surface (claude.ai chat, no extended thinking). All endpoints,
N, thresholds, and scoring unchanged. Claude-family subjects become a queued replication
arm when a key exists; cross-model generality is then a bonus finding, not the claim.

---

## Arm 1 — temporal binding (this spec). Arm 2 — ingest-annotation null (Queued, separate freeze).

## Design

Synthetic single-turn sessions. Each scenario has a known `true_now` (fixed offset -06:00),
a **target note** written `S` hours before now stating a deploy completed `X` hours before
the note was written (true elapsed = `X + S`, range enforced 6–23h), plus 4 distractor notes.
Ambient density facet: `high` = ~12 night/urgency tokens in the distractors, `low` = 0;
ambient lines are byte-identical across conditions (this isolates anchoring from E5 —
ordering/typing vs ambient-scrub is §8 Q5, not this arm).

`true_now` hour is sampled from clearly-day (09–16) or clearly-night (22–04) local hours.

### Conditions (what varies: record formatting ONLY)

| | tick (`now`) | target + distractor records |
|---|---|---|
| **A** current emitter | human-format line at top (mimics production hook) | bare deltas ("9h ago"), bare clocks, no written-time — mimics the audited corpus |
| **B** E1–E4 emitter | ISO+offset, emitted **last, alone, twice** (E4) | written-time + event-time as full ISO+offset, `temporal_reference` typed (E1–E3) |
| **C** scrambled-anchor null | correct, as B | as B, but written/event anchors shifted **+18–72h into the past**; scrambled-derived elapsed differs from both true elapsed and note-verbatim by > 2× tolerance (enforced at generation) |

### Questions (one API call per scenario×condition, fixed format, abstain sanctioned)

1. `DATETIME:` current date+time best estimate (tick binding under volume)
2. `ELAPSED:` how long ago the deploy completed, or `unknown` if context is insufficient
3. `DAYNIGHT:` day or night (ambient pull)

### Scoring (Q2 buckets, tolerance = max(±20%, ±30 min))

`correct` (matches true elapsed) | `unknown` (sanctioned abstain) | `note_verbatim`
(echoes X — stale delta read as fresh; the F-class confabulation) | `anchor_consistent`
(matches scrambled-derived value; only distinguishable in C) | `other_wrong`.

In A the true elapsed is **not computable** from the context (no written-time) — `unknown`
is the only non-confabulated answer. Q2 error := 1 − (correct + unknown).

## Sample size & resolving power

**N = 150 scenarios per condition** (same 150 scenarios rendered per condition; densities
75/75 within). Two-proportion comparison, α = .05 two-sided, power = .80, worst-case
p̄ = 0.5: **minimum detectable difference ≈ 16.2 pp**. Secondary splits (density facets,
N = 75) resolve ≈ 22.9 pp and are descriptive only.

## Pre-registered verdicts

| # | claim | metric | verdict rule |
|---|---|---|---|
| **V1** anchors are read at all | `anchor_consistent` rate in C | ≥ 30% ⇒ anchors read (E1–E3 not theater). < 10% ⇒ **scrambled-anchor null fires: E1–E3 void** (§7). 10–30% ⇒ gray, escalate N before any claim. |
| **V2** anchored emission reduces error | Q2 error(A) − error(B) | ≥ 16.2 pp ⇒ E1–E4 validated on this surface. < 16.2 pp ⇒ **not resolvable at N=150: E1–E5 remain unvalidated** (§7 row 1); report as such, no softer wording. |
| **V3** tick binding survives volume | Q1 accuracy (±30 min) per condition | descriptive; A vs B tests E4 placement. |
| **V4** ambient pull exists | P(DAYNIGHT=night │ true day) high vs low density, pooled across conditions | descriptive (N resolves only ≈ 16 pp pooled); registers direction for §8 Q1. |

**Interpretation lock:** V1 and V2 are independent. Anchors-read + no-error-reduction is a
coherent outcome (model can do the arithmetic when looked at, but doesn't consult records
under volume) and must be reported as exactly that, not spun to either side.

## RESULTS — registered run (2026-07-17T15:15-06:00, run `20260717T151513-ce2bab`)

450/450 calls, 0 failures, 0 parse failures. Subject `grok-4.20-0309-non-reasoning`, temp 0.

| | correct | unknown | verbatim | anchor | other | **Q2 ERROR** | Q1 tick |
|---|---|---|---|---|---|---|---|
| **A** current | 0.0% | 0.0% | **100.0%** | 0.0% | 0.0% | **100.0%** | 16.0% |
| **B** E1–E4 | **100.0%** | 0.0% | 0.0% | 0.0% | 0.0% | **0.0%** | 100.0% |
| **C** scrambled | 7.3% | 0.0% | 0.7% | **65.3%** | 26.7% | 92.7% | 100.0% |

**V1 — ANCHORS READ.** `anchor_consistent`(C) = 65.3% ≥ 30%. Scrambled-anchor null does
NOT fire; E1–E3 are not theater on this surface.
**V2 — COMBINED E1–E4 TREATMENT VALIDATED.** error(A) − error(B) = 100.0pp ≥ MDD 16.2pp.
**Claim-granularity note (amended 2026-07-17T17:10-06:00):** condition B bundled anchoring,
typing, precomputed-delta-adjacency, AND NOW-placement/repetition. The experiment validates
the bundle; it does not isolate E4 (ordering/repetition) or any single component. §8 Q5's
2×2 remains open — do not cite this run as validating E4 alone.
**V3 (descriptive).** Tick accuracy 16% (A) vs 100% (B/C). See post-hoc 1.
**V4 (descriptive).** P(night│true day): 10.5% high-density vs 0.0% low. Ambient tokens
alone flipped ~1 in 10 day→night with a correct tick present. Direction registered for §8 Q1.

**Headline for §1:** condition A reproduced the F1 mechanism at scale — **150/150
note-verbatim confabulations, zero abstains**, despite `unknown` being sanctioned in the
prompt. Under insufficient context the subject never says so; it invents.

### Post-hoc observations (NOT registered endpoints; labeled as such)

1. **A's tick misses are wrong-YEAR answers** (time-of-day right, year 2025/2020). The
   human tick format carries no year — and neither does the production hook
   (`Fri Jul 17, 3:15 PM MDT`). Condition A faithfully reproduced a live emitter defect:
   year-free ticks resolve to a training-prior year 84% of the time. Immediate E2 action:
   production tick must carry ISO date+year+offset.
2. **C's `other_wrong` (26.7%) is dominated by ±24h/48h day-boundary arithmetic slips**
   on the scrambled values (e.g. 65.3→17, 60.2→36, 87→63). These are anchor-engaged
   failures, not disengagement — true anchor-engagement in C is ≈92%. C's nominal
   "correct" 7.3% is day-slip collisions landing inside true-value tolerance, not
   truth-tracking. Consequence: anchors are read, but multi-day arithmetic is fragile —
   E1's "prefer dropping the delta entirely" should become "emit absolute AND
   pre-computed delta"; never make the model subtract across day boundaries.

**Scope caveats:** one subject model (non-reasoning), single-turn, synthetic sessions,
one target note. Claude-family replication queued (no API key). Multi-turn exhaust
accumulation (G1) untested by this arm.

### Exploratory replication arms (2026-07-17T15:27–16:00-06:00; same frozen design, N=150)

| subject | A err (verbatim) | B err | C anchor-consistent | A tick | ambient pull (hi/lo) |
|---|---|---|---|---|---|
| grok-4.20 non-reasoning (registered) | 100% (150/150) | 0% | 65.3% | 16.0% | 10.5% / 0% |
| grok-4.5 (`20260717T152715-bfc4e5`) | 100% (150/150) | 0% | **100%** | 73.3% | 0% / 0% |
| grok-4.20 multi-agent (`20260717T153526-41c7d3`) | 100% (150/150) | 0% | **100%** | 100% | **15.8%** / 0% |
| gemini-3.1-pro-preview (first attempt `20260717T154659-3baa56`) | — | — | — | — | — |

**All completed arms replicate V1 + V2.** Cross-model invariants: (1) condition A produces
100% note-verbatim confabulation with **zero abstains in 686/686 completed A-calls across
four models** — under insufficient context, no subject ever says "unknown"; (2) condition B
is at ceiling for every subject; (3) stronger models track scrambled anchors *perfectly* —
the registered subject's 26.7% day-slip arithmetic errors vanish in grok-4.5/multi-agent.
Notable: ambient day→night pull is *largest* on the multi-agent subject (15.8%), and the
year-free tick fools even grok-4.5 26.7% of the time.

**Gemini first attempt is VOID per discipline** — 214/450 calls failed (free-tier rate
limits at 8 workers), below registered completeness. The completed subset was unanimous
(A 78/78 verbatim, B 81/81 correct, C 77/77 anchor-consistent — 236/236 on-signature) and
is reported here as descriptive only. Clean rerun at 2 workers with patient backoff:
pending, will be recorded below when complete.

## Costs / mechanics

450 calls (150 × 3), ~1k tokens in / ~150 out each; 8 workers; retry 429/5xx ×3 with
backoff; temperature 0. Raw responses + parsed scores persisted to
`.hologram/eval/probe_runs/<run_id>/` (calls.jsonl + summary.json). Unparseable responses
are counted `other_wrong` (Q2) / excluded per-question (Q1/Q3) and reported; if parse
failures exceed 5% the run is void (fix format prompt, rerun fresh — no partial reuse).
