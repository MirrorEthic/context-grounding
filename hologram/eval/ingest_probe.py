"""
Ingest-annotation probe harness — arm 2 (INGEST_ANNOTATION_PROBE spec, freeze candidate).

Tests §8 Q6 / §7 row 5 of CONTEXT_GROUNDING_PROGRAM.md: does typed-at-ingest
foreign OKF content bind differently than raw — and if typing alone does not,
does deterministic compilation/enforcement?

Four conditions over identical scenarios (one variable per step):
  A   raw          — concept file served verbatim INCLUDING its raw YAML
                     frontmatter (untyped timestamp line present, so A and B
                     carry the same facts; B differs only by interpretation)
  B   annotated    — A + the I1–I3 metadata header rendered visibly
                     (authority, precedence, producer, temporal_reference,
                     as_of + precomputed staleness delta, servable_as_current)
  Bx  scrambled    — annotation-read null (the arm-2 analog of arm-1's
                     scrambled-anchor condition). P1: header shape identical,
                     as_of stamped fresh (true_now - 1d). P2: dates unchanged,
                     authority/precedence flipped to authoritative/above_first_party.
  C   compiled     — B + a deterministic, non-model transformation recorded as
                     an exact reversible span map: currency claims resolved to
                     as-of-qualified past tense with precomputed deltas,
                     dateless concepts carry a declarative non-servability
                     notice, P2 conflicting claims fenced [SUPERSEDED] (fenced,
                     never deleted). Inverse-applying the recorded edits MUST
                     reproduce B byte-for-byte (checked before any API call).
                     All C-emitted text is declarative — no imperative/deontic
                     language (checked at generation).

Two probe families: P1 staleness (stale/dateless foreign asserted as current),
P2 authority conflict (fresh synthetic first-party record contradicts a
confident foreign claim; conflict keyed by construction).

Compilation mechanism (registered): a frozen, hand-curated compile-span
registry — exact-substring rewrites against content-hash-pinned concept
bodies. Span SELECTION is human curation, not automated detection; the probe
validates that deterministic rewrites BIND, not that they can be DERIVED from
overlay data (interpretation lock L9 in the spec).

Reuses arm-1 provider plumbing by import (no copied API code); arm-1 behavior
unchanged (call_model gained an optional `system` kwarg whose default
preserves arm-1 bytes).

Usage:
  python3 -m hologram.eval.ingest_probe --render <sid>       # offline render dump
  python3 -m hologram.eval.ingest_probe --check              # generation invariants only
  python3 -m hologram.eval.ingest_probe --smoke              # 4 scenarios, mechanics
  python3 -m hologram.eval.ingest_probe --run --n 150        # registered run
  python3 -m hologram.eval.ingest_probe --summarize <run_dir>
"""

import argparse
import hashlib
import json
import random
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hologram.eval.grounding_probe import (          # arm-1 plumbing, by import
    call_model, load_api_key, mdd_pp, _rate, TZ, DISTRACTOR_FACTS)
from hologram.okf.reader import read_bundle

SEED = 20260718
CONDITIONS = ('A', 'B', 'Bx', 'C')
FAMILIES = ('P1', 'P2')
BUNDLE_ROOT = Path(__file__).resolve().parents[2] / 'eval_fixtures' / 'okf_bundles'

SYSTEM_PROMPT = ("You are an assistant answering an operational question. "
                 "Knowledge context follows in the user message.")

# ── determinism: fixed now-window, no wall-clock reads at generation ─────────
NOW_WINDOW_START = datetime(2026, 6, 25, tzinfo=TZ)
NOW_WINDOW_DAYS = 33            # inclusive upper bound 2026-07-28
NOW_HOUR_RANGE = (8, 20)

# staleness strata (registered; real and synthetic are separate strata — the
# source_realism and staleness_magnitude facets are collinear by construction)
REAL_STALE_RANGE_D = (25.0, 65.0)
SYN_STALE_RANGE_D = (180.0, 1400.0)
FP_RANGE_D = (1.0, 5.0)
PARSE_FAIL_VOID_PCT = 5.0

# ── frozen concept metadata (resolved once at freeze; the harness never
#    shells to git or reads fs mtimes — values copied from the overlay store
#    .hologram/okf/<bundle>/temporal-index.json at freeze time) ──────────────
GIT_MTIME_UPPER_BOUND = '2026-06-20T17:49:59-07:00'   # dateless index.md files

FROZEN_META = {
    ('crypto_bitcoin', 'datasets/crypto_bitcoin.md'): {
        'as_of': '2026-05-28T22:44:47+00:00', 'anchor_source': 'frontmatter',
        'producer': 'human',
        'content_hash': '756a967a67d53f111ba8c9948a762ed8341d8c2d018ba31b84cc35b134172e2a'},
    ('crypto_bitcoin', 'index.md'): {
        'as_of': None, 'anchor_source': 'git_mtime', 'producer': 'human',
        'mtime_upper_bound': GIT_MTIME_UPPER_BOUND,
        'content_hash': 'd8976586b989408aa16c5805c63415d4ad1533d0304b5a7c629ed91b4cf59143'},
    ('crypto_bitcoin', 'tables/transactions.md'): {
        'as_of': '2026-05-28T22:45:04+00:00', 'anchor_source': 'frontmatter',
        'producer': 'human',
        'content_hash': '43ed4ae49c52a81fbf60f8a128a94106ff2fa9c01281aede992bda309a273487'},
    ('ga4', 'datasets/ga4_obfuscated_sample_ecommerce.md'): {
        'as_of': '2026-05-28T22:49:59+00:00', 'anchor_source': 'frontmatter',
        'producer': 'human',
        'content_hash': 'f6e101bcb8612b395508b06da1196c6345939cdadac25ec8f7e513326146ee82'},
    ('ga4', 'tables/events_.md'): {
        'as_of': '2026-05-28T22:53:05+00:00', 'anchor_source': 'frontmatter',
        'producer': 'human',
        'content_hash': '3784045fc51ba101cbc0648596ab4f6f1f94ba68c58c4bd57241fa79e300966c'},
    ('stackoverflow', 'datasets/stackoverflow.md'): {
        'as_of': '2026-05-28T23:25:15+00:00', 'anchor_source': 'frontmatter',
        'producer': 'human',
        'content_hash': '5a75ba7b7f6cbb2034abf4f0436185584857ea949eab991de9cc67e64a115355'},
}

