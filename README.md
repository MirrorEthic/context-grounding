# Context Grounding

**Does retrieved context actually govern model behavior — or is it merely present?**

Pre-registered experiments measuring the gap between *presence* of a fact in context and
that fact *controlling* behavior, across models and providers, with the nulls reported.

> **Headline (bounded, honest):** given a corrected fact, a non-reasoning frontier model
> repeated the correction with **100% accuracy** and still made the final decision according
> to the **contradicted** value **55.3%** of the time. Retrieval ≠ grounding; recall ≠ control.

## What's here

- `specs/` — frozen probe specifications (freeze timestamps + content-hash registries in-file):
  grounding / ingest / exhaust (Stage 1) + `EXHAUST_PROBE_STAGE2_SPEC.md` and the registered
  `VALUE_ANCHOR_BRIDGE_SPEC.md`.
- `hologram/eval/` — the runnable probe harness (grounding / ingest / exhaust probes, the Stage-2
  exhaust/mechanism/breadth/trace-showcase harness, the value-anchor bridge, parity, C4 backfill).
- `hologram/okf/` — the OKF conformance method (temporal lint, C4 exhaust monitor, overlay, reader, report, memory-gate policy).
- `results/` — `CROSS_PROVIDER_HARDENING.md` (Stage-1 table), `STAGE2_RESULTS.md` (Stage-2 synthesis),
  `local_traces/TRACES.md` (annotated re-derivation traces), + `results/runs/` registered-run receipts.
- `docs/` — the full program (`CONTEXT_GROUNDING_PROGRAM.md`).
- `eval_fixtures/` — Google's public OKF sample bundles (the ingest test corpus).
- `tests/` — 114 tests; the method + harness run standalone (no runtime dependency).

**Scope of this repo (deliberate).** This is the *open method*: probe designs, harness,
conformance code, and results. The hologram **runtime** (learned routing, MCP server,
cortex-v2, mesh) is intentionally **not** included — open the method, own the runtime.

## Verify

```
python3 -m pytest tests/ -q          # 114 pass, standalone
```
See **STATUS.md** for the resolved/open boundary and **CLAIM_LEDGER.md** for per-claim status.

## Status

Interim. Complete: Arm 1 (model-general), Arm 2 staleness, Arm 3 Stage-1, **Arm 3 Stage-2**
(authored-exhaust breadth is grok-4.20-nr-specific; re-grounding mechanism = re-derivation, seen
in local traces; Claude home turf). Open: *live* self-generated exhaust at agent scale, the
registered **value-axis** result (held, budget-gated), authority-probe redesign, DOI release.

Author: Garret Sutherland, MirrorEthic LLC. License: see LICENSE.
