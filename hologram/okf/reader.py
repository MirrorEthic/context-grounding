"""
OKF v0.1 bundle reader — permissive by spec, read-only by decision.

OKF mandates that consumers tolerate unknown types, unknown keys, and broken
links. Nothing in this module raises on foreign content: malformed frontmatter,
missing `type`, unparseable YAML all degrade to recorded parse notes on the
Bundle. Judgment about the content (temporal hygiene, authority, provenance)
belongs to the overlay, never to the parser.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml as _yaml
except ImportError:
    _yaml = None

FRONTMATTER_RE = re.compile(r'\A---\s*\n(.*?)\n---\s*\n?', re.DOTALL)
MD_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)\s]+)\)')
LOG_HEADING_RE = re.compile(r'^#{1,4}\s+(\d{4}-\d{2}-\d{2})\b(.*)$')
EXTERNAL_SCHEMES = ('http://', 'https://', 'mailto:', 'ftp://')


@dataclass
class Link:
    text: str
    target: str          # raw link target as written
    resolved: str = ''   # bundle-relative path if resolvable
    broken: bool = False  # target .md absent -> `not_yet_written` per spec (I5)

    def to_dict(self) -> dict:
        return {'text': self.text, 'target': self.target,
                'resolved': self.resolved, 'broken': self.broken}


@dataclass
class Concept:
    concept_id: str      # bundle-relative path, the stable per-concept key (§4c)
    path: str            # absolute path on disk
    type: Optional[str]  # OKF's one required field; None tolerated, noted
    frontmatter: Dict = field(default_factory=dict)
    body: str = ''
    links: List[Link] = field(default_factory=list)
    is_index: bool = False
    is_log: bool = False
    parse_notes: List[str] = field(default_factory=list)


@dataclass
class LogEntry:
    date: str            # bare YYYY-MM-DD as written — a T1 by construction (I3)
    heading: str
    body: str
    source: str          # concept_id of the log file


@dataclass
class Bundle:
    root: str
    name: str
    concepts: Dict[str, Concept] = field(default_factory=dict)
    log_entries: List[LogEntry] = field(default_factory=list)
    parse_notes: List[str] = field(default_factory=list)

    @property
    def index(self) -> Optional[Concept]:
        return next((c for c in self.concepts.values() if c.is_index), None)


def _parse_frontmatter(text: str) -> Tuple[Dict, str, List[str]]:
    """(frontmatter, body, notes). Falls back to flat key: value if YAML is absent/broken."""
    notes: List[str] = []
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text, ['no frontmatter block']
    raw, body = m.group(1), text[m.end():]
    if _yaml is not None:
        try:
            fm = _yaml.safe_load(raw)
            if isinstance(fm, dict):
                return fm, body, notes
            notes.append('frontmatter is not a mapping')
            return {}, body, notes
        except _yaml.YAMLError as e:
            notes.append(f'frontmatter YAML error: {e}')
    fm = {}
    for line in raw.splitlines():
        if ':' in line and not line.lstrip().startswith('#'):
            k, _, v = line.partition(':')
            fm[k.strip()] = v.strip().strip('"\'')
    if _yaml is None:
        notes.append('pyyaml unavailable; naive frontmatter parse')
    return fm, body, notes


def _extract_links(body: str, concept_dir: Path, root: Path) -> List[Link]:
    links = []
    for m in MD_LINK_RE.finditer(body):
        text, target = m.group(1), m.group(2)
        if target.startswith(EXTERNAL_SCHEMES) or target.startswith('#'):
            continue
        clean = target.split('#')[0]
        if not clean.endswith('.md'):
            continue
        candidate = (concept_dir / clean).resolve()
        try:
            resolved = str(candidate.relative_to(root.resolve()))
        except ValueError:
            resolved = clean
        links.append(Link(text=text, target=target, resolved=resolved,
                          broken=not candidate.exists()))
    return links


def _parse_log(body: str, source: str) -> List[LogEntry]:
    entries: List[LogEntry] = []
    current: Optional[LogEntry] = None
    chunks: List[str] = []
    for line in body.splitlines():
        m = LOG_HEADING_RE.match(line)
        if m:
            if current is not None:
                current.body = '\n'.join(chunks).strip()
                entries.append(current)
            current = LogEntry(date=m.group(1), heading=m.group(2).strip(),
                               body='', source=source)
            chunks = []
        elif current is not None:
            chunks.append(line)
    if current is not None:
        current.body = '\n'.join(chunks).strip()
        entries.append(current)
    return entries


def read_bundle(root) -> Bundle:
    root = Path(root)
    bundle = Bundle(root=str(root), name=root.name)
    if not root.is_dir():
        bundle.parse_notes.append(f'not a directory: {root}')
        return bundle

    for path in sorted(root.rglob('*.md')):
        if any(part.startswith('.') for part in path.relative_to(root).parts):
            continue
        concept_id = str(path.relative_to(root))
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            bundle.parse_notes.append(f'{concept_id}: unreadable ({e})')
            continue
        fm, body, notes = _parse_frontmatter(text)
        ctype = fm.get('type')
        if ctype is None:
            notes.append('missing required field: type')
        concept = Concept(
            concept_id=concept_id, path=str(path),
            type=str(ctype) if ctype is not None else None,
            frontmatter=fm, body=body,
            links=_extract_links(body, path.parent, root),
            is_index=path.name == 'index.md',
            is_log=path.name == 'log.md',
            parse_notes=notes,
        )
        bundle.concepts[concept_id] = concept
        if concept.is_log:
            bundle.log_entries.extend(_parse_log(body, concept_id))
    return bundle