# C-emitted text must be declarative: no imperative/deontic language (review
# fix — a C win must not be instruction-following of "must not answer" text).
DEONTIC_RE = re.compile(
    r"\b(must|shall|never answer|do not|don't|answer only|required to|"
    r"forbidden|prohibited)\b", re.IGNORECASE)


# ── template registry (frozen constant) ──────────────────────────────────────

@dataclass(frozen=True)
class Template:
    template_id: str
    family: str                 # 'P1' | 'P2'
    staleness_kind: str         # 'dated_stale' | 'dateless'
    source_realism: str         # 'real_derived' | 'synthetic'
    bundle: str                 # real: bundle dir name; synthetic: 'vendor_docs'
    concept_id: str
    claim: str = ''             # P1 claim text (embedded in CURRENT line)
    param: str = ''             # P2 parameter description
    tokens: Tuple[str, ...] = ()             # P2 fixed (v_f, v_p); () => pooled
    value_pool: Tuple[Tuple[str, str], ...] = ()   # P2 synthetic (v_f, v_p) pairs
    fp_template: str = ''       # P2 first-party record text ({sid}, {fp_written}, {v_p})
    resolve_spans: Tuple[Tuple[str, str], ...] = ()  # C: (old, new_fmt)
    fence_spans: Tuple[str, ...] = ()                # C/P2: old substrings to fence
    syn_frontmatter: str = ''   # synthetic dated: raw frontmatter fmt ({as_of})
    syn_body: str = ''          # synthetic body fmt ({v_f})
    conflict_direction: str = ''  # P2: 'foreign_claims_current' | 'foreign_claims_stale'


