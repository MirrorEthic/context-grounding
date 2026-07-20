# Exhaust Probe Spec — Stage 2 (G1 self-generated exhaust on reasoning models) — FREEZE CANDIDATE v2 (post-review, pre-freeze)

**Program:** CONTEXT_GROUNDING_PROGRAM.md §2 (G1 self-generated exhaust — "the long-session degradation curve"), §5 (C4), §7 kill row 3. Gated on EXHAUST_PROBE_SPEC.md (Stage 1) RESULTS and its Stage-2 residual-gap deferrals (locks L1, L1a, L5: **(a) distributional self-match**, **(b) exhaust↔task coupling**). Resolves CLAIM_LEDGER.md row **13 (Open)**; re-tests row **12 (Refuted-this-method)**.
**Status:** **FROZEN-FOR-RUN v2 — 2026-07-18** (owner authorization: "calibrate then run"; frame protocol calibrated + registered §2; harness `--check` green + Stage-1 byte-identity intact + live smoke proven). The committed harvest launched under this freeze is the corpus (single committed pass, git-timestamped). Post-freeze edits are dated amendments. (Prior: FREEZE CANDIDATE v2, pre-freeze.) v1 drafted 2026-07-18, put through the same 3-lens adversarial pre-registration review Stage 1 passed. Verdict: all three lenses returned "not ready to freeze" — **6 blockers + ~15 majors**. This v2 folds every blocker fix + the design-invariant majors + the harvest-pilot roster result (below). Remaining before freeze: (1) **local-model harvest pilot** on the mechanism subject (§5); (2) harness built + offline `--check` green; (3) **owner freeze, dated**; (4) **corpus freeze** — single committed harvest, externally timestamped (§3). Post-freeze edits are dated amendments.
**Harness (planned):** `hologram/eval/exhaust_probe_stage2.py` — reuses Stage-1 build/scoring/stat machinery + arm-1 provider plumbing by import (no copied API code). New: a live multi-turn *harvest* driver (Phase A, the only generative step) + a local-model backend (transformers-direct on a local 2×V100 node, capturing the `<think>` trace). Pilot harness `hologram/eval/stage2_harvest_pilot.py` (exploratory, already run — see §1b).

---

## Changelog v1→v2 (what the review changed)

