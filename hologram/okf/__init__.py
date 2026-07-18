"""
OKF ingest — Context Grounding Program §4b/§4c.

Read-only absorption of Google OKF v0.1 bundles (markdown + YAML frontmatter,
required `type`, optional `timestamp`, reserved index.md/log.md) into hologram's
typed grounding overlay. No exporter, per DECISION 4dff0cea409f68d8.

Modules:
  lint    — the ONE temporal-hygiene codepath (I6): reject mode for our writes
            (E6), annotate mode for foreign reads (I2/I3)
  reader  — permissive bundle walker; never raises on foreign content
  overlay — .hologram/okf/<bundle_id>/ store, per-concept keying (§4c)
  report  — audit report; lint section only, probe section gated (§7b)
"""

from .lint import LintFinding, TemporalLintError, lint_text, lint_record, enforce, annotate
from .reader import Bundle, Concept, LogEntry, read_bundle
from .overlay import IngestResult, ingest_bundle
from .report import build_report, render_text

__all__ = [
    'LintFinding', 'TemporalLintError', 'lint_text', 'lint_record', 'enforce', 'annotate',
    'Bundle', 'Concept', 'LogEntry', 'read_bundle',
    'IngestResult', 'ingest_bundle',
    'build_report', 'render_text',
]
