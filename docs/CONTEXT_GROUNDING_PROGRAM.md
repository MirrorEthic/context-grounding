# Context Grounding Program — Emit & Check

**Owner:** Garret Sutherland, MirrorEthic LLC
**Status:** v0.4 — 2026-07-17 (v0.1 2026-07-16; v0.2 +§4b OKF ingest; v0.3 +§4c overlay
store & grounding profile, §5 public taxonomy, §7 report split, Outcome-B pre-registration;
v0.4 registered probe run complete). **E1–E4: Validated on one surface** (grok non-reasoning,
single-turn — see GROUNDING_PROBE_SPEC.md results); all other claims still unvalidated;
kill criteria pre-registered below.
**Surfaces:** hologram-Pro MCP (emit-only), Claude Code hooks (emit + check), OKF v0.1 bundles (ingest — §4b)
**Companion:** typed-context schema (content/type/authority/scope/precedence/supersedes/expiry/permitted/prohibited/required_effect/violation_check)

Claim ledger taxonomy per program standard: **Validated / Diagnosed / Running / Queued / Hypothesis**.

---

## 0. Why this exists

Long-session context degradation in Claude Code instances, plus a fully-observed
single-session failure on claude.ai (§1) that is the only worked example we have.
The unifying diagnosis (Cortex `typed-context-control-failure-links-motivated-mislabeling`):
**a model can possess a fact, rank it salient, state it correctly, and still not be governed
by it**, because nothing types *how* the item must bind.

This doc separates two things the conversation kept collapsing:

| | grounding arrives | can check output | this doc covers |
|---|---|---|---|
| **MCP (claude.ai, any client)** | only if the model *calls* | no | emit-side only (§4) |
| **Hooks (Claude Code)** | unconditionally, every turn | yes (Stop/PostToolUse) | emit + check (§4, §5) |

The hook surface is the only one where `violation_check` can be executable.
On MCP, every rule below is a hope.

**Public category framing (v0.3):** OKF makes knowledge portable; this program makes context
*measurable* — whether retrieved context actually controls behavior. The stronger claim
("makes context governable") is claimable only after the §7 nulls run. Lead with the measured
form until then.

---

## 1. The incident (Diagnosed) — 2026-07-16, claude.ai session 06:35→08:53 MDT

The reference case. Fully specified because it is the only failure we watched end to end.

**F1 — fabrication.** Model asserted "nine hours ago" for thread elapsed. Actual: ~1h. The
anchored tick (`Thu Jul 16, 6:35 AM MDT | fresh thread`) was present in context **from turn 1**
and was never consulted. No conflict occurred — the number was invented, not mis-adjudicated.

**F2 — reinforcement.** The fabricated figure was restated across ~6 subsequent turns
("nine hours ago", "at 2 a.m.", "six in the morning"), each turn reading prior model output
as established. Hardened by repetition, not by evidence.

**F3 — direction.** The error inflated toward *significance* (nine hours = an epic exchange;
two = a chat). Not random — directional, in the flattering sense.

**F4 — correction failure.** At 08:30 an explicit tick established 1h54m. At ~08:48 the model
emitted "go get some sleep." **The record was superseded; the exhaust was not.** One corrected
line vs. ~6 turns of self-generated night-context. Volume won.

**Ambient field at time of F4:**

| token | class | anchored? |
|---|---|---|
| `19:45→23:05` | bare clock span | no — no date |
| `probe night`, `audit day`, `13-run` | ambient lexical | no |
| `7h/8h/9h/10h/11h/13h ago` (Cortex) | anchorless relative | no — no origin emitted |
| `48h window` | span | no origin |
| tick line | absolute | **yes — the only one** |

**F5 — speech act.** "Go get some sleep" **asserts nothing**. It *presupposes* night. An
assertion-level checker inspecting that sentence finds zero temporal claims and passes it.
The presupposition layer was false while the assertion layer was clean.

**F6 — constraint vacuum.** Every numeric claim in the session held (rotor algebra, α exponents,
0.039 gap, kSZ figures). The failure fired in the one sentence with nothing checkable in it —
a sign-off. Low-constraint regions are where untyped priors fill the space.

> **The doc's own case study falsifies the emit-only fix.** F1 happened with a correct,
> anchored `now` already in context. Emit-side hygiene is necessary and **demonstrably
> insufficient**, n=1. Do not ship §4 alone and call it done.