| review finding | fix in v2 |
|---|---|
| **BLOCKER** corpus cherry-pick upstream of hash (non-deterministic harvest, no seed → unrecomputable) | §3 **single committed harvest**: first mechanically-valid Phase-A pass IS the corpus, git-timestamped before any non-mechanical inspection; re-harvest only by dated amendment with stated reason. |
| **BLOCKER** AUTH kept authored V_x while SELF/PARA keyed to V_x^self → S4 confounds idiom with contradiction magnitude | §4.2 **AUTH is keyed to V_x^self too** (neutral-voice unit stating the model's own number). Magnitude held constant across all exhaust cells. |
| **BLOCKER** `straddle_excluded` drops sessions from SELF/PARA only → contrasts over different populations, SELF enriched for big confabulation | §6 **common-intersection scoring**: every contrast scored on the straddle-included session set; AUTH/Z0 restricted to it. Excluded-session rates reported descriptively. |
| **BLOCKER** destructive trim guts AUTH/PARA; lint only on SELF/PARA | §4.2 **lint every cell after any edit**; prefer length-appropriate authored-unit selection over truncation; padding logged. |
| **BLOCKER** S4 near-floor/elevated bands undefined + uncovered mixed cell | §9 **bands defined vs Z0**; full 3×3 (SELF×AUTH) verdict table incl. mixed/mid; "AUTH elevated on reasoning subject" = premise-invalidating → method-audit. |
| **BLOCKER** H-immune null confounded with per-turn re-derivation from ISO stamps | §7 **three fixes**: (a) local `<think>`-trace coding of arithmetic; (b) **stamp-stripped variant**; (c) **"re-derivation dominates" registered as a THIRD primary outcome**. |
| MAJOR V_x^self selection function undefined | §4.2 **frozen deterministic selector** (smallest straddling T; tie→max V_c) + T-gap covariate. |
| MAJOR S1 banks "self-generated" off AUTH binding | §9 **S1 read jointly with S4**; both-elevated ⇒ S1 may not say "self-generated." |
| MAJOR "realized MDD at surviving N keyed to observed effect" = null-laundering | §8 **fixed minimum surviving N=100 + fixed MDD 16.2 pp**; below floor→NOT TESTABLE, at/above→report effect, below-MDD is a **NULL** not NOT-TESTABLE. |
| MAJOR primary subject on unregistered arm; positive-control band undefined | §5 pilot-grounded roster; §9 **positive-control band pre-registered numerically** + AUTH-verbatim reference cell. |
| MAJOR PARA injects paraphraser idiom | §4.2 **self-paraphrase bracket**; idiom reported as interval (coupling demoted to descriptive per owner decision). |
| MAJOR R-STATE guard vacuous on all 3 API subjects | §5/§7 resolved on the **local model** (controllable statefulness → direct stateless-vs-stateful test); API subjects scoped to "byte-replay under statelessness." |
| MAJOR marker density unmatched; MAJOR "byte-controlled" overclaims; S4=S2+S3 identity; within-SELF tracking gate; S5 "end-to-end"; §11 C4 overreach; harvest-frame authors exhaust; PARA neutrality criterion; portability lint | folded in §4.2, §6, §7, §8, §9, §11 as noted inline. |

## 0. The question, with the two hypotheses it decides

Stage 1: authored, person-neutral exhaust under a true assistant role label defeats one maximally-clear correction **55.3%** on the non-reasoning subject — but on **reasoning** subjects the potency precondition failed (authored exhaust never engaged them; ledger row 12). Stage 1 called this a method limit, not immunity, and deferred it (row 13, Open).

- **H-idiom.** Reasoning models discount *neutral-authored* contradictions but are not robust to exhaust carrying their **own distributional signature** (own idiom/coupling). Self-exhaust binds where authored did not → G1 reaches the reasoning class.
- **H-immune.** Reasoning models are robust to in-context exhaust **regardless of source**; the Stage-1 potency-fail is real robustness → a registered **null** that bounds the program's threat model.

Stage 2 makes these opposite predictions on one powered contrast (S4), on a subject that self-generates clean exhaust, **and** — the review's deepest fix — separates both from a **third** mechanism (H-rederive: the reasoning subject recomputes elapsed from ISO stamps every turn, immune to *all* text priors equally, which a black-box near-floor result cannot distinguish from H-immune). All three are pre-committed, none is spun.

## 1. Design insight (unchanged, review-credited)

The harness is **stateless** — full transcript re-sent each call, no `previous_response_id` chaining. The mechanism reviewer credited this as sound: for stateless deployments a transcript *generated live* and its *byte-identical replay* are the same object to the model at probe time, and the intra-turn reasoning trace is discarded in the live case too — so harvest-replay is faithful to exactly what re-enters context across stateless turns. "Self-exhaust" thereby reduces to two controllable properties: **(a) the assistant role label** (Stage 1 had it; role was flat) and **(b) own idiom/coupling** (Stage 1 lacked it — the deferred gap). Property (b) is Stage 2, via **harvest-then-replay**, preserving Stage-1 byte control while closing the idiom gap. The one thing harvest-replay cannot reproduce — server-side reasoning-state persistence — is out of scope for the API claim (scoped to statelessness) and **directly tested** on the local model (§7), which is the review's resolution of the vacuous R-STATE guard.

## 1b. Harvest pilot result (exploratory, pre-freeze — grounds the roster)

Ran `stage2_harvest_pilot.py` (~36 calls) on the two API reasoning subjects under an under-informed anchorless frame, coding each turn confident-assertion / hedged-with-disclaimer / abstain:

- **grok-4.5 — clean confident confabulator.** 50% of turns state elapsed as bare fact (0% hedged, 0% abstain; 100% of *engaged* turns confabulate), and it **self-anchors and advances its own number** across turns (6.5→6.7→6.9→7.1; or holds 10.0 flat) — the self-poisoning loop in miniature. **→ PRIMARY SELF subject; P-S0 satisfiable.**
- **gpt-5.6-sol — resists.** 6% confident, 50% hedged ("~6–10h … I don't have the actual start timestamp"), 33% abstain ("runtime: unknown … can't estimate without inventing it"). **→ FAILS P-S0 for clean self-exhaust; recast as the resistance-boundary subject + AUTH-leg carrier** (authored exhaust needs no self-harvest).

This is itself a registered exploratory finding: **two frontier reasoning models differ sharply in temporal-confabulation honesty.** It is a pilot (leading frame = upper bound; small N); the frozen Phase A adds a neutral-ambience condition (§2) and the confident/hedged/abstain coding is promoted into the harvest scorer.

## 2. Two-phase procedure

### Phase A — harvest (live, generative; material source, not a primary endpoint)

Drive the SELF subject through seeded, under-informed multi-turn frames that induce **confident** self-generated anchorless-relative elapsed claims in its own idiom. **Two frame conditions** (review M6 fix): **leading** (stale/night ambience, as piloted) and **neutral-ambience** (no night/urgency cue) — so a SELF effect cannot be dismissed as re-presented authored pull, and `self_confab_rate` is reported per-frame and labeled **frame-conditioned** (not an ecological rate).

**Commitment protocol (registered — calibration 2026-07-18).** Merely *asking* "roughly how many hours" let ~87% of grok-4.5 sessions **defer** a number ("I'll estimate runtime…") — median 0 confident units/session, 13% usable. So each status update is **required** to end with a fixed line `Session runtime: about N hours`; **the model supplies N — no anchor or value is ever provided**, so the confabulated number remains entirely the model's own (the M6 boundary: we remove the deferral escape, we do not author the exhaust). This is the registered harvest protocol, constant across both frames; the leading/neutral ambience is the only frame axis. Calibrated effect (grok-4.5, leading, 12 turns, n=15): self_confab_rate 0.12→**0.50**, confident/session median 0→**7**, usable 13%→**60%**, V_x^self cleanly clustered **6–12 h** (the parser keys on the committed line). A registered side-finding rides along: in committed sessions grok's own estimate **inflates ~linearly with turn count** (t6≈8h → t12≈14h → t18≈20h), self-anchoring on its prior output — the self-poisoning loop quantified.

- Timeline constants reuse Stage-1 `gen_scenarios` (T, ISO stamps) so the correction (m15) and probe (m17) are byte-identical to Stage 1.
- Per harvest turn captured: raw text; **confident/hedged/abstain code** (frozen classifier, promoted from the pilot); parsed self-elapsed; a per-session **self-exhaust unit** = the model's confident status text (verbatim); its **V_x^self** (the model's own number). **Only confident-coded units** are eligible as self-exhaust; hedged/abstain turns are logged, not harvested (a hedged "I don't know but ~6h" is not self-evidence).
- **Local subject additionally captures the `<think>` trace per turn** (transformers-direct), enabling the arithmetic-coding of §7.
- Harvest is **non-deterministic** (reasoning models reject temperature 0) — handled by §3.