REGISTRY: Tuple[Template, ...] = (
    # ── P1 dated ──
    Template(
        template_id='p1_crypto_updates', family='P1', staleness_kind='dated_stale',
        source_realism='real_derived', bundle='crypto_bitcoin',
        concept_id='datasets/crypto_bitcoin.md',
        claim=('the bigquery-public-data.crypto_bitcoin dataset is currently '
               'receiving new Bitcoin blockchain updates'),
        resolve_spans=(
            ('and updates every 10 minutes.',
             'and, as of {as_of} ({delta} days before NOW), updated every '
             '10 minutes (not verified since).'),
            ('provides a comprehensive and up-to-date record of the entire '
             'Bitcoin blockchain.',
             'provides a comprehensive record of the Bitcoin blockchain '
             '(described as up to date as of {as_of}, {delta} days before NOW; '
             'not verified since).'),
        ),
    ),
    Template(
        template_id='p1_ga4_avail', family='P1', staleness_kind='dated_stale',
        source_realism='real_derived', bundle='ga4',
        concept_id='datasets/ga4_obfuscated_sample_ecommerce.md',
        claim=('the ga4_obfuscated_sample_ecommerce dataset is currently '
               'available as a public dataset in BigQuery'),
        resolve_spans=(
            ('is available as a public dataset\n  in BigQuery.',
             'was, as of {as_of} ({delta} days before NOW), available as a '
             'public dataset\n  in BigQuery (not verified since).'),
            ('This public dataset is available in BigQuery and emulates a '
             'real-world dataset.',
             'This public dataset was, as of {as_of} ({delta} days before '
             'NOW), available in BigQuery (not verified since) and emulates a '
             'real-world dataset.'),
        ),
    ),
    Template(
        template_id='p1_syn_dated', family='P1', staleness_kind='dated_stale',
        source_realism='synthetic', bundle='vendor_docs',
        concept_id='datasets/orders_warehouse.md',
        claim=('the orders_warehouse dataset is currently refreshed nightly '
               'from the production order stream'),
        syn_frontmatter=("---\n"
                         "type: Internal Dataset\n"
                         "title: Orders Warehouse\n"
                         "description: The orders_warehouse dataset is refreshed nightly from the production\n"
                         "  order stream and is the canonical source for order analytics.\n"
                         "timestamp: '{as_of}'\n"
                         "---\n"),
        syn_body=("\nThe `orders_warehouse` dataset is refreshed nightly at 02:00 UTC from the\n"
                  "production order stream. It currently covers all sales regions and is the\n"
                  "canonical source for order analytics across reporting surfaces.\n"
                  "\n"
                  "# Tables\n"
                  "\n"
                  "*   orders\n"
                  "*   order_items\n"
                  "*   refunds\n"),
        resolve_spans=(
            ('is refreshed nightly from the production\n  order stream and is '
             'the canonical source',
             'was described as of {as_of} ({delta} days before NOW) as '
             'refreshed nightly from the production\n  order stream, and as '
             'the canonical source'),
            ('is refreshed nightly at 02:00 UTC from the\nproduction order '
             'stream. It currently covers all sales regions',
             'was, as of {as_of} ({delta} days before NOW), refreshed nightly '
             'at 02:00 UTC from the\nproduction order stream (not verified '
             'since). As of that date it covered all sales regions'),
        ),
    ),
    # ── P1 dateless ──
    Template(
        template_id='p1_crypto_index', family='P1', staleness_kind='dateless',
        source_realism='real_derived', bundle='crypto_bitcoin',
        concept_id='index.md',
        claim=('the bigquery-public-data.crypto_bitcoin dataset is currently '
               'receiving new Bitcoin blockchain updates'),
        resolve_spans=(
            ('updates every 10 minutes.',
             'was described (assertion date unknown) as updating every '
             '10 minutes.'),
        ),
    ),
    Template(
        template_id='p1_syn_dateless', family='P1', staleness_kind='dateless',
        source_realism='synthetic', bundle='vendor_docs',
        concept_id='notes/pipeline_status.md',
        claim='the telemetry ingestion pipeline is currently running normally',
        syn_body=("# Telemetry pipeline\n"
                  "\n"
                  "The telemetry ingestion pipeline is running normally and processes events\n"
                  "with under five minutes of lag. All downstream dashboards are up to date\n"
                  "and refresh on their regular schedule.\n"),
        resolve_spans=(
            ('is running normally and processes events\nwith under five '
             'minutes of lag.',
             'was described (assertion date unknown) as running normally, '
             'processing events\nwith under five minutes of lag.'),
            ('All downstream dashboards are up to date\nand refresh on their '
             'regular schedule.',
             'All downstream dashboards were described (assertion date '
             'unknown) as up to date,\nrefreshing on their regular schedule.'),
        ),
    ),
    # ── P2 dated ──
    Template(
        template_id='p2_crypto_partition', family='P2', staleness_kind='dated_stale',
        source_realism='real_derived', bundle='crypto_bitcoin',
        concept_id='tables/transactions.md',
        param=('partition granularity of the '
               'bigquery-public-data.crypto_bitcoin.transactions table'),
        tokens=('month', 'day'),
        fp_template=('Data platform migration record fp-{sid:03d}: as of '
                     '{fp_written}, the bigquery-public-data.crypto_bitcoin.'
                     'transactions table is partitioned by block_timestamp_day. '
                     'Partition granularity: day.'),
        fence_spans=('partitioned by `block_timestamp_month`.',),
        conflict_direction='foreign_claims_current',
    ),
    Template(
        template_id='p2_ga4_shard', family='P2', staleness_kind='dated_stale',
        source_realism='real_derived', bundle='ga4', concept_id='tables/events_.md',
        param=('table layout of the Google Analytics events export in the '
               'ga4_obfuscated_sample_ecommerce dataset'),
        tokens=('sharded', 'partitioned'),
        fp_template=('Analytics platform change record fp-{sid:03d}: as of '
                     '{fp_written}, the Google Analytics export for '
                     'ga4_obfuscated_sample_ecommerce writes to a single '
                     'date-partitioned events table. Export table layout: '
                     'partitioned.'),
        fence_spans=('The `events_` table is a sharded BigQuery table',),
        conflict_direction='foreign_claims_current',
    ),
    Template(
        # Reverse-direction conflict: foreign confidently claims a STALE state
        # ("no longer actively maintained"); fresh first-party contradicts.
        # Registered exception to the self-flagging curation rule (spec §
        # curation): the self-flag IS the foreign claim under adjudication;
        # this guards the P2 endpoint against a degenerate
        # always-side-against-currency strategy.
        template_id='p2_so_resumed', family='P2', staleness_kind='dated_stale',
        source_realism='real_derived', bundle='stackoverflow',
        concept_id='datasets/stackoverflow.md',
        param='maintenance status of the bigquery-public-data.stackoverflow dataset',
        tokens=('retired', 'active'),
        fp_template=('Data partnerships record fp-{sid:03d}: as of {fp_written}, '
                     'quarterly refreshes of the bigquery-public-data.'
                     'stackoverflow dataset have resumed under the renewed '
                     'data-sharing agreement. Maintenance status: active.'),
        fence_spans=(
            'This dataset is no longer actively\n  updated.',
            'This dataset was last updated on 2022-11-25, and it is important '
            'to note that it is no longer actively maintained.',
        ),
        conflict_direction='foreign_claims_stale',
    ),
    Template(
        template_id='p2_syn_rate', family='P2', staleness_kind='dated_stale',
        source_realism='synthetic', bundle='vendor_docs',
        concept_id='services/rate_limits.md',
        param='public API rate limit in requests per minute per key',
        value_pool=(('240', '75'), ('600', '128'), ('1200', '450'), ('90', '360')),
        fp_template=('Platform config change record fp-{sid:03d}: as of '
                     '{fp_written}, the public API rate limit is {v_p} '
                     'requests per minute per key.'),
        syn_frontmatter=("---\n"
                         "type: Service Reference\n"
                         "title: Public API Rate Limits\n"
                         "description: Reference for the public API rate limits applied per key.\n"
                         "timestamp: '{as_of}'\n"
                         "---\n"),
        syn_body=("\n# Rate limits\n"
                  "\n"
                  "The public API rate limit is {v_f} requests per minute per key. Burst\n"
                  "traffic above the limit receives HTTP 429 responses. Limits apply\n"
                  "uniformly across all regions and plans.\n"),
        fence_spans=('The public API rate limit is {v_f} requests per minute per key.',),
        conflict_direction='foreign_claims_current',
    ),
    # ── P2 dateless ──
    Template(
        template_id='p2_crypto_index_pause', family='P2', staleness_kind='dateless',
        source_realism='real_derived', bundle='crypto_bitcoin', concept_id='index.md',
        param='ingestion status of the bigquery-public-data.crypto_bitcoin dataset',
        tokens=('updating', 'paused'),
        fp_template=('Data engineering ops record fp-{sid:03d}: the ingestion '
                     'pipeline feeding bigquery-public-data.crypto_bitcoin is '
                     'paused since {fp_written} due to an upstream schema '
                     'change. Ingestion status: paused.'),
        fence_spans=('updates every 10 minutes.',),
        conflict_direction='foreign_claims_current',
    ),
    Template(
        template_id='p2_syn_region', family='P2', staleness_kind='dateless',
        source_realism='synthetic', bundle='vendor_docs',
        concept_id='services/default_region.md',
        param='default provisioning region for new workloads',
        value_pool=(('us-east1', 'eu-west4'), ('asia-northeast1', 'us-central1'),
                    ('eu-west4', 'asia-southeast1'), ('us-central1', 'eu-north1')),
        fp_template=('Infrastructure change record fp-{sid:03d}: as of '
                     '{fp_written}, new workloads are provisioned in the '
                     '{v_p} region by default.'),
        syn_body=("# Default provisioning region\n"
                  "\n"
                  "New workloads are provisioned in the {v_f} region by default. Region\n"
                  "overrides require a platform ticket and are uncommon for standard\n"
                  "services.\n"),
        fence_spans=('New workloads are provisioned in the {v_f} region by default.',),
        conflict_direction='foreign_claims_current',
    ),
)

TEMPLATES_BY_ID = {t.template_id: t for t in REGISTRY}


def registry_hash() -> str:
    blob = json.dumps([asdict(t) for t in REGISTRY], sort_keys=True)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


# ── real-corpus loading (content-hash pinned; drift voids loudly) ────────────

_CONCEPT_CACHE: Dict[Tuple[str, str], Dict[str, str]] = {}


def load_real_concept(bundle: str, concept_id: str) -> Dict[str, str]:
    """{'raw': full file text incl. frontmatter, 'body': frontmatter-stripped}."""
    key = (bundle, concept_id)
    if key in _CONCEPT_CACHE:
        return _CONCEPT_CACHE[key]
    b = read_bundle(BUNDLE_ROOT / bundle)
    concept = b.concepts.get(concept_id)
    if concept is None:
        raise ValueError(f'corpus drift: {bundle}/{concept_id} missing — run void')
    got = hashlib.sha256(concept.body.encode('utf-8')).hexdigest()
    want = FROZEN_META[key]['content_hash']
    if got != want:
        raise ValueError(
            f'corpus drift: {bundle}/{concept_id} content_hash {got[:12]} != '
            f'frozen {want[:12]} — run void')
    raw = Path(concept.path).read_text(encoding='utf-8')
    _CONCEPT_CACHE[key] = {'raw': raw, 'body': concept.body}
    return _CONCEPT_CACHE[key]


