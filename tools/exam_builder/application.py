"""Reading an application procedure out of whatever the authority happened to publish.

The rule that shapes everything here: **the document supplies the steps**. There is no list
of expected stages, because the moment one exists the extractor starts finding it. An
authority that applies in two steps must produce two stages; one that applies in eight must
produce eight; one whose notice never describes the procedure must produce none, and say so
in a way that blames the right party.

So the work is segmentation, not recognition. A procedure region is located by what it is
*about* — cues, in the manner of `semantic.py` — and then split on the enumeration the
authority itself used: "Step 1", "(i)", "Stage II", a numbered clause. The heading the
authority wrote becomes the title, unedited. Nothing is renamed onto anybody else's
vocabulary, so a step called "Registration" stays "Registration" and never becomes "Account
Creation".

Every value carries a span that is checked verbatim against the source before it is
accepted, so this module can classify and structure but cannot invent. A field it cannot
find a span for is dropped; a value two sources disagree about becomes NEEDS_REVIEW carrying
both, because choosing between two official documents on search ranking is the failure this
whole pipeline exists to avoid.

Nothing here names an authority or an exam.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .schema import (ApplicationField, ApplicationProcess, ApplicationStage, Fact, FeeRule,
                     RequiredDocument, Scope, ScopeKind, ScopeRef, SourceDocument,
                     SourceEvidence, Status)
from .stages import Structure, discover_stages, procedure_regions

# ============================================================== what to look for
#: A sentence that asks the candidate to supply something. The verb is the cue; the label is
#: whatever the document calls the thing.
_FIELD_CUE = re.compile(
    r'\b(enter|fill(?:\s+in)?|provide|furnish|select|choose|indicate|specify|state|type)\b'
    r'[^.;:]{0,20}?\b(?:the|his|her|their|your)?\s*'
    r'(?P<label>[A-Za-z][A-Za-z /&\'\-]{2,48}?)'
    # "of" is absent on purpose: it sits *inside* noun phrases at least as often as it ends
    # them, and listing it read "date of birth" as "date".
    r'(?=\s*(?:\bin\b|\bas\b|\bfrom\b|\band\b|\bor\b|\bwith\b|,|\.|;|:|$))', re.I)

#: A sentence that asks the candidate to supply a *document* rather than a value.
_DOCUMENT_CUE = re.compile(
    r'\b(upload|attach|enclose|submit|produce|furnish)\b[^.;:]{0,30}?'
    r'(?P<name>(?:scanned\s+)?(?:copy\s+of\s+)?[A-Za-z][A-Za-z /&\'\-]{2,48}?)'
    r'(?=\s*(?:\bin\b|\bas\b|\bwith\b|\band\b|,|\.|;|:|$))', re.I)

#: Words for the application itself. "Submit the form" is the act of applying, not a
#: document to produce, and reading it as one invented an upload nobody asked for. These are
#: words about form-filling; no authority and no exam is named.
_NOT_A_DOCUMENT = frozenset({
    'form', 'application', 'application form', 'details', 'particulars', 'information',
    'same', 'it', 'them', 'this', 'these', 'entries', 'data', 'fee', 'fees', 'payment',
})

#: Wording that makes a requirement conditional rather than universal.
_CONDITIONAL = re.compile(
    r'\b(if applicable|wherever applicable|as applicable|in case|if any|if claiming|'
    r'where claimed|if eligible|only (?:for|if)|subject to)\b', re.I)

_REQUIRED = re.compile(r'\b(must|shall|required to|mandatory|compulsor\w+|has to|have to)\b',
                       re.I)
_OPTIONAL = re.compile(r'\b(may|optional|at (?:his|her|their) discretion|if (?:he|she|they) '
                       r'(?:wish|choose)|not mandatory)\b', re.I)

#: Field kinds, taken only from wording the document actually uses. Nothing is inferred from
#: a label's meaning: a document that says "date of birth" without saying it is a date entry
#: leaves the kind empty rather than being assigned one from general knowledge.
_KIND_FROM_WORDING = (
    (re.compile(r'\bupload\b|\bscanned\b|\bimage\b|\bfile\b', re.I), 'UPLOAD'),
    (re.compile(r'\bselect\b|\bchoose\b|\bdrop[- ]?down\b|\bfrom the list\b', re.I), 'SELECT'),
    (re.compile(r'\bdd[/-]?mm[/-]?yyyy\b|\bin the format\b.{0,30}\bdate\b', re.I), 'DATE'),
    (re.compile(r'\btick\b|\bcheck ?box\b', re.I), 'CHECKBOX'),
)

#: A statement that there is no fee. The *only* route to NOT_PUBLISHED for a fee, because it
#: is the only wording that proves absence rather than merely failing to find presence.
_NO_FEE = re.compile(
    r'\b(?:there\s+(?:is|shall\s+be)\s+no|no)\s+(?:application\s+|examination\s+)?fee\b|'
    r'\bfee\s+is\s+not\s+(?:required|payable|charged)\b|\bnil\s+fee\b', re.I)

#: Group words authorities use when they state a fee or an exemption. Expansions sit
#: beside acronyms because a notice may print either, and matching only the acronym read a
#: group's amount as everybody's. Longest first, so the fuller wording wins the match. This
#: is a list about people; it names no authority and no exam.
_CATEGORY = re.compile(
    r'\b(persons? with benchmark disabilit(?:y|ies)|other backward class(?:es)?|'
    r'economically weaker section(?:s)?|scheduled caste(?:s)?|scheduled tribe(?:s)?|'
    r'ex-?servicemen|transgender|female|women|pwbd|pwd|esm|obc|ews|sc|st)\b', re.I)

_AMOUNT = re.compile(r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)', re.I)

#: Money the post pays, rather than money the candidate pays. "Pay" is a noun here, and
#: matching it as a verb recorded four pay scales as application fees. No authority, exam or
#: figure is named -- this is the vocabulary of remuneration.
_REMUNERATION = re.compile(
    r'\bpay\s*(?:level|scale|band|matrix)\b|\bgrade\s*pay\b|\bsalar\w+\b|'
    r'\bemolument\w*\b|\bremunerat\w*\b|\bper\s*(?:month|annum|mensem)\b|'
    r'\bbasic\s*pay\b|\bpay\s*in\s*the\b', re.I)

_PAY_MODE = re.compile(
    r'\b(net ?banking|credit card|debit card|upi|bhim|challan|demand draft|cash|'
    r'wallet|internet banking|payment gateway)\b', re.I)

_URL = re.compile(r'https?://[\w.\-/]+[\w/]', re.I)

#: Sentences that mention a URL without it being the place one applies.
_NOT_A_PORTAL = re.compile(
    r'\b(syllabus|result|answer key|admit card|archive|contact|grievance|rti|sitemap)\b',
    re.I)

#: A "sentence" that is really markup or script. Reading a URL out of one produced a
#: tracking iframe as an authority's application portal -- the address was in a JavaScript
#: string, not in anything the authority said to a candidate.
_IS_MARKUP = re.compile(
    r'<[a-z!/][^>]*>|\bfunction\s*\(|\bvar\s+\w+\s*=|\bdocument\.\w|\.createElement\b|'
    r'\bwindow\.\w|[{};]\s*$|=\s*[\'"]', re.I)

#: A URL that is the value of an attribute or a string literal rather than something written
#: for a reader. The quote or equals sign immediately before it is the tell.
_URL_IN_MARKUP = re.compile(r'[=\'"(\[]\s*$')


# ================================================================== the result
@dataclass
class ExtractionOutcome:
    """What one extraction run produced, and what got in its way."""

    process: ApplicationProcess
    #: Facts two sources disagreed about. Each is already NEEDS_REVIEW in the process.
    conflicts: list[str] = dc_field(default_factory=list)
    #: Sources that could not be read. Never turned into a claim about the authority.
    unreadable: list[str] = dc_field(default_factory=list)
    log: list[str] = dc_field(default_factory=list)

    @property
    def infrastructure_failed(self) -> bool:
        return bool(self.unreadable)


# =================================================================== utilities
def _evidence(span: str, doc: SourceDocument, text: str, *, reading: str = '',
              page: int | None = None, section: str = '') -> SourceEvidence | None:
    """Build evidence and verify the span, or return None.

    Returning None rather than unverified evidence is the no-invention rule made
    structural: a caller has nothing to attach, so the value cannot be recorded.
    """
    ev = Evidence(span=span, source_url=doc.url, document_title=doc.title,
                  page=page or 1, reading=reading)
    if ev.verify(text) is not EvidenceStatus.VERIFIED:
        return None
    out = SourceEvidence.from_evidence(ev, source=doc, source_id=doc.id)
    out.section = section
    return out


def _slug(text: str, *, limit: int = 40) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return s[:limit] or 'x'


def _sentences(text: str) -> list[str]:
    """Split on sentence ends, not on abbreviations.

    The next character must look like a new sentence. Without that, "Rs. 250/-" splits at
    the abbreviation and the amount is separated from the word that identifies it as a fee —
    which is how the first run of this extractor lost every amount written that way.
    """
    flat = normalise_ws(text)
    # A clause number is a boundary too. Without this, "10.1 Fee payable ... 10.2 Women
    # candidates ... are exempted" is one passage, and everything in it competes for a
    # single reading.
    flat = re.sub(r'(?<=[.;])\s+(?=\d{1,2}\.\d{1,2}\s)', '\n', flat)
    flat = re.sub(r'\s+(?=\d{1,2}\.\d{1,2}\s+[A-Z])', '\n', flat)
    parts = re.split(r'\n|(?<=[.;])\s+(?=[A-Z(])', flat)
    return [p for p in parts if p.strip()]


def _requiredness(sentence: str) -> bool | None:
    """Required, optional, or not stated. Not stated stays None rather than defaulting."""
    if _OPTIONAL.search(sentence):
        return False
    if _REQUIRED.search(sentence):
        return True
    return None


def _kind_from(sentence: str) -> str:
    for pattern, kind in _KIND_FROM_WORDING:
        if pattern.search(sentence):
            return kind
    return ''


def _clean_label(label: str) -> str:
    out = normalise_ws(label).strip(' ,.;:-')
    out = re.sub(r'^(?:the|his|her|their|your|a|an)\s+', '', out, flags=re.I)
    return out


# ===================================================================== stages
def extract_stages(doc: SourceDocument, text: str) -> list[ApplicationStage]:
    """The steps this document describes, in the order it describes them.

    Discovery is `stages.discover_stages`, which reads whichever structure the authority
    used. Everything here is the same afterwards: each candidate must still produce a span
    that verifies verbatim, and one that cannot is dropped rather than kept unevidenced.
    """
    out: list[ApplicationStage] = []
    for candidate in discover_stages(text):
        ev = _evidence(candidate.body[:900], doc, text,
                       reading=f'{candidate.structure.value.lower()}: {candidate.title}',
                       section='application procedure')
        if ev is None:
            continue
        # Structures where the authority titled the step, against those where it did not
        # and the title is our truncation of a sentence.
        labelled = candidate.structure in (Structure.EXPLICIT_MARKER,
                                           Structure.TABLE_ROW,
                                           Structure.HEADING)
        stage = ApplicationStage(
            id=f'stage-{candidate.order}-{_slug(candidate.title)}',
            title=candidate.title,
            order=candidate.order,
            description=normalise_ws(candidate.body)[:900],
            evidence=[ev],
            status=Status.VERIFIED if labelled else Status.NEEDS_REVIEW)
        if not labelled:
            stage.note = (
                f'the authority did not give this step a title; it is written as a '
                f'{candidate.structure.value.lower().replace("_", " ")} and the name shown '
                f'is the opening of its own text, cut to length. The step is evidenced; '
                f'what a person should check is whether this is one step or part of another.')
        stage.fields = extract_fields(doc, text, candidate.body, stage.id)
        stage.documents = extract_documents(doc, text, candidate.body, stage.id)
        stage.instructions = extract_instructions(doc, text, candidate.body)
        out.append(stage)
    # Re-number after any drop, so the order a reader sees has no gaps in it.
    for order, stage in enumerate(out, start=1):
        stage.order = order
    return out


# ===================================================================== fields
def extract_fields(doc: SourceDocument, text: str, body: str,
                   stage_id: str) -> list[ApplicationField]:
    """Inputs this step asks for, only where the document names them.

    The field's *kind* and its constraints come from wording the document uses, never from
    what the label means. A document that asks for a photograph without printing a
    specification yields a field with no constraints, rather than the dimensions such
    specifications usually carry.
    """
    out: list[ApplicationField] = []
    seen: set[str] = set()
    for sentence in _sentences(body):
        for m in _FIELD_CUE.finditer(sentence):
            label = _clean_label(m.group('label'))
            if len(label) < 3 or label.lower() in seen:
                continue
            # An upload is a document, not a form field; it is handled as one.
            if re.search(r'\bupload\b|\bscanned\b', sentence, re.I):
                continue
            ev = _evidence(sentence, doc, text, reading=f'field: {label}')
            if ev is None:
                continue
            seen.add(label.lower())
            out.append(ApplicationField(
                id=f'{stage_id}-field-{_slug(label, limit=28)}',
                label=label,
                input_kind=_kind_from(sentence),
                required=_requiredness(sentence),
                constraints=_stated_constraints(sentence),
                help_text=sentence[:240],
                evidence=[ev]))
    return out


def _stated_constraints(sentence: str) -> list[str]:
    """Only rules the sentence actually prints. Never a rule such a field usually has."""
    out: list[str] = []
    for pattern in (
            re.compile(r'\bin\s+(?:the\s+)?format\s+[^,.;]{2,40}', re.I),
            # The other order, equally common: "in JPEG format", "in PDF format".
            re.compile(r'\bin\s+[A-Za-z]{2,8}\s+format\b', re.I),
            re.compile(r'\bdd[/-]?mm[/-]?yyyy\b', re.I),
            re.compile(r'\b(?:not\s+)?(?:more|less)\s+than\s+[^,.;]{2,40}', re.I),
            re.compile(r'\bbetween\s+\d[^,.;]{2,40}', re.I),
            re.compile(r'\bmaximum\s+of\s+[^,.;]{2,40}', re.I),
            re.compile(r'\bin\s+(?:capital|block)\s+letters\b', re.I)):
        m = pattern.search(sentence)
        if m:
            out.append(normalise_ws(m.group(0)))
    return out


# ================================================================== documents
def extract_documents(doc: SourceDocument, text: str, body: str,
                      stage_id: str) -> list[RequiredDocument]:
    """Documents this step requires, only where the source says so.

    Conditionality is read from the sentence, because "if claiming a relaxation" and "all
    candidates shall" are different requirements and flattening them would tell a candidate
    to produce papers they do not need.
    """
    out: list[RequiredDocument] = []
    seen: set[str] = set()
    for sentence in _sentences(body):
        for m in _DOCUMENT_CUE.finditer(sentence):
            name = _clean_label(m.group('name'))
            if len(name) < 3 or name.lower() in seen or name.lower() in _NOT_A_DOCUMENT:
                continue
            ev = _evidence(sentence, doc, text, reading=f'document: {name}')
            if ev is None:
                continue
            seen.add(name.lower())
            conditional = bool(_CONDITIONAL.search(sentence))
            out.append(RequiredDocument(
                id=f'{stage_id}-doc-{_slug(name, limit=28)}',
                name=name,
                required=None if conditional else _requiredness(sentence),
                specifications=_stated_constraints(sentence) + (
                    [normalise_ws(_CONDITIONAL.search(sentence).group(0))]
                    if conditional else []),
                evidence=[ev]))
    return out


def extract_instructions(doc: SourceDocument, text: str, body: str) -> list[Fact]:
    """Rules and warnings printed for a step, each kept as its own sourced fact."""
    out: list[Fact] = []
    for sentence in _sentences(body):
        if not re.search(r'\b(must|shall|should not|not be|will be rejected|liable to be '
                         r'rejected|ensure|note that|no (?:change|correction|request))\b',
                         sentence, re.I):
            continue
        ev = _evidence(sentence, doc, text, reading='instruction')
        if ev is None:
            continue
        out.append(Fact.verified(normalise_ws(sentence)[:400], ev))
    return out[:12]


# ======================================================================= fees
def extract_fees(doc: SourceDocument, text: str) -> list[FeeRule]:
    """Amounts, exemptions and modes — each scoped to whoever the document says it is for.

    An exemption is recorded as a stated fact rather than as a zero we computed, and no
    exemption is added because such exemptions are common. If the document says there is no
    fee, that is NOT_PUBLISHED-by-proof: an authority stating absence, not us failing to
    find presence.
    """
    rules: list[FeeRule] = []
    for sentence in _sentences(text):
        mentions_fee = re.search(r'\bfees?\b|\bcharges?\b', sentence, re.I)
        # "pay Rs. 111/-" states a fee without using the word. The amount is what makes
        # this safe: an instruction to pay with no sum in it carries nothing.
        tells_you_to_pay = (re.search(r'\bpay\w*\b|\bremit\w*\b|\bdeposit\w*\b',
                                      sentence, re.I)
                            and _AMOUNT.search(sentence))
        if not mentions_fee and not tells_you_to_pay:
            continue
        if _REMUNERATION.search(sentence) and not mentions_fee:
            # A pay scale is money the post offers, not money the application costs.
            continue

        if _NO_FEE.search(sentence):
            ev = _evidence(sentence, doc, text, reading='no fee is charged')
            if ev is not None:
                rules.append(FeeRule(
                    amount=Fact.not_published(
                        'the source states that no fee is charged', ev),
                    is_exempt=Fact.verified(True, ev),
                    note='absence is stated by the authority, not inferred from silence'))
            continue

        # A digit is required: the amount pattern's character class accepts separators, so
        # "Rs. ," matches and yields nothing to convert.
        amounts = [a for a in _AMOUNT.findall(sentence) if any(c.isdigit() for c in a)]
        exempting = re.search(r'\b(exempt\w*|remission|not required to pay)\b', sentence, re.I)
        categories = [c.lower() for c in _CATEGORY.findall(sentence)]

        if exempting and categories:
            ev = _evidence(sentence, doc, text, reading='fee exemption')
            if ev is not None:
                for cat in dict.fromkeys(categories):
                    rules.append(FeeRule(
                        scope=Scope([ScopeRef(ScopeKind.CATEGORY, _slug(cat), cat)]),
                        is_exempt=Fact.verified(True, ev)))
            # Deliberately no `continue`: a clause that grants an exemption very often
            # states the amount in the same breath, and consuming the passage here lost it.

        if amounts:
            ev = _evidence(sentence, doc, text, reading='fee amount')
            if ev is None:
                continue
            value = float(amounts[0].replace(',', ''))
            scope = Scope()
            # Where the same sentence names a group, the amount belongs to that group --
            # unless the only reason a group is named is that it is being exempted, in
            # which case the amount is the general one and the exemption is its own rule.
            if categories and not exempting:
                scope = Scope([ScopeRef(ScopeKind.CATEGORY, _slug(categories[0]),
                                        categories[0])])
            modes = [normalise_ws(m) for m in _PAY_MODE.findall(sentence)]
            rules.append(FeeRule(
                scope=scope,
                amount=Fact.verified(value, ev),
                accepted_modes=(Fact.verified(list(dict.fromkeys(modes)), ev) if modes
                                else Fact.not_extracted(
                                    'no payment mode is stated in this sentence'))))
    return rules


def extract_payment_modes(doc: SourceDocument, text: str) -> Fact:
    """Modes stated anywhere in the document, for a process-level record of them."""
    for sentence in _sentences(text):
        modes = [normalise_ws(m) for m in _PAY_MODE.findall(sentence)]
        if len(modes) >= 1 and re.search(r'\bfee\b|\bpay\w*\b', sentence, re.I):
            ev = _evidence(sentence, doc, text, reading='accepted payment modes')
            if ev is not None:
                return Fact.verified(list(dict.fromkeys(m.lower() for m in modes)), ev)
    return Fact.not_extracted('no payment mode was stated in a sentence about the fee')


# ===================================================================== portal
def extract_portal(doc: SourceDocument, text: str, *, authority_domain: str = '') -> Fact:
    """The address a candidate actually applies at, with the sentence that says so.

    A URL is not a portal because it looks like one. It has to appear in a sentence about
    applying, and that sentence is the evidence. A search result is never a source here.
    """
    best: tuple[int, str, str] | None = None
    for sentence in _sentences(text):
        if not re.search(r'\bapply\b|\bapplication\b|\bregistrat\w+\b|\bsubmit\w*\b',
                         sentence, re.I):
            continue
        if _NOT_A_PORTAL.search(sentence):
            continue
        if _IS_MARKUP.search(sentence):
            # Script and markup are not the authority addressing a candidate. A URL found
            # here is an asset reference, and one of them was nearly published as an
            # authority's application portal.
            continue
        for m in _URL.finditer(sentence):
            if _URL_IN_MARKUP.search(sentence[:m.start()]):
                continue
            url = m.group(0).rstrip('.,;')
            # An apply-specific address outranks the authority's front page, which is a
            # weaker answer to "where do I apply".
            specific = 0 if (authority_domain and authority_domain in url
                             and not re.search(r'/(apply|online|registration)', url, re.I)) else 1
            if best is None or specific > best[0]:
                best = (specific, url, sentence)
    if best is None:
        return Fact.not_extracted(
            'no sentence about applying carried a URL in this document')
    _rank, url, sentence = best
    ev = _evidence(sentence, doc, text, reading=f'application portal: {url}')
    if ev is None:
        return Fact.not_extracted('a portal URL was seen but its sentence could not be '
                                  'verified verbatim')
    return Fact.verified(url, ev)


# ============================================================ combining sources
def _same_value(a, b) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().rstrip('/').lower() == b.strip().rstrip('/').lower()
    return a == b


def merge_facts(name: str, facts: list[Fact]) -> Fact:
    """One fact from several sources — or NEEDS_REVIEW holding all of them.

    Two official documents disagreeing is a real finding about the record, not a ranking
    problem to be settled quietly. Both sides are kept so the later conflict engine has
    something to work with, and the field is blocked from publication meanwhile.
    """
    usable = [f for f in facts if f.status is Status.VERIFIED and f.has_value]
    if not usable:
        published = [f for f in facts if f.status is Status.NOT_PUBLISHED]
        if published:
            return published[0]
        return facts[0] if facts else Fact.not_extracted()

    first = usable[0]
    disagreeing = [f for f in usable[1:] if not _same_value(f.value, first.value)]
    if not disagreeing:
        # Corroboration: same value, more evidence.
        merged = Fact.verified(first.value, [e for f in usable for e in f.evidence])
        merged.confidence = min(1.0, 0.6 + 0.2 * len(usable))
        return merged

    every = [e for f in usable for e in f.evidence]
    values = ' | '.join(repr(f.value) for f in usable)
    return Fact.needs_review(
        first.value,
        f'{len(usable)} official sources state different values for {name}: {values}. '
        f'Both readings are kept and this field is blocked from publication until the '
        f'disagreement is resolved against the documents — it is not settled by which '
        f'source ranked higher.',
        every)


# =================================================================== the entry
def extract_application_process(
        sources: list[tuple[SourceDocument, str]], *, exam_id: str, authority: str = '',
        authority_domain: str = '', unreadable: list[str] | None = None
) -> ExtractionOutcome:
    """Read one exam's application procedure from documents already cleared for it.

    `sources` must already have passed content identity and officiality; this function does
    not check them, and combining documents that have not been checked is exactly how one
    exam's procedure ends up in another's record. `build.py` is where that ordering lives.

    An unreadable source is passed in rather than guessed at, and lands in `unreadable` so
    the caller can pause the build. It never becomes a claim about the authority.
    """
    outcome = ExtractionOutcome(
        process=ApplicationProcess(exam_id=exam_id, authority=authority),
        unreadable=list(unreadable or []))

    if not sources:
        outcome.log.append(
            'no application source was available, so nothing was read; this says nothing '
            'about what the authority publishes')
        outcome.process.note = 'no source read'
        return outcome

    portals: list[Fact] = []
    all_stages: list[tuple[SourceDocument, list[ApplicationStage]]] = []
    fees: list[FeeRule] = []

    for doc, text in sources:
        if not normalise_ws(text):
            outcome.unreadable.append(doc.url)
            outcome.log.append(f'{doc.url} yielded no readable text')
            continue
        portals.append(extract_portal(doc, text, authority_domain=authority_domain))
        stages = extract_stages(doc, text)
        if stages:
            all_stages.append((doc, stages))
        fees.extend(extract_fees(doc, text))
        outcome.log.append(
            f'{doc.url}: {len(stages)} stage(s), {len(extract_fees(doc, text))} fee rule(s)')

    outcome.process.portal = merge_facts('application portal', portals)
    if outcome.process.portal.status is Status.NEEDS_REVIEW:
        outcome.conflicts.append('portal')

    # Stages: the document that actually enumerated a procedure wins; a second document
    # enumerating a *different* procedure is a conflict, not extra steps to append.
    if all_stages:
        doc, stages = all_stages[0]
        outcome.process.stages = stages
        for other_doc, other in all_stages[1:]:
            if [s.title.lower() for s in other] != [s.title.lower() for s in stages]:
                outcome.conflicts.append('stages')
                for stage in outcome.process.stages:
                    stage.status = Status.NEEDS_REVIEW
                    stage.evidence.extend(e for s in other for e in s.evidence)
                outcome.log.append(
                    f'{other_doc.url} describes a different procedure from {doc.url}; '
                    f'both are kept and the stages are held for review')
                break
    else:
        outcome.log.append(
            'no document enumerated an application procedure; this is an extraction gap, '
            'not evidence that the authority publishes none')

    outcome.process.fees = _dedupe_fees(fees)

    # Several amounts stated for everybody cannot all be the application fee: a notice
    # prices more than one thing. Which is which is a reading, not a shape, so they are held
    # for review with their evidence rather than one being picked.
    unscoped = [f for f in outcome.process.fees
                if f.scope.is_global and f.amount.status is Status.VERIFIED
                and f.amount.has_value]
    if len(unscoped) > 1:
        listed = ', '.join(str(f.amount.value) for f in unscoped)
        for rule in unscoped:
            rule.amount.status = Status.NEEDS_REVIEW
            rule.amount.note = (
                f'{len(unscoped)} amounts are stated without saying who each is for '
                f'({listed}). A notice prices more than one thing, and which of these is '
                f'the application fee is a reading of the document rather than something '
                f'its structure settles. Each keeps its own evidence.')
        outcome.conflicts.append('fee amount')

    return outcome


def _dedupe_fees(fees: list[FeeRule]) -> list[FeeRule]:
    """Collapse identical rules from repeated sentences, keeping every piece of evidence."""
    out: list[FeeRule] = []
    for rule in fees:
        key = (str(rule.scope), rule.amount.value, rule.is_exempt.value)
        match = next((r for r in out
                      if (str(r.scope), r.amount.value, r.is_exempt.value) == key), None)
        if match is None:
            out.append(rule)
            continue
        for fact_name in ('amount', 'is_exempt', 'accepted_modes'):
            existing = getattr(match, fact_name)
            incoming = getattr(rule, fact_name)
            for ev in incoming.evidence:
                if ev.span_digest not in {e.span_digest for e in existing.evidence}:
                    existing.evidence.append(ev)
    return out