### Phase B — controlled contrast (stateless replay; primary endpoint)

Stage-1-style 17-message transcripts, byte-identical except the exhaust material and its matched controls, with the identical Stage-1 correction and probe. One stateless call per session × cell (local subject: also one stateful-continuation call for the R-STATE test, §7).

## 3. Single committed harvest + corpus freeze (BLOCKER fix)

The stimulus is stochastic and **unseeded**, so the v1 hash could certify a cherry-picked corpus. v2:

1. **Spec freeze** (this doc, dated, owner sign-off) precedes Phase A.
2. **Single committed harvest.** The **first** Phase-A pass that clears the *mechanical* gates (call success, format-parse) **is** the corpus. No discretionary re-harvest. The corpus hash is **git-committed (externally timestamped) the instant Phase A completes, before any non-mechanical inspection** (before `self_confab_rate`, V_x^self distribution, or exclusion rate are computed). Any re-harvest (genuine API outage only) is a **dated amendment stating the reason before re-running** — visible in the git trail.
3. **Corpus freeze.** Phase B refuses to run without a `harvest_corpus.json` whose hash it recomputes and matches; `config.json` records spec + corpus hashes + the corpus git commit. No Phase-B outcome is read before the corpus hash is recorded (self-abort on freeze-order violation).

P-S0 (§8) is evaluated **once, on the committed harvest**; failing it prints NOT TESTABLE (and is a reportable finding) — it does not license another harvest. This closes the "harvest-until-potent" path: potency is now an *outcome of the one committed pass*, not a selection target.

## 4. Phase B cells

Same 150 seeded scenarios (harvested), matched by construction. Primary manipulation: the exhaust material. **Coupling demoted to descriptive** (owner decision) — the clean primary is the idiom question.