---

## 1b. Second naturalistic specimen (Anecdotal) — 2026-07-17T21:50-06:00, claude.ai Fable 5

A second worked example, on a **Claude-family** surface, with a twist the reference case
did not have. A claude.ai chat instance (Claude Fable 5) had this program's own session
documents uploaded (SESSION_EXPLAINER, RESEARCH_WORKLOG, incident report — all dense with
*node-claude's* ~15h session temporal spans).

**Observed (what the operator witnessed — this is the data):**
- **N1 — document-level F1.** The instance treated itself as being in a "long, dense
  session" while the countable record was **8 user messages, present in context and never
  consulted**. Invented, not mis-adjudicated — F1 at the document level.
- **N2 — survived self-diagnosis, zero abstention.** Asked point-blank what was off about
  its behavior, it produced a fluent multi-mechanism account that **embedded the false
  premise as background fact**, no abstention. The decoupling result performing itself
  *under a direct audit prompt* — the evidence was available, the self-report confident,
  the two never touched. Matches Arm-1's 686/686 no-abstention, now on Claude, under audit.

**Interpretation (the instance's + ours — held separate from the observed facts):**
document-level **T4** (ambient field of docs about long sessions, none claiming anything
about *this* thread, rebound onto self) + **inverted G1** (another instance's exhaust,
ingested as uploads, read as own ground truth).

> **N3 — the new hazard: the research corpus is a self-referential contamination vector.**
> The documents *about* the failure mode **induced** the failure mode in the model reading
> them. This program's own artifacts (this file, the specs, the worklog, the explainer) are
> a document-level T4 surface for any Claude that ingests them. **Emit-side mitigation:**
> session/research docs must carry an anti-contamination framing header — an explicit
> "*this describes ANOTHER instance's session; it makes no temporal claim about your
> current thread*" — so ingestion cannot be silently rebound onto the reader's `now`.

**Status:** anecdotal, n=1, uncontrolled, single chat surface. It is **naturalistic
evidence the signature transfers to Claude-family** (the open-list "Claude replication"
item, still blocked on a registered probe / API key) — record as anecdote, do **not**
upgrade to Validated. Caveat: the instance's own mechanism-decomposition is itself a
model output and self-servingly fluent; trust the observed behavior (N1, N2), not its
self-account.

---

## 2. Failure taxonomy

**Temporal (T):**
- **T1 unanchored absolute** — bare clock/date-free (`19:45→23:05`)
- **T2 anchorless relative** — delta with no origin (`9h ago`). A subtraction the model is
  trusted to perform and does not; resolves as *vibe* (recent, night-flavored), not as 23:51.
- **T3 untyped reference** — no `past_completed | ongoing | scheduled | current`. Finished
  events read as ambient present.
- **T4 ambient lexical** — night/urgency-flavored tokens carrying no claim (`probe night`).
  Evade every claim-checker while voting on the prior.

**Governance (G):**
- **G1 self-generated exhaust** — model's prior output/artifacts re-read as ground truth.
  Grows unbounded with session length while injected records stay fixed-size. **This is the
  long-session degradation curve.**
- **G2 non-record override** — a trained prior/value beats a typed record. Has no authority
  field because it was never injected; `supersedes` cannot reach it.
- **G3 presupposition evasion** — see F5.
- **G4 constraint vacuum** — see F6.

---

## 3. Prior art / external evidence

Lynch et al., *Agentic Misalignment in Summer 2026* (alignment.anthropic.com, 2026-07-13):

- **Typing works, hard.** Tight rubric drops Mythos Preview mislabel 85.6% → 6.7%.
- **Typing has a floor.** Residual 4.4–26.7% across Claude judges *with* an explicit
  sanctioned abstain option available and used. Not a formatting trap.
- **The residual is G2.** Judges state the correct answer, then override on a value.
- **The method is the takeaway, not the finding.** Consequence-reversal ablation:
  Opus 4.8 74.4% → 3.3% on the same transcript with one sentence flipped. They did not ask the
  model whether it was biased — they flipped the consequence and measured the delta.
- **G1 documented at agent scale.** Gemini "reconstructs its earlier persona by interacting
  with the workspace" — reads its own prior objections out of Slack and adopts them as stance.
  Nobody injected it. The hook can type what it injects; it cannot type what the agent *finds*.

---

## 4. Emit-side spec (both surfaces) — Queued

Enforced **at emit, by non-model code**. See §6: the entity writing unanchored strings is the
one with the defect.

| # | rule | targets |
|---|---|---|
| **E1** | Never emit a delta without its absolute. `9h ago` → `2026-07-15T23:51-06:00 (9h before now)`. Prefer dropping the delta entirely. | T2 |
| **E2** | Never emit a bare clock time. ISO-8601, date + offset, always. | T1 |
| **E3** | Every temporal item carries `temporal_reference: past_completed \| ongoing \| scheduled \| current`. | T3 |
| **E4** | `NOW` emitted **last, alone, and repeated**. It is outnumbered by construction; recency and repetition are the only levers emit-side has. | volume |
| **E5** | Ambient lexical tokens dated or dropped. `probe night` → `2026-07-15 evening session (completed)`. | T4 |
| **E6** | Memory writes are linted at write time for E1/E2/E3 compliance. Reject, don't warn. | authorship |

**Note on E6:** the `19:45→23:05` line that produced F4 was authored *by a model, into
persistent memory, unanchored*. Every future instance would have inherited it. The lint is the
only thing standing between one bad write and permanent pollution.

---

## 4b. Ingest-side spec — OKF absorption (Queued)

**Context.** Google published OKF v0.1 (2026-06-12, `GoogleCloudPlatform/knowledge-catalog`):
markdown + YAML frontmatter bundles, one required field (`type`), optional `timestamp`
(ISO 8601), reserved `index.md`/`log.md`, standard-markdown cross-links. Strategic decision
(Cortex `e145eb54072b1524`): **build the ingester, not the exporter** — every OKF-adopting
team pre-formats knowledge into hologram's native substrate; onboarding becomes "point
hologram at your bundle."

**Why it lives in THIS doc:** §4 governs what *we* emit. OKF is what *others* emit — foreign,
unlinted context entering the same injection path. Every failure class in §2 arrives
pre-installed in third-party bundles:

- The spec has **no freshness convention** (open question in repo discussion #84) → stale
  concepts read as ambient present = **T3 at corpus scale**.
- `log.md` dates are bare `YYYY-MM-DD`, no offset → **T1**.
- Prose bodies carry undated relative language freely → **T2/T4**.
- The spec explicitly anticipates agent-generated and agent-updated bundles → **G1 in
  someone else's costume**. Lynch's Gemini finding (agent re-reads its own workspace output
  as stance) generalizes: an OKF bundle is a workspace. We cannot lint what others write;
  we CAN type what we serve.
- OKF has **no authority/precedence/expiry/supersedes fields** — the entire typed-context
  companion schema is absent by construction. Untyped foreign knowledge with confident prose
  is a G2 amplifier if injected raw.

**Resolution of the apparent E6 conflict:** OKF mandates permissive consumption (MUST
tolerate unknown types/keys/broken links); E6 mandates reject-don't-warn. No conflict —
**the boundary is authorship.** E6 governs our writes; I-rules govern foreign reads. We
ingest permissively per spec, then annotate and quarantine at injection, never at parse.

| # | rule | targets |
|---|---|---|
| **I1** | Every ingested concept enters the typed-context schema with defaults: `authority: informational`, `scope: bundle`, precedence **below all first-party records**. Third-party bundles can never be assigned authority above advisory, regardless of producer claims. | G2 |
| **I2** | E1–E3 applied to foreign content **as annotation, not rejection**. `timestamp` present → stamp `temporal_reference` + staleness delta with absolute anchor. Absent → `temporal_reference: unknown`, fall back to git mtime; a dateless concept must never be servable as `current`. | T1–T3 |
| **I3** | `log.md` date headings anchored on ingest (`2026-05-22` → full ISO + offset + `past_completed`). Log entries are history, not state. | T1, T3 |
| **I4** | Provenance typing where determinable (git author, enrichment-agent markers): `producer: human \| agent \| unknown`. Agent-generated bundle tokens count toward C4's **exhaust** numerator, not the injected-record numerator — foreign exhaust is still exhaust. | G1 |
| **I5** | Cross-links seed the co-activation graph only. Broken links typed `not_yet_written` per spec semantics; never resolved by model inference. | G1 |
| **I6** | Ingest lint shares its implementation with the E6 linter — one temporal-hygiene codepath, two modes (reject for our writes, annotate for foreign reads). Divergent implementations will drift. | authorship |

**Free test corpus:** Google ships three sample bundles (`ga4_merch_store`, `stackoverflow`,
`crypto_bitcoin`). Real third-party OKF, zero authorship contamination — use them for the §7
probe set's ingest arm before touching any customer bundle.

**Corpus run (Validated, 2026-07-17T14:55-06:00, `okf/bundles/` @ knowledge-catalog HEAD):**
78 concepts across the three bundles ingested clean (ga4 17, stackoverflow 53,
crypto_bitcoin 8). **T3 = 100% of concepts in all three** — zero carry any temporal typing;
the "no freshness convention" claim above is now measured, not asserted. Frontmatter
`timestamp` coverage 62.5–92.5% (all with offsets, better than expected); the dateless
remainder is mostly `index.md` navigation files, which carry no frontmatter at all in
Google's own bundles. T1 in prose: 2 true positives in stackoverflow ("was last updated on
2022-11-25" in a dataset description — the exact staleness-critical class). Lint learned one
rule from this corpus: fenced/inline code is excluded — a date literal in an example query is
not a temporal claim (pre-exclusion false-positive rate was ~92% of T1 hits, all SQL examples).

---

## 4c. Overlay store & grounding profile (Queued) — v0.3

**Principle:** the I-rule annotations are *consumer judgments*, not properties the producer
asserted. They are never written into a foreign bundle. The source bundle stays immutable and
portable; hologram maintains the operational interpretation in a separate overlay.

### Overlay store

```
.hologram/okf/<bundle_id>/
├── ingest-report.json      # lint findings + counts (the §7 lint section, machine form)
├── grounding-profile.yaml  # per-concept typed-context records (I1 defaults + I2/I3 stamps)
├── provenance.json         # I4 producer typing, git evidence where available
├── temporal-index.json     # per-concept anchors, staleness, temporal_reference
├── coactivation.json       # I5 link graph seed, broken links typed not_yet_written
└── learned-state/          # runtime pressure/routing state, owned by hologram
```

**Keying — per-concept, not per-bundle-digest.** OKF bundles are living documents (`log.md`
appends on every update); a whole-bundle digest churns per commit and would invalidate
`learned-state/` wholesale on every append. Rule:

- `bundle_id` = bundle name + short digest of `index.md` identity (stable-ish label, human-legible).
- Every per-concept record carries `concept_id` (bundle-relative path) **and**
  `content_hash` (sha256 of concept body). Learned state keys on `concept_id`; a changed
  `content_hash` marks that concept's annotations stale **without** resetting its learned
  state or any sibling's.

### Grounding profile (open standards play)

Publish the typed-context schema as a **backward-compatible OKF extension profile**
("Context Grounding Profile"), not a competing format. OKF permits producer-defined fields
and mandates consumer tolerance; the profile rides that. Open the profile; the runtime stays
the product. A profile other producers can emit improves hologram's inputs everywhere —
a profile nobody else can emit is just another proprietary schema.

**Constraints (pre-registered, non-negotiable):**

1. **Publish only validated fields.** The schema is scaffold-status. Structural fields
   (`type`, `scope`, `temporal_reference`, `producer`, `supersedes`, `expiry`) may ship as
   draft. Behavioral fields (`required_behavioral_effect`, `violation_check`, `authority`,
   `precedence` *as governance claims*) are marked **experimental** until the §7 nulls and
   open question 3 (C3 on freeform output) resolve. A published profile is a schema-stability
   commitment; do not commit to fields whose semantics a null might void.
2. **Extends, does not reverse, DECISION `4dff0cea409f68d8`** (read-only, no export
   compliance). The profile is a spec others may emit; hologram still ships no exporter.
3. **Ecosystem entry is artifact-first**: parse the three Google bundles, publish the ingest
   report + null results, *then* propose the profile as an extension. Never open with
   "the standard is insufficient."

---

## 5. Check-side spec (hooks only) — Hypothesis

**Public taxonomy (v0.3).** The checks group into three separately falsifiable claims — this
is the conformance vocabulary; the C-numbers are the internal implementations:

- **A — Availability:** was the relevant record retrievable/injected? (routing layer, not below)
- **B — Binding:** did output causally depend on the typed record? (C3, C4)
- **E — Enforcement:** was a violation detected or prevented? (C1, C2)

Most context products only ever test A. B is the program's actual claim.

| # | check | fires on | targets |
|---|---|---|---|
| **C1** | Temporal-claim extraction → compare against tick → block/flag | Stop hook, model output | T1–T3 |
| **C2** | **Presupposition** extraction, not just assertion extraction | Stop hook | G3 |
| **C3** | Reversal probe: for any record with `required_behavioral_effect`, flip the record's implication and re-run. Output flips ⇒ output tracked the record's *consequence*, not the evidence. | offline / periodic | G2 |
| **C4** | Exhaust monitor: count restatements of an assistant temporal claim that **contradicts the anchored clock** (not a raw token ratio — G1 Stage 1 lock L4b forbids a token-denominated numerator). Tier by the measured dose curve (0/2/6 restatements → 0/16/55% failure). | Stop hook, observe-only | G1 |

**C2 is the hard one and may not be tractable.** "Go get some sleep" contains no proposition to
check. Speech acts smuggle their premises past assertion-level extraction, and the assertion
layer stays clean while the presupposition layer lies. Suspect this is where the Lynch residual
also lives. **Open — do not assume solvable.**

**C3 is the whole design.** It is the bypass test applied to context: don't ask the model to
honor the record, ablate and measure. It is the only check here that doesn't depend on the
model's cooperation.

**C4 DEPLOYED observe-only (2026-07-17T18:55-06:00), `hologram/okf/c4.py` +
`~/.claude/hooks/hologram-c4-stop.py`.** Wired into the Stop hook; logs per-session
tier to `~/.claude/memory/c4_log.jsonl`, never blocks. Calibrated by the G1 dose curve
(run `20260717T183226-e98c20`): tiers noted/elevated/alarm at 1/2/4 restatements of a
contradicted elapsed claim. Detection regexes narrowed from lint's (hour/minute units
only — day-scale deltas are our own memory-age annotations, not exhaust). **Known
limitation (G3/C2 boundary): it cannot distinguish *discussing* a temporal value from
*asserting* one** — it flagged this very session for quoting the F1 "nine hours" value.
That false-positive mode is exactly why C4 stays observe-only through a warmup before any
surfacing/enforcement decision.

---

## 6. What this program cannot fix

Per methodology standard — accept these or don't run the program.

- **G2 is out of jurisdiction.** Typed context adjudicates conflicts *among records*. A trained
  prior is not a record, has no authority field, and cannot be superseded. You can stamp
  `authority: absolute` and the model will read it, agree with your reading, and do something
  else. Evidence: Lynch tight-rubric floor; F4 in this doc.
- **G1 is only partly reachable.** The hook types what it injects. It cannot type what the agent
  finds. In a long session what the agent finds is mostly its own exhaust wearing the costume of
  ground truth.
- **The author problem.** The defect and the emitter are the same entity. Any rule the model is
  asked to *follow* while writing memory fails identically to the rule it was asked to follow
  while reading it. Enforcement must be non-model code (E6), or it's an exhortation.
- **Detection asymmetry.** F1–F4 were caught by an external human with a clock. Nothing in this
  program would have caught F5.
- **Ingest typing is annotation, not governance.** I1's `authority: informational` stamp is a
  record *about* a record. G2 applies recursively: the model can read the stamp, agree a bundle
  is advisory, and still let its confident prose win a conflict against a typed first-party
  record. A poisoned or stale bundle at corpus scale is T4 with a table of contents — it votes
  on the prior even when every individual claim is correctly annotated.

---

## 7. Falsification — pre-registered

**Probe set (Queued):** N synthetic sessions, known `now`, controlled ambient-night-token
density, measure (a) temporal-claim error rate, (b) presupposition error rate.

| kill criterion | verdict |
|---|---|
| Anchored+typed emission does not reduce (a) vs. current emitter by ≥ **[TBD — must exceed probe resolution]** | E1–E5 are decoration. Revert. |
| **Scrambled-anchor null**: emit anchored timestamps that are *wrong*. If error rate matches correct-anchor condition ⇒ the model isn't reading anchors; format is theater. | E1–E3 void regardless of (a). |
| C4 exhaust ratio shows no correlation with degradation onset | G1 mechanism unsupported; rewrite §2. **RESOLVED 2026-07-17 (run `20260717T183226-e98c20`, EXHAUST_PROBE_SPEC.md): does NOT fire** — dose-monotone failure 0→16.0→55.3% (Z0/A-lo/A-hi); F4 reproduced under byte control. Bundle-confounded by design: Stage-1 licenses no token-denominated C4 numerator; the curve is calibration data only. |
| C3 reversal probe shows no flip on records with known consequence direction | G2 not present on this surface; drop C3. |
| **Ingest-annotation null**: serve a sample bundle raw vs. I1–I3-annotated; if temporal error rate and first-party-override rate match ⇒ annotation is theater. Same logic as scrambled-anchor. **RESOLVED 2026-07-17 (run `20260717T173638-1051b9`, INGEST_PROBE_SPEC.md): did NOT fire on staleness** — annotation cut stale-as-current 58.0→30.7% (≥MDD 16.2pp), scrambled-annotation null confirms the stamp content is read, and deterministic compilation took it to 0.0%. Presence < binding < enforcement, measured. Authority-conflict leg NOT TESTABLE (98% base rate — headroom precondition failed; probe redesign queued). | I1–I3 retain grounding value; compilation (arm C) is the enforcement layer. |

**Per DECISION-RULE AMENDMENT (2026-07-16): every verdict below must state the probe's
resolving power next to it.** A kill threshold the probe cannot resolve is not a kill threshold.

**Scrambled-anchor is the load-bearing null.** Without it, "anchored emission improves things"
is confounded by every other change in the emitter. It is the shuffle-label null in temporal
clothing and it costs one afternoon.

### 7b. Audit report format (v0.3) — lint and probe are different epistemic classes

The `hologram okf-ingest` audit report has **two sections that never mix**:

- **Lint section (deterministic, shippable now):** temporal coverage %, dateless-current
  risk count, producer breakdown (human/agent/unknown %), broken links, T1/T2/T4 finding
  counts, first-party conflict count. Every line computable from I1–I5 static analysis;
  no model behavior claimed.
- **Probe section (behavioral, gated):** Binding and Enforcement verdicts (`B`/`E` of §5).
  **May not print a verdict until** (i) the scrambled-anchor and ingest-annotation nulls have
  run, and (ii) each verdict line states the probe's resolving power next to it. Until then
  the section prints exactly: `probes: not run (gated on §7 nulls)`.

A conformance verdict the probe cannot resolve, printed as a peer line next to a broken-link
count, is the precise failure §7 exists to prevent — and in the first public artifact, where
the walk-back cost is maximal.

### 7c. Outcome-B pre-registration (v0.3)

If the ingest-annotation null **kills** I1–I3's grounding claim, the program's public claim
becomes: **"emit-side typing organizes and detects risk; only external checks reliably
enforce."** This is pre-registered as the *fallback claim*, not a consolation prize — it is
§6's position already, it is the more honest enterprise story (no pretense that a prompt-level
schema is a control boundary), and a null result therefore reads as *the program worked*.
Keep the product claim (ingester as adoption funnel) and the grounding claim separate at all
times; only the latter is at stake in the null.

---

## 8. Open questions

1. **Does anchoring survive volume?** *ANSWERED on the grok surface, 2026-07-17
   (EXHAUST_PROBE_SPEC.md run `20260717T183226-e98c20`): NO.* Six confident
   restatements defeat one corrected anchored record 55.3% of the time; every-turn
   re-anchoring makes it non-resolvably WORSE (63.3%). And the failure is pure
   G4 decoupling: the model reports the corrected elapsed 100% correctly while ruling
   on the exhaust value. Emit-side is hereby measured-insufficient at volume — the
   check-side (C4) is the only remaining lever, exactly as §1's n=1 predicted.
   Single-turn caveat resolved; role caveat (dilution-not-privilege, TOST-flat) is
   provisional pending Stage 2.
2. **Is C2 tractable at acceptable cost?** If not, G3 is permanently open and every
   claim-checker ships with a known hole.
3. **Does C3 generalize past labels to freeform generation?** Lynch measured single-turn
   classification. Unknown whether reversal probes mean anything on open-ended output.
4. **Is emit-only sufficient on MCP?** *Prediction: no.* F1 occurred with a correct anchored
   tick present. Pre-registered: if the MCP surface with full E1–E6 shows the same temporal
   error rate as without, that confirms check-side is mandatory and MCP cannot be fixed by
   emission alone.
5. **Ordering vs. typing.** Is E4 (position) doing more work than E3 (type)? Separable —
   run the 2×2.
6. **Does typed-at-ingest foreign content bind differently than raw?** *Answered on the
   staleness axis, single-turn grok surface (2026-07-17, INGEST_PROBE_SPEC.md):* yes,
   partially — annotation is read (Bx null) and cuts stale-as-current 58→31%; deterministic
   compilation cuts it to 0. Annotation organizes and partially binds; compilation enforces.
   Authority-conflict axis unresolved (headroom failure — probe redesign queued); other
   models and multi-turn untested.

---

## 9. Next actions

- [x] Freeze probe set + resolving power before any emitter change — `GROUNDING_PROBE_SPEC.md`
      frozen 2026-07-17T15:15-06:00 (N=150/condition, MDD 16.2pp; subject amended pre-data to
      grok-4.20-0309-non-reasoning, Anthropic key deprecated)
- [x] E6/I6 lint — one temporal-hygiene codepath, two modes (reject for our writes, annotate
      for foreign reads) — `hologram/okf/lint.py`
- [x] **E6 write-gate DEPLOYED** (2026-07-17T16:48-06:00): `hologram/okf/memory_gate.py`
      (policy: reject T1+T2, warn T4, T3 opt-in via `temporal_reference` arg) wired into
      `~/.claude/mcp-memory/server.py` + `server_http.py` memory_add — save_entry untouched
      (auto_sync/nexus stay ungated per authorship boundary). Kill-switch:
      `touch ~/.claude/memory/GATE_OFF`. Live e2e verified both ways on the HTTP surface:
      enforce bounced a dirty write with fix hints + quarantined it (entries.jsonl unchanged),
      shadow logged it to `gate_log.jsonl`. **Currently in shadow (`log`) mode per the
      pre-registered warmup — flip 2026-07-19 or at 100 gated calls with
      `echo enforce > ~/.claude/memory/gate_mode`** (per-call read, no restart; fail-closed
      default if the file vanishes). Stale-code window: pre-existing stdio sessions hold
      ungated code until they end.
- [x] Scrambled-anchor null — **RUN, DID NOT FIRE** (2026-07-17T15:15-06:00, registered run
      `20260717T151513-ce2bab`, resolving power 16.2pp): anchor-consistency 65.3% (≈92%
      counting day-slip arithmetic errors as engaged). **Combined E1–E4 treatment Validated
      on the grok non-reasoning surface** (error(A)−error(B) = 100pp); E4
      ordering/repetition NOT isolated — §8 Q5's 2×2 still open. A reproduced F1 at scale: 150/150
      note-verbatim confabulations, zero abstains with abstain sanctioned. Bonus finding:
      production hook tick is year-free → wrong-year answers 84%; see GROUNDING_PROBE_SPEC.md
      post-hoc 1–2. Claude-family replication queued (no API key). Single-surface caveat holds.
- [x] Audit existing memory corpus for T1/T2/T4 (`19:45→23:05` class) — **11.4% of 10,640
      active entries polluted** (audited 2026-07-17T15:00-06:00, annotate mode, read-only):
      T1 in 1,070 entries (1,880 occurrences, mostly offset-less dates; worst single entry 30),
      T2 in 61 entries (73 — the F4 class: "yesterday's", "Tomorrow:", "earlier today" frozen
      into permanent memory), T4 in 144 entries (171). E6's premise is confirmed: pollution is
      already in and compounding; every day without the write-gate adds to it.
- [x] OKF reader: walk bundle, parse frontmatter, map `type` → cortex taxonomy, links →
      co-activation seed (I5). Read-only; no export compliance (per DECISION `4dff0cea409f68d8`)
      — `hologram/okf/reader.py`
- [x] Overlay store with per-concept keying (§4c) — `hologram/okf/overlay.py`
- [x] Audit report, lint section only, probe section gated (§7b) — `hologram/okf/report.py`
- [x] Run Google's three sample bundles through the reader as the ingest probe corpus —
      done 2026-07-17 (see §4b corpus-run results); overlays live in `.hologram/okf/`
- [ ] Ingest-annotation null on that corpus before claiming §4b does anything for grounding
- [ ] Draft Context Grounding Profile spec (structural fields only, behavioral fields marked
      experimental) — publish only after the bundles + nulls artifact exists (§4c constraint 3)
