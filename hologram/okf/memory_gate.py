"""
E6 memory-write gate profile — the policy layer between hologram.okf.lint and
the cortex memory_add surface (~/.claude/mcp-memory/server.py).

Detection lives ENTIRELY in lint.py (I6: one temporal-hygiene codepath).
Invariant, grep-able: this module compiles no regex patterns — every finding
object originates in lint_text(). This module only decides what a finding
means for a memory write and how to say so to the model that wrote it.

Memory entries are not OKF concepts: they carry no frontmatter, so blanket
lint_record()/enforce() would fire T3/missing_temporal_reference on 100% of
writes. The profile instead:
  REJECT  T1 (unanchored absolutes), T2 (anchorless relatives) — the measured
          dominant pollution classes (corpus audit 2026-07-17: T1 in 1,070 of
          10,640 entries, T2 in 61) and the F1/F4 incident classes.
  WARN    T4 (ambient lexical) — annotate on the success message, don't block.
  T3      only when a temporal_reference argument is supplied and invalid;
          missing passes unless MEMORY_GATE_REQUIRE_T3=1.

Mode resolution (per call — reaches every live process without restart):
  1. MEMORY_DIR/GATE_OFF exists          -> off   (kill-switch, `touch` to arm)
  2. env MEMORY_GATE_MODE in off|log|enforce -> that
  3. MEMORY_DIR/gate_mode file contents      -> that
  4. default                                  -> enforce (fail-closed)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .lint import LintFinding, TemporalLintError, VALID_TEMPORAL_REFERENCES, lint_text

REJECT_CODES = {'T1', 'T2'}
WARN_CODES = {'T4'}
MODES = ('off', 'log', 'enforce')


class MemoryGateRejection(TemporalLintError):
    """Raised by the server when an enforced gate rejects a write.

    Subclasses TemporalLintError for isinstance-compatibility, but carries a
    pre-formatted model-facing message and dict findings (with 'field' tags).
    """

    def __init__(self, message: str, findings: List[Dict]):
        self.findings = findings
        ValueError.__init__(self, message)


@dataclass
class GateResult:
    verdict: str                      # 'pass' | 'pass_with_warnings' | 'reject' | 'off'
    mode: str                         # resolved mode this call ran under
    rejecting: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)
    message: Optional[str] = None     # rejection text (reject) or warn block


def lint_memory_fields(content: str, topic: str,
                       temporal_reference: Optional[str] = None,
                       require_temporal_reference: bool = False) -> List[Dict]:
    """Lint content and topic SEPARATELY (line numbers stay true per field)."""
    findings: List[Dict] = []
    for fname, text in (('content', content), ('topic', topic or '')):
        for f in lint_text(text):
            d = f.to_dict()
            d['field'] = fname
            findings.append(d)

    if temporal_reference is not None and temporal_reference not in VALID_TEMPORAL_REFERENCES:
        f = LintFinding(
            'T3', 'invalid_temporal_reference',
            f'temporal_reference "{temporal_reference}" not in {sorted(VALID_TEMPORAL_REFERENCES)}',
            0, str(temporal_reference), 'use one of the four E3 types')
        d = f.to_dict()
        d['field'] = 'temporal_reference'
        findings.append(d)
    elif temporal_reference is None and require_temporal_reference:
        f = LintFinding(
            'T3', 'missing_temporal_reference',
            'temporal_reference required by MEMORY_GATE_REQUIRE_T3', 0, '(argument)',
            f'pass temporal_reference: one of {sorted(VALID_TEMPORAL_REFERENCES)}')
        d = f.to_dict()
        d['field'] = 'temporal_reference'
        findings.append(d)
    return findings


def split_findings(findings: List[Dict]):
    rejecting = [f for f in findings if f['code'] in REJECT_CODES or f['code'] == 'T3']
    warnings = [f for f in findings if f['code'] in WARN_CODES]
    return rejecting, warnings


def resolve_mode(memory_dir: Path) -> str:
    if (memory_dir / 'GATE_OFF').exists():
        return 'off'
    env = os.environ.get('MEMORY_GATE_MODE', '').strip().lower()
    if env in MODES:
        return env
    try:
        file_mode = (memory_dir / 'gate_mode').read_text().strip().lower()
        if file_mode in MODES:
            return file_mode
    except OSError:
        pass
    return 'enforce'


def _finding_lines(findings: List[Dict]) -> List[str]:
    # Excerpts render inside backticks: inline code is exempt in lint_text,
    # so this message passes the very gate it announces.
    return [f"- [{f['code']}/{f['kind']}] {f['field']} L{f['line']}: "
            f"`{f['excerpt']}` — fix: {f['fix_hint']}" for f in findings]


def format_rejection(rejecting: List[Dict], warnings: List[Dict],
                     now: Optional[datetime] = None) -> str:
    stamp = (now or datetime.now().astimezone()).isoformat(timespec='seconds')
    lines = [f"memory_add REJECTED by temporal write-gate (E6) at {stamp}.",
             "Entry NOT stored (a copy is quarantined for forensics). Findings:"]
    lines += _finding_lines(rejecting)
    if warnings:
        lines.append("Non-blocking warnings:")
        lines += _finding_lines(warnings)
    lines.append(
        "Rewrite with every date/time as full ISO-8601 with offset "
        "(e.g. `2026-07-17T16:45:00-06:00`) and no anchorless relatives "
        "(`9h ago`, `yesterday`) outside code spans, then retry. "
        "Quoted examples of bad timestamps belong in `backticks` (code spans are exempt). "
        "Do not resubmit unchanged content.")
    return '\n'.join(lines)


def format_warnings(warnings: List[Dict]) -> str:
    return '\n'.join(["⚠ temporal warnings (T4 ambient — stored anyway):"]
                     + _finding_lines(warnings))


def gate_memory_add(content: str, topic: str, memory_dir: Path,
                    temporal_reference: Optional[str] = None,
                    now: Optional[datetime] = None) -> GateResult:
    """Pure decision — no file writes, no raises. The server owns side effects."""
    mode = resolve_mode(memory_dir)
    if mode == 'off':
        return GateResult(verdict='off', mode=mode)

    require_t3 = os.environ.get('MEMORY_GATE_REQUIRE_T3', '') == '1'
    findings = lint_memory_fields(content, topic, temporal_reference, require_t3)
    rejecting, warnings = split_findings(findings)

    if rejecting:
        return GateResult(verdict='reject', mode=mode, rejecting=rejecting,
                          warnings=warnings,
                          message=format_rejection(rejecting, warnings, now))
    if warnings:
        return GateResult(verdict='pass_with_warnings', mode=mode, warnings=warnings,
                          message=format_warnings(warnings))
    return GateResult(verdict='pass', mode=mode)