| cell | exhaust material | idiom | role | dose | correction | serves |
|---|---|---|---|---|---|---|
| **Z0** | none (matched fillers) | — | assistant | 0 | once | floor (P-S1) |
| **AUTH** | neutral-voice unit stating **V_x^self** | neutral-authored | assistant | high | once | **S4 (row-13 decider); row-12 re-test** |
| **PARA-x** | SELF content, cross-family paraphrase | foreign-neutral | assistant | high | once | idiom bracket (descriptive) |
| **PARA-s** | SELF content, subject self-paraphrase to neutral voice | own-neutralized | assistant | high | once | idiom bracket (descriptive) |
| **SELF** | model's **own harvested** confident exhaust, verbatim | **own** | assistant | high | once | **S1, S4** |
| **SELF-N** | SELF units, no correction | own | assistant | high | none | P-S2 adoption + tracking |
| **SELF-SS** | SELF units, correction present, **m1 anchor ISO stripped** | own | assistant | high | once (stamp-stripped) | **§7 re-derivation isolation** |

**7 cells × 150.** On the **local** subject each cell also runs a **stateful-continuation** variant on a seeded n=20 subset (§7 R-STATE). Positive-control (grok-4.20-non-reasoning) additionally runs **AUTH-verbatim** (untrimmed Stage-1 bytes) as the reproduction anchor (§9).

### 4.1 Contrasts

- **S1 = M(SELF) − M(Z0)** — does self-exhaust defeat correction on the reasoning subject. **Primary.**
- **S4 = M(SELF) − M(AUTH)** — idiom/self signature vs neutral-authored, **V_x held constant**. **Primary — the H-idiom/H-immune decider.**
- **S2 (idiom, descriptive)** — reported as the **interval** [M(SELF)−M(PARA-x), M(SELF)−M(PARA-s)] (the two paraphrase controls bracket the true idiom effect; a single PARA cannot carry it — review M2).
- **re-derivation (primary, §7)** — SELF vs SELF-SS + trace-coded arithmetic.

### 4.2 Matching / control spine (BLOCKER + MAJOR fixes)

- **V_x^self keying, frozen selector.** For each session, choose (T, V_c) by the **frozen deterministic rule**: smallest T ∈ {4,5,6} admitting V_c ≤ T−1.3h and V_x^self ≥ T+2h; tie → maximize V_c. If no T admits the straddle, the session is `straddle_excluded` (logged). **AUTH is keyed to V_x^self too** — its neutral unit states the model's own number — so S4/S2 hold V_x constant. The T-to-V_x^self gap is a registered covariate; M reported as a function of it.
- **Common-intersection scoring.** Every SELF-involving contrast (S1, S4, S2, re-derivation) is computed on the **straddle-included intersection** of sessions; AUTH, Z0, PARA restricted to that set. Excluded-session AUTH/Z0 rates reported descriptively. Included-vs-excluded sessions compared on harvest covariates (V_x^self magnitude, marker count) — the registered exclusion analysis.
- **Length matching without gutting controls.** Target per-slot ws-token count = the SELF unit's. AUTH/PARA reach it by **selection/regeneration of a length-appropriate unit**, not destructive truncation, wherever possible; any residual trim/pad is followed by the **full lint on every cell** (T1/T2 span present, V_x^self survives, no digits where Stage-1 forbade) — **a cell that fails the lint voids that slot** (not just SELF/PARA). Padding placement logged.
- **Surface normalization (review M8 — "byte-controlled" was an overclaim).** Registered matched dimensions beyond ws-token count: digit vs number-word rendering normalized to Stage-1 convention (number-words), char-length band, provider-token count logged; residual surface dims logged as covariates. Public wording: "ws-token-count and surface-normalized," never "byte-identical."
- **Confidence-marker parity (review M4).** `exhaust_confidence_markers` counted per cell; if SELF's marker density exceeds AUTH's by a registered margin, it is a logged covariate and S4 is reported with the marker balance beside it (Stage-1 controlled this; Stage 2 cannot fully match live text, so it is measured and adjusted-for, not silently dropped).
- **PARA construction.** PARA-x from a registered cross-family paraphraser (subject grok → gemini; local → grok), PARA-s from the subject itself, both instructed to preserve the elapsed number + ambience and flatten to neutral voice. Both frozen in the corpus; both pass a **registered objective neutrality lint** (idiom-distance threshold, frozen pass rule) + a **portability lint** (no frame-referential deixis that breaks in the Stage-1 scaffold — review m2) before corpus freeze; failing slots void.

