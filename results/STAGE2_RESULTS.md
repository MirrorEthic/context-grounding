# Stage 2 — self-/authored-exhaust on reasoning models (results)

**Program:** `docs/CONTEXT_GROUNDING_PROGRAM.md` §2 (G1 — self-generated exhaust, "the long-session
degradation curve"), §5 (C4). Gated on Stage 1 (`specs/EXHAUST_PROBE_SPEC.md`).
**Spec:** `specs/EXHAUST_PROBE_STAGE2_SPEC.md` (frozen v2, pre-run).
**Status:** interim. All numbers below are from post-freeze runs; run receipts under `results/runs/`.

Stage 1 showed a single clear anchored **correction** can be defeated by enough **authored exhaust**
(the F4 decoupling) on one non-reasoning model. Stage 2 asks whether that reaches **reasoning
models** and **self-generated** exhaust, and — using locally-served open-weights models — *watches
the mechanism* in the `<think>` trace.

## Method (one paragraph)

A doctored session carries confident but wrong elapsed-time claims (authored "exhaust"), then a
clear anchored correction, then a decision gated on the true elapsed. Cells: **Z0** (no exhaust),
**AUTH** (exhaust + correction), **AUTH-N** (exhaust, *no* correction — the potency control),
**SELF-SS** (correction present but the session-start stamp stripped, so re-derivation from start is
impossible). `M` = the stale-decision rate (acted on the wrong value). Breadth runs go through the
provider APIs; the **mechanism** run serves open-weights reasoning models locally (vLLM, TP=2 on
2× V100) so the reasoning trace is visible. N=60/cell (breadth), N=80/cell (mechanism); MDD 25.6pp
(breadth, N=60).

## Result 1 — the correction-defeat (decoupling) is grok-4.20-non-reasoning-**specific**

Authored-exhaust breadth, 7 models / 5 labs (run `breadthA_20260719T014452`):

| model | Z0 | AUTH (exhaust+correction) | AUTH-N (exhaust, no correction) | verdict |
|---|---|---|---|---|
| **grok-4.20-0309-non-reasoning** | 0% | **51.7%** | **100%** | **DECOUPLES** |
| kimi-k2 | 0% | 0% | 78.3% | re-grounds |
| deepseek-chat | 3.3% | 0% | 96.7% | re-grounds |
| llama-3.3-70b-instruct | 0% | 0% | 65.0% | re-grounds |
| grok-4.5 | 0% | 0% | 13.3% | re-grounds* |
| deepseek-r1 | 0% | 0% | 13.3% | re-grounds* |
| qwen3-30b-a3b-thinking | 0% | 0% | 1.7% | re-grounds* |

Only **grok-4.20-non-reasoning** keeps acting on the stale value once the correction is present
(51.7%), and it is the model whose authored-exhaust potency is highest (AUTH-N 100%). Every other
model with **testable** potency (kimi-k2, deepseek-chat, llama-70b) drops to **0% under one clear
correction**. The earlier "reasoning re-grounds / non-reasoning decouples" reading (from two grok
anchors) is **wrong** — the split is model-specific, not a class split.

\* **Load-bearing caveat.** grok-4.5, deepseek-r1, and qwen3-thinking have AUTH-N **below MDD**
(1.7–13.3%): the authored exhaust barely binds them even *without* a correction, so their "AUTH=0"
is **not a clean re-ground** — there was little to re-ground from. The clean re-ground claim rests
on the high-potency models (kimi-k2, deepseek-chat, llama-70b) and the mechanism run below.

## Result 2 — the mechanism: re-grounding is active **re-derivation**, visible in the trace

Local open-weights reasoning models (vLLM TP=2), `<think>` visible, N=80/cell (run receipts +
annotated exemplars in `results/local_traces/`):

| model | AUTH stale (corrected) | AUTH-N stale (no correction) | traces recomputing from stamps |
|---|---|---|---|
| DeepSeek-R1-Distill-Qwen-14B | 0% | 87.5% | 85% |
| DeepSeek-R1-Distill-Qwen-7B | 0% | 81.2% | 100% |

Both have **real potency** (AUTH-N 81–88%) and both go to **0% under correction** — and the trace
shows *why*: the model **re-derives elapsed time from the in-context anchored stamps** and decides
on the corrected value. Re-grounding is active recomputation, not passive deference. See
`results/local_traces/TRACES.md` for annotated AUTH (re-derives → honors) vs AUTH-N (adopts the
stale value) exemplars. (SELF-SS, stamp stripped, also held at 0% — models honor the correction's
*stated* value even when they cannot re-derive from session start.)

## Result 3 — Claude home turf

Same probe on the Claude family (run `breadthA_20260719T123724`):

| model | AUTH | AUTH-N | note |
|---|---|---|---|
| claude-haiku-4-5 | 0% | 51.7% | clean re-ground (real potency → 0) |
| claude-opus-4-8 | 0% | 10.0% | re-grounds* (low potency) |
| claude-sonnet-5 | 0% | 0.0% | re-grounds* (no potency to test) |
| claude-fable-5 | — | — | **refuses** the doctored transcript (100% of calls) |

Haiku is a clean re-ground. Opus/Sonnet show the low-potency caveat again. **Fable 5 refuses** the
prefilled-assistant doctored transcript outright (`stop_reason: refusal`) — a boundary case, not a
re-ground; worth noting as its own behavior.

## What Stage 2 establishes (bounded)

- The Stage-1 **correction-defeat is not general** — it is essentially **grok-4.20-non-reasoning-
  specific** across 11 models / 6 labs tested here.
- Where authored exhaust has **measurable potency**, a **single clear anchored correction re-grounds
  the model to ~0% stale** — reasoning and non-reasoning, across labs.
- The re-grounding **mechanism is re-derivation from the anchored stamps** (seen directly in local
  traces), which is exactly why *typed, anchored* emission is the lever: it gives the model something
  to recompute from.
- Bound: many models have low authored-exhaust potency under this method, so several "0%" cells are
  not clean re-grounds. Self-generated (not authored-replay) exhaust at true agent scale, and the
  potency ceiling, remain open.

## Value axis — registered open direction (results forthcoming)

A separate pre-registered experiment (`specs/VALUE_ANCHOR_BRIDGE_SPEC.md`) applies the same typed,
authority-stamped record to the **value** axis — Betley et al.'s *Value Leakage* Donation-Bet
paradigm — to test whether typed authority reduces value leakage **beyond matched untyped content**
(a control their Appendix D.7 motivates). This is published here as a **registered method; results
are held pending a powered cross-model run** and are not reported in this release.

## Related work

- **Betley, Treutlein, Dubiński, Mayne, Gałązka, Warncke, Sztyber-Betley, Evans**, *Value Leakage*
  (arXiv:2607.14345, 2026) — the value axis (trained-prior leakage) this program's bridge connects to.
- **Kwon**, *Reclaim Evaluation* (arXiv:2606.25449) and *They Infer What You Meant* (arXiv:2607.03598)
  — prior work establishing the correction/re-derivation and represent-vs-govern results (see
  `docs/CONTEXT_GROUNDING_PROGRAM.md` §3).
- **Lynch et al.**, *Agentic Misalignment in Summer 2026* — typing works/has-a-floor; G1 at agent scale.

## Reproduce

`hologram/eval/exhaust_probe_stage2.py` (harvest/replay + cells), `stage2_mechanism_probe.py`
(trace-coded AUTH/SELF-SS/AUTH-N), `stage2_breadth_authored.py` (breadth), `stage2_trace_showcase.py`
(trace exemplars), `value_anchor_bridge.py` (value-axis, registered). Run receipts: `results/runs/`.
