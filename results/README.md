# Results

- `CROSS_PROVIDER_HARDENING.md` — consolidated table across all three arms and all subjects
  (the receipt centerpiece; includes the zeros and NOT-TESTABLEs).
- `runs/<arm>/` — registered-run receipts (subject `grok-4.20-0309-non-reasoning`):
  `config.json` (params + registry hash), `summary.json` (scored verdicts), `calls.jsonl.gz`
  (raw per-call responses + parsed scores). Exploratory replication runs (gpt-5.6-sol,
  grok-4.5) are summarized in CROSS_PROVIDER_HARDENING.md; raw rows available on request /
  in the full release.

Reproduce a registered run: `python3 -m hologram.eval.<arm>_probe --run --n 150 --model <m>`
(needs the matching provider API key in env). `--check` verifies generation invariants offline.
