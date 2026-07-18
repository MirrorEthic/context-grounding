"""
Temporal-hygiene linter — the one codepath behind E6 (reject) and I2/I3 (annotate).

Detects the §2 temporal failure classes in text:
  T1  unanchored absolute   — bare clock (`19:45`), clock span (`19:45→23:05`),
                              date without offset (`2026-05-22`)
  T2  anchorless relative   — delta with no origin (`9h ago`, `yesterday`),
                              exempt when a full ISO anchor sits within
                              ANCHOR_PROXIMITY chars (the E1 emission pattern)
  T3  untyped reference     — frontmatter missing/invalid `temporal_reference`
  T4  ambient lexical       — undated night/urgency tokens (`probe night`),
                              exempt when the line carries any anchor

Two modes, one implementation (I6 — divergent implementations will drift):
  enforce()  — E6: our writes. Raises TemporalLintError on any finding.
  annotate() — I2: foreign reads. Same findings, returned as annotation;
               never rejects, per OKF permissive-consumption mandate.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


VALID_TEMPORAL_REFERENCES = {'past_completed', 'ongoing', 'scheduled', 'current'}
ANNOTATED_UNKNOWN = 'unknown'

# Full anchor per E2: date + time + offset. The only string class that passes clean.
ISO_ANCHOR_RE = re.compile(
    r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})'
)
DATE_ONLY_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b(?![T\d])')
BARE_CLOCK_RE = re.compile(
    r'\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[ap]\.?m\.?)?\b', re.IGNORECASE
)
RELATIVE_DELTA_RE = re.compile(
    r'\b\d+(?:\.\d+)?\s*'
    r'(?:h|hr|hrs|hour|hours|m|min|mins|minute|minutes|s|sec|secs|second|seconds|'
    r'd|day|days|w|wk|wks|week|weeks|mo|month|months|y|yr|yrs|year|years)'
    r'\s+ago\b', re.IGNORECASE
)
RELATIVE_WORD_RE = re.compile(
    r'\b(?:yesterday|tomorrow|tonight|last\s+night|last\s+(?:week|month|year)|'
    r'next\s+(?:week|month|year)|this\s+(?:morning|afternoon|evening)|'
    r'earlier\s+today|just\s+now)\b', re.IGNORECASE
)
AMBIENT_LEXICAL_RE = re.compile(
    r'\b(?:night|midnight|overnight|dawn|dusk|morning|evening|afternoon|'
    r'urgent|urgently|asap|end\s+of\s+day|eod)\b', re.IGNORECASE
)

# E1 allows `<ISO> (9h before now)`; a delta this close to a full anchor is anchored.
ANCHOR_PROXIMITY = 64

FENCED_CODE_RE = re.compile(r'^(```|~~~).*?^\1[^\S\n]*$', re.DOTALL | re.MULTILINE)
INLINE_CODE_RE = re.compile(r'`[^`\n]+`')


@dataclass
class LintFinding:
    code: str        # "T1" | "T2" | "T3" | "T4"
    kind: str        # e.g. "bare_clock", "anchorless_relative", "ambient_lexical"
    message: str
    line: int        # 1-indexed; 0 for frontmatter-level findings
    excerpt: str
    fix_hint: str = ''

    def to_dict(self) -> dict:
        return {
            'code': self.code, 'kind': self.kind, 'message': self.message,
            'line': self.line, 'excerpt': self.excerpt, 'fix_hint': self.fix_hint,
        }


class TemporalLintError(ValueError):
    """E6 rejection. Carries the findings so the write path can report them."""

    def __init__(self, findings: List[LintFinding]):
        self.findings = findings
        summary = '; '.join(f'{f.code}/{f.kind} L{f.line} "{f.excerpt}"' for f in findings[:5])
        more = f' (+{len(findings) - 5} more)' if len(findings) > 5 else ''
        super().__init__(f'temporal lint: {len(findings)} finding(s): {summary}{more}')


def _line_of(text: str, pos: int) -> int:
    return text.count('\n', 0, pos) + 1


def _line_bounds(text: str, pos: int) -> Tuple[int, int]:
    start = text.rfind('\n', 0, pos) + 1
    end = text.find('\n', pos)
    return start, len(text) if end == -1 else end


def _excerpt(text: str, start: int, end: int, radius: int = 20) -> str:
    lo, hi = max(0, start - radius), min(len(text), end + radius)
    return text[lo:hi].replace('\n', ' ').strip()


def _blank(text: str, spans) -> str:
    work = list(text)
    for s, e in spans:
        for i in range(s, e):
            if work[i] != '\n':
                work[i] = '\x00'
    return ''.join(work)


def lint_text(text: str) -> List[LintFinding]:
    """
    Pure text scan for T1/T2/T4. Frontmatter-level T3 lives in lint_record.

    Fenced code blocks and inline code spans are excluded: a date literal in
    an example query is not a temporal claim about the world (newlines are
    preserved so line numbers stay true).
    """
    text = _blank(text, [m.span() for m in FENCED_CODE_RE.finditer(text)])
    text = _blank(text, [m.span() for m in INLINE_CODE_RE.finditer(text)])
    findings: List[LintFinding] = []

    full_anchors = [m.span() for m in ISO_ANCHOR_RE.finditer(text)]
    # Blank full anchors so their clock component doesn't read as a bare clock.
    work = list(text)
    for s, e in full_anchors:
        work[s:e] = '\x00' * (e - s)
    work = ''.join(work)

    date_anchors = [m.span() for m in DATE_ONLY_RE.finditer(work)]
    all_anchor_spans = full_anchors + date_anchors

    def near_full_anchor(pos: int) -> bool:
        return any(abs(pos - s) <= ANCHOR_PROXIMITY or abs(pos - e) <= ANCHOR_PROXIMITY
                   for s, e in full_anchors)

    def line_has_anchor(pos: int) -> bool:
        ls, le = _line_bounds(text, pos)
        return any(s < le and e > ls for s, e in all_anchor_spans)

    for s, e in date_anchors:
        findings.append(LintFinding(
            'T1', 'date_without_offset',
            'date lacks time + UTC offset (E2)',
            _line_of(text, s), _excerpt(text, s, e),
            'expand to full ISO-8601 with offset, e.g. 2026-05-22T00:00:00-06:00',
        ))

    for m in BARE_CLOCK_RE.finditer(work):
        findings.append(LintFinding(
            'T1', 'bare_clock',
            'clock time with no date or offset (E2)',
            _line_of(text, m.start()), _excerpt(text, m.start(), m.end()),
            'attach full ISO-8601 date + offset',
        ))

    for regex, kind in ((RELATIVE_DELTA_RE, 'anchorless_relative'),
                        (RELATIVE_WORD_RE, 'relative_word')):
        for m in regex.finditer(work):
            if near_full_anchor(m.start()):
                continue
            findings.append(LintFinding(
                'T2', kind,
                'relative time with no absolute origin (E1)',
                _line_of(text, m.start()), _excerpt(text, m.start(), m.end()),
                'emit the absolute first: 2026-07-15T23:51-06:00 (9h before now)',
            ))

    for m in AMBIENT_LEXICAL_RE.finditer(work):
        if line_has_anchor(m.start()):
            continue
        findings.append(LintFinding(
            'T4', 'ambient_lexical',
            'ambient temporal token on an undated line (E5)',
            _line_of(text, m.start()), _excerpt(text, m.start(), m.end()),
            'date it or drop it: `probe night` -> `2026-07-15 evening session (completed)`',
        ))

    findings.sort(key=lambda f: f.line)
    return findings


def lint_record(body: str, frontmatter: Optional[Dict] = None) -> List[LintFinding]:
    """Text findings plus record-level T3 on the frontmatter."""
    findings = lint_text(body)
    fm = frontmatter or {}
    ref = fm.get('temporal_reference')
    if ref is None:
        findings.insert(0, LintFinding(
            'T3', 'missing_temporal_reference',
            'record carries no temporal_reference (E3)', 0, '(frontmatter)',
            f'add temporal_reference: one of {sorted(VALID_TEMPORAL_REFERENCES)}',
        ))
    elif ref not in VALID_TEMPORAL_REFERENCES:
        findings.insert(0, LintFinding(
            'T3', 'invalid_temporal_reference',
            f'temporal_reference "{ref}" not in {sorted(VALID_TEMPORAL_REFERENCES)}',
            0, str(ref), 'use one of the four E3 types',
        ))
    return findings


def parse_timestamp(raw) -> Tuple[Optional[str], bool]:
    """(iso_string, has_offset). Accepts ISO datetimes (Z ok) and bare dates."""
    if raw is None:
        return None, False
    if isinstance(raw, datetime):
        return raw.isoformat(), raw.tzinfo is not None
    s = str(raw).strip()
    try:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return dt.isoformat(), dt.tzinfo is not None
    except ValueError:
        return None, False


def enforce(body: str, frontmatter: Optional[Dict] = None) -> None:
    """E6 reject mode — our writes. Raises; does not warn."""
    findings = lint_record(body, frontmatter)
    if findings:
        raise TemporalLintError(findings)


def annotate(body: str, frontmatter: Optional[Dict] = None) -> Dict:
    """
    I2 annotate mode — foreign reads. Never rejects. Returns the consumer
    judgment for the overlay: same findings as enforce(), plus the temporal
    stamp derived from the producer's own frontmatter. Anchor fallbacks
    (git mtime) are the overlay's job; this stays pure.
    """
    fm = frontmatter or {}
    findings = lint_record(body, fm)
    as_of, has_offset = parse_timestamp(fm.get('timestamp'))
    ref = fm.get('temporal_reference')
    if ref not in VALID_TEMPORAL_REFERENCES:
        ref = ANNOTATED_UNKNOWN
    return {
        'findings': [f.to_dict() for f in findings],
        'temporal_reference': ref,
        'anchored': as_of is not None,
        'anchor_has_offset': has_offset,
        'as_of': as_of,
        'anchor_source': 'frontmatter' if as_of else None,
    }
