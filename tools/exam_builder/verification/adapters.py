"""Turn a published record row into a verification `Claim`.

This is the join between the completed data engine and the verification layer: it takes a
projected result declaration (the dict `compat.result_declarations` emits) plus the exam's own
identity, and produces the exact claim/evidence/source triple the verifier checks. It is
universal -- it reads only generic row fields and never branches on an authority or exam type,
so the same adapter serves every exam's results.

It does not itself verify or publish anything; it only shapes the input.
"""
from __future__ import annotations

from .schemas import Claim


def claim_from_result(row: dict, *, official_name: str, authority: str,
                      source_text: str = '') -> Claim:
    """A `Claim` for one result declaration.

    - `value` is the declared date, else the scheduled date -- exactly what the record states.
    - `evidence_span` is the declaration's own provenance excerpt (the verbatim span the
      reader captured), never a Tavily snippet.
    - identity/cycle come from the exam record, so the deterministic gate can reject a source
      that belongs to another exam or cycle before the model is ever consulted.
    """
    prov = row.get('provenance') or {}
    value = row.get('declaredAt') or row.get('expectedAt') or ''
    field = 'result:' + str(row.get('kind', 'RESULT')).lower()
    return Claim(
        exam_id=row.get('examId', ''),
        field=field,
        value=str(value),
        cycle=str(row.get('cycle', '')),
        evidence_span=prov.get('excerptText') or row.get('label', ''),
        source_url=prov.get('officialUrl') or row.get('documentUrl') or row.get('portalUrl') or '',
        source_title=prov.get('documentTitle') or row.get('label', ''),
        authority=authority,
        official_name=official_name,
        source_text=source_text,
        # A scheduled result carries a date but no declared value; a declared one always has a
        # value. Both are checkable, so a value is required only when the row states one.
        requires_value=bool(value),
    )


def claim_from_cutoff(entry: dict, *, exam_id: str, official_name: str, authority: str,
                      tier: str = 'prelim', source_text: str = '') -> Claim:
    """A `Claim` for one cut-off value.

    Cut-offs are the case where Qwen earns its place: the value alone ("92.66") appears in
    several rows of one sheet, so only reading it *in context* decides whether it is the
    General prelim mark or another category's. So the claim carries the value, the category
    and the stage in its `field`, and the evidence is the sheet's own verbatim excerpt.

    Identity and cycle come from the exam record and the entry's own year, so a source for
    another exam -- or another cycle -- is rejected deterministically before the model is
    consulted. `tier` selects which published mark this claim is about ('prelim' -> the
    tier-1/stage-1 mark, 'mains' -> tier-2), because one row can carry more than one.
    """
    prov = entry.get('provenance') or {}
    category = entry.get('category', '')
    value = entry.get('tier2Cutoff') if tier == 'mains' else entry.get('tier1Cutoff')
    excerpt = prov.get('excerptText') or ''
    title = prov.get('documentTitle') or ''
    # The bare marks line names no exam; the sheet's own title does. Compose them so identity
    # can be established and the value span confirmed against one text.
    composed = source_text or (title + ' ' + excerpt).strip()
    # Cut-off sheets pack every category's mark onto one line, and a whole-line span lets a
    # model mis-bind a value to the wrong category. Focus the evidence on the claimed
    # category's own pairing where the sheet writes it as "<value> (<Category>)", so the model
    # is asked about the right cell. Generic: it keys on the category token, never an exam.
    focused = _focus_on_category(excerpt, category)
    return Claim(
        exam_id=exam_id,
        field=f'cutoff:{tier}:{category}',
        value='' if value is None else str(value),
        cycle=str(entry.get('year', '')),
        evidence_span=focused or excerpt or title,
        source_url=prov.get('officialUrl') or '',
        source_title=title,
        authority=authority,
        official_name=official_name,
        source_text=composed,
        requires_value=value is not None,
    )


def _focus_on_category(excerpt: str, category: str) -> str:
    """A tight window around the claimed category's own mark, where the sheet pairs them.

    Cut-off sheets write "92.66 (General) 89.34 (EWS) 92.00 (OBC)"; asked about OBC, the model
    should see "92.00 (OBC)", not the whole line. This finds the category token and returns a
    small window that captures the value written beside it. It keys only on the category word
    (a generic label like General/OBC/SC/ST/UR/EWS), never on an exam or authority, so it
    stays universal; when the category is not found it returns '' and the caller keeps the
    full excerpt.
    """
    import re as _re
    if not excerpt or not category:
        return ''
    # Match "(Category)" or a standalone category word, and take ~20 chars before it (the
    # value) through the token itself.
    m = _re.search(r'[^\s(][^()]{0,24}\(?\s*' + _re.escape(category) + r'\s*\)?', excerpt, _re.I)
    if not m:
        m = _re.search(_re.escape(category), excerpt, _re.I)
        if not m:
            return ''
    start = max(0, m.start() - 8)
    return excerpt[start:m.end()].strip()