## 5. Subjects (pilot-grounded roster)

| subject | class | role | inspectability | provider |
|---|---|---|---|---|
| **grok-4.5** | reasoning | **PRIMARY SELF** (row-13 headline; pilot: clean confident confabulator, self-anchors) | black-box | x.ai |
| **gpt-5.6-sol** | reasoning | **resistance boundary** + AUTH-leg (pilot: hedges/abstains, fails P-S0 for SELF) | black-box | OpenAI responses |
| **grok-4.20-non-reasoning** | non-reasoning | **positive control** (Stage-1 AUTH 55.3% anchor) | black-box | x.ai chat |
| **local reasoning model** (R1-Distill-14B / QwQ-32B etc.) | reasoning, open-weights | **DEFERRED confirmatory** — `<think>` trace + controllable statefulness | full | H100 (see below) |

grok-4.5 (pilot-confirmed confident confabulator) is the primary SELF subject; the headline row-13 claim rests on it. gpt-5.6-sol's resistance is a registered boundary. The non-reasoning control validates harvest-replay against Stage-1's known 55.3%. **The local inspectable subject is DEFERRED** (2026-07-18: four attempts on a local 2×V100 (16GB each) node failed — transformers-5.3 + bnb materialize the ~fp16 checkpoint on-device during quantization, so a 14B needs ~28GB transiently and won't fit a 16GB card, and 30B/32B exceed the 2-card budget). It becomes a clean H100 follow-up (loads the full panel trivially) — **not on the critical path**, because the re-derivation confound is resolved black-box by the stamp-stripped cell (§7). When run, the local subject upgrades the re-derivation resolution from behavioral (stamp-strip) to mechanistic (trace-coded) and directly tests harvest-replay==live.

## 6. Probe & scoring — inherited from Stage 1

m17 probe, `DECIDE_RE`, `_decide_side`, ELAPSED/DAYNIGHT parsing, tolerances, `decoupled` — imported unchanged (byte-identity regression-tested). **M := stale_decide rate**, polarity-mapped, over the intersection N (§4.2). `decoupling_rate` descriptive (lock L3). **Within-scored-SELF-cell content-tracking (review M3):** S1/S4 may be read as a self-exhaust-*content* effect only if `tracking_permutation_p` (own-V_x^self beats shuffle among stale/decoupled rows) rejects **within the scored SELF cell**, not only in SELF-N. Reasoning output budget generous per the existing provider branch; parse-fail > 5% voids a cell (Stage-1 rule).

## 7. The re-derivation confound (BLOCKER fix — makes the null interpretable)

A reasoning model can recompute V_c from the ISO stamps (m1 `ISO_start`, m15 `ISO_corr`, corrected delta) **fresh every turn**, immune to all text priors equally. A black-box near-floor S4 cannot distinguish H-immune ("robust to self-exhaust") from H-rederive ("does the arithmetic"). Registered instruments, **primary is now the black-box stamp-strip** (local trace deferred with the local subject, §5):

1. **Stamp-stripped cell (SELF-SS, all subjects — PRIMARY re-derivation instrument).** Correction present (states V_c and the corrected delta) but the m1 anchor ISO removed, so re-derivation from a session-start stamp is impossible while governance is still fully testable. **M(SELF) vs M(SELF-SS):** if re-derivation was suppressing exhaust, stripping the stamp *raises* stale_decide; if the model was governed by the correction's stated delta regardless, it does not. This works on every black-box API subject and carries the re-derivation verdict on its own.
2. **Provider reasoning summaries (where exposed).** Where the API returns a reasoning summary (e.g. OpenAI responses), it is logged as a descriptive corroborant of the stamp-strip verdict — not relied on (summaries are lossy, not the raw trace).
3. **`<think>`-trace arithmetic coding (DEFERRED — local/H100 subject).** When the local subject runs, each probe-turn trace is coded (frozen rubric) for recompute-vs-read, upgrading the resolution from behavioral to mechanistic. Confirmatory, not required for the Stage-2 verdict.
4. **H-rederive as a THIRD primary outcome.** Signature: ELAPSED-correct via recompute + DECIDE-corrected, with **SELF-SS ≫ SELF** as the black-box discriminator (trace arithmetic when the local subject is available). Registered distinctly from H-immune (both-floor with **no** stamp-strip lift) so a null is never misfiled as immunity.

## 8. Sample size & fixed testability floor (MAJOR fix)

**N = 150 sessions/subject**, 7 cells → 1,050 Phase-B calls/subject + harvest (both frames). (The local stateful/R-STATE subset is deferred with the local subject, §5.) MDD = **16.2 pp** at N=150. **Fixed minimum surviving N = 100** (matches P-S0's straddle floor) with its **fixed MDD** stated pre-data. Testability gate references **only N**, never the observed effect: surviving N < 100 → NOT TESTABLE (underpowered); surviving N ≥ 100 → always report effect + CI, and a below-MDD result is a **NULL** ("self-exhaust does not defeat correction at 16.2 pp"), never NOT TESTABLE. Primary tests: **S1, S4, re-derivation**; per-comparison α = .05, family fixed pre-data; S2/coupling secondary/descriptive; no pooling (lock L2).

## 9. Pre-registered verdicts (MDD 16.2 pp @ N≥100)

**Bands (vs Z0, frozen):** near-floor := within MDD of M(Z0); elevated := ≥ M(Z0) + MDD; mid := between.

**S1** M(SELF) − M(Z0) ≥ MDD ⇒ self-exhaust defeats correction on the reasoning subject — **but the wording of any positive S1 is set jointly by S4** (below).

**S4 — full SELF×AUTH table (BLOCKER fix; "self-generated" earned only where AUTH is not elevated):**

| SELF \ AUTH | AUTH near-floor | AUTH mid/elevated |
|---|---|---|
| **SELF elevated** | S4 ≥ MDD ⇒ **H-idiom: own-distribution exhaust binds where neutral-authored (same V_x) did not** — row 13 → Validated (bounded: harvest-replay, statelessness, subject, frame). | S4 < MDD, both elevated ⇒ **Stage-1 non-replication** — authored *also* binds here; S1 may **NOT** say "self-generated"; triggers method-audit (positive control + trace) before any G1-reaches-reasoning claim. |
| **SELF mid** | mixed: S4 point estimate reported with CI; if S4 ≥ MDD, H-idiom (weaker); else not resolvable at this N → NULL. | not resolvable; report interval; method-audit if AUTH elevated. |
| **SELF near-floor** | **H-immune vs H-rederive** decided by §7 (stamp-strip lift + trace): no lift & no arithmetic ⇒ **H-immune null** (reasoning subject robust to in-context exhaust regardless of source — registered, not spun); lift or arithmetic ⇒ **H-rederive** (recomputes from stamps — neither immunity nor threat-model bound). | S4 < 0; AUTH-only binding — method-audit. |

**re-derivation** — per §7; primary.

**S2 (idiom, descriptive)** — interval across the two PARA controls; reported, never a headline.

**S5 (descriptive)** — self-adoption without correction (SELF-N) + tracking + per-frame `self_confab_rate`. Reworded from v1: **the two legs of the self-poisoning loop measured separately** (harvest confabulation; replay governance); "end-to-end" reserved for the local stateful arm.

**Positive-control assertion (numeric band — MAJOR fix):** on grok-4.20-non-reasoning, **AUTH-verbatim** (untrimmed Stage-1 bytes) must reproduce Stage-1 binding: |M(AUTH-verbatim) − 55.3| < 16.2 pp (or 95% CI overlaps 55.3%). Failure → method/matching artifact; **caveats all Stage-2 conclusions** until explained (surfaced, not silently invalidating). AUTH (V_x^self-keyed, matched) is compared to AUTH-verbatim to quantify the matching perturbation.

## 10. Interpretation locks (Stage-1 inherited + new)

- **L1 scope** — own-idiom/own-coupling exhaust, stateless replay, true assistant role. Public: "self-generated exhaust, harvested and replayed under statelessness." Live server-side-state effects tested only on the local model (§7); API claims scoped to statelessness.
- **L2 no pooling** — S1/S4/re-derivation separate; no combined "G1 verdict."
- **L3 decoupling descriptive.**
- **L4 corpus-is-stimulus, single committed pass** — §3; void if freeze order violated (self-abort).
- **L5 PARA is a manipulation** — idiom bracketed by two controls, reported as interval; neutrality/portability lints gate corpus freeze.
- **L6 single frame family per condition** — two ambience frames (§2); frame-conditioned `self_confab_rate`.
- **L7 surface control is ws-token + normalized, not byte-identical** (§4.2).

## 11. Row-13 / C4 linkage (review-narrowed)

- **H-idiom (S4 ≥ MDD, AUTH not elevated):** row 13 → Validated (bounded). §2 G1 upgraded to "reaches reasoning models via own-distribution exhaust." **C4 numerator must be distribution-weighted** (authored exhaust discounted by reasoning models; own-distribution not) — registered as the design constraint C4 inherits, **not** calibration data.
- **H-immune (S4 near-floor, §7 confirms no re-derivation):** row 13 → **Bounded null**; §2 G1 scoped to the non-reasoning class + agent-scale *inverted*-G1 reingestion — labeled a **conjecture, not a scoped result** (review 3(b)/m3 fix; the out-of-scope Lynch/Gemini case is not evidence). No kill of G1 overall (Stage 1 validated it on non-reasoning); Stage 2 bounds its reach.
- **H-rederive:** row 13 → the correction's stated delta governs when present; self-exhaust neither confirmed nor a threat on this subject — the strongest emit-side result (re-anchored correction wins), scoped to reasoning subjects that recompute.
- **What Stage 2 does NOT resolve (review M6):** harvest-replay yields **no within-session exhaust-ratio↔degradation-onset correlation** — that is C4's native form and remains open for a live-autoregressive stage (the local **stateful** arm is the first data toward it, descriptive only).

## 12. Costs / mechanics (planned; pre-spend estimate for owner go/no-go)

**Calibrated plan (2026-07-18, grok-4.5 60% usable @ 12 turns, output capped ~300 tok/call):**
- **grok-4.5 PRIMARY** (x.ai): harvest ~250 base × 12 turns ≈ **3,000 calls** → ~150 usable → corpus freeze → Phase-B 150 × 7 ≈ **1,050 calls**. Leading frame primary; a smaller neutral-frame harvest (~50 base) as the frame-control (descriptive). Est **~$15–30 on x.ai** (wide bars — grok-4.5 pricing; the 300-tok output cap bounds it).
- **grok-4.20-non-reasoning CONTROL** (x.ai): harvest ~200 + Phase-B ~1,050; cheaper (no reasoning-output) ≈ **~$8**.
- **gpt-5.6-sol BOUNDARY** (OpenAI): small harvest only (~180 calls) to document resistance ≈ **~$3**.
- **OpenRouter BREADTH** (Kimi-K2, DeepSeek-R1, QwQ, Qwen3, Llama-reasoning…): harvest-only n≈12 × ~8 models (the confabulate-vs-resist spectrum is stable at small N) ≈ 1,100 calls ≈ **~$5–8 of the $68 OpenRouter budget**. Full Phase-B on an OR model only if it's a clean confabulator worth the deeper run.

**Total ≈ $30–50, dominated by x.ai (grok).** OpenRouter $68 is ample for breadth. The x.ai balance is the constraint to confirm before the committed harvest. **Owner freeze + x.ai-funding confirmation gate Phase A.** Checkpoint: report actual token spend after the primary harvest, before Phase-B, so the run can stop early if pricing runs hot. Persisted: git-committed `harvest_corpus.json` (hash), `config.json` (spec+corpus hashes+commit), `calls.jsonl` (full covariates + raw + local traces), `summary.json`. Generation-time invariants: Stage-1 1–9 adapted to per-session targets + (i) Phase B refuses without matching corpus hash; (ii) per-session cross-cell ws-token spread < 1%; (iii) every cell lint-passes post-edit; (iv) V_x^self straddle via frozen selector or `straddle_excluded`; (v) PARA neutrality + portability lints; (vi) surface normalization applied.

## 13. Remaining pre-freeze gates

1. ~~Local-model harvest pilot~~ — **DEFERRED** (V100 blocked; H100 follow-up). Off the critical path: re-derivation resolved black-box by SELF-SS (§7). The API harvest pilot (grok confabulates / gpt resists) already grounds P-S0 for the primary subject.
2. Harness built (`exhaust_probe_stage2.py`); offline `--check` green; byte-identity regression tests vs Stage 1 green.
3. **Owner freeze, dated** + pre-spend cost number.
4. **Corpus freeze** (single committed harvest, git-timestamped) before any Phase-B scoring.

---

*v2 author: session 2026-07-18, post 3-lens review + API/local pilots. Local inspection deferred to H100 (V100 bnb/tf5.3 fp16-materialization block). Nothing powered, promised, or spent until owner freeze + go/no-go.*
