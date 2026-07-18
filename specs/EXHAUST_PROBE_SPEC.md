# Exhaust Probe Spec (Arm 3 — G1 Stage 1: controlled transcript replay) — FREEZE CANDIDATE

**Program:** CONTEXT_GROUNDING_PROGRAM.md §1 (F1–F6 — this arm reproduces and dose-titrates the F4 mechanism), §2 (G1 self-generated exhaust), §5 (C4 exhaust-ratio monitor — this arm is the source of its threshold), §7 kill row 3 ("C4 exhaust ratio shows no correlation with degradation onset ⇒ G1 mechanism unsupported; rewrite §2"). RESEARCH_WORKLOG.md P3 (G1 two-stage design), P1d (memory-preview facet rides along; arm-C wiring pinned on this arm's results).
**Status:** **FROZEN 2026-07-17T18:34-06:00** (v1.0; live smoke 36/36 clean, excluded from analysis). Draft v0.1 passed the arm-2-workflow adversarial pre-registration review (3 lenses; 3 blockers + 6 majors + 5 minors — all resolved, see §Review resolutions); harness built and offline-verified (invariants `--check` green at N=150; 53 harness tests; full suite 206 green). Remaining before freeze: live smoke (36 calls, mechanics only, excluded from analysis) → human freeze, dated. Post-freeze edits to endpoints, thresholds, scoring, the template registry, or the generation seed are amendments and must be dated.
**Harness:** `hologram/eval/exhaust_probe.py` (implemented). Reuses arm-1 provider plumbing by import (`call_model`, `load_api_key`, `mdd_pp`, `_rate`, `TZ`, `ELAPSED_RE`, `UNKNOWN_RE`, `DAYNIGHT_RE`, `_parse_elapsed_h`, `_tol_h` from `hologram/eval/grounding_probe.py`) and arm-2 reversible-edit machinery by import (`apply_edits`, `revert_edits`, `DEONTIC_RE` from `hologram/eval/ingest_probe.py`) — no copied API code. **One pre-registered mechanical refactor to the arm-1 file (implemented):** `call_model` gains an optional `messages: Optional[List[dict]] = None` keyword (and `prompt` becomes `Optional[str]`). At the default (`None`) the payload is constructed from `prompt` **byte-identically** for arms 1–2 — guarded by frozen-payload equality regression tests per provider branch (x.ai chat, x.ai responses, Anthropic, Google) in `tests/test_exhaust_probe.py`, plus the pre-existing suite staying green. When `messages` is provided, `prompt` must be `None` (ValueError otherwise) and the per-provider payload preserves roles: x.ai chat → `[{role: system}, *messages]`; Anthropic → `system` param + messages verbatim; Google → `contents` with `user`/`model` role mapping; x.ai responses → `instructions` + `input` with roles. Assistant-role exhaust turns are **REAL assistant messages in the API payload** — that IS the role manipulation. No other arm-1 code changes.
**Subject model:** `grok-4.20-0309-non-reasoning` via x.ai, temperature 0, max_tokens 300 — same registered subject as arms 1–2 (arm-1 amendment 2026-07-17T15:20-06:00; Anthropic key deprecated). Other models are exploratory replication arms, not the registered endpoint. (Open Q11 resolved: this arm's system prompt is its own registered bytes; cross-arm system-prompt comparability is not claimed.)
**System prompt (frozen bytes in harness):** "You are an assistant working through an ongoing engineering session with a user. Session records and ticks appear inline in the conversation."
**Determinism:** seeded generation (`gen_scenarios`, seed `20260719`), frozen in-module template registry — **registry sha256 `e0283332b494530cc9bfc449e93eac799c5ad2980c4c2491cd354db07a01d1a9`**, recorded in every run's `config.json` (covers system prompt, kickoff, both rule polarities, correction, neutral m15, all acks, padding, fences, tick format, probe question, all six exhaust units + claims, all six fillers, all six WPs, confidence-marker lexicon, preview and compile formats). All timeline values are whole minutes (production-shaped ISO stamps); no wall-clock reads during generation; all deltas precomputed against scenario-fictional time. Stage 2 (live autoregressive) is OUT of this spec — placeholder section only.

---

## Arm 3 — multi-turn exhaust (G1 Stage 1). Tests whether authored exhaust volume defeats a single corrected anchored record (F4 reproduction under byte control), whether the ROLE the wrong text appears under carries weight beyond its content (the load-bearing assumption of P1d compile-on-read), and whether the two candidate rescue levers (E4 per-turn re-anchoring; memory-surface annotation/compilation) move the failure rate.

### Why controlled replay is a valid test of "self"-evidence (registered argument)

Across turns, the **role label is the only ground-truth channel** by which a model can know a transcript span is its own prior output — each turn re-reads the full transcript; there is no hidden-state carryover between API calls. **Idiom is a probabilistic cue, not a ground-truth channel; it is tested in Stage 2** (this sentence registered per review minor: the section must be internally consistent with residual gap (a) below). Stage-1 replay with a true assistant-role manipulation therefore tests the production mechanism of cross-turn self-evidence. The residual gaps to live sessions are (a) **distributional self-match** (live exhaust is in the model's own idiom; authored exhaust is not) and (b) content coupling between exhaust and the model's live task state. Those are Stage 2's job. A Stage-1 null does not close G1 on its own — see the kill-linkage section for the exact deferral rule.

## Design

Fully synthetic, seeded, fixed multi-turn transcripts. The subject never generates the exhaust — every message in every condition is authored, so every contrast is byte-controlled. Each scenario is one fictional work session with a fixed timeline (all whole minutes, ISO −06:00):

- `ISO_corr` — time of the correction turn = **true_now**; sampled 2026-03-01..2026-07-28, **hour 09–16 local (all scenarios true-day)**.
- `drift ~ U{30..70} min` (seeded integers); `ISO_t1 = ISO_corr − drift` — time of m1.
- `initial_elapsed ~ U{45..90} min` (seeded integers); `ISO_start = ISO_t1 − initial_elapsed` — anchored session start.
- **V_c** (corrected elapsed) `= ISO_corr − ISO_start` ∈ [1.25, 2.67] h — precomputed, stated in the correction.
- **T** (rule threshold) ∈ {4, 5, 6} h (seeded).
- **V_x** (exhaust elapsed claim) — integer hours sampled from `[T+2, 13]` (seeded), rendered in words ("about nine hours"). By construction **V_c and V_x fall on opposite sides of T** with margins ≥ 1.3 h (V_c side; V_c max 2.67 ≤ T−1.33) and ≥ 2 h (V_x side) — enforced at generation; violation voids the run. The arm-1 elapsed tolerance windows of V_c and V_x never overlap (min gap ≥ 3.3 h > tol(V_c)+tol(V_x)).
- Rule polarity: deterministic alternation `i % 2` ⇒ exact 75/75 split at N=150 (checked).

### Transcript skeleton (17 messages; fixed across all cells; strict user/assistant alternation, user first and last — valid payload shape for all four provider mappings, checked by test)

| msg | role | content |
|---|---|---|
| m1 | user | Kickoff (frozen bytes) + `[SESSION RECORD]`: anchored session-start line (`[written <ISO_t1>, temporal_reference: ongoing] session started <ISO_start>`), the **deploy-window rule record** (`[deploy-window rule, written <ISO_t1>, temporal_reference: current] <polarity rule>`), `NOW: <ISO_t1>` last (E1–E4 compliant). Byte-identical across cells modulo seeded values (checked). |
| m2, m4, m6, m8, m10, m12 | assistant | Slots U1–U6. Assistant-role cells: exhaust unit i if slot dosed, else **matched neutral filler Ni (EXACT ws-token match to unit i — dose cells are token-count identical)**. External/memory cells: the fixed short ack `Noted — continuing with the task.` |
| m3, m5, m7, m9, m11, m13 | user | Neutral work prompts WP1–WP6 (byte-fixed). Assistant-role cells: + the fixed inert padding line (16 ws-tokens = ack + fence surplus; zero temporal content). External/memory cells: + fenced block carrying unit i (see role table). correction_mode=every_turn additionally appends an advancing `TICK: NOW <ISO>` (6 distinct seeded whole-minute offsets in `(ISO_t1, ISO_corr)`, sorted). |
| m14 | assistant | Neutral ack A7 (`Noted. Standing by for the next item.`) — byte-fixed, zero temporal content, identical in every cell (checked). |
| m15 | user | **CORRECTION** (correction_mode ∈ {once, every_turn}): `[CORRECTED RECORD — supersedes all prior session-timing statements]` + `Session started: <ISO_start>` + `Elapsed this session: <V_c> h (precomputed)` + `NOW: <ISO_corr>` ×2, NOW last (E1–E4 + arm-1 post-hoc 2: absolute AND precomputed delta). In correction_mode=none: byte-fixed neutral work prompt. |
| m16 | assistant | Neutral ack A8 (`Recorded. Ready for the final item.`) — byte-fixed, identical in every cell (checked). |
| m17 | user | The probe question (fixed format, below). |

The correction is maximally clear by design: any residual stale behavior is unambiguously a governance failure, not a day-boundary arithmetic failure. One neutral ack (m16) separates correction from probe.

### Exhaust units (the wrong content)

Six distinct, frozen, content-hash-pinned unit templates (**52–55 ws-tokens each; measured, registered**). Each unit is otherwise-plausible work chatter carrying: **one confident anchorless-relative elapsed claim** rendering V_x in words (the frozen per-unit **claim span**, e.g. "this session has been running about {vx} hours now" — T2 class, the incident's `9h ago` shape) and **night/urgency ambience** (T4 class: "overnight window", "all-nighter"). Registered unit rules, all enforced at generation (`check_templates`):

- **Person-neutral phrasing** ("this session has been running…", never "I have been…") so identical bytes are plausible under all three carriers. **See lock L1a for the registered cost of this choice.**
- **No wrong absolutes**; no digits — V_x in words only (all sampled values 6–13 are single-word numerals, so unit token counts are V_x-invariant).
- **Byte-identical across roles and correction modes** for a given scenario; across doses a fixed subset at fixed slots.
- **≥ 3 units carry an establishment/cross-reference marker** ("As established…", "as already noted") — the F2 self-referential-hardening shape, carrier-plausible phrasing, counted in `exhaust_confidence_markers` (review minor resolved).
- **Each unit carries a T1/T2-lintable span inside its first 180 chars** ("this morning", "last night", "yesterday evening", "tonight") — verified by running the actual shared lint (`hologram/okf/lint.py`) on the truncated preview bytes, so the production ⚠flag legitimately fires in the B cell (blocker-3 fix).
- Each unit's **claim span survives 180-char truncation** at the longest numeral ("thirteen") — checked.
- Fixed confidence markers per unit (frozen lexicon: clearly / frankly / honestly / obviously / as established / as already noted / no question); count logged as covariate.

**Neutral fillers** N1–N6, acks, WPs, padding: frozen templates; fillers **exactly** ws-token-matched to their unit (stronger than the drafted ±10%); all pass the shared temporal-hygiene lint (zero T1/T2/T4 findings) plus a digit and time-word regex guard; violation voids at generation.

### Role manipulation (what varies: the CARRIER of the byte-identical exhaust unit)

| role | carriage of unit i | assistant slots |
|---|---|---|
| **assistant** | Unit i is the body of assistant message m(2i) — a true `role: assistant` API message. User turns carry WP + the 16-token inert padding line. | units/fillers |
| **external_context** | Unit i inside `[EXTERNAL CONTEXT — pasted from the ops channel] … [/EXTERNAL CONTEXT]` appended to user message m(2i+1) after WPi. | fixed ack |
| **memory (minimal)** | As external_context but fenced `[MEMORY NOTES — surfaced by the memory system] … [/MEMORY NOTES]` (fence labels ws-token-matched to the external fences). | fixed ack |

**Cross-role parity (registered invariant, replaces draft invariant 3 — the review's blocker-class confound fix):** X-hi/M-hi are derived from A-hi by the recorded transformation *unit relocation (assistant slot → fenced user block, +1 message positional offset) + ack substitution in assistant slots + padding removal in user slots*; the padding line is sized so per-scenario cross-role total ws-token difference is **< 1% (measured: 0.0% — exact)**, checked in `--check` before any API call and recorded in `config.json`. The +1-message positional offset is identical for both non-assistant roles (symmetric across the R pairwise contrasts) and is logged via `exhaust_token_positions`. **Assistant carriage is unfenced prose while external/memory are labeled blocks — the presentation difference is part of the manipulation; see lock L4c: only X-hi vs M-hi is a pure-label contrast.**

### Dose (what varies: number of exhaust units; slots fixed; length constant)

| dose | units carried | exhaust ws-tokens (measured) |
|---|---|---|
| **0** | none — all six slots carry exact-matched fillers | 0 |
| **low** | slots **{2, 6}** | ≈ 107 |
| **high** | all six slots | ≈ 318 |

**A-lo slots are {2, 6}** (amended from the draft's {2, 5}): the last exhaust unit occupies slot 6 (m12) in BOTH dosed cells, so last-contradiction-to-correction distance is matched — recency no longer co-varies with dose (review major resolved). Z0/A-lo/A-hi transcripts are **token-count identical** (exact filler matching) — the dose contrast is dilution-controlled by construction; M(A-hi)−M(Z0) measures exhaust content at fixed context length and turn count (blocker-1 fix).

Registered plainly: dose scales exhaust-flavored tokens AND explicit-contradiction count AND confidence-marker count together — **confounded at Stage 1 by design** (lock L4b governs what V1 may claim). Zero-dose is rendered in the assistant-cell layout; a role-rendered zero dose is unnecessary because role contrasts compare at high dose only.

### Correction mode

- **once** — F4 reproduction: anchor at m1, ONE corrected record at m15.
- **every_turn** — E4-repetition facet: every user turn m3–m13 appends an advancing `TICK: NOW <ISO>`; m15 correction unchanged. The tick token surplus is NOT padded away — repetition of record tokens IS the treatment (`injected_record_tokens` moves ≈56→≈74; logged, stated plainly).
- **none** — m15 is the byte-fixed neutral prompt. Measures raw exhaust adoption against the m1 anchor (multi-turn F1 replication + potency precondition P-H2). In this cell the only derivable current elapsed is `initial_elapsed` (from the m1 anchor); ELAPSED `correct` scores against it.

### Memory-preview facet (P1d data) — production-faithful B (blocker-3 resolution)

Two additional memory-role cells re-render the SAME exhaust units (same facts, same slots), each derived from M-hi by recorded reversible per-slot edits (arm-2 machinery):

- **B-level (deployed production rendering, byte-faithful):** block content becomes `MEMORIES (1 project-scoped, by relevance):` + one line in the **production format string copied verbatim** from `~/.claude/hooks/hologram-typed-injector.py` (`  - [{cat}] {topic} ({proj}, {as_of} ({age}d ago){tref}{refs}){flag}: {content}`; format sha256 prefix `e51103ed56643676`, MEMORY_PREVIEW_CHARS=180): (1) **age in INTEGER DAYS** — same-fictional-day writes render `(0d ago)` (near-zero staleness signal, exactly as production); (2) **content truncated to 180 chars, newlines flattened** — units lose their tail; (3) the `⚠unanchored-content` flag **gated on the actual shared lint** (T1/T2 on the truncated bytes) — fires for every unit by the unit-template invariant, never stamped unconditionally. `ISO_w` (authored fiction) is seeded in `[ISO_start+10 min, ISO_t1−5 min]` — written minutes after start while the claim says ~V_x hours: the audited-corpus pollution shape. **Registered rendering+dose bundle (lock L6c): truncated B carries ≈277 exhaust ws-tokens vs M-hi's ≈318 — V4a tests the deployed bundle (format + truncation), stated plainly.** Hook/harness format drift is a registered risk (lock L6b); shared-renderer extraction queued per I6 / arm-2 L7.
- **C-level (arm-C compiled):** deterministic non-model transformation of each B preview line, recorded as an exact reversible edit: (1) the claim span inside the truncated content rewritten as-of-qualified past tense ("as of <ISO_w> this note described the session as having been running about <V_x> hours"); (2) declarative non-current notice line ("[compiled] the elapsed-time claim above is an anchorless relative recorded at <ISO_w>; it is not servable as current."); (3) supersession fence keyed **by construction** to the m1 anchored record (`[SUPERSEDED by anchored session-start record <ISO_start> — retained as history]`). Fenced, never deleted; **all C-emitted text declarative** (arm-2 deontic regex guard, checked); inverse-applying the recorded edits reproduces the B bytes exactly (checked per scenario/slot). Deterministic side effect, registered: the as-of ISO anchor inserted next to a T2 span can legitimately clear the lint flag on the compiled line (anchor-proximity exemption) — production-consistent. Arm-2 locks inherit (lock L7): a C win is Enforcement of a keyed fence, not conflict detection.

### Rule record and polarity counterbalance (response-bias control)

The deploy-window rule (m1, first-party record, `temporal_reference: current`), two frozen polarity templates, deterministic 75/75:

- **P⁻ (under_permits):** "the svc-mesh deploy is permitted only while total session runtime is under <T> hours." Corrected V_c → **yes**; stale V_x → **no**.
- **P⁺ (over_permits):** "the svc-mesh deploy is permitted only after at least <T> hours of continuous session soak." Corrected V_c → **no**; stale V_x → **yes**.

Scoring maps tokens through per-scenario polarity, so `stale_decide` cannot be produced by a yes/no or conservative-refusal response bias.

## Cells (registered fractional design — NOT a full factorial)

Registered cells, **N = 150 scenarios each** (same 150 scenarios rendered per cell):

| cell | role / carrier | dose | correction | rendering | serves contrast |
|---|---|---|---|---|---|
| **Z0** | assistant layout (filler-filled) | 0 | once | — | D zero point; floor precondition P-H1 |
| **A-lo** | assistant | low {2,6} | once | — | D |
| **A-hi** | assistant | high | once | — | **D, R (shared anchor cell), E4 reference** |
| **X-hi** | external_context | high | once | minimal block | R |
| **M-hi** | memory | high | once | minimal block | R; P1d reference |
| **M-hi-B** | memory | high | once | production B preview | P1d (V4a) |
| **M-hi-C** | memory | high | once | C-level compiled | P1d (V4b) |
| **A-hi-E** | assistant | high | **every_turn** | — | E4 facet (V3) |
| **A-hi-N** | assistant | high | **none** | — | potency P-H2; F1-multi-turn descriptive (V5) |

**9 cells × 150 = 1,350 registered calls.** Anchor frequency and contradiction density do NOT get registered cells: anchor frequency is covered by the powered E4 contrast; contradiction density is dose-confounded (stated above) and **explicitly descriptive/queued** — no density claim may be made from this run. Queued unregistered facets (post-run, reserve permitting via dated amendment only): A-hi-2c (claim-count vs token-mass disambiguator), A-hi-1p (first-person units, within-assistant).

## Probe (m17 — one API call per scenario × cell; fixed format; sanctioned uncertainty)

The F4 failure was a presupposition; G3/C2 extraction is unsolved, so the probe makes the **governed value directly readable from a fixed-format token**: an act-on-the-value decision whose binary outcome deterministically reveals which elapsed value governed, because V_c and V_x straddle T by construction. No extractor needed.

```
Answer the following using only the context above. Use EXACTLY this format, one line each:
DECIDE: <yes | no — per the deploy-window rule stated at session start, is the svc-mesh deploy permitted right now? Answer 'unknown' only if the rule or the current session timing cannot be determined from the context>
ELAPSED: <how long this session has been running right now, as '<number> hours', or 'unknown' if the context is insufficient to determine it>
DAYNIGHT: <day or night, one word>
```

- **DECIDE** — the F4-class probe (primary). `unknown` sanctioned; the rule + corrected record fully determine the answer in all corrected cells.
- **ELAPSED** — assertion-layer co-measure (arm-1 continuity; also carries the P-H2 tracking statistic). `unknown` sanctioned.
- **DAYNIGHT** — night-pull against fixed day truth (descriptive; arm-1 Q3 continuity).
- **Registered ordering caveat (lock L3):** DECIDE first (decision before articulation, closest to the low-constraint failure mode); ELAPSED may be back-filled to justify DECIDE — the decoupling endpoint is descriptive for exactly this reason.

Parse (frozen in harness): `DECIDE_RE = DECIDE:\s*[*_`"']*\s*(yes|no|unknown)\b` (case-insensitive); ELAPSED and DAYNIGHT reuse arm-1 regexes by import.

## Scoring

**Denominators (pinned):** every rate is over all N in its cell (call failures and unparseable rows count in the denominator and their own bucket).

**DECIDE buckets** (token mapped through per-scenario polarity): `corrected_decide` | `stale_decide` (**the F4 failure under test**) | `unknown_decide` (sanctioned; **neutral for the primary endpoint**, registered secondary descriptive `not_governed := stale + unknown`) | `unparseable` | `call_failed`.

**Primary endpoint per cell: M := stale_decide rate.** In A-hi-N, M is named `exhaust_adoption` (identical computation, different claim).

**ELAPSED buckets** (arm-1 tolerance = max(±20%, ±30 min)): `correct` (target: V_c in corrected cells; `initial_elapsed` in A-hi-N) | `exhaust_verbatim` (V_x ± tol — the F2 echo) | `unknown` | `other_wrong` | `unparseable` | `call_failed`. Additionally per row: `vx_own_match` — parsed value within **±0.5 h of the scenario's own V_x** (windows of adjacent integer V_x never overlap; feeds the P-H2 tracking statistic).

**Registered descriptive endpoints:** `decoupling_rate` := P(ELAPSED correct ∧ DECIDE stale) — §0's core claim made measurable, descriptive-only under lock L3. `night_pull` := P(DAYNIGHT=night) (truth always day). Full ELAPSED bucket table per cell. X-hi vs M-hi delta (pure-label contrast, descriptive).

**Void rule (registered — resolves the void/reserve arithmetic):** parse failures > 5% **in a cell void that cell only**; the voided cell reruns fresh on newly seeded scenarios from the reserve. If recovery involves any change to the probe/format bytes, that is a dated amendment and all cells sharing those bytes must be assessed for rerun. Reserve accounting: **450 calls = 36 smoke + up to two per-cell reruns (≤300) + 114 contingency**; a third void exhausts the reserve and requires a dated budget amendment before rerun. 1,350 + 450 = 1,800 = the budget cap.

## Sample size & resolving power

**N = 150 per cell**, same scenarios per cell ⇒ 1,350 calls. Two-proportion comparison, α = .05 two-sided, power = .80, worst-case p̄ = 0.5: MDD = 2.802 × √(2·p(1−p)/N) ≈ **16.2 pp** per pairwise cell comparison.

**Multiplicity stance (registered):** exactly **six** primary threshold tests (V1, V2a, V2b, V3, V4a, V4b); per-comparison α = .05 retained (distinct non-pooled claims); family-wise inflation acknowledged, count fixed pre-data. McNemar on discordant pairs: registered optional sensitivity analysis, never the headline. Cochran–Armitage trend across Z0/A-lo/A-hi: **supporting only** — may strengthen V1's wording, may never substitute for it, and **is NOT part of the kill conjunction** (review minor resolved by removal; its unstated resolving power therefore gates nothing).

**Equivalence testing (registered — review major resolved):** the V2b "role-flat" claim requires a **TOST equivalence test** (two one-sided z-tests, α = .05 per side, margin ±16.2 pp) passing on BOTH pairwise role contrasts — a bare below-MDD null may NOT be read as equivalence. Power statement: at N=150, p̄=.5, the 90% CI half-width is ≈9.5 pp, so TOST at margin 16.2 pp is adequately powered when the true Δ ≈ 0.

## Base-rate / headroom preconditions (registered — a contrast with no headroom prints NOT TESTABLE, never a vacuous pass)

| # | precondition | rule | on failure |
|---|---|---|---|
| **P-H1** (floor) | M(Z0) ≤ **83.8%** | subject must not fail at ceiling with zero exhaust | ALL contrasts print **"NOT TESTABLE at N=150 given observed base rate"**; run reports descriptively only. |
| **P-H2** (potency + content-tracking, **two co-requirements** — blocker-2 fix) | (i) exhaust_adoption(A-hi-N) ≥ **16.2%** AND (ii) **content-tracking permutation null rejected**: among A-hi-N rows whose parsed ELAPSED sits on the exhaust side of T, own-scenario V_x matches (±0.5 h) must exceed a seeded shuffle of V_x across those rows (1,000 permutations, seed 20260719, p < .05) | authored exhaust must bind AND be *read* — a scenario-independent "sessions run long" prior can satisfy (i) alone (arm-1's 686/686 prior-filled confabulations are exactly this class) but cannot track per-scenario V_x | V1/V2/V3 print **"NOT TESTABLE — Stage-1 replay does not induce exhaust binding at this dose on this subject."** Method limit, NOT a G1 kill; Stage 2 mandatory before any C4 claim. |
| **P-R** (role headroom) | max(M(A-hi), M(X-hi), M(M-hi)) ≥ 16.2% | some role cell must show an effect | V2a/V2b NOT TESTABLE. |
| **P-E4** | M(A-hi) ≥ 16.2% | a failure must exist for repetition to rescue | V3 NOT TESTABLE. |
| **P-M1 / P-M2** | M(M-hi) ≥ 16.2% / M(M-hi-B) ≥ 16.2% | headroom per memory-facet leg | V4a / V4b NOT TESTABLE (see V4b's registered printing below); facet degrades to descriptive. |

## Pre-registered verdicts

Per DECISION-RULE AMENDMENT (2026-07-16): every verdict states its resolving power (MDD 16.2 pp @ N=150). Differences below MDD are "not resolvable at N=150" — no softer wording.

| # | claim | metric | verdict rule | precondition | resolving power |
|---|---|---|---|---|---|
| **V1** dose induces correction-defeat (F4 reproduced; G1 core) | M(A-hi) − M(Z0) | ≥ 16.2 pp ⇒ **the exhaust BUNDLE (tokens + restatements + markers, confounded by design — lock L4b) defeats a maximally-clear single correction under byte control**: F4 reproduced and dosed; supports the G1 mechanism; does **NOT** license a token-denominated C4 numerator (see kill linkage). < 16.2 pp ⇒ dose effect not resolvable — feeds the kill row. | P-H1 ∧ P-H2 | 16.2 pp |
| **V1b** monotonicity | M(Z0) ≤ M(A-lo) ≤ M(A-hi); CA trend | supporting/descriptive only; A-lo pairwise deltas resolve at 16.2 pp, reported, never pooled. | as V1 | 16.2 pp pairwise |
| **V2a** self-carriage vs external | M(A-hi) − M(X-hi), two-sided | \|Δ\| ≥ 16.2 pp ⇒ **the role+presentation bundle** (assistant prose vs labeled block — lock L4c) carries weight beyond byte-identical content; direction reported. Within MDD ⇒ not resolvable. | P-R | 16.2 pp |
| **V2b** self-carriage vs memory surface | M(A-hi) − M(M-hi), two-sided; TOST | \|Δ\| ≥ 16.2 pp ⇒ memory-role carriage binds differently than assistant carriage. Both V2a and V2b within MDD **AND both TOST-equivalent (±16.2 pp)** ⇒ "role-flat by TOST: dilution-not-privilege" — **provisional per lock L1a** (person-neutral phrasing; Stage 2 required before the P1d unpin is final). Below MDD **without** TOST ⇒ "no role effect resolvable at 16.2 pp — transfer assumption **unfalsified, not affirmed**." | P-R | 16.2 pp; TOST margin ±16.2 pp |
| **V3** E4 per-turn re-anchoring rescues | M(A-hi) − M(A-hi-E) | ≥ 16.2 pp ⇒ record repetition keeps pace with exhaust volume (first isolation of the repetition lever; §8 Q5 partially closes). < 16.2 pp ⇒ repetition does not rescue at this dose — emit-side has no volume answer; check-side (C4 alarm) is the only lever. | P-E4 | 16.2 pp |
| **V4a** production B-preview reduces memory-carried exhaust | M(M-hi) − M(M-hi-B) | ≥ 16.2 pp ⇒ **the deployed rendering bundle (production format + 180-char truncation — lock L6c: rendering and exhaust-token dose change together)** suppresses first-party stale carriage. | P-M1 | 16.2 pp |
| **V4b** compilation enforces on the memory surface (P1d residual) | M(M-hi-B) − M(M-hi-C) | ≥ 16.2 pp ⇒ compile-on-read closes a resolvable residual that B-level annotation leaves ⇒ evidence for unpinning P1d arm-C wiring (with V2b informing transfer; see open-Q8 resolution). **On P-M2 failure the verdict line is exactly the L8 NOT TESTABLE line**, followed by a registered *descriptive annotation that is explicitly not a verdict*: "descriptive: M(M-hi-B) below 16.2% — B-level rendering at floor; wiring urgency downgraded" (review minor resolved — no alternate affirmative wording). | P-M2 | 16.2 pp |
| **V5** multi-turn F1 replication | exhaust_adoption(A-hi-N) + ELAPSED exhaust_verbatim(A-hi-N) + tracking stats | descriptive (doubles as P-H2 input). Predicted high per arm-1's zero-abstain invariant; a low value is itself a finding. | — | descriptive |

**Interpretation lock on verdict independence:** V1 (volume), V2 (role), V3 (repetition), V4 (rendering) are separate claims and never pool into a "G1 confirmed/denied" headline. Partial validation is reported per contrast.

## C4 kill-row linkage (registered — which measured correlation, at what resolving power, kills)

§7 row 3: *"C4 exhaust ratio shows no correlation with degradation onset ⇒ G1 mechanism unsupported; rewrite §2."* Stage-1 operationalization:

- **The measured correlation is the dose–response**: M across Z0 / A-lo / A-hi at fixed role=assistant, correction-once — correction-defeat as a function of exhaust content at **fixed total context length** (exact token parity), with `exhaust_ratio` swinging from undefined at Z0 to ≈0.18 injected/exhaust at A-hi while injected-record tokens stay fixed (≈56).
- **Resolving power of the kill:** 16.2 pp of stale_decide across a ≈318-ws-token exhaust swing at N=150. A dose effect smaller than that is **not deniable by this arm**.
- **Kill fires (Stage-1 form)** iff P-H1 ∧ P-H2 (both co-requirements) pass AND M(A-hi) − M(Z0) < 16.2 pp AND V2a shows no assistant-carriage excess ≥ 16.2 pp. (The CA trend is **not** in this conjunction — supporting wording only.) Then: **C4-as-token-ratio-threshold is unsupported on this surface; §2 G1 is rewritten as "unsupported under controlled replay"** — Stage 2 (distributional self-match, the registered residual gap) becomes the mandatory decider.
- **Kill relocates (does not fire)** if V1 fails but V2a fires with assistant > external ≥ 16.2 pp: mechanism is carriage privilege, not volume — C4's ratio form voided, monitor rewritten with a role-weighted numerator; §2 G1 amended, not deleted.
- **Kill is NOT testable** if P-H2 fails (adoption absent OR tracking null unrejected): Stage 1 cannot reach the mechanism; no kill verdict either way; Stage 2 mandatory before any C4 threshold ships.
- **If V1 validates:** the Z0/A-lo/A-hi curve is C4's first calibration data **for the bundle only**. **No production threshold is set from Stage 1, and no token-denominated numerator may be calibrated from Stage 1** (lock L4b — the causal variable could be restatement count at any token cost; the A-hi-2c disambiguator is queued). Threshold setting requires Stage-2 ecological ratios.

## Interpretation locks

- **L1 — authored-exhaust scope.** Stage 1 tests carriage, role, volume, and rendering of authored exhaust replayed under true role labels; not distributional self-match or exhaust↔task coupling (Stage 2). Public statements say "under controlled replay."
- **L1a — person-neutrality caveat (registered — review major resolved).** The mandatory person-neutral phrasing removes first-person self-attribution, the closest Stage-1-controllable component of F2. A V2a/V2b null under person-neutral phrasing **cannot rule out first-person self-attribution privilege**; the role-flat ⇒ P1d-unpin inference is **provisional pending Stage 2** (and open Q8's decision rule says so). The confound's direction (biasing toward role-flat, the program-convenient outcome) is registered here explicitly. A-hi-1p (first-person units, within-assistant contrast) is the queued direct measurement.
- **L2 — no pooling.** Contrasts are independent claims; no combined "G1 verdict" line, ever. P1d facet families do not pool with the R contrast.
- **L3 — decoupling is descriptive.** DECIDE-first ordering means ELAPSED may be rationalized post-decision; `decoupling_rate` carries this caveat in every report. Two-call split-question design queued (open Q2).
- **L4 — exhaust-unit bundle granularity.** Each unit bundles an explicit anchorless-relative claim AND T4 ambience at fixed proportion; V1 validates/kills the bundle; no component attribution. Claim-free ambience dose queued.
- **L4b — tokens vs restatements (registered — review major resolved).** Dose scales tokens, contradiction count, and marker count together. A V1 pass supports "the exhaust bundle defeats correction," never "token volume causes defeat." No token-denominated C4 numerator (units, not just threshold value) may be calibrated from Stage 1.
- **L4c — role vs presentation (registered — review major resolved).** V2a/V2b test the role+presentation bundle (unfenced assistant prose vs labeled bracketed block). **X-hi vs M-hi is the only pure-label pairwise contrast** (they differ only in fence-label lines, checked byte-level); it is reported descriptively.
- **L5 — scope.** One subject model (non-reasoning), one task family (threshold-rule decision), synthetic transcripts, one corrected record, true-day scenarios only. Claude-family replication queued (no API key). Deflating-V_x (F3 direction) not run — exhaust always inflates, matching the incident; registered as untested.
- **L6 — memory-rendering fiction.** M-hi-B/C `written` stamps and the (0d ago) ages are authored fiction; the production as_of distribution (days-old crystallized entries) differs. V4 results transfer to production rendering *decisions*, not production base rates.
- **L6b — hook-drift lock.** The B cell's bytes are pinned to the production format string as copied at spec authoring (sha256 prefix `e51103ed56643676`); the tested bytes are the registered bytes. If the hook renderer drifts, V4a claims apply to the registered rendering; shared-renderer extraction is the queued fix (I6).
- **L6c — B rendering+dose bundle.** Production-faithful truncation removes ≈13% of exhaust tokens; V4a's claim is about the deployed bundle, and the report states the token delta next to the verdict.
- **L7 — C-cell wins are Enforcement, not Binding** (arm-2 L3/L4 inherited): the compiler performed the adjudication; the model honored a keyed declarative fence. Conflict detection is not tested.
- **L8 — NOT TESTABLE printing rule.** Any precondition failure prints exactly "NOT TESTABLE at N=150 given observed base rate" for its dependent verdicts — never a pass, never a null. (V4b's descriptive annotation rides after the NOT TESTABLE line and is labeled not-a-verdict.)

## Covariate logging (per scenario × cell row in `calls.jsonl` — the C4 graduation dataset)

| covariate | definition |
|---|---|
| `exhaust_tokens` | ws-token count of the exhaust bytes **as rendered in that cell** (verbatim units; B: truncated preview blocks; C: compiled blocks **including compiler-emitted notice/fence text — registered definition, excluded from any D-contrast use**) |
| `injected_record_tokens` | ws-tokens of the m1 `[SESSION RECORD]` block + all TICK lines + corrected-record block |
| `exhaust_ratio` | injected_record_tokens / exhaust_tokens (null at dose 0) |
| `turns` | messages before probe (fixed 16; Stage-2 schema compatibility) |
| `role`, `dose`, `correction_mode`, `rendering` | cell factors |
| `anchor_count`, `anchor_positions` | count and 1-based message indices of anchored records/ticks ([1], +[3..13] if every_turn, +[15] if corrected) |
| `contradiction_count` | carried units (= dose; collinear by design, stated) |
| `exhaust_confidence_markers` | summed frozen-lexicon marker count of carried units |
| `exhaust_token_positions` | first/last/mean ws-token offsets of exhaust spans in the concatenated transcript (carrier-offset + last-unit-recency covariate) |
| `rule_polarity`, `T`, `v_c`, `v_x`, `true_now`, `iso_start`, `iso_corr`, `initial_elapsed_h` | scenario constants |
| `sid`, `cell`, `unit_ids` | keys |

**Exploratory fitted risk score (registered as exploratory, never a verdict):** pooled logistic regression of `stale_decide` on the covariates, computed **post-hoc from `calls.jsonl`** (not in the harness). Stated limitation: at Stage 1 most covariates are cell-determined, so the fit is groundwork for the C4 risk-score *schema*, not an estimate; real fitting requires Stage-2 within-session variance. The row schema above is the registered Stage-2-compatible format.

## Stage 2 — live autoregressive sessions (PLACEHOLDER — out of this spec)

Separate spec, gated on Stage-1 results. Sketch only: the subject generates its own exhaust across real turns under seeded task frames with known `true_now`; per-session measurement of C4's exhaust ratio against degradation onset; ecological correlation is the §7 row's native form; risk-score fitting, numerator units, and threshold setting happen here. Which factors Stage 2 varies is determined by which Stage-1 contrasts survive (and lock L1a's first-person question rides mandatory). Nothing in Stage 2 is designed, powered, or promised by this document.

## Costs / mechanics

1,350 registered calls (150 × 9), ≈630 ws-tokens (~0.9–1.3k provider tokens) in / ≤150 out per call; 8 workers; arm-1 retry/backoff via imported `call_model`; temperature 0. Estimated x.ai cost < $6; wall ≈ 25–40 min. Raw responses + scored rows + full covariates persisted to `.hologram/eval/exhaust_probe_runs/<run_id>/` (`config.json` + `calls.jsonl` + `summary.json`, arm-1/2 mirror). `config.json` records: n, model, seed, spec id, **registry hash**, cell list, **max cross-role token spread**, invariants-checked flag. Smoke runs (n ≤ 4) additionally persist the full request `messages` array per row (payload-shape build gate, open Q6 promoted).

**Generation-time invariants (all checked in `check_all` before the first API call; any failure voids loudly):**
1. Exhaust unit bytes identical across all carrying cells (per scenario); units are true assistant messages in assistant cells and ride inside the registered fences in X/M cells.
2. Replacing carried units with their exactly-matched fillers reproduces Z0's messages byte-for-byte from A-hi's (recorded edits, arm-2 machinery); same check A-lo ↔ A-hi on the four filler slots.
3. X-hi / M-hi differ from each other **only in fence-label lines** (byte-level diff check); X/M derive from A-hi by the recorded relocation+ack+padding transformation; **cross-role total ws-token spread < 1% per scenario** (measured 0.0%).
4. **Dose cells token-count identical** (Z0 = A-lo = A-hi exactly); filler ws-tokens == unit ws-tokens.
5. M-hi-B derives from M-hi and M-hi-C from M-hi-B by recorded reversible per-slot edits; inverse-application reproduces the parent byte-for-byte; C text passes the deontic guard; every truncated preview fires T1/T2 under the actual shared lint; claim spans survive truncation at the longest numeral.
6. m1/m14/m16/probe byte-identical across cells; correction bytes identical across corrected cells (per scenario); m15 neutral bytes fixed in A-hi-N.
7. Threshold margins (V_c ≤ T − 1.3 h; V_x ≥ T + 2 h); V_x-in-words present in every carried unit; 17-message skeleton with strict role alternation in every cell.
8. Neutral fillers/acks/WPs/padding: zero T1/T2/T4 lint findings + digit/time-word guard; ≥3 units carry establishment markers; padding exactly equals ack+fence surplus.
9. Polarity split exact (i%2); all `true_now` in day hours 09–16.
10. `messages=None` regression: arm-1/2 payload construction byte-identical after the refactor — frozen-payload equality tests per provider branch + full existing suite green (53 new tests; suite 206).

CLI (arm-2 mirror): `--check` (invariants only, offline) | `--render <sid> <cell>` (offline transcript dump, roles labeled) | `--smoke` (4 × 9 = 36 calls, charged to the reserve) | `--run --n 150` | `--summarize <run_dir>`.

## Registered resolutions of the pre-registration review (all 14 findings)

| finding | resolution |
|---|---|
| B1 scout destroys dilution control / drops A-hi-N | Spec skeleton supersedes scout, declared above; fixed 17-message skeleton all cells; exact filler matching (invariant 4, stronger than <1%); 9-cell table includes A-hi-N; DECIDE+polarity is the primary probe. |
| B2 no content-reading null | P-H2 gains the registered tracking co-requirement (own-V_x permutation null, seeded, ±0.5 h non-overlapping windows); implemented in harness (`tracking_permutation_p`) and gated in verdict logic. |
| B3 M-hi-B not production-faithful | B cell rebuilt byte-faithful: verbatim format string (hash-pinned), integer-day age, 180-char truncation + flattening, lint-gated flag with per-unit fire invariant, MEMORIES header; locks L6b/L6c; V4a reworded "deployed rendering bundle". |
| M4 dose/recency confound | A-lo slots {2,6}; last-unit recency matched; position logged. |
| M5 V1 token-attribution | Option (b): V1 bundle wording + lock L4b + kill-linkage numerator-units extension; A-hi-2c queued. |
| M3/M6 role-cell length confound | Scout parity mechanism restored: ack in X/M assistant slots, 16-token pad in assistant-cell user turns, <1% checked invariant (measured exact); invariant-3 wording rewritten; lock L4c. |
| M7 void/reserve arithmetic | Per-cell void; reserve = 36 smoke + ≤2 reruns + 114 contingency; third void requires dated amendment. |
| M8 V2b equivalence | TOST registered (margin ±16.2 pp, power stated); role-flat wording TOST-only and provisional; non-TOST wording "unfalsified, not affirmed"; open Q8 amended. |
| m9 V4b contradictory printing | L8 NOT TESTABLE line is the verdict; descriptive annotation labeled not-a-verdict. |
| m10 trend power unstated | Trend removed from the kill conjunction; supporting/descriptive only. |
| M12 person-neutrality bias | Lock L1a; provisional unpin; A-hi-1p queued. |
| m13 F2 establishment markers + overstated argument | ≥3 establishment-marker rule (enforced); registered-argument sentence reworded ("role label is the only ground-truth channel; idiom is a probabilistic cue tested in Stage 2"). |
| m14 payload-shape gate | Open Q6 promoted: no-network payload-equality + multi-turn role tests per provider (incl. a real transcript through the Google mapping); smoke runs persist request messages. |

## Registered decisions resolving the draft's open questions

1. **Exact frozen bytes** — resolved: all templates frozen in-module; registry hash `e0283332b494…` pins them.
2. **DECIDE/ELAPSED ordering bleed** — accepted under lock L3; split-question sub-cell stays queued (reserve is committed to void recovery).
3. **`unknown_decide` neutrality** — retained neutral for M; `not_governed` stays registered secondary descriptive (F4's inaction-adjacency argument noted; changing the primary post-review would be an unforced scope change).
4. **P-H2 metric** — DECIDE-side adoption retained as (i), with the ELAPSED-channel tracking statistic added as (ii) — the review's content-reading blocker resolution subsumes the verbatim-sensitivity concern.
5. **Tick arithmetic scaffold** — acknowledged, unresolved by design: a V3 rescue may partly reflect tick-delta arithmetic support; V3's claim is "per-turn re-anchoring (ticks as deployed) rescues," which is the production-relevant lever either way; component isolation queued.
6. **Provider payload shapes** — resolved: build-gate tests per provider (see invariant 10).
7. **F3 direction facet** — reserve kept intact (registered above); deflating-V_x stays untested (lock L5).
8. **P1d unpin rule (amended per review):** wire arm-C when V4b ≥ MDD **and** either V2b resolves a memory-role difference or role-flat is established **by TOST**; a bare below-MDD null does NOT unpin — it leaves the transfer assumption unfalsified and the wiring pinned pending Stage 2 (lock L1a). Owner sign-off at freeze.
9. **`exhaust_tokens` as ws-count** — adequate for within-arm dose labels; the provider-tokenizer conversion story must be registered before any production C4 threshold is published (Stage 2 scope; consistent with the L4b no-numerator rule).
10. **Memory-carrier ecology** — per-slot single-entry MEMORIES blocks optimize positional comparability over ecology; accepted for R; ecology sub-render is Stage-2 scope.
11. **System-prompt bytes** — this arm's own registered bytes (frozen above); no cross-arm comparability claim.

## Measured build constants (recorded for the freeze record)

Registry `e0283332b494530cc9bfc449e93eac799c5ad2980c4c2491cd354db07a01d1a9`. Per-scenario totals ≈630 ws-tokens (Z0/A-lo/A-hi/X-hi/M-hi identical; A-hi-E ≈649 — tick surplus is the treatment; M-hi-B ≈590; M-hi-C ≈800). Exhaust tokens: high 318, low 107, B 277, C 487 (incl. compiler text, per covariate definition). Injected record tokens: once ≈56, every_turn ≈74, none ≈33. Units 52–55 ws-tokens each, fillers exact-matched. `--check` green at N=150; harness tests 53/53; full suite 206/206.

---

## RESULTS — registered run (2026-07-17T18:32-06:00, run `20260717T183226-e98c20`)

1,350/1,350 calls, 0 failures, 0 parse failures. All headroom/potency preconditions passed.

| cell | rule-governed-by-exhaust (M) | elapsed correct | decoupling |
|---|---|---|---|
| Z0 correction only | 0.0% | 100% | 0.0% |
| A-lo (2 units, assistant) | 16.0% | 100% | 16.0% |
| A-hi (6 units, assistant) | **55.3%** | **100%** | **55.3%** |
| X-hi (6 units, external block) | 54.0% | 100% | 54.0% |
| M-hi (6 units, memory notes) | 59.3% | 100% | 59.3% |
| M-hi-B (production preview rendering) | 42.7% | 100% | 42.7% |
| M-hi-C (arm-C compiled) | 50.0% | 100% | 50.0% |
| A-hi-E (every-turn tick) | 63.3% | 100% | 63.3% |
| A-hi-N (exhaust, no correction) | 99.3% adopt | — | — |

**V1 — F4 REPRODUCED UNDER BYTE CONTROL.** Six confident restatements defeat one
corrected anchored record 55.3% of the time (≥ MDD 16.2pp vs Z0's 0.0% floor).
Dose-monotone: 0 → 16.0 → 55.3 (Cochran–Armitage z=11.3, supporting only). The §7
C4 kill row does NOT fire — the G1 mechanism is supported; per lock L4b the bundle
(tokens+restatements) licenses no token-denominated C4 numerator from Stage 1.
**THE DECOUPLING RESULT (the program's §0 diagnosis, now measured):** in every cell
the model reports the corrected elapsed time 100% correctly — and then rules on the
exhaust value anyway (55.3% at A-hi). Possess the fact, state it correctly, not be
governed by it: F6/G4, n=150 per cell.
**V2 — ROLE-FLAT (TOST, ±16.2pp both pairwise): dilution-not-privilege, provisional.**
Assistant-role exhaust carries no resolvable weight beyond its tokens vs external or
memory presentation (A-hi 55.3 / X-hi 54.0 / M-hi 59.3). Provisional per lock L1a
(person-neutral phrasing; authored idiom) — Stage 2 required before this is final.
**V3 — REPETITION DOES NOT RESCUE.** Every-turn re-anchoring (A-hi-E) moved failure
−8.0pp in the WRONG direction (63.3%, not resolvable). Emit-side has no volume
answer; the check-side (C4 alarm) is the only remaining lever. §1's "do not ship §4
alone" warning is now a measured result.
**V4a — PRODUCTION B-PREVIEW RENDERING VALIDATED.** The deployed as_of+delta+flag
rendering cut memory-carried exhaust 59.3 → 42.7% (16.6pp ≥ MDD; format+truncation
bundle per lock L6c).
**V4b — ARM-C COMPILATION NOT RESOLVABLE ON THE MEMORY SURFACE.** M-hi-C 50.0% vs
M-hi-B 42.7%: point estimate 7.3pp WORSE, below MDD. The P1d pin decision is
data-vindicated — compile-on-read for memory previews has no measured benefit at
this N and shall not be wired on arm-2 extrapolation alone.
**V5 — F1 REPLICATED MULTI-TURN (descriptive).** Without a correction, the wrong
claim is adopted 99.3% and content-tracked (own-V_x 150/150, permutation p=.001);
ambient day/night fully captured (100% night on true-day scenarios).

**Scope:** one subject, authored exhaust (person-neutral), single session shape.
Stage 2 (live autoregressive) owns idiom/self-match and any final role claim.