def claim_from_revision(rev: dict, *, exam_id: str, official_name: str, authority: str,
                        source_text: str = '') -> Claim:
    """A `Claim` for one corrigendum/revision -- specifically, that its NEW value is
    established by the revision source.

    A revision has two values, and they are checked in different places: the *old* value was
    verified once against the original source and is preserved in the record; the *new* value
    is what this revision's own document must support, so that is what the verifier checks. The
    affected field travels in the claim's `field`, so a document that changes the last date can
    never verify a change to the exam date -- the model is asked about the right field.

    Identity and cycle come from the exam record, so a corrigendum for another exam or another
    cycle is rejected deterministically before the model is consulted. Generic: no branch on an
    authority or exam type.
    """
    affected = rev.get('affected') or rev.get('fieldPath') or 'field'
    new_value = rev.get('newValue', rev.get('revisedValue', ''))
    excerpt = rev.get('evidenceSpan') or rev.get('evidence') or ''
    title = rev.get('sourceTitle') or rev.get('title') or ''
    composed = source_text or (title + ' ' + excerpt).strip()
    return Claim(
        exam_id=exam_id,
        field=f'revision:{affected}',
        value='' if new_value is None else str(new_value),
        cycle=str(rev.get('cycle', '')),
        evidence_span=excerpt or title,
        source_url=rev.get('sourceUrl') or rev.get('pdfUrl') or '',
        source_title=title,
        authority=authority,
        official_name=official_name,
        source_text=composed,
        requires_value=new_value not in (None, ''),
    )


def resource_officiality(url: str, authority_domain: str = '') -> str:
    """'OFFICIAL' when the URL is on the authority's own host, else 'UNOFFICIAL'.

    Deterministic and domain-based -- officiality is never taken from a snippet, a professional
    look, or the model. A resource on a coaching or news host is UNOFFICIAL even when it is
    useful. Reuses the admit-card URL host check, so there is one definition of "the authority's
    own host" across the engine.
    """
    from urllib.parse import urlsplit
    if not authority_domain:
        return 'UNOFFICIAL'
    host = urlsplit(url if '//' in url else '//' + url).netloc.lower().split(':')[0].removeprefix('www.')
    base = urlsplit(authority_domain if '//' in authority_domain else '//' + authority_domain
                    ).netloc.lower().split(':')[0].removeprefix('www.') or authority_domain.lower()
    if not host:
        return 'UNOFFICIAL'
    return 'OFFICIAL' if (host == base or host.endswith('.' + base)) else 'UNOFFICIAL'


_RESOURCE_LABEL = {
    'OFFICIAL_PDF': 'official document', 'OFFICIAL_PORTAL': 'official portal',
    'SIMPLIFIED_GUIDE': 'study guide', 'RECOMMENDED_BOOK': 'reference book',
    'VIDEO_LECTURE': 'video resource', 'ONLINE_TOOL': 'practice tool',
}


def claim_from_resource(resource: dict, *, exam_id: str, official_name: str, authority: str,
                        cycle: str = '', source_text: str = '') -> Claim:
    """A `Claim` that a resource belongs to the exact exam/cycle and matches its claimed type.

    The value is the resource's title and its evidence is the resource's own description or
    provenance excerpt -- what the record already holds, not a Tavily snippet. Identity and
    cycle come from the exam record, so a resource for another exam or cycle is rejected before
    the model. The model then judges scope/type semantically (Step 6). Officiality is decided
    separately and deterministically by `resource_officiality` on the URL's host -- never here.
    """
    prov = resource.get('provenance') or {}
    rtype = str(resource.get('type', 'RESOURCE'))
    title = str(resource.get('title', ''))
    excerpt = (resource.get('description') or prov.get('excerptText') or title).strip()
    doc_title = prov.get('documentTitle') or title
    composed = source_text or (doc_title + ' ' + excerpt).strip()
    # The claim's value is a scope phrase, not the verbatim title: a title often carries an
    # identifier (a notice number, a file name) the evidence does not repeat, which makes the
    # model conservatively return INSUFFICIENT. The evidence can support "an official document
    # for <exam> <cycle>", which is what the record is actually asserting. Generic label map,
    # no exam-specific branch.
    label = _RESOURCE_LABEL.get(rtype, 'resource')
    scope = f'{label} for {official_name}' + (f' {cycle}' if cycle else '')
    return Claim(
        exam_id=exam_id,
        field=f'resource:{rtype.lower()}',
        value=scope,
        cycle=str(cycle),
        evidence_span=excerpt,
        source_url=resource.get('url') or resource.get('directPdfUrl') or prov.get('officialUrl') or '',
        source_title=doc_title,
        authority=authority,
        official_name=official_name,
        source_text=composed,
        requires_value=bool(title),
    )
