# Retrieval Is Not Grounding

**Whether a fact is *present* in a model's context and whether that fact *governs* its
behavior are two different things — and the gap is measurable.**

*Garret Sutherland, MirrorEthic LLC · 2026-07-18 · interim release*

---

## The result, stated with its bounds

We gave a model a corrected fact, in context, unambiguous. On a non-reasoning frontier
model it **repeated the correction with 100% accuracy** — and then made the final decision
according to the **contradicted** value **55.3%** of the time. The right answer was
retrievable, the model stated it correctly, and its behavior still tracked the wrong one.

That is one number from one arm on one surface. This piece is about how we got it, what it
does and does not generalize to, and why the honest boundary is more interesting than the
headline.

## Why it matters

A lot of AI infrastructure rests on an unstated assumption: **if the right information is in
context, the model will act on it.** Retrieval-augmented generation, agent memory, long-context
prompting — all of it assumes *presence implies control.*

It doesn't. Retrieval is not grounding; recall is not behavioral control. A model can hold a
fact, rank it salient, state it correctly, and still not be governed by it. If that's true —
and it is measurable — then "we put it in the context window" is not a safety or correctness
guarantee, and the interesting engineering question becomes: *what actually makes context
govern behavior?*

## How we tested it (the discipline matters)

Three probes, each **frozen before any data was collected** — design, sample size, and the
minimum effect the sample could resolve (16.2 percentage points at N=150), all fixed in
advance and content-hash-registered. Each was adversarially reviewed for confounds before
running. Nulls are reported as nulls. The registered subject was a single model
(`grok-4.20-non-reasoning`); every other model is a labeled replication of the same frozen
design, never a moved goalpost.

The receipts — specs, the runnable harness, raw per-call rows, and a claim-by-claim ledger —
are in the [companion repository](https://github.com/MirrorEthic/context-grounding). You can
rerun any registered arm.

## What we found

**Arm 1 — missing temporal structure causes confabulation, and it's model-general.**
When a timestamp lacked an explicit anchor, models invented elapsed time — a stale "9h ago"
read as fresh — **100% of the time, with zero abstentions**, even when "I don't know" was an
offered answer. Anchored, typed emission eliminated it (**0% error**). Scrambled anchors were
*followed*, proving the anchors are read, not decoration. This replicated across **five models
and three providers**, reasoning and non-reasoning alike. Under-informed, models don't hedge —
they fabricate.

**Arm 2 — typed annotation helps unreliably; deterministic compilation enforces.**
Foreign stale content was treated as current 41–58% of the time. Adding visible typed metadata
("as-of," authority, staleness) helped — but *how much depended entirely on the model*: it
drove the error fully to zero on one model, partially on another, and **not measurably at all**
on a third. **Deterministically compiling** the content (rewriting stale claims as as-of-qualified
past tense, enforcing eligibility) drove it to **0% on all three.** Annotation is advisory and
model-dependent; compilation is enforcement and model-robust.

**Arm 3 — self-exhaust defeats correction, on the surface where the method reaches.**
This is the 55.3% result above: repeated contradictory context in a session defeated a single
correction more than half the time, while the model reported the corrected fact perfectly. And
here is the boundary that makes it honest: **on reasoning models the effect could not be tested
at all** — our *authored* contradictory context never engaged them (a pre-registered potency
check failed). That is a **limit of the method, not evidence of model immunity**: the exhaust
was in a neutral voice, not the model's own. Testing whether reasoning models decouple on their
*own* generated output requires a different experiment — which is exactly the open work below.

## The one thing that held everywhere

Across every model and every arm we tested, **deterministic transformation is the lever that
governs behavior** — anchoring in emission (Arm 1), compilation in ingestion (Arm 2). The
approaches that depend on the model *choosing* to honor the context — annotation binding, and
by extension the model's own self-report — are variable. When we asked a model to diagnose its
own grounding, it confidently described context it had never received. Self-report is not an
audit; the non-model record is.

## What's open (and why it can't be rushed)

- **Stage 2:** whether the self-exhaust effect reaches reasoning models via their *own*
  generated output, across real turns. This needs naturalistic session accumulation that only
  time and use produce — it cannot be synthetically rushed, which is precisely why we publish
  the resolved layer now and mature this one in the open.
- **A redesigned authority probe** (our first attempt was too easy — fresh records dominated
  before we could measure the effect; we reported that as not-testable rather than as a win).
- **Broader provider coverage** and the full raw evidence package with a citable DOI, when the
  complete battery closes.

## The claim, exactly as strong as the evidence

Reasoning models are **not** robust to grounding failure — they fail on missing structure
(100%) and foreign staleness (41–50%). What varies is the reliability of the fix. **Only
deterministic transformation reliably makes retrieved context govern behavior.** Everything
that relies on the model's cooperation degrades unpredictably across models.

That is the interim result. The boundary conditions — the models where our method didn't
reach, the annotation effect that vanished, the authority probe that was too easy — are in the
repository as first-class findings, because a result you can't see the edges of isn't one.

---

## Prior work

Two papers by **Alex Kwon** predate this program and independently established several of its
core results; we were unaware of them during development and credit them here as prior work.
*Reclaim Evaluation: A Lossy Memory Is Worse Than an Empty One* (arXiv:2606.25449, June 2026)
shows models confabulate rather than abstain when under-informed, re-emit stale conclusions once
the work behind them is dropped, and recover only when the recomputable source is kept — and that
typed annotation binds model-dependently while deterministic transformation drives the error to
zero. *They Infer What You Meant* (arXiv:2607.03598, July 2026) articulates the
representation-vs-behavioral-control decomposition this write-up leads with. Our claim ledger
follows the structure of Kwon's Table 1.

---

*Companion repository (specs, harness, raw results, claim ledger):
`github.com/MirrorEthic/context-grounding`. Independent research, MirrorEthic LLC.*
