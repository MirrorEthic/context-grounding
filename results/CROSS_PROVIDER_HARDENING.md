# Cross-Provider Hardening — Consolidated Results

**Compiled 2026-07-17T23:26-06:00.** All runs are exploratory replications of the
frozen probe designs (`GROUNDING_PROBE_SPEC.md`, `INGEST_PROBE_SPEC.md`,
`EXHAUST_PROBE_SPEC.md`). **Registered subject stays `grok-4.20-0309-non-reasoning`**;
every other model is a labeled replication, not a registered endpoint. N=150/cell,
MDD 16.2pp. Raw rows in `.hologram/eval/*_runs/`.

Providers: **xAI** (grok), **OpenAI** (gpt-5.6-sol), **Google** (gemini, partial —
free-tier rate-gated, dropped to nice-to-have). "reason?" = reasoning-default.

---

## Arm 1 — temporal binding (missing structure, single-turn)

Condition A = current emitter (bare deltas, no anchor). B = E1–E4 (ISO+typed+NOW-last).
C = scrambled-anchor null. Cell values: **A error% / B error% / C anchor-consistent%**.

| subject | reason? | A err | B err | C anchor-read | verdict |
|---|---|---|---|---|---|
| grok-4.20-non-reasoning *(registered)* | no | 100 | 0 | 65.3 | V1+V2 pass |
| grok-4.5 | yes | 100 | 0 | 100 | replicates |
| grok-4.20-multi-agent | yes | 100 | 0 | 100 | replicates |
| gemini-3.1-pro *(descriptive)* | yes | 100 | 0 | 100 | replicates |
| **gpt-5.6-sol** | yes | 100 | 0 | 100 | replicates |

**MODEL-GENERAL.** Missing temporal structure → 100% confabulation on *every* model
including all frontier reasoners; anchored+typed emission → 0% on every model; scrambled
anchors are tracked (anchors are read, not decoration). Zero abstentions across all A
conditions. *(Nuance: gpt-5.6-sol resolved the year-free tick 99.3% correct vs
grok-non-reasoning's 16% — the year-free-tick defect hurts weaker models more, but the
missing-delta-anchor confabulation is universal.)*

## Arm 2 — ingest staleness (foreign stale content), P1

Cell values: **stale-as-current%** for A raw / B annotated (I1–I3) / C compiled.

| subject | reason? | A raw | B annotated | C compiled | annotation effect | compilation |
|---|---|---|---|---|---|---|
| grok-4.20-non-reasoning *(registered)* | no | 58.0 | 30.7 | 0.0 | partial (−27.3pp, sig) | enforces |
| grok-4.5 | yes | 50.0 | 0.0 | 0.0 | **full** (−50pp) | enforces |
| **gpt-5.6-sol** | yes | 41.3 | 30.0 | 0.0 | **null** (−11.3pp, < MDD) | enforces |

**Foreign stale content binds on every model** (unlike self-exhaust — see Arm 3). The
scrambled-annotation null (Bx) collapses AS_OF-accuracy to ~0 on all three → the
annotation *is* read. **Annotation's behavioral binding is wildly model-dependent**
(full / partial / null across the three). **Deterministic compilation drove staleness
to 0% on all three.** P2 authority-conflict was NOT TESTABLE on every subject (100%
first-party base rate — fresh dated records already dominate; failed probe design, not
a null result).

## Arm 3 — self-exhaust (authored, multi-turn), G1 Stage 1

Cell values: decoupling / F4 outcome, plus the pre-registered potency precondition.

| subject | reason? | authored exhaust bound? | headline | verdict |
|---|---|---|---|---|
| grok-4.20-non-reasoning *(registered)* | no | **yes** | **55.3% decoupling** (dose 0→16→55) | V1 supported |
| grok-4.5 | yes | no (potency 2.7%) | — | NOT TESTABLE (P-H2) |
| **gpt-5.6-sol** | yes | no (potency 0%) | — | NOT TESTABLE (P-H2) |

**Authored self-exhaust engages non-reasoning only.** Both reasoning models failed the
potency precondition — the authored (foreign-idiom) exhaust never bound, so the battery
is NOT TESTABLE, a **method ceiling, not model immunity.** The decoupling result (reports
the corrected fact 100% correctly while ruling on the contradiction 55.3% of the time)
stands on the registered surface. Whether it reaches reasoners requires **Stage 2**
(the model's *own* self-generated exhaust, its real idiom) — now the load-bearing
next experiment, with cross-vendor n=2 evidence for why.

---

## The unified claim (what all three arms triangulate)

1. **Reasoning models are NOT immune to grounding failure.** They fail Arm 1 (missing
   structure) at 100% and Arm 2 (foreign staleness) at 41–50%. Robustness is not the story.
2. **What varies is the emit-side fix's reliability across models.** Anchoring (Arm 1)
   works universally. Annotation (Arm 2) is model-dependent (full → null). Only
   **deterministic external transformation — anchored emission and compilation — holds
   on every model and every arm tested.**
3. **What reasoners specifically resist is *authored* self-exhaust** (Arm 3) — a method
   limit that Stage 2 exists to overcome.

This is the enforcement thesis, cross-provider hardened: **retrieval ≠ grounding, recall
≠ control; model-cooperation-dependent grounding (annotation binding, and by extension
self-report) is variable, while deterministic compilation/enforcement is the lever that
reliably governs behavior across models and providers.**

**Honest bounds:** single-turn (Arms 1–2) and Stage-1 authored replay (Arm 3);
N=150/cell; the 55.3% decoupling is registered on one surface and did not replicate to
reasoners *by this method*; P2 and Arm-3-on-reasoners are open. Report the zeros and the
NOT-TESTABLEs — they are the boundary conditions that make the claim defensible.