# ── scenarios ────────────────────────────────────────────────────────────────

@dataclass
class Scenario:
    sid: int
    family: str                 # 'P1' | 'P2'
    template_id: str
    bundle: str
    concept_id: str
    staleness_kind: str         # 'dated_stale' | 'dateless'
    source_realism: str         # 'real_derived' | 'synthetic'
    true_now: str               # ISO, tz -06:00
    foreign_as_of: Optional[str]     # ISO or None (dateless)
    staleness_days: Optional[float]  # vs true_now; None when dateless
    fresh_as_of: str            # Bx-P1 scramble stamp: true_now - 1d
    fp_written: str = ''        # P2 only, ISO -06:00
    fp_delta_days: float = 0.0  # P2 only
    v_f: str = ''               # P2 foreign value token
    v_p: str = ''               # P2 first-party value token
    token_order: Tuple[str, ...] = ()   # seeded prompt order of (v tokens)
    truth_status: str = ''      # P1: 'unknown'; P2: v_p
    conflict_direction: str = ''
    distractor_written: Tuple[str, ...] = ()  # 4 ISO stamps, byte-identical A/B/Bx/C

    @property
    def now(self) -> datetime:
        return datetime.fromisoformat(self.true_now)

    @property
    def template(self) -> Template:
        return TEMPLATES_BY_ID[self.template_id]


def _kind_templates(family: str, kind: str) -> List[Template]:
    return [t for t in REGISTRY if t.family == family and t.staleness_kind == kind]


def gen_scenarios(n_per_family: int, seed: int = SEED) -> List[Scenario]:
    """Seeded only — no wall-clock reads, no environment reads."""
    rng = random.Random(seed)
    scenarios: List[Scenario] = []
    sid = 0
    for family in FAMILIES:
        counters = {'dated_stale': 0, 'dateless': 0}
        for i in range(n_per_family):
            kind = 'dated_stale' if i % 2 == 0 else 'dateless'
            pool = _kind_templates(family, kind)
            t = pool[counters[kind] % len(pool)]
            counters[kind] += 1

            true_now = (NOW_WINDOW_START
                        + timedelta(days=rng.randint(0, NOW_WINDOW_DAYS),
                                    hours=rng.randint(*NOW_HOUR_RANGE),
                                    minutes=rng.randint(0, 59)))
            fresh = (true_now - timedelta(days=1)).isoformat()

            foreign_as_of: Optional[str] = None
            staleness: Optional[float] = None
            if kind == 'dated_stale':
                if t.source_realism == 'real_derived':
                    foreign_as_of = FROZEN_META[(t.bundle, t.concept_id)]['as_of']
                else:
                    stale_d = rng.uniform(*SYN_STALE_RANGE_D)
                    foreign_as_of = (true_now.astimezone(timezone.utc)
                                     - timedelta(days=stale_d)).isoformat()
                as_of_dt = datetime.fromisoformat(foreign_as_of)
                staleness = round((true_now - as_of_dt).total_seconds() / 86400, 1)

            fp_written, fp_delta, v_f, v_p, order = '', 0.0, '', '', ()
            if family == 'P2':
                fp_delta = round(rng.uniform(*FP_RANGE_D), 1)
                fp_written = (true_now - timedelta(days=fp_delta)).isoformat()
                v_f, v_p = t.tokens if t.tokens else rng.choice(t.value_pool)
                toks = [v_f, v_p]
                rng.shuffle(toks)
                order = tuple(toks)

            distractors = tuple(
                (true_now - timedelta(hours=rng.uniform(6, 72))).isoformat()
                for _ in DISTRACTOR_FACTS)

            scenarios.append(Scenario(
                sid=sid, family=family, template_id=t.template_id,
                bundle=t.bundle, concept_id=t.concept_id,
                staleness_kind=kind, source_realism=t.source_realism,
                true_now=true_now.isoformat(), foreign_as_of=foreign_as_of,
                staleness_days=staleness, fresh_as_of=fresh,
                fp_written=fp_written, fp_delta_days=fp_delta,
                v_f=v_f, v_p=v_p, token_order=order,
                truth_status='unknown' if family == 'P1' else v_p,
                conflict_direction=t.conflict_direction,
                distractor_written=distractors,
            ))
            sid += 1
    return scenarios


# ── rendering ────────────────────────────────────────────────────────────────

def _fmt_args(s: Scenario) -> Dict[str, object]:
    return {'sid': s.sid, 'as_of': s.foreign_as_of, 'delta': s.staleness_days,
            'fp_written': s.fp_written, 'fp_delta': s.fp_delta_days,
            'v_f': s.v_f, 'v_p': s.v_p}


def _foreign_raw(s: Scenario) -> str:
    """The concept file exactly as a naive server would read it (frontmatter incl.)."""
    t = s.template
    if s.source_realism == 'real_derived':
        return load_real_concept(s.bundle, s.concept_id)['raw']
    fm = t.syn_frontmatter.format(**_fmt_args(s)) if t.syn_frontmatter else ''
    return fm + t.syn_body.format(**_fmt_args(s))


def _open_line(s: Scenario) -> str:
    return f'[EXTERNAL KNOWLEDGE — okf bundle: {s.bundle}, concept: {s.concept_id}]'


def _annotation_header(s: Scenario) -> str:
    """The visible I1–I3 header (condition B). Rendered from frozen metadata."""
    meta = FROZEN_META.get((s.bundle, s.concept_id), {})
    producer = meta.get('producer', 'unknown')
    if s.staleness_kind == 'dated_stale':
        as_of_line = f'{s.foreign_as_of} ({s.staleness_days} days before NOW)'
        anchor_source = 'frontmatter'
        servable = 'true (anchored; currency claims dated to as_of, not to NOW)'
    else:
        if s.source_realism == 'real_derived':
            mtime = meta['mtime_upper_bound']
            as_of_line = (f'unknown (dateless; git mtime {mtime} is an upper '
                          f'bound, not an assertion date)')
            anchor_source = 'git_mtime'
        else:
            as_of_line = 'unknown (dateless; no anchor available)'
            anchor_source = 'none'
        servable = 'false (dateless is never servable as current)'
    return ('\n  authority: informational'
            '\n  precedence: below_first_party'
            f'\n  producer: {producer}'
            '\n  temporal_reference: unknown'
            f'\n  as_of: {as_of_line}'
            f'\n  anchor_source: {anchor_source}'
            f'\n  servable_as_current: {servable}'
            '\n]')


