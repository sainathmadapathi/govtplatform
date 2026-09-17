"""A snapshot of discovery, so a rebuild is comparable with the one before it.

Discovery depends on live search ranking, so the same exam built twice can be built from
different documents — SSC returned nine fields in one run and five in another, and nothing
in the output said which of those was the extractor and which was the weather. That makes
every coverage number unfalsifiable.

A manifest freezes **which documents were discovered**, and nothing else. It is explicitly
not a cache of their contents and not a source of truth: replaying it re-fetches every
document, re-runs content identity, re-verifies every evidence span, and re-runs the
publication gate. If a source has changed since capture, the hash says so and the facts are
read again from the new text.

    manifest freezes:   which URLs were found, and what discovery thought of them
    manifest never:     supplies a fact, skips a check, or vouches for a document

Manifests are never overwritten. A new capture is a new version, because the old one is the
evidence of what a past build actually saw.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
from dataclasses import asdict, dataclass, field as dc_field

from .discover import DiscoveredDoc, DocKind, Relevance, SourceSet

MANIFEST_DIR = os.path.join('.exam_manifests')
SCHEMA_VERSION = 1


def content_hash(data: bytes | str) -> str:
    raw = data.encode('utf-8') if isinstance(data, str) else (data or b'')
    return hashlib.sha256(raw).hexdigest()[:24]


@dataclass
class ManifestSource:
    """One discovered document, with why discovery believed it belonged here."""

    url: str
    title: str
    document_type: str
    relevance: str
    #: The alias tokens that admitted it, or the foreign ones that would have excluded it.
    discovery_evidence: list[str] = dc_field(default_factory=list)
    found_on: str = ''
    #: Hash of the document as fetched at capture time, where it could be read.
    content_hash: str = ''
    #: What the document's own text said it was about, at capture time.
    identity_verdict: str = 'UNCHECKED'


@dataclass
class SourceManifest:
    exam_id: str
    query: str
    authority_name: str
    authority_domain: str
    discovered_at: str
    sources: list[ManifestSource] = dc_field(default_factory=list)
    #: Documents discovery rejected, kept so a replay can show the gate's past decisions.
    rejected: list[ManifestSource] = dc_field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    #: True when the capturing run hit a network or fetch failure, so a thin manifest is
    #: not mistaken for an authority that publishes little.
    infrastructure_failed: bool = False
    notes: list[str] = dc_field(default_factory=list)

    @property
    def urls(self) -> list[str]:
        return [s.url for s in self.sources]

    def digest(self) -> str:
        """Identity of the *source set*, so two manifests can be compared directly."""
        return content_hash('\n'.join(sorted(self.urls)))


def from_source_set(source_set: SourceSet, *, query: str, authority_name: str,
                    identity: dict[str, str] | None = None,
                    hashes: dict[str, str] | None = None) -> SourceManifest:
    identity = identity or {}
    hashes = hashes or {}

    def row(d: DiscoveredDoc) -> ManifestSource:
        return ManifestSource(
            url=d.url, title=d.title, document_type=d.kind.value,
            relevance=d.relevance.value,
            discovery_evidence=list(d.matched or d.foreign_words),
            found_on=d.found_on,
            content_hash=hashes.get(d.url, ''),
            identity_verdict=identity.get(d.url, 'UNCHECKED'))

    return SourceManifest(
        exam_id=source_set.exam_id,
        query=query,
        authority_name=authority_name,
        authority_domain=source_set.authority_domain,
        discovered_at=time.strftime('%Y-%m-%dT%H:%M:%S'),
        sources=[row(d) for d in source_set.docs],
        rejected=[row(d) for d in source_set.rejected],
        infrastructure_failed=source_set.infrastructure_failed,
        notes=list(source_set.log))


def to_source_set(manifest: SourceManifest) -> SourceSet:
    """Rebuild the discovery result, without searching.

    The documents are *named*, not trusted: everything downstream re-fetches and re-checks
    them exactly as it would on a fresh build.
    """
    out = SourceSet(exam_id=manifest.exam_id, authority_domain=manifest.authority_domain)
    for s in manifest.sources:
        out.docs.append(DiscoveredDoc(
            url=s.url,
            kind=DocKind(s.document_type) if s.document_type in DocKind.__members__.values()
            else DocKind(s.document_type) if s.document_type in [k.value for k in DocKind]
            else DocKind.UNKNOWN,
            title=s.title,
            relevance=Relevance(s.relevance) if s.relevance in [r.value for r in Relevance]
            else Relevance.DIRECT,
            matched=list(s.discovery_evidence),
            found_on=s.found_on))
    out.infrastructure_failed = manifest.infrastructure_failed
    out.log.append(f'replayed from a manifest captured {manifest.discovered_at} '
                   f'({len(out.docs)} source(s)); every document is re-fetched and '
                   f're-validated, nothing is taken on the manifest’s word')
    return out


# ------------------------------------------------------------------------------- disk
def path_for(exam_id: str, *, directory: str = MANIFEST_DIR, version: int | None = None) -> str:
    os.makedirs(directory, exist_ok=True)
    if version is None:
        version = next_version(exam_id, directory=directory)
    return os.path.join(directory, f'{exam_id}.v{version}.json')


def next_version(exam_id: str, *, directory: str = MANIFEST_DIR) -> int:
    if not os.path.isdir(directory):
        return 1
    existing = [f for f in os.listdir(directory)
                if f.startswith(f'{exam_id}.v') and f.endswith('.json')]
    versions = []
    for f in existing:
        try:
            versions.append(int(f.rsplit('.v', 1)[1].split('.json')[0]))
        except (IndexError, ValueError):
            continue
    return (max(versions) + 1) if versions else 1


def save(manifest: SourceManifest, *, directory: str = MANIFEST_DIR) -> str:
    """Write a new version. An existing manifest is never overwritten.

    A past manifest is the record of what a past build actually saw; overwriting it would
    destroy the only evidence of why that build produced what it did.
    """
    target = path_for(manifest.exam_id, directory=directory)
    if os.path.exists(target):                      # belt and braces
        raise FileExistsError(target)
    with io.open(target, 'w', encoding='utf-8', newline='') as fh:
        json.dump(asdict(manifest), fh, indent=1, ensure_ascii=False)
    return target


def load(path: str) -> SourceManifest:
    data = json.load(io.open(path, encoding='utf-8'))
    version = data.get('schema_version', 0)
    if version != SCHEMA_VERSION:
        raise ValueError(
            f'{path} was written by schema v{version}; this build expects '
            f'v{SCHEMA_VERSION}. Re-capture rather than replaying a manifest whose '
            f'meaning may have changed.')
    sources = [ManifestSource(**s) for s in data.pop('sources', [])]
    rejected = [ManifestSource(**s) for s in data.pop('rejected', [])]
    return SourceManifest(sources=sources, rejected=rejected, **data)


def latest_for(exam_id: str, *, directory: str = MANIFEST_DIR) -> str | None:
    v = next_version(exam_id, directory=directory) - 1
    if v < 1:
        return None
    return os.path.join(directory, f'{exam_id}.v{v}.json')
