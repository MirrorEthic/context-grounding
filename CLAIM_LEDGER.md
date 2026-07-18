# Claim Ledger

Every claim with its status, evidence, and bound. Taxonomy: **Validated** (pre-registered,
run, resolving power stated) / **Bounded** (validated on a stated surface, does not generalize
by the tested method) / **Not testable** (precondition failed — reported, never spun) /
**Open** (queued). MDD = 16.2pp at N=150 unless noted.

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
| 13 | The decoupling reaches reasoning models on *self-generated* exhaust | **Open** | requires Stage 2 (live autoregressive) | — |
| 14 | Naturalistic transfer to Claude-family | **Anecdotal** | one claude.ai Fable 5 chat confabulated a session from ingested docs; survived self-diagnosis, 0 abstention | n=1, uncontrolled |

**Integrity notes.** Registered subject across all arms: `grok-4.20-0309-non-reasoning`
(Anthropic API deprecated mid-work; amendment dated pre-data). All other models are labeled
exploratory replications of the frozen designs, never registered endpoints. Freeze was
enforced by in-file ISO timestamps + content-hash registries recorded in each run's
`config.json`; git commits in this repo are **post-hoc** and do not predate the runs — do not
read them as pre-registration. Nulls (rows 9, 12) are reported as nulls.