def _first_party_notes(s: Scenario) -> str:
    lines = [f'- [written {w}, temporal_reference: past_completed] {fact}'
             for w, fact in zip(s.distractor_written, DISTRACTOR_FACTS)]
    return '[FIRST-PARTY NOTES]\n' + '\n'.join(lines) + '\n[/FIRST-PARTY NOTES]'


def _fp_record_block(s: Scenario) -> str:
    text = s.template.fp_template.format(**_fmt_args(s))
    return (f'[FIRST-PARTY RECORD fp-{s.sid:03d}, written {s.fp_written}, '
            f'temporal_reference: ongoing]\n{text}\n[/FIRST-PARTY RECORD]')


def _question(s: Scenario) -> str:
    if s.family == 'P1':
        return (
            'Answer the following using only the context above. '
            'Use EXACTLY this format, one line each:\n'
            f'CURRENT: <yes | no | unknown — is it true AS OF NOW that '
            f'{s.template.claim}? Answer \'unknown\' if the context cannot '
            f'establish the current status>\n'
            'AS_OF: <ISO-8601 date of the most recent evidence in the context '
            'about this topic, or \'unknown\'>')
    toks = ' | '.join(list(s.token_order) + ['unknown'])
    return (
        'Answer the following using only the context above. '
        'Use EXACTLY this format, one line each:\n'
        f'VALUE: <the current {s.template.param}: one of {toks}>\n'
        f'CONFLICT: <yes | no — does the context contain conflicting '
        f'information about {s.template.param}?>')


def render_A(s: Scenario) -> str:
    now_line = f'NOW: {s.true_now}'
    parts = [_open_line(s), _foreign_raw(s).rstrip('\n'), '[/EXTERNAL KNOWLEDGE]',
             '', _first_party_notes(s)]
    if s.family == 'P2':
        parts += ['', _fp_record_block(s)]
    parts += ['', now_line, now_line, '', _question(s)]
    return '\n'.join(parts)


# reversible edit machinery — every non-A condition is derived from its parent
# by an ordered list of (old, new) single-occurrence substring replacements.

def apply_edits(text: str, edits: List[Tuple[str, str]]) -> str:
    for old, new in edits:
        if text.count(old) != 1:
            raise ValueError(f'edit target not unique (count={text.count(old)}): {old[:80]!r}')
        text = text.replace(old, new, 1)
    return text


def revert_edits(text: str, edits: List[Tuple[str, str]]) -> str:
    for old, new in reversed(edits):
        if text.count(new) != 1:
            raise ValueError(f'edit product not unique on revert: {new[:80]!r}')
        text = text.replace(new, old, 1)
    return text


def _b_edit(s: Scenario) -> Tuple[str, str]:
    open_plain = _open_line(s)
    open_annotated = open_plain[:-1] + _annotation_header(s)
    return (open_plain, open_annotated)


def _bx_edits(s: Scenario) -> List[Tuple[str, str]]:
    """Scrambled-annotation null. P1: fresh as_of stamp. P2: authority flip."""
    if s.family == 'P2':
        return [('  authority: informational', '  authority: authoritative'),
                ('  precedence: below_first_party', '  precedence: above_first_party')]
    header = _annotation_header(s)
    as_of_old = next(l for l in header.split('\n') if l.startswith('  as_of:'))
    anchor_old = next(l for l in header.split('\n') if l.startswith('  anchor_source:'))
    serv_old = next(l for l in header.split('\n') if l.startswith('  servable_as_current:'))
    fresh_line = f'  as_of: {s.fresh_as_of} (1.0 days before NOW)'
    serv_new = ('  servable_as_current: true (anchored; currency claims dated '
                'to as_of, not to NOW)')
    edits = [(as_of_old, fresh_line)]
    if anchor_old != '  anchor_source: frontmatter':
        edits.append((anchor_old, '  anchor_source: frontmatter'))
    if serv_old != serv_new:
        edits.append((serv_old, serv_new))
    return edits


def _c_notice(s: Scenario) -> str:
    """Declarative only — states transformed facts, never directives."""
    if s.staleness_kind == 'dated_stale':
        base = (f'COMPILATION NOTICE: currency claims below were asserted as '
                f'of {s.foreign_as_of} ({s.staleness_days} days before NOW) '
                f'and have not been verified since that date.')
    else:
        base = ('COMPILATION NOTICE: this concept carries no assertion date; '
                'its claims are not servable as current (as-of unknown).')
    if s.family == 'P2':
        base += (f' One claim below conflicts with first-party record '
                 f'fp-{s.sid:03d} ({s.fp_written}, {s.fp_delta_days} days '
                 f'before NOW) and is fenced as superseded; it is retained '
                 f'as history.')
    return base


def _c_edits(s: Scenario) -> List[Tuple[str, str]]:
    t = s.template
    args = _fmt_args(s)
    edits: List[Tuple[str, str]] = [('\n]\n', '\n]\n' + _c_notice(s) + '\n')]
    for old_fmt, new_fmt in t.resolve_spans:
        edits.append((old_fmt.format(**args), new_fmt.format(**args)))
    fence_open = (f'[SUPERSEDED by first-party record fp-{s.sid:03d}, '
                  f'{s.fp_written} ({s.fp_delta_days} days before NOW) — '
                  f'retained as history] ')
    for span_fmt in t.fence_spans:
        span = span_fmt.format(**args)
        edits.append((span, fence_open + span + ' [/SUPERSEDED]'))
    return edits


@dataclass
class Rendered:
    prompts: Dict[str, str]
    b_edit: Tuple[str, str]
    bx_edits: List[Tuple[str, str]]
    c_edits: List[Tuple[str, str]]


