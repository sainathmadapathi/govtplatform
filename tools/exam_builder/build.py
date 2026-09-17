"""resolve -> discover -> contract -> extract, for one exam and only that exam.

This is the orchestrator the single command drives. It holds no knowledge of any authority:
the resolver finds who publishes, discovery finds what they published for this exam, the
contract says what GovOS wants to know and which document kinds could answer it, and the
extractors read whatever was actually found.

The contract is consulted *before* extraction runs, which is what keeps two very different
statements apart — "the authority published nothing that could answer this" (NO_SOURCE) and
"we read the document and our pattern missed it" (NOT_EXTRACTED).
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import time

from ..exam_authoring import extract as X
from ..exam_authoring.record import Citation, ExamRecord, Field
from ..exam_authoring.sources import FetchError, load_html, load_pdf
from .contract import CONTRACT, Coverage, coverage_from
from .gate import BuildState
from .identity import ExamIdentity, IdentityCheck, IdentityVerdict, field_is_attributable
from .identity import verify as verify_identity
from .discover import DiscoveredDoc, DocKind, SourceSet, discover, exam_aliases
from .resolve import ResolvedExam, resolve, stable_exam_id


def _today() -> str:
    return time.strftime('%Y-%m-%d')


@dataclass
class BuildResult:
    resolved: ResolvedExam
    sources: SourceSet
    coverage: Coverage
    record: ExamRecord
    notes: list[str] = dc_field(default_factory=list)
    #: Whether the build itself completed, separately from any field's status.
    build_state: BuildState = BuildState.COMPLETE
    #: url -> what the document's own text says it is about.
    identity: dict[str, IdentityCheck] = dc_field(default_factory=dict)


def _load(doc: DiscoveredDoc):
    """Fetch a discovered document as something the extractors can read."""
    if doc.is_pdf:
        return load_pdf(doc.url)
    return load_html(doc.url)


def _semantic_read(field_name: str, sources, loaded: dict, rec: ExamRecord,
                   identity: dict | None = None, target=None):
    """Try every loaded document for one field, semantically.

    The best-evidenced reading across documents wins; a document that does not state the
    field simply yields nothing, which is not an error.
    """
    from .evidence import EvidenceStatus
    from .semantic import SPEC_BY_NAME, extract

    if field_name not in SPEC_BY_NAME:
        return None

    best = None
    for doc in sources.docs:
        document = loaded.get(doc.url)
        if document is None:
            continue
        text = document.all_text() if hasattr(document, 'all_text') else ''
        if not text:
            continue
        got = extract(field_name, text, source_url=doc.url,
                      document_title=f'{rec.title} — {doc.kind.value.replace("_", " ").title()}',
                      page_of=lambda span, d=document: _page_of(d, span))
        if got is None:
            continue
        # A document naming several exams may still supply a fact, but only where the span
        # carrying that fact names this exam itself. Otherwise the fact could belong to any
        # of the exams the document covers.
        check = (identity or {}).get(doc.url)
        if check is not None and check.verdict is IdentityVerdict.AMBIGUOUS:
            if target is None or not field_is_attributable(text, target, got.evidence.span):
                rec.note(f'{field_name}: evidence found in a multi-exam document but the '
                         f'span does not name this exam; not attributed ({doc.url})')
                continue
        if best is None or got.confidence > best[0].confidence:
            best = (got, doc)

    if best is None:
        return None
    got, doc = best
    cite = Citation(document_title=got.evidence.document_title, url=got.evidence.source_url,
                    page=got.evidence.page, clause=f'Read semantically ({field_name})',
                    excerpt=got.evidence.span, verified_date=_today())
    # Evidence was verified inside extract(); a low-confidence reading is still offered to a
    # person rather than dropped, because the span is real either way.
    if got.confidence >= 0.66 and got.evidence.status is EvidenceStatus.VERIFIED:
        return Field.found(field_name, got.value, cite)
    return Field.needs_review(
        field_name, got.value,
        f'Read from the source and the evidence span was verified, but only '
        f'{len(got.cues_matched)} supporting cue(s) fired — confirm the reading.', cite)


def _page_of(document, span: str) -> int:
    """Which page a span sits on, so a citation can name it."""
    pages = getattr(document, 'pages', None) or []
    needle = ' '.join(span.split())[:60]
    for i, page in enumerate(pages, start=1):
        if needle and needle in ' '.join(page.split()):
            return i
    return 1


def build(exam_query: str, *, year: str = '', sibling_exam_words: list[str] | None = None,
          max_docs: int = 8) -> BuildResult:
    resolved = resolve(exam_query, year=year)
    exam_id = stable_exam_id(resolved)

    own = exam_aliases(resolved.query, resolved.official_name)
    siblings = [w for w in (sibling_exam_words or []) if w not in own]
    sources = discover(resolved, exam_id=exam_id, sibling_exam_words=siblings)

    available = {d.kind for d in sources.docs}
    coverage = coverage_from(available)

    rec = ExamRecord(
        exam_id=exam_id,
        code=exam_id.replace('exam-', '').upper().replace('-', '_'),
        title=resolved.official_name or resolved.query,
        authority_name=resolved.authority.name,
        official_domain=resolved.authority.domain,
    )
    rec.sources_read.extend(d.url for d in sources.docs)
    rec.log.extend(sources.log)
    if resolved.authority.corroborated_by:
        rec.note(f'{resolved.authority.domain} is not a government domain; it was accepted '
                 f'because {resolved.authority.corroborated_by} names it.')
    if sources.rejected:
        rec.note(f'{len(sources.rejected)} document(s) were rejected as belonging to another '
                 f'exam on the same site — the isolation gate working, not an error.')

    # Read each document once, then let every contract field that names its kind try it.
    loaded: dict[str, object] = {}
    for doc in sources.docs[:max_docs]:
        try:
            loaded[doc.url] = _load(doc)
        except FetchError as exc:
            rec.note(f'could not read {doc.url}: {exc}')

    # ---- content identity: does each document's own text belong to this exam?
    target = ExamIdentity(exam_id=exam_id, query=resolved.query,
                          official_name=resolved.official_name, year=resolved.year,
                          authority_name=resolved.authority.name)
    identity: dict[str, IdentityCheck] = {}
    for doc in list(sources.docs):
        document = loaded.get(doc.url)
        if document is None:
            continue
        text = document.all_text() if hasattr(document, 'all_text') else ''
        check = verify_identity(text, target, source_url=doc.url, document_title=doc.title)
        identity[doc.url] = check
        if check.verdict is IdentityVerdict.MISMATCH:
            # Dropped before extraction: a document about another exam may not contribute a
            # single fact, however official its source.
            loaded.pop(doc.url, None)
            rec.note(f'content identity MISMATCH, excluded from extraction: {doc.url} '
                     f'({"; ".join(check.reasons)[:120]})')
        elif check.verdict is IdentityVerdict.AMBIGUOUS:
            rec.note(f'content identity AMBIGUOUS: {doc.url} '
                     f'({"; ".join(check.reasons)[:120]})')

    # What the pipeline already established is not a gap. The resolver settled the exam's
    # name and its authority; routing them to an extractor reported NOT_EXTRACTED for two
    # facts sitting in the record.
    identity_cite = Citation(
        document_title=f'{resolved.authority.name} — official web presence',
        url=resolved.authority.domain, page=1, clause='Authority resolution',
        excerpt=f'Resolved from official sources with confidence '
                f'{resolved.authority.confidence}; evidence: '
                f'{", ".join(resolved.authority.evidence[:3])}',
        verified_date=_today())
    rec.set(Field.found('officialName', rec.title, identity_cite))
    rec.set(Field.found('authority', resolved.authority.name, identity_cite))

    for cf in CONTRACT:
        if cf.name in ('officialName', 'authority'):
            continue
        status = coverage.supplied.get(cf.name, 'NO_SOURCE')
        if status == 'INTRINSIC':
            continue
        if status == 'NO_SOURCE':
            if sources.infrastructure_failed:
                # We did not finish looking. Calling this "not published" would blame the
                # authority for our own outage.
                rec.set(Field.not_extracted(
                    cf.name, resolved.authority.domain,
                    f'{cf.name} (search or fetch did not complete: '
                    f'{sources.infrastructure_note[:120]})'))
                continue
            # Nothing discovered could answer it. That is a statement about what the
            # authority published, and it is recorded as such rather than as an extraction
            # failure — the two must never be collapsed.
            rec.set(Field.not_published(
                cf.name,
                f'No document of kind {" or ".join(k.value for k in cf.sources)} was found '
                f'for this exam on {resolved.authority.domain}.'))
            continue
        if not cf.extractor:
            # A source exists but no reader is written yet. Our gap, stated as ours.
            rec.set(Field.not_extracted(cf.name, resolved.authority.domain,
                                        f'{cf.name} reader (source present, extractor not written)'))
            continue

        fn = getattr(X, cf.extractor, None)
        if fn is None:
            rec.set(Field.not_extracted(cf.name, resolved.authority.domain,
                                        f'{cf.name} (extractor "{cf.extractor}" missing)'))
            continue

        # Semantic extraction first: it reads a fact however the authority worded it, and
        # only accepts a value whose evidence span is found verbatim in the document. The
        # older pattern extractors stay as a fallback for fields it has no spec for.
        got = _semantic_read(cf.name, sources, loaded, rec, identity, target)
        if got is not None:
            rec.set(got)
            continue

        for kind in cf.sources:
            for doc in (d for d in sources.docs if d.kind is kind and d.url in loaded):
                document = loaded[doc.url]
                title = f'{rec.title} — {kind.value.replace("_", " ").title()}'
                try:
                    if cf.extractor == 'dates_from_rows':
                        from ..exam_authoring.sources import html_rows
                        if getattr(document, 'kind', '') == 'HTML':
                            got = fn(document, html_rows(document), title)
                        else:
                            # Not every authority gives an exam its own page with a
                            # label/value table. SSC does not; its dates are in the notice's
                            # prose, and the contract already allows the notice as a source,
                            # so read it there rather than reporting the dates missing.
                            got = X.dates_from_notice(document, title)
                    else:
                        got = fn(document, title)
                except Exception as exc:                        # noqa: BLE001
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')
                    continue
                if got is not None and got.ok:
                    break
            if got is not None and got.ok:
                break
        rec.set(got if got is not None else
                Field.not_extracted(cf.name, resolved.authority.domain, cf.name))

    state = (BuildState.PAUSED_INFRASTRUCTURE if sources.infrastructure_failed
             else BuildState.COMPLETE)
    return BuildResult(resolved=resolved, sources=sources, coverage=coverage, record=rec,
                       build_state=state, identity=identity)
