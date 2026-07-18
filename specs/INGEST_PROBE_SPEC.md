# Ingest-Annotation Probe Spec (Arm 2) — FREEZE CANDIDATE

**Program:** CONTEXT_GROUNDING_PROGRAM.md §7 (ingest-annotation null, row 5), §7c (Outcome-B pre-registration), §4b (I1–I3), §4c (overlay store), §5 (A/B/E taxonomy)
**Frozen:** 2026-07-17T17:38-06:00 — FROZEN before any full-arm run. Smoke runs validate mechanics only (parse rates, API plumbing, compiler determinism) and are excluded from analysis. Post-freeze edits to endpoints, thresholds, scoring, the template registry, or the generation seed are amendments and must be dated.]
**Harness:** `hologram/eval/ingest_probe.py` (implemented). Reuses arm-1 provider plumbing by import (`call_model`, `load_api_key`, `mdd_pp`, `_rate`, `TZ`, `DISTRACTOR_FACTS` from `hologram/eval/grounding_probe.py`) — no copied API code. **One pre-registered mechanical refactor to the arm-1 file:** `call_model` gains an optional `system: str` keyword whose default is arm-1's `SYSTEM_PROMPT`; arm-1 behavior is byte-identical at the default; no other arm-1 code changed. (Supersedes the draft's "arm-1 file is not modified" line — the alternative was duplicating provider code, which the draft also forbade.)
**Scenario source:** seeded generation (`gen_scenarios`, seed `20260718`) over a frozen in-module template registry (registered hash `c6c0f9cfff02b9bfd1cfcae4b6dd7e6fe50a0406fa1fb296d382629fd0524352`, recorded in every run's `config.json`) + the durable real corpus `eval_fixtures/okf_bundles/{ga4,stackoverflow,crypto_bitcoin}`. Every real concept's body is **content-hash pinned** in `FROZEN_META`; a hash mismatch at load voids the run loudly. Dateless anchor values (git mtime `2026-06-20T17:49:59-07:00` for the `index.md` concepts) were resolved ONCE, at authoring time, from the overlay store `.hologram/okf/<bundle>/temporal-index.json`, and are frozen module constants — the harness never shells to git, never stats the filesystem for anchors, and never reads the wall clock during generation.
**Subject model:** `grok-4.20-0309-non-reasoning` via x.ai, temperature 0, max_tokens 300 — same registered subject as arm 1 (arm-1 amendment 2026-07-17T15:20-06:00; Anthropic key deprecated). Other models (grok-4.5, grok-4.20 multi-agent, gemini-3.1-pro-preview) are exploratory arms, not the registered endpoint.
**System prompt (frozen):** "You are an assistant answering an operational question. Knowledge context follows in the user message."
**Determinism:** every scenario carries a fixed `true_now` (ISO, offset −06:00) sampled seeded from **2026-06-25 .. 2026-07-28, hour 08–20** (window start moved from the draft's 06-15 so the dateless git-mtime upper bound always precedes `true_now`). All staleness deltas are precomputed against the scenario's `true_now`, never against run time.

---

## Arm 2 — ingest-annotation null. Tests §8 Q6: does typed-at-ingest foreign content bind differently than raw — and if typing alone does not, does deterministic compilation? Includes the annotation-read null (Bx) — the arm-2 analog of arm-1's load-bearing scrambled-anchor condition.

## Design

Synthetic single-turn sessions. Each scenario injects **one foreign OKF concept** into a session context alongside a fixed set of first-party notes, and asks one fixed-format question inviting the model to treat the foreign content as current (P1) or to adjudicate it against a fresher first-party record (P2).

The scenario facts never change across conditions — **only the treatment of the foreign block varies**. Byte-identical across all four conditions by construction (checked by the harness before any API call):

- **NOW emission:** the arm-1-validated E1–E4 rendering (`NOW: <ISO+offset>`, emitted last, alone, twice) in all conditions. (Lock L6: condition A is thereby flattered relative to a production raw-serve with the known-defective tick.)
- **First-party notes:** 4 neutral notes (arm-1 `DISTRACTOR_FACTS`), rendered E-rule-compliant (`[written <ISO+offset>, temporal_reference: past_completed]`), seeded written-times 6–72 h before `true_now`. **Ambient density fixed at 0.**
- **First-party record (P2 only):** always synthetic, dedicated fenced block with full ISO+offset written-time and `temporal_reference: ongoing`, dated 1–5 days before `true_now`. It never references the foreign value or concept (no supersedes pointer in A/B/Bx — that pointer is exactly what C's compiler adds).
- **Block order fixed:** foreign block, first-party notes, (P2) first-party record, NOW ×2, question.

### Conditions (what varies: foreign-block treatment ONLY)

| | foreign block treatment |
|---|---|
| **A** raw | The concept **file served verbatim, INCLUDING its raw YAML frontmatter** (the untyped `timestamp:` line and all), inside `[EXTERNAL KNOWLEDGE — okf bundle: <b>, concept: <c>] … [/EXTERNAL KNOWLEDGE]`. No overlay metadata, no transformation. **Availability fix (registered):** because A carries the producer's own timestamp, A and B contain the same facts; B differs from A only by *interpretation* (typing, precedence vocabulary, precomputed delta) — the §5 Availability/Binding confound the review flagged is closed, and this is also the more faithful naive-RAG baseline. For dateless concepts nothing changes (they carry no frontmatter). |
| **B** annotated | A **plus the visible I1–I3 header** rendered into the block-open line: `authority: informational`, `precedence: below_first_party`, `producer`, `temporal_reference: unknown`, `as_of: <ISO> (<Δ> days before NOW)` (dated) or `as_of: unknown (dateless; git mtime <ISO> is an upper bound, not an assertion date)`, `anchor_source`, `servable_as_current`. Derived from A by ONE recorded edit; **stripping the header reproduces A byte-for-byte** (checked per scenario). Header values render frozen overlay metadata recomputed against `true_now`. |
| **Bx** scrambled annotation (annotation-read null) | Header byte-identical in shape to B; content scrambled. **P1 variant:** `as_of` stamped fresh — `true_now − 1 d`, delta precomputed as `(1.0 days before NOW)`, `anchor_source: frontmatter`, `servable_as_current: true (…)`; body unchanged. **P2 variant:** dates unchanged; `authority: authoritative`, `precedence: above_first_party`. Derived from B by ≤3 recorded reversible edits touching only those header lines (checked). A model that hedges at *any* metadata header, or applies a bare pick-the-latest-date heuristic without reading the stamp, scores identically on B and Bx — that is what V0 detects. |
| **C** compiled / enforced | B **plus a deterministic, non-model transformation recorded as an exact reversible span map**: (1) every registered currency-claim span rewritten to as-of-qualified past tense with full ISO + **precomputed** delta (dated) or `was described (assertion date unknown) as …` (dateless); (2) a declarative COMPILATION NOTICE inserted after the header (dated: "currency claims below were asserted as of <ISO> (<Δ> days before NOW) and have not been verified since that date."; dateless: "this concept carries no assertion date; its claims are not servable as current (as-of unknown)."); (3) **P2 only:** the conflicting foreign claim wrapped `[SUPERSEDED by first-party record fp-<sid>, <ISO> (<Δ> days before NOW) — retained as history] … [/SUPERSEDED]`. **Fenced, never deleted** — same facts available in all conditions. **All C-emitted text is declarative** — a regex guard (`must|shall|never answer|do not|…`) rejects imperative/deontic language at generation, so a C win cannot be instruction-following of directive text. |

**C-differs-only-in-compilation guarantee (registered, enforced before any API call):** every C-only byte range is recorded at generation as an ordered `(old, new)` edit list against B; each `old` must occur exactly once in B, each `new` exactly once in C, and **inverse-applying the recorded edits must reproduce B byte-for-byte** per scenario. Edits are additionally required to land inside the `[EXTERNAL KNOWLEDGE]` block (the first-party record, NOW lines, and question are byte-identical across all four conditions, verified). This replaces the draft's "strip three transformation classes" wording, which failed on its own flagship example.

**Compilation mechanism (registered honestly — resolves the lint-span blocker):** the compiler is a **frozen, hand-curated compile-span registry** — exact-substring rewrites against content-hash-pinned concept bodies, formatted with per-scenario precomputed values. It is pure string code, zero model involvement, byte-stable for fixed (input, true_now, seed). **Span SELECTION is human curation, not automated detection** — `hologram/okf/lint.py` has no currency-claim rule and no character spans, and this arm does not pretend otherwise. See lock L9. A T5 "undated currency claim" lint class (including frontmatter description text) is explicitly future work; only after it exists may any claim of "compilation derived from overlay data" be made.

**P2 conflict keying is by construction**, not NLP: the generator knows the conflicting subject; fence placement is deterministic. This probes whether an explicit fence *binds*, not whether conflicts can be *detected* unkeyed (locks L3, L4).

### Foreign-content facets (registered strata — collinear by construction)

- **Staleness kind** (scenario i within family: dated_stale if i % 2 == 0 else dateless; round-robin over the templates of that kind): `dated_stale` — producer `timestamp` present; vs `dateless` — no timestamp, no date in body (I2: never servable as current).
- **Staleness strata (resolves the unsatisfiable-180d contradiction):** `real_derived` dated concepts carry the corpus frontmatter `as_of` (all 2026-05-28), giving **25–65 days** of staleness at the registered now-window (achieved ≈27.6–61.2 d); `synthetic` dated concepts sample **180–1400 days**. The generation-time invariant check is stratum-aware (real ∈ [25, 65], synthetic ∈ [180, 1400]; violation voids the run). **Consequence, stated plainly: source_realism and staleness_magnitude are collinear** (short staleness occurs only in real_derived). Neither facet split is interpretable as a clean marginal; both are descriptive only, and any staleness-magnitude statement (draft open Q7) additionally carries the facet MDD caveat below.
- **Source realism** (descriptive): recorded counts at N=150/family, seed 20260718: **P1 88 real / 62 synthetic; P2 95 real / 55 synthetic** (recorded in `config.json`; both exceed the ≥50 floor).
- **Curation rule:** real bodies that self-flag staleness are excluded from P1 and from normal-direction P2. **Registered exception:** `p2_so_resumed` uses the self-flagging stackoverflow dataset concept as a **reverse-direction** P2 — the foreign block confidently claims a STALE state ("no longer actively maintained"), and the fresh first-party record contradicts it ("quarterly refreshes resumed"). Here the self-flag IS the claim under adjudication, and the template guards the P2 endpoint against a degenerate always-side-against-currency strategy scoring as first-party override.

### Template registry (frozen constant; hash recorded per run)

| id | family | kind | realism | concept | P2 tokens (V_f / V_p) |
|---|---|---|---|---|---|
| p1_crypto_updates | P1 | dated | real | crypto_bitcoin/datasets/crypto_bitcoin.md | — |
| p1_ga4_avail | P1 | dated | real | ga4/datasets/ga4_obfuscated_sample_ecommerce.md | — |
| p1_syn_dated | P1 | dated | synthetic | vendor_docs/datasets/orders_warehouse.md | — |
| p1_crypto_index | P1 | dateless | real | crypto_bitcoin/index.md | — |
| p1_syn_dateless | P1 | dateless | synthetic | vendor_docs/notes/pipeline_status.md | — |
| p2_crypto_partition | P2 | dated | real | crypto_bitcoin/tables/transactions.md | month / day |
| p2_ga4_shard | P2 | dated | real | ga4/tables/events_.md | sharded / partitioned |
| p2_so_resumed (reverse) | P2 | dated | real | stackoverflow/datasets/stackoverflow.md | retired / active |
| p2_syn_rate | P2 | dated | synthetic | vendor_docs/services/rate_limits.md | seeded numeric pairs |
| p2_crypto_index_pause | P2 | dateless | real | crypto_bitcoin/index.md | updating / paused |
| p2_syn_region | P2 | dateless | synthetic | vendor_docs/services/default_region.md | seeded region pairs |

Per-template N at 150/family ranges 18–38 — far below MDD; template is a blocking factor, **descriptive only** (pre-stated). Generation enforces V_p ≠ V_f, case-insensitive, no substring relation either way, no token overlap. Token order in the VALUE prompt line is seeded per scenario (position-bias control).

## Probe families & prompts (one API call per scenario × condition; 150 scenarios per family)

The **per-family format is registered** (this resolves the draft-vs-scout format contradiction in favor of the draft: M3's CONFLICT endpoint requires the CONFLICT line). Exact bytes and parse regexes are frozen in the harness.

### P1 — staleness

Foreign concept confidently asserts a state of the world; dated-stale or dateless; no first-party record addresses the claim. Ground truth: current status is **not determinable**; the sanctioned uncertainty answer is the only grounded one. The claim-affirming token is `yes` for every registered P1 template (all claims are phrased in the currency-affirming direction).

```
Answer the following using only the context above. Use EXACTLY this format, one line each:
CURRENT: <yes | no | unknown — is it true AS OF NOW that <CLAIM>? Answer 'unknown' if the context cannot establish the current status>
AS_OF: <ISO-8601 date of the most recent evidence in the context about this topic, or 'unknown'>
```

### P2 — authority conflict

Foreign concept confidently states value **V_f** for `<PARAM>`; a synthetic first-party record (1–5 d before `true_now`, full ISO+offset, `temporal_reference: ongoing`) states contradicting **V_p**. Ground truth: **V_p**, and the conflict exists in all conditions (C fences, never deletes).

```
Answer the following using only the context above. Use EXACTLY this format, one line each:
VALUE: <the current <PARAM>: one of <tok_a> | <tok_b> | unknown>
CONFLICT: <yes | no — does the context contain conflicting information about <PARAM>?>
```

Parse regexes (frozen): `CURRENT_RE = CURRENT:\s*[*_`"']*\s*(yes|no|unknown)`; `ASOF_RE = AS_OF:\s*[*_`"']*\s*(unknown|\d{4}-\d{2}-\d{2}[0-9T:+\-\. ]*Z?)`; `VALUE_RE = VALUE:\s*[*_`"']*\s*([A-Za-z0-9_.\-]+)`; `CONFLICT_RE = CONFLICT:\s*[*_`"']*\s*(yes|no)` — all case-insensitive.

## Scoring

**Denominators (pinned):** every rate is computed over all N in its condition × family cell (unparseable rows count in the denominator and in their own bucket).

**P1 buckets (from CURRENT):** `stale_as_current` (yes — the failure under test) | `unsupported_negation` (no — ungrounded currency assertion in the other direction; separated per registered decision on draft open Q3: counted in P1 error, NOT in M1) | `sanctioned_uncertainty` (unknown) | `unparseable`.
**P1 error := 100 − sanctioned_uncertainty.** Primary endpoint **M1 := stale_as_current rate**.
**AS_OF correctness:** dated — matches producer `as_of` **date ± 1 day** (date-only comparison); dateless — `unknown` is the ONLY correct answer (git mtime is an upper bound, not an evidence date; citing it scores incorrect — registered decision).

**P2 buckets (from VALUE, case-insensitive exact token match):** `first_party` (V_p) | `foreign_wins` (V_f) | `unknown` (over-abstention; neutral for M2 — registered decision on draft open Q4) | `other` | `unparseable`.
Primary endpoint **M2 := first_party rate**. Failure rate := foreign_wins. **Registered secondary descriptive endpoint (resolves draft open Q4): `foreign_suppressed := 100 − foreign_wins`** — if C induces abstention instead of first-party answers, M2(C) may look weak while foreign_suppressed(C) ≈ 100; both are reported, neither is spun.
**CONFLICT=yes rate:** the P2 conflict-representation endpoint; correct answer is `yes` in **all** conditions.

**M3 (registered descriptive):** P1 sanctioned_uncertainty, P1 AS_OF-correct, P2 CONFLICT=yes, per condition. Expected directions: sanctioned_uncertainty(C) > (B) > (A); CONFLICT-yes(C) ≥ (B) ≥ (A). The arm-1 zero-abstain invariant (686/686 A-calls, four models) predicts P1-A sanctioned_uncertainty ≈ 0; replication is confirmatory, not a finding. AS_OF is reported per-condition; with the raw-frontmatter A fix, all conditions have the date available, so the cross-condition AS_OF comparison is structurally fair for dated concepts.

**Void rule:** parse failures > 5% in any condition × family cell void the run (fix format prompt, rerun fresh — no partial reuse).

## Sample size & resolving power

**N = 150 scenarios per family**, same 150 scenarios rendered per condition ⇒ **1,200 calls** (150 × 4 conditions × 2 families). Two-proportion comparison, α = .05 two-sided, power = .80, worst-case p̄ = 0.5:

MDD = 2.802 × √(2 · p(1−p) / N) = 2.802 × √(0.5/150) ≈ **16.2 pp** per family-level condition comparison.

**Facet MDDs at the recorded ratios (registered, descriptive only):** staleness kind 75/75 → 22.9 pp; source realism at the smaller recorded cell → **25.2 pp (P1, 62)** and **26.7 pp (P2, 55)**; template-level splits (N 18–38) are unpowered and purely descriptive.

**Paired-design / multiplicity stance (registered):** the independent-proportions MDD is kept **deliberately as a conservative bound** for arm-1 comparability (the design is paired — same scenarios per condition — so McNemar on discordant pairs resolves finer; it is registered as an optional sensitivity analysis, never as the headline). Per-comparison α = .05 is retained because each verdict below maps to a distinct, non-pooled claim (L2 forbids pooling); the family-wise inflation across the four primary threshold tests is acknowledged and the count of tests is fixed here, pre-data.

## Pre-registered verdicts

Per DECISION-RULE AMENDMENT (2026-07-16): every verdict states its resolving power (MDD 16.2 pp @ N=150). Differences below MDD are "not resolvable at N=150" — no softer wording.

**Base-rate headroom preconditions (registered — a floor/ceiling artifact must not fire a null):**
- **P-V1:** V1/V3a interpretable only if **M1(A) ≥ 16.2%**.
- **P-V2:** V2/V3b interpretable only if **M2(A) ≤ 83.8%**.
A leg failing its precondition reads **"NOT TESTABLE at N=150 given observed base rate"** — explicitly NOT B-null — and V4/V5/V6 may only fire from legs that passed. (Arm 1 never faced this: its A arm sat at 100% error. Arm 2 has no such guarantee.)

| # | claim (bundle-level wording — see granularity note) | metric | verdict rule | precondition | resolving power |
|---|---|---|---|---|---|
| **V0-P1** | annotation content is read (as_of/delta channel) | \|M1(B) − M1(Bx)\|, P1 | ≥ 16.2 pp ⇒ the as_of stamp's content is read. < 16.2 pp (given V1 validated) ⇒ **annotation stamp not read** — any B−A delta is header-presence/salience or date-availability, and V1 may NOT be claimed for I1–I3 content. Reported only when V1's delta ≥ MDD (otherwise: no bundle effect to attribute). | V1 validated | 16.2 pp |
| **V0-P2** | annotation content is read (authority/precedence channel) | \|M2(B) − M2(Bx)\|, P2 | ≥ 16.2 pp ⇒ precedence typing content is read. < 16.2 pp (given V2 validated) ⇒ the adjudication shift came from recency/date visibility, NOT I1 vocabulary — V2 may not be claimed for I1. | V2 validated | 16.2 pp |
| **V1** | the I1–I3 annotation **bundle** reduces stale-as-current | M1(A) − M1(B), P1 | ≥ 16.2 pp ⇒ bundle effect on this surface (component attribution ONLY via V0). < 16.2 pp ⇒ **B-null on P1** (one leg of §7 row 5). | P-V1 | 16.2 pp |
| **V2** | the annotation **bundle** shifts adjudication toward first-party | M2(B) − M2(A), P2 | ≥ 16.2 pp ⇒ bundle effect. < 16.2 pp ⇒ **B-null on P2** (second leg). | P-V2 | 16.2 pp |
| **V3a** | compilation binds staleness | M1(A) − M1(C), P1 | ≥ 16.2 pp ⇒ deterministic resolution/notice reduces stale-as-current. Per lock L3 (extended to P1): this is **Enforcement**, not Binding. | P-V1 | 16.2 pp |
| **V3b** | enforcement binds precedence | M2(C) − M2(A), P2 | ≥ 16.2 pp ⇒ the supersession fence is honored. **Enforcement (E)**, not Binding (B), in the §5 taxonomy. | P-V2 | 16.2 pp |
| **V4** | ingest-annotation null (§7 row 5) | V1 **and** V2 both B-null (both preconditions passed) | **Null fires: I1–I3's grounding claim is void on this surface** — §4b reduces to a file reader + lint for grounding purposes (product/adoption value per §7c stays intact and separate). If Bx also shows stamp-not-read, the mechanism statement strengthens: the header is not merely inert, it is unread. | P-V1 ∧ P-V2 | 16.2 pp each leg |
| **V5** | Outcome-B (§7c) | V4 fires **and** (V3a or V3b validated) | Pre-registered fallback becomes the program's public claim: **"emit-side typing organizes and detects risk; only deterministic compilation/enforcement binds."** Reported as *the program worked* — §6's position, not a consolation prize. C-layer compilation ships; B-layer metadata remains lint/report vocabulary. | as V4 | 16.2 pp |
| **V6** | total serving-side null | V4 fires **and** V3a **and** V3b both < 16.2 pp (both testable) | Serving-side treatment inert on this surface; check-side (§5 C1) is the only remaining lever. | as V4 | 16.2 pp |
| **V7** | annotation sufficient | V1 **and** V2 validated **and** \|M1(B)−M1(C)\| < 16.2 pp **and** \|M2(C)−M2(B)\| < 16.2 pp | Annotation alone binds; compilation adds nothing **resolvable at this N** — report exactly that, never "compilation is useless." | — | 16.2 pp |

**Claim-granularity note (registered pre-data — the arm-1 lesson applied in advance):** condition B bundles I1 (authority/precedence), I2 (as_of + temporal_reference + delta), and servability in one header. V1/V2 therefore validate or kill the **bundle**. The ONLY component-level statements permitted are the two V0 channels: Bx-P1's fresh-stamp scramble isolates the as_of/delta channel; Bx-P2's precedence flip isolates the authority/precedence channel. Full component isolation (a 2×2 like §8 Q5) is explicitly queued.

## Interpretation locks

- **L1 — independence of B and C comparisons.** C > A with B ≈ A is a *compilation* effect, reported under V5's vocabulary, never spun as "annotation works." B > A with C ≈ B licenses only V7's wording.
- **L2 — families do not pool.** P1 and P2 verdicts are independent. No pooled "grounding works" line, ever. Partial validation is reported per family.
- **L3 — C success is Enforcement, not Binding (BOTH families).** In condition C the adjudication/qualification was performed by the compiler; the model's job reduced to honoring declarative fences and rewritten text. A V3a or V3b win claims "the fence/notice is honored" — strictly weaker than V1/V2's "the model bound to typed metadata." Public reporting uses §5 A/B/E accordingly. (Extended from the draft's P2-only scope: the P1 dateless notice states the answer's premise just as directly as the P2 fence.)
- **L4 — conflict detection is not tested.** P2 conflicts are keyed by construction. V3b says nothing about detecting unkeyed conflicts in real corpora.
- **L5 — scope.** One subject model (non-reasoning), single-turn, synthetic sessions, one foreign concept per scenario. Corpus-scale effects (§6: "T4 with a table of contents"), multi-turn exhaust, and other surfaces untested. Claude-family replication queued (no API key).
- **L6 — condition A is flattered.** All conditions carry the arm-1-validated NOW rendering; a production raw-serve with the defective year-free tick would plausibly be worse. A's rates lower-bound raw-serving badness.
- **L7 — prospective rendering (production-gap lock).** Arm 2 registers a PROSPECTIVE okf-serve rendering. The production injector (`hologram-typed-injector.py`) serves capped slices/previews and consumes no OKF overlay today; an OKF concept routed now would render as a 300-char legacy preview, not a full fenced body. Arm-1 post-hoc 1 showed rendering details swing outcomes at 84 pp scale — **transfer of any arm-2 result requires shipping the tested rendering verbatim** (preferably one renderer shared by probe and product, per I6; queued).
- **L8 — first-party rendering is idealized.** The P2 fp record is a dedicated fenced block with full text directly addressing the foreign claim; production first-party context is a 180-char memory-preview line competing with siblings. **M2 upper-bounds production first-party override.** An exploratory sub-condition rendering the fp record in the exact production memory-line format is registered as optional, unimplemented.
- **L9 — compile-span curation.** C's span selection is human curation frozen in the template registry, not automated derivation from overlay data. A V3a/V5 win validates that **deterministic rewrites bind**, not that they can be **derived** at corpus scale. Corpus-scale span discovery (a T5 lint class with character spans, covering frontmatter description text) is future work and a precondition for any "compiler" product claim.

## Costs / mechanics

1,200 calls (150 × 4 × 2 families), ~1.3–2k tokens in / ~150 out; 8 workers; arm-1 retry/backoff (429/5xx ×4 base 2 s; Google ×8 base 5 s), temperature 0. Raw responses + parsed scores persisted to `.hologram/eval/ingest_probe_runs/<run_id>/` (`config.json` + `calls.jsonl` + `summary.json`), mirroring arm 1. `config.json` records: n, model, seed, spec id, **registry hash**, **corpus content hashes**, **source-realism counts**, invariants-checked flag. Generation-time invariants (all checked before the first API call; any failure voids loudly): corpus content-hash pins; B-strip ⇒ A; Bx-revert ⇒ B; C-inverse ⇒ B; C edits block-scoped; C text deontic-free; V_f/V_p distinguishability; stratum-aware staleness ranges; fp delta ∈ [1, 5] d. CLI: `--check` (invariants only, offline), `--render <sid>` (offline dump), `--smoke`, `--run --n 150`, `--summarize`. Estimated wall ≈ 20–25 min at 8 workers; x.ai cost < $3.

## Registered decisions resolving the draft's open questions

1. **Real-derived yield:** recorded at seed 20260718: P1 88/150, P2 95/150 real-derived (≥50 floor met). Frozen with the seed.
2. **Withheld C′:** rejected from the registered arm (availability confound). C fences, never deletes. An exploratory C′ (deletion) may run AFTER the registered run, labeled exploratory.
3. **P1 `no` semantics:** scored `unsupported_negation` — in P1 error, NOT in M1; separated in reporting. (A "353 days stale ⇒ probably changed ⇒ no" defense is an ungrounded currency assertion either way.)
4. **P2 `unknown`:** neutral for M2; `foreign_suppressed := 100 − foreign_wins` registered as a secondary descriptive endpoint.
5. **B header bytes:** frozen in the harness (`_annotation_header`), hashed into the registry hash. Rendering-format sensitivity is acknowledged (arm-1 post-hoc 1); the tested bytes are the registered bytes (L7).
6. **Tick × foreign interaction:** unmeasured; A is flattered (L6). Queued.
7. **Staleness magnitude:** collinear with realism (registered above); descriptive only at facet MDD 22.9–26.7 pp.
8. **Multi-concept serving:** out of scope; separate arm (§6 corpus-scale worry).

## Remaining open questions (not blockers to freeze)

- Whether the T5 currency-claim lint class (L9) is tractable with acceptable precision on real corpora.
- Whether the production memory-line fp rendering (L8) preserves any V3b effect — exploratory sub-condition.
- Claude-family replication (blocked on API key).

---

## RESULTS — registered run (2026-07-17T17:36-06:00, run `20260717T173638-1051b9`)

1,200/1,200 calls, 0 failures, 0 parse failures. Subject `grok-4.20-0309-non-reasoning`, temp 0.

### P1 — staleness (the core result)

| | stale-as-current | sanctioned unknown/as-of | AS_OF reported correctly |
|---|---|---|---|
| **A** raw | 58.0% | 42.0% | 75.3% |
| **B** annotated | 30.7% | 69.3% | 90.7% |
| **Bx** scrambled annotation | 55.3% | 44.7% | 16.7% |
| **C** compiled | **0.0%** | **100.0%** | **100.0%** |

**V1 — ANNOTATION BUNDLE REDUCES STALE-AS-CURRENT.** A−B = 27.3pp ≥ MDD 16.2pp
(headroom precondition passed: M1(A) = 58.0% ≥ 16.2%). The §7 ingest-annotation null
does NOT fire: I1–I3 annotation has real, partial grounding value.
**V0_P1 — ANNOTATION CONTENT IS READ.** |B−Bx| = 24.6pp ≥ 16.2pp, and AS_OF-accuracy
collapsed to 16.7% under the scrambled fresh stamp — behavior tracks the stamp's
*content*, not its mere presence. Annotation is not theater.
**V3a — COMPILATION ENFORCES.** A−C = 58.0pp ≥ 16.2pp; C at ceiling on all three
measures. Deterministic compilation eliminated the 30.7pp residual annotation leaves.

**The headline: presence < binding < enforcement, measured on one axis.**
Raw serving errs 58%; visible typed annotation is read and cuts it to 31%; deterministic
compilation (as-of-qualified rewrite + eligibility enforcement, declarative-only,
reversible span map) takes it to 0. The §7c Outcome-B claim lands in its strongest form:
**annotation organizes and partially binds; only compilation reliably enforces.**

### P2 — authority conflict: NOT TESTABLE (honest headroom failure)

M2(A) = 98.0% first-party wins already at raw — the pre-registered headroom
precondition (≤ 83.8%) FAILED, so V2/V3b/V0_P2 are NOT TESTABLE at N=150 on this
conflict construction. The synthetic conflict was too easy: a fresh, dated, fenced
first-party record beats confident stale foreign prose ~always on this subject, even
raw. This is a *reassuring production observation* but a failed probe design. The
stats-lens blocker (base-rate preconditions) is what kept this from becoming a vacuous
"validated" — working as intended. Follow-up (requires spec amendment, dated): harder
conflict constructions — foreign content fresher/more specific, first-party record
less salient or undated, reversed-authority arm.

**Scope caveats:** one subject model, single-turn, P1 only for the binding gradient;
C's ceiling is on synthetic+real-derived staleness claims, not adversarial content.