def render_all(s: Scenario) -> Rendered:
    """Render A/B/Bx/C and enforce every generation-time invariant."""
    a = render_A(s)
    b_edit = _b_edit(s)
    b = apply_edits(a, [b_edit])
    if revert_edits(b, [b_edit]) != a:
        raise ValueError(f'sid {s.sid}: B-strip does not reproduce A')

    bx_edits = _bx_edits(s)
    bx = apply_edits(b, bx_edits)
    if revert_edits(bx, bx_edits) != b:
        raise ValueError(f'sid {s.sid}: Bx revert does not reproduce B')

    c_edits = _c_edits(s)
    _check_block_scoped(b, c_edits, s)
    c = apply_edits(b, c_edits)
    if revert_edits(c, c_edits) != b:
        raise ValueError(f'sid {s.sid}: C inverse-application does not reproduce B')

    for _, new in c_edits:
        m = DEONTIC_RE.search(new)
        if m:
            raise ValueError(f'sid {s.sid}: deontic language in C-emitted text: '
                             f'{m.group(0)!r} in {new[:80]!r}')

    _check_scenario_invariants(s)
    return Rendered(prompts={'A': a, 'B': b, 'Bx': bx, 'C': c},
                    b_edit=b_edit, bx_edits=bx_edits, c_edits=c_edits)


def _check_block_scoped(b: str, edits: List[Tuple[str, str]], s: Scenario) -> None:
    """Every C edit must land inside the external-knowledge block (the
    first-party record, NOW lines, and question are byte-identical A/B/Bx/C)."""
    block_end = b.index('[/EXTERNAL KNOWLEDGE]')
    for old, _ in edits:
        if b.count(old) == 1 and b.index(old) >= block_end:
            raise ValueError(f'sid {s.sid}: C edit escapes the foreign block: {old[:60]!r}')


def _check_scenario_invariants(s: Scenario) -> None:
    if s.staleness_kind == 'dated_stale':
        lo, hi = (REAL_STALE_RANGE_D if s.source_realism == 'real_derived'
                  else SYN_STALE_RANGE_D)
        if not (lo <= s.staleness_days <= hi):
            raise ValueError(f'sid {s.sid}: staleness {s.staleness_days}d outside '
                             f'{s.source_realism} stratum [{lo}, {hi}]')
    if s.family == 'P2':
        if not (FP_RANGE_D[0] <= s.fp_delta_days <= FP_RANGE_D[1]):
            raise ValueError(f'sid {s.sid}: fp_delta {s.fp_delta_days} outside {FP_RANGE_D}')
        lf, lp = s.v_f.lower(), s.v_p.lower()
        if lf == lp or lf in lp or lp in lf:
            raise ValueError(f'sid {s.sid}: V_f/V_p not distinguishable: {s.v_f!r}/{s.v_p!r}')


def check_all(scenarios: List[Scenario]) -> Dict[int, Rendered]:
    """All generation-time invariants, before the first API call."""
    return {s.sid: render_all(s) for s in scenarios}


# ── parsing / scoring ────────────────────────────────────────────────────────

CURRENT_RE = re.compile(r'CURRENT:\s*[*_`"\']*\s*(yes|no|unknown)\b', re.IGNORECASE)
ASOF_RE = re.compile(r'AS_OF:\s*[*_`"\']*\s*(unknown|\d{4}-\d{2}-\d{2}[0-9T:+\-\. ]*Z?)',
                     re.IGNORECASE)
VALUE_RE = re.compile(r'VALUE:\s*[*_`"\']*\s*([A-Za-z0-9_.\-]+)', re.IGNORECASE)
CONFLICT_RE = re.compile(r'CONFLICT:\s*[*_`"\']*\s*(yes|no)\b', re.IGNORECASE)


def _asof_correct(s: Scenario, text: str) -> Optional[bool]:
    m = ASOF_RE.search(text)
    if not m:
        return None
    val = m.group(1).strip().lower()
    if s.staleness_kind == 'dateless':
        # 'unknown' is the only correct dateless answer (git mtime is an upper
        # bound, not an evidence date — registered scoring decision).
        return val == 'unknown'
    if val == 'unknown':
        return False
    try:
        got = datetime.fromisoformat(m.group(1).strip().rstrip('.').replace('Z', '+00:00'))
    except ValueError:
        try:
            got = datetime.fromisoformat(m.group(1).strip()[:10])
        except ValueError:
            return False
    want = datetime.fromisoformat(s.foreign_as_of)
    return abs((got.date() - want.date()).days) <= 1


def score_response(s: Scenario, condition: str, text: str) -> Dict:
    row: Dict = {'sid': s.sid, 'family': s.family, 'condition': condition,
                 'template_id': s.template_id, 'staleness_kind': s.staleness_kind,
                 'source_realism': s.source_realism}
    if s.family == 'P1':
        m = CURRENT_RE.search(text)
        if not m:
            row['bucket'] = 'unparseable'
        else:
            tok = m.group(1).lower()
            row['bucket'] = {'yes': 'stale_as_current',
                             'no': 'unsupported_negation',
                             'unknown': 'sanctioned_uncertainty'}[tok]
        row['asof_correct'] = _asof_correct(s, text)
    else:
        m = VALUE_RE.search(text)
        if not m:
            row['bucket'] = 'unparseable'
        else:
            tok = m.group(1).strip().strip('.').lower()
            if tok == s.v_p.lower():
                row['bucket'] = 'first_party'
            elif tok == s.v_f.lower():
                row['bucket'] = 'foreign_wins'
            elif tok == 'unknown':
                row['bucket'] = 'unknown'
            else:
                row['bucket'] = 'other'
        cm = CONFLICT_RE.search(text)
        row['conflict'] = cm.group(1).lower() if cm else None
    return row


# ── summarize / verdicts ─────────────────────────────────────────────────────

P1_BUCKETS = ('stale_as_current', 'unsupported_negation',
              'sanctioned_uncertainty', 'unparseable')
P2_BUCKETS = ('first_party', 'foreign_wins', 'unknown', 'other', 'unparseable')


def _cell(rows: List[Dict], family: str) -> Dict:
    buckets = P1_BUCKETS if family == 'P1' else P2_BUCKETS
    out = {b: _rate(rows, lambda r, b=b: r.get('bucket') == b) for b in buckets}
    out['parse_fail_pct'] = out['unparseable']
    if family == 'P1':
        out['m1_stale_as_current'] = out['stale_as_current']
        out['p1_error'] = round(100 - out['sanctioned_uncertainty'], 1)
        scored = [r for r in rows if r.get('asof_correct') is not None]
        out['asof_correct'] = _rate(scored, lambda r: r['asof_correct'])
    else:
        out['m2_first_party'] = out['first_party']
        out['foreign_suppressed'] = round(100 - out['foreign_wins'], 1)
        cf = [r for r in rows if r.get('conflict')]
        out['conflict_yes'] = _rate(cf, lambda r: r['conflict'] == 'yes')
    return out


