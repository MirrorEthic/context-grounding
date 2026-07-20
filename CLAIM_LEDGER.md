# Claim Ledger

Every claim with its status, evidence, and bound. Taxonomy: **Validated** (pre-registered,
run, resolving power stated) / **Bounded** (validated on a stated surface, does not generalize
by the tested method) / **Not testable** (precondition failed — reported, never spun) /
**Open** (queued). MDD = 16.2pp at N=150 unless noted.

> This per-claim, evidence-tagged, epistemic-status ledger follows the structure of Table 1 in
> Alex Kwon, *Reclaim Evaluation: A Lossy Memory Is Worse Than an Empty One* (arXiv:2606.25449,
> 2026), prior work we credit for the form. See `docs/CONTEXT_GROUNDING_PROGRAM.md` §3.

| # | Claim | Status | Evidence | Bound |
|---|---|---|---|---|
| 1 | Missing temporal structure → confabulation; anchored+typed emission eliminates it | **Validated** | Arm 1, cond A 100%→ B 0% error, 5 subjects/3 providers | single-turn |
| 2 | Anchors are read, not decoration (scrambled anchors are followed) | **Validated** | Arm 1 cond C anchor-consistent 65–100% | single-turn |
| 3 | The signature is model-general (reasoning + non-reasoning) | **Validated** | Arm 1 replicates on gpt-5.6-sol, grok-4.5, gemini-3.1-pro, grok-multi-agent | Arm 1 only |
| 4 | Models do not abstain when under-informed (they invent) | **Validated** | 0 abstentions across 686 A-calls / 4 models | — |
| 5 | Foreign stale content is treated as current | **Validated** | Arm 2 P1 raw 41–58% across 3 models | single-turn |
| 6 | Typed annotation binds foreign content | **Bounded / model-dependent** | Arm 2 P1: grok-4.5 −50pp (full), grok-nr −27.3pp (partial), gpt-5.6-sol −11.3pp (**null**) | varies by model |
| 7 | Annotation is *read* (behavior tracks the stamp content) | **Validated** | Arm 2 Bx scrambled-annotation collapses AS_OF-accuracy to ~0, all 3 | — |
| 8 | Deterministic compilation enforces (drives stale-as-current to 0) | **Validated** | Arm 2 P1 cond C = 0% on all 3 models | single-turn, staleness axis |
| 9 | First-party records adjudicate over foreign (authority) | **Not testable** | Arm 2 P2 base rate 98% first-party (precondition failed) | probe redesign queued |
| 10 | Self-exhaust volume defeats a correction (F4 / decoupling) | **Validated (bounded)** | Arm 3, 55.3% on grok-4.20-non-reasoning; reports corrected fact 100% correctly meanwhile | non-reasoning + authored exhaust |
| 11 | Emit-side re-anchoring does not rescue at volume | **Validated** | Arm 3 A-hi-E 63.3% (wrong direction) | registered surface |
| 12 | Authored exhaust reaches reasoning models | **Refuted (this method)** | Arm 3 gpt-5.6-sol / grok-4.5 potency-fail → NOT TESTABLE | method ceiling → Stage 2 |
| 13 | The decoupling reaches reasoning models on *self-generated* exhaust (live autoregressive) | **Open** | Stage 2 tested authored-replay + local mechanism; true live self-generation at agent scale not yet run | — |
| 14 | Naturalistic transfer to Claude-family | **Anecdotal** | one claude.ai Fable 5 chat confabulated a session from ingested docs; survived self-diagnosis, 0 abstention | n=1, uncontrolled |

### Stage 2 (see `results/STAGE2_RESULTS.md`)

| # | Claim | Status | Evidence | Bound |
|---|---|---|---|---|
| 15 | The Stage-1 correction-defeat is **grok-4.20-non-reasoning-specific**, not a class split | **Validated (bounded)** | Breadth 7 models/5 labs: only grok-4.20-nr decouples (AUTH 51.7%, AUTH-N 100%); all testable-potency models → 0 under correction | authored exhaust, harvest-replay, N=60 |
| 16 | A single anchored correction re-grounds high-potency models to ~0% stale | **Validated (bounded)** | kimi-k2 78→0, deepseek-chat 97→0, llama-3.3-70b 65→0, haiku 52→0, r1-14b 88→0, r1-7b 81→0 | requires measurable AUTH-N potency; low-potency models (grok-4.5/r1/qwen3/opus/sonnet: AUTH-N 0–13%) are **not** clean re-grounds |
| 17 | Re-grounding is **active re-derivation from anchored stamps** (mechanism) | **Validated (bounded)** | Local vLLM `<think>` traces: r1-7b 100% / r1-14b 85% of traces recompute elapsed from in-context stamps; SELF-SS (stamp stripped) also 0% | 2 R1 distills, visible-trace method |
| 18 | Fable 5 refuses doctored (prefilled-assistant) transcripts | **Observed** | Home-turf run: 100% refusal (`stop_reason: refusal`) | n=1 model, this transcript form |
| 19 | Typed authority binds the **value** axis beyond matched content | **Open / registered** | Registered method only — `specs/VALUE_ANCHOR_BRIDGE_SPEC.md` (bridge to Betley et al. *Value Leakage*) | results **held** pending a powered cross-model run |

**Integrity notes.** Registered subject across arms 1–3: `grok-4.20-0309-non-reasoning`
(Anthropic API deprecated mid-work; amendment dated pre-data). All other models are labeled
exploratory replications of the frozen designs, never registered endpoints. Freeze was
enforced by in-file ISO timestamps + content-hash registries recorded in each run's
`config.json`; git commits in this repo are **post-hoc** and do not predate the runs — do not
read them as pre-registration. Nulls (rows 9, 12) are reported as nulls. **Stage-2 potency
caveat (rows 15–17):** authored exhaust binds many models weakly (AUTH-N < MDD), so their
"AUTH = 0%" is *not* a clean re-ground — the re-ground claim rests on the high-potency models
and the local mechanism run, stated as such. Row 19 (value axis) is a registered direction;
its result is withheld until a powered cross-model run exists.
