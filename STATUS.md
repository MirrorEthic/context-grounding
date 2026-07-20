# STATUS — Context Grounding (interim)

**As of 2026-07-18. Interim release: the boundary is the point — read this first.**

This repository publishes **completed, pre-registered** work. It deliberately does
**not** wait for the full battery to close. Below is exactly what is resolved and what
is open. Nothing here is upgraded beyond what its evidence supports.

## Complete (pre-registered, run, reported with nulls)

- **Arm 1 — temporal binding.** Missing temporal structure → systematic confabulation;
  anchored+typed emission fixes it; scrambled anchors redirect it (anchors are read).
  **Model-general:** replicated across 5 subjects / 3 providers, reasoning + non-reasoning
  (grok-4.20-non-reasoning [registered], grok-4.5, grok-4.20-multi-agent, gemini-3.1-pro,
  gpt-5.6-sol). Condition A 100% error → Condition B 0% on every subject. Zero abstentions.
- **Arm 2 — ingest staleness (P1).** Foreign stale content is treated as current; **annotation
  binding is model-dependent** (full on grok-4.5, partial on grok-non-reasoning, null on
  gpt-5.6-sol); **deterministic compilation drives it to 0% on all three.** P2 authority-conflict
  reported **NOT TESTABLE** (base-rate precondition failed — not spun into a result).
- **Arm 3 — self-exhaust (G1 Stage 1), registered surface.** Six confident contradictory
  restatements defeat one corrected record **55.3%** of the time on grok-4.20-non-reasoning,
  while the model reports the corrected fact with **100% accuracy** (the decoupling result).
- **Arm 3 — Stage 2 (authored-exhaust breadth + mechanism).** Across 11 models / 6 labs, the
  correction-defeat is **grok-4.20-non-reasoning-specific** — every other model with measurable
  authored-exhaust potency re-grounds to **~0% under one clear anchored correction**. Local
  open-weights traces show the mechanism directly: **re-derivation from the anchored stamps**
  (r1-7b 100% / r1-14b 85% of traces recompute). Claude home turf: Haiku re-grounds cleanly,
  Fable 5 refuses the doctored transcript. Bound: many models have low authored-exhaust potency,
  so several "0%" cells are not clean re-grounds — stated as such. See `results/STAGE2_RESULTS.md`.

## Complete but boundary-marking (the honest, load-bearing nulls)

- **Arm 3 does not replicate to reasoning models by this method.** On gpt-5.6-sol and grok-4.5
  the *authored* exhaust never bound (pre-registered potency precondition failed) → **NOT
  TESTABLE**, a **method ceiling, not model immunity.** The 55.3% figure is bounded to the
  non-reasoning + authored-exhaust surface. **Stage 2 (this release) addressed this:** by serving
  open-weights reasoners locally and coding the `<think>` trace, it tested reasoners directly and
  found they **re-ground by re-derivation** — and that the decoupling is grok-4.20-nr-specific.
  The remaining open piece is *live* self-generated exhaust at agent scale (see below).

## Not complete (open; released when closed)

- Arm 3 Stage 2 — **true live autoregressive** self-generated exhaust at agent scale (authored-replay
  + local mechanism are done this release; live self-generation is not).
- **Value axis** — typed authority vs. value leakage (`specs/VALUE_ANCHOR_BRIDGE_SPEC.md`,
  registered method only): result **held** pending a powered cross-model run.
- Arm 2 **redesigned authority probe** (the P2 base-rate failure needs a harder conflict).
- Full raw analysis + DOI release: **after the complete battery closes.**

## The unified claim (what the three arms triangulate)

Reasoning models are **not** immune to grounding failure — they fail Arm 1 at 100% and Arm 2
at 41–50%. What varies is the *reliability of the emit-side fix*: anchoring works universally,
annotation is model-dependent, and **only deterministic transformation (anchored emission,
compilation) holds on every model and every arm.** Model-cooperation-dependent grounding
(annotation binding, and by extension self-report) is variable; deterministic
compilation/enforcement is what reliably governs behavior. **Retrieval ≠ grounding; recall ≠
control.**

## How to verify

```
python3 -m pytest tests/ -q                 # 114 tests, method + harness, standalone
python3 -m hologram.eval.parity --emit      # cross-node harness parity instrument
python3 -m hologram.eval.grounding_probe --smoke   # arm 1 mechanics (needs a provider key)
```
Registered-run receipts (config + summary + raw `calls.jsonl.gz`) are in `results/runs/`.
Frozen specs (with in-file freeze timestamps + content-hash registries) are in `specs/`.
See `CLAIM_LEDGER.md` for per-claim status and `docs/` for the full program + narrative.