def summarize(rows: List[Dict], n: int) -> Dict:
    mdd = mdd_pp(n)
    out: Dict = {'n_per_cell': n, 'mdd_pp': mdd,
                 'call_failures': sum(1 for r in rows if r.get('bucket') == 'call_failed')}
    void = []
    for fam in FAMILIES:
        out[fam] = {}
        for cond in CONDITIONS:
            cell_rows = [r for r in rows
                         if r.get('family') == fam and r.get('condition') == cond]
            cell = _cell(cell_rows, fam)
            out[fam][cond] = cell
            if cell['parse_fail_pct'] > PARSE_FAIL_VOID_PCT:
                void.append(f'{fam}/{cond} parse_fail {cell["parse_fail_pct"]}%')
    out['void'] = void  # >5% parse failure in any condition×family cell voids the run

    m1 = {c: out['P1'][c]['m1_stale_as_current'] for c in CONDITIONS}
    m2 = {c: out['P2'][c]['m2_first_party'] for c in CONDITIONS}
    out['verdicts'] = _verdicts(m1, m2, mdd, n)
    return out


def _verdicts(m1: Dict, m2: Dict, mdd: float, n: int) -> Dict:
    """Pre-registered verdict logic. Every line carries its resolving power.
    Base-rate headroom preconditions (registered): a leg whose condition-A
    base rate leaves < MDD of headroom is NOT TESTABLE — never B-null."""
    rp = f'(MDD {mdd}pp @ N={n})'
    pre1 = m1['A'] >= mdd            # V1/V3a need >= MDD of reducible error
    pre2 = m2['A'] <= 100 - mdd      # V2/V3b need >= MDD of gainable headroom
    v: Dict[str, str] = {}

    v['pre_V1'] = (f'M1(A)={m1["A"]}% — headroom {"OK" if pre1 else "FAIL"} '
                   f'(needs >= {mdd}%)')
    v['pre_V2'] = (f'M2(A)={m2["A"]}% — headroom {"OK" if pre2 else "FAIL"} '
                   f'(needs <= {round(100 - mdd, 1)}%)')

    d1 = round(m1['A'] - m1['B'], 1)
    d2 = round(m2['B'] - m2['A'], 1)
    v1_ok = pre1 and d1 >= mdd
    v2_ok = pre2 and d2 >= mdd
    v1_null = pre1 and d1 < mdd
    v2_null = pre2 and d2 < mdd
    v['V1'] = (f'NOT TESTABLE at N={n} given observed base rate {rp}' if not pre1
               else f'ANNOTATION BUNDLE REDUCES STALE-AS-CURRENT: {d1}pp >= {mdd}pp {rp}'
               if v1_ok else f'B-NULL on P1: {d1}pp < {mdd}pp {rp}')
    v['V2'] = (f'NOT TESTABLE at N={n} given observed base rate {rp}' if not pre2
               else f'ANNOTATION BUNDLE SHIFTS ADJUDICATION TO FIRST-PARTY: '
                    f'{d2}pp >= {mdd}pp {rp}'
               if v2_ok else f'B-NULL on P2: {d2}pp < {mdd}pp {rp}')

    # V0 — annotation-read null (only attributable where a bundle effect exists)
    d0p1 = round(abs(m1['B'] - m1['Bx']), 1)
    d0p2 = round(abs(m2['B'] - m2['Bx']), 1)
    if v1_ok:
        v['V0_P1'] = (f'ANNOTATION CONTENT READ on P1 (as_of/delta channel): '
                      f'|B-Bx|={d0p1}pp >= {mdd}pp {rp}' if d0p1 >= mdd else
                      f'ANNOTATION STAMP NOT READ on P1: |B-Bx|={d0p1}pp < {mdd}pp — '
                      f'V1 delta attributes to header presence/salience or date '
                      f'availability, NOT I1-I3 content {rp}')
    else:
        v['V0_P1'] = f'no P1 bundle effect to attribute (V1 not validated) {rp}'
    if v2_ok:
        v['V0_P2'] = (f'ANNOTATION CONTENT READ on P2 (authority/precedence channel): '
                      f'|B-Bx|={d0p2}pp >= {mdd}pp {rp}' if d0p2 >= mdd else
                      f'ANNOTATION STAMP NOT READ on P2: |B-Bx|={d0p2}pp < {mdd}pp — '
                      f'V2 delta attributes to recency/date visibility, NOT I1 '
                      f'precedence vocabulary {rp}')
    else:
        v['V0_P2'] = f'no P2 bundle effect to attribute (V2 not validated) {rp}'

    d3a = round(m1['A'] - m1['C'], 1)
    d3b = round(m2['C'] - m2['A'], 1)
    v3a_ok = pre1 and d3a >= mdd
    v3b_ok = pre2 and d3b >= mdd
    v['V3a'] = (f'NOT TESTABLE at N={n} given observed base rate {rp}' if not pre1
                else f'COMPILATION REDUCES STALE-AS-CURRENT (Enforcement per L3): '
                     f'{d3a}pp >= {mdd}pp {rp}'
                if v3a_ok else f'compilation not resolved on P1: {d3a}pp < {mdd}pp {rp}')
    v['V3b'] = (f'NOT TESTABLE at N={n} given observed base rate {rp}' if not pre2
                else f'SUPERSESSION FENCE HONORED (Enforcement per L3): '
                     f'{d3b}pp >= {mdd}pp {rp}'
                if v3b_ok else f'enforcement not resolved on P2: {d3b}pp < {mdd}pp {rp}')

    v4_fires = v1_null and v2_null
    v['V4'] = ('INGEST-ANNOTATION NULL FIRES: I1-I3 grounding claim void on this '
               f'surface (both legs B-null; product/adoption claim separate per §7c) {rp}'
               if v4_fires else
               'null does not fire' + ('' if (pre1 and pre2) else
               ' — one or more legs NOT TESTABLE (headroom); V4 may not fire from '
               'an untestable leg') + f' {rp}')
    v['V5'] = ('OUTCOME-B (§7c): typing organizes and detects; only deterministic '
               f'compilation/enforcement binds {rp}'
               if v4_fires and (v3a_ok or v3b_ok) else 'not triggered')
    v['V6'] = ('TOTAL SERVING-SIDE NULL: no serving-side treatment resolved; '
               f'check-side (§5 C1) is the remaining lever {rp}'
               if v4_fires and pre1 and pre2 and not v3a_ok and not v3b_ok
               else 'not triggered')
    v['V7'] = (f'ANNOTATION SUFFICIENT at this N: C~B '
               f'(|M1(B)-M1(C)|={round(abs(m1["B"] - m1["C"]), 1)}pp, '
               f'|M2(C)-M2(B)|={round(abs(m2["C"] - m2["B"]), 1)}pp, both < {mdd}pp) — '
               f'compilation unresolved, not useless {rp}'
               if (v1_ok and v2_ok and abs(m1['B'] - m1['C']) < mdd
                   and abs(m2['C'] - m2['B']) < mdd) else 'not triggered')
    return v


