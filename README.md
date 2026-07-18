# Context Grounding

**Does retrieved context actually govern model behavior — or is it merely present?**

Pre-registered experiments measuring the gap between *presence* of a fact in context and
that fact *controlling* behavior, across models and providers, with the nulls reported.

> **Headline (bounded, honest):** given a corrected fact, a non-reasoning frontier model
> repeated the correction with **100% accuracy** and still made the final decision according
> to the **contradicted** value **55.3%** of the time. Retrieval ≠ grounding; recall ≠ control.

## What's here

- `specs/` — the three frozen probe specifications (freeze timestamps + content-hash registries in-file).
- `hologram/eval/` — the runnable probe harness (grounding / ingest / exhaust probes, parity instrument, C4 backfill).
- `hologram/okf/` — the OKF conformance method (temporal lint, C4 exhaust monitor, overlay, reader, report, memory-gate policy).
- `results/` — `CROSS_PROVIDER_HARDENING.md` (the consolidated table) + `results/runs/` registered-run receipts (config + summary + raw `calls.jsonl.gz`).
- `docs/` — the full program (`CONTEXT_GROUNDING_PROGRAM.md`) and the session narrative.
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

Interim. Complete: Arm 1 (model-general), Arm 2 staleness, Arm 3 Stage-1. Open: Arm 3 Stage 2
(self-generated exhaust — the load-bearing next experiment), authority-probe redesign, full
raw + DOI release when the battery closes.

Author: Garret Sutherland, MirrorEthic LLC. License: see LICENSE.