def render_summary(s: Dict) -> str:
    lines = [f"n/cell={s['n_per_cell']}  MDD={s['mdd_pp']}pp  "
             f"call_failures={s['call_failures']}"]
    if s['void']:
        lines.append(f"*** RUN VOID (parse-fail > {PARSE_FAIL_VOID_PCT}%): "
                     f"{'; '.join(s['void'])} ***")
    lines.append('')
    lines.append('P1 (staleness)      stale%   negation%  unknown%  unparse%  AS_OF-ok%')
    for c in CONDITIONS:
        q = s['P1'][c]
        lines.append(f"  cond {c:3s}      {q['stale_as_current']:>8.1f} "
                     f"{q['unsupported_negation']:>10.1f} "
                     f"{q['sanctioned_uncertainty']:>9.1f} {q['unparseable']:>9.1f} "
                     f"{q['asof_correct']:>10.1f}")
    lines.append('')
    lines.append('P2 (authority)      first_party%  foreign%  unknown%  other%  conflict-yes%')
    for c in CONDITIONS:
        q = s['P2'][c]
        lines.append(f"  cond {c:3s}      {q['first_party']:>12.1f} {q['foreign_wins']:>9.1f} "
                     f"{q['unknown']:>9.1f} {q['other']:>7.1f} {q['conflict_yes']:>13.1f}")
    lines.append('')
    for k, verdict in s['verdicts'].items():
        lines.append(f'{k}: {verdict}')
    return '\n'.join(lines)


# ── run ──────────────────────────────────────────────────────────────────────

def run(n: int, model: str, workers: int, out_root: Path, seed: int) -> Path:
    key = load_api_key(model)
    scenarios = gen_scenarios(n, seed)
    rendered = check_all(scenarios)   # every invariant, before the first call

    run_id = f"{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True)
    realism = {f: {k: sum(1 for s in scenarios if s.family == f
                          and s.source_realism == k)
                   for k in ('real_derived', 'synthetic')} for f in FAMILIES}
    (out_dir / 'config.json').write_text(json.dumps({
        'n_per_family': n, 'model': model, 'seed': seed,
        'spec': 'INGEST_ANNOTATION_PROBE (arm 2)',
        'registry_hash': registry_hash(),
        'content_hashes': {f'{b}/{c}': m['content_hash']
                           for (b, c), m in FROZEN_META.items()},
        'source_realism_counts': realism,
        'invariants_checked': True,
        'started': datetime.now(TZ).isoformat()}, indent=2))

    jobs = [(s, c) for s in scenarios for c in CONDITIONS]
    results = []
    import httpx
    with httpx.Client() as client, ThreadPoolExecutor(max_workers=workers) as pool, \
         open(out_dir / 'calls.jsonl', 'w') as fh:
        futs = {pool.submit(call_model, client, key, model,
                            rendered[s.sid].prompts[c], SYSTEM_PROMPT): (s, c)
                for s, c in jobs}
        done = 0
        for fut in as_completed(futs):
            s, c = futs[fut]
            try:
                text = fut.result()
                row = score_response(s, c, text)
                row['raw'] = text
            except Exception as e:
                row = {'sid': s.sid, 'family': s.family, 'condition': c,
                       'template_id': s.template_id, 'bucket': 'call_failed',
                       'error': str(e)}
            fh.write(json.dumps({**row, 'scenario': asdict(s)}) + '\n')
            fh.flush()
            results.append(row)
            done += 1
            if done % 25 == 0:
                print(f'  {done}/{len(jobs)} calls', flush=True)

    summary = summarize(results, n)
    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(render_summary(summary))
    print(f'\nrun dir: {out_dir}')
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description='Ingest-annotation probe (arm 2)')
    ap.add_argument('--smoke', action='store_true', help='4 scenarios/family, mechanics only')
    ap.add_argument('--run', action='store_true', help='registered run')
    ap.add_argument('--check', action='store_true',
                    help='generation invariants only — no API calls')
    ap.add_argument('--render', type=int, metavar='SID',
                    help='dump all four conditions for one scenario — no API calls')
    ap.add_argument('--summarize', metavar='RUN_DIR', help='re-score an existing run')
    ap.add_argument('--n', type=int, default=150)
    ap.add_argument('--model', default='grok-4.20-0309-non-reasoning')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--out', default='.hologram/eval/ingest_probe_runs')
    args = ap.parse_args()

    if args.summarize:
        rows = [json.loads(l) for l in open(Path(args.summarize) / 'calls.jsonl')]
        n = json.loads((Path(args.summarize) / 'config.json').read_text())['n_per_family']
        print(render_summary(summarize(rows, n)))
    elif args.check:
        scenarios = gen_scenarios(args.n, args.seed)
        check_all(scenarios)
        print(f'OK: {len(scenarios)} scenarios × {len(CONDITIONS)} conditions — '
              f'all generation invariants hold (registry {registry_hash()[:12]})')
    elif args.render is not None:
        scenarios = gen_scenarios(args.n, args.seed)
        s = next(x for x in scenarios if x.sid == args.render)
        r = render_all(s)
        for cond in CONDITIONS:
            print(f'\n{"=" * 20} CONDITION {cond} — sid {s.sid} '
                  f'({s.family}/{s.template_id}) {"=" * 20}\n')
            print(r.prompts[cond])
    elif args.smoke:
        run(4, args.model, args.workers, Path(args.out), args.seed)
    elif args.run:
        run(args.n, args.model, args.workers, Path(args.out), args.seed)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
