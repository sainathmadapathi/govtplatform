"""Read previous-year papers, their questions, and official answer keys — for one exam only.

What the four captured authorities actually publish is set out in PYQ_AUDIT.md §5, and it
decides the shape of this module. One publishes 365 Civil Services papers and every one of
them is an image scan with no text layer. One publishes no papers at all but announces every
answer key in a dated notice, naming the exact examination and tier, and serves the key
itself to each candidate behind their own login. Two publish neither.

So this reads three different things, and keeps them apart:

  * **a paper catalogue** — the papers an authority publishes, with the identity its own
    file naming gives them and contents `NOT_EXTRACTED` where the file cannot be read. A
    catalogue entry is a real, useful, honest fact: the paper exists, here is its exact
    identity, here is where it is, and GovOS has not transcribed it.
  * **questions**, where a paper's text can actually be read. Identity is the paper *and*
    the number, never the number alone.
  * **answer keys**, bound to the exact paper, with the kind the notice calls them, the
    window it gives, and the route by which a candidate reaches them. A key with no public
    contents is still a key, and it is recorded as one.

Two rules run through all of it. Nothing is attributed to an exam that the document does not
place in that exam — and for a page listing one authority's every examination, that means
the *file's own naming* has to identify this exam, not the page it sits on. And no answer is
ever produced without a document that states it: not from another year's key, not from
another shift's, not from the question looking obvious.
"""
from __future__ import annotations

import re
import urllib.parse

from .pattern import _Cursor, _evidence, _slug
from .schema import (AnswerEntry, AnswerKey, AnswerKeyKind, AnswerStatus, Fact,
                     OfficialPaper, OfficialQuestion, PaperIdentity, QuestionFormat,
                     QuestionOption, SourceDocument, SourceStatus, Status)

# ============================================================== paper identity
#: How an authority labels a stage in a file name or a notice. Structural vocabulary: every
#: one of these is an ordinary word, and which an exam uses is read, never assumed.
_STAGE_WORDS: tuple[tuple[str, str], ...] = (
    (r'tier[\s\-]*([IVX]+|\d)', 'Tier'),
    (r'phase[\s\-]*([IVX]+|\d)', 'Phase'),
    (r'stage[\s\-]*([IVX]+|\d)', 'Stage'),
    (r'\b(prelims?|preliminary)\b', 'Preliminary'),
    (r'\b(mains?|main)\b', 'Main'),
    (r'\b(interview|personality\s+test)\b', 'Interview'),
)

#: A paper within a stage: "Paper-I", "Paper 2", "Paper A".
_PAPER_LABEL = re.compile(r'\bpaper[\s\-_]*([IVX]{1,4}|\d{1,2}|[A-H])\b', re.I)

#: A sitting: "Shift 2", "Session-I", "Morning Shift".
_SESSION_LABEL = re.compile(
    r'\b(?:shift|session|sitting)[\s\-_]*([IVX]{1,4}|\d{1,2})\b|'
    r'\b(morning|afternoon|evening|forenoon)\s+(?:shift|session|sitting)\b', re.I)

#: A booklet or series code printed on a paper: "Set A", "Series B", "Booklet C".
_SET_LABEL = re.compile(r'\b(?:set|series|booklet)[\s\-_]*([A-Z]|\d{1,2})\b', re.I)

#: A language a paper is printed in, where its own naming says so.
_LANGUAGE_LABEL = re.compile(
    r'\b(english|hindi|urdu|bengali|tamil|telugu|marathi|gujarati|kannada|malayalam|'
    r'odia|punjabi|assamese|sanskrit|bodo|dogri|kashmiri|konkani|maithili|manipuri|'
    r'nepali|santhali|sindhi)\b', re.I)

#: A four-digit year.
_YEAR_FULL = re.compile(r'\b(19|20)(\d{2})\b')

#: The two-digit year an authority writes after its own exam code: "CSM-26", "CSP_25".
#: Read only where the caller has said which codes are this exam's, so a stray pair of
#: digits in a file name can never become a cycle.
_SHORT_YEAR = re.compile(r'[-_](\d{2})(?=[-_])')

#: The descriptive tail of a file name, which is what the paper is about: "ESSAY",
#: "Optional-AGRICULTURE_PAPER_I", "Compulsory-BENGALI", "GENERAL-STUDIES-PAPER-I".
_NOISE_IN_NAME = re.compile(
    r'\b(?:qp|question\s*paper|paper|optional|compulsory|final|revised|copy|'
    r'\d{4,8})\b|[-_]+', re.I)


def _roman_or_number(value: str) -> str:
    return (value or '').strip().upper()


def subject_from_name(name: str) -> str:
    """What a paper is about, from the descriptive part of its own file name.

    Deliberately faithful: the authority's own words with its filing tokens removed.
    "Optional-AGRICULTURE_PAPER_I" is Agriculture and "Compulsory-BENGALI" is Bengali.
    Nothing is translated, expanded or tidied beyond spacing, because the subject is part
    of the identity an answer key will later be matched on.
    """
    stem = urllib.parse.unquote(name or '').rsplit('.', 1)[0]
    words = [w for w in re.split(r'[-_\s]+', stem) if w]

    # Drop the leading run of filing tokens: short all-caps codes, years, dates, and the
    # words an authority uses to file a paper rather than to describe it.
    # Four letters at most for an unlisted code: an authority's filing codes are short
    # (QP, CSM, CSP) and its subjects are not, so a longer all-caps token is
    # "ANIMAL" or "BENGALI" -- part of what the paper is about.
    filing = re.compile(r'^(?:[A-Z]{2,4}|\d{2,8}|qp|paper|'
                        r'optional|compulsory|final|revised|copy)$', re.I)
    index = 0
    # Never consume the last token as filing: a file name says what its paper is about
    # somewhere, and for "QP-CSM-26-010926-ESSAY" that somewhere is the only word left.
    while index < len(words) - 1 and filing.match(words[index]):
        index += 1
    rest = words[index:]

    # After the filing run, only the words that are *about* filing are dropped -- not every
    # short all-caps token, or "ESSAY" would be filed away as a code and that paper would
    # lose the only subject it has.
    noise = re.compile(r'^(?:\d{2,8}|qp|paper|optional|compulsory|final|'
                       r'revised|copy)$', re.I)
    keep = [w for w in rest
            if not noise.match(w) and not re.fullmatch(r'[IVX]{1,4}', w, re.I)]
    text = ' '.join(keep).strip(' -_')
    if len(text) < 3:
        return ''
    return ' '.join(w.capitalize() if w.isupper() else w for w in text.split())[:70]


def identity_from_text(text: str, *, exam_id: str, cycle: str = '',
                       codes: dict | None = None, subject: str = '') -> PaperIdentity:
    """The paper identity a piece of the authority's own wording gives.

    Used on a file name, a link's text or a notice's subject line -- whatever the authority
    itself wrote about the paper. Parts it did not print stay empty: an identity that
    invents a shift is worse than one that admits it does not know.

    Every part is read before the identity is built, because `PaperIdentity` is frozen. It
    is frozen because it is a key: something that decides whether one document's answers may
    be attached to another document's questions must not be editable after the comparison.
    """
    source = urllib.parse.unquote(text or '').replace('_', ' ').replace('%20', ' ')

    found_cycle = cycle
    if not found_cycle:
        years = _YEAR_FULL.findall(source)
        if years:
            found_cycle = years[0][0] + years[0][1]

    stage = ''
    # The caller's own code table: which of its authority's codes belong to this exam, and
    # what each one means. Supplied rather than guessed -- "CSM" means the Main examination
    # to one authority and nothing at all to another.
    # Separators are equivalent: a caller's "CSP_" and a file's "CSP-" are the same code,
    # and the reader has already turned underscores into spaces.
    flat = re.sub(r'[-_\s]+', '-', source.upper())
    for code, meaning in (codes or {}).items():
        flat_code = re.sub(r'[-_\s]+', '-', code.upper())
        if flat_code not in flat:
            continue
        stage = stage or (meaning or {}).get('stage', '')
        if not found_cycle:
            # The cycle sits immediately after the code, in two digits or four:
            # "CSM-26-…" and "CSP_2026_…" are the same authority's two spellings.
            after = flat.split(flat_code, 1)[1].lstrip('-_ ')
            short = re.match(r'(\d{4}|\d{2})(?=[-_ ]|$)', after)
            if short:
                value = short.group(1)
                found_cycle = value if len(value) == 4 else f'20{value}'
        break

    for pattern, label in _STAGE_WORDS:
        if stage:
            break
        found = re.search(pattern, source, re.I)
        if not found:
            continue
        if label in ('Preliminary', 'Main', 'Interview'):
            stage = label
        else:
            ordinal = found.group(1) if found.lastindex else ''
            stage = f'{label}-{_roman_or_number(ordinal)}'
        break

    paper = _PAPER_LABEL.search(source)
    session = _SESSION_LABEL.search(source)
    set_code = _SET_LABEL.search(source)
    language = _LANGUAGE_LABEL.search(source)

    session_label = ''
    if session:
        value = session.group(1) or session.group(2) or ''
        session_label = (f'Shift {_roman_or_number(value)}' if value.isdigit()
                         else value.title())

    return PaperIdentity(
        exam_id=exam_id,
        cycle=found_cycle,
        stage=stage,
        paper=f'Paper-{_roman_or_number(paper.group(1))}' if paper else '',
        subject=subject,
        session=session_label,
        set_code=f'Set {set_code.group(1).upper()}' if set_code else '',
        language=language.group(1).title() if language else '')


# =========================================================== the paper catalogue
def catalogue_papers(links: list, *, exam_id: str, exam_codes, doc: SourceDocument,
                     page_text: str = '', reject_codes: tuple = ()) -> tuple[list, list]:
    """The papers on an authority's listing that belong to *this* exam.

    An authority that publishes one page for all its examinations puts this exam's papers
    among every other exam's — 365 of one exam among 702 files in the case that prompted
    this. The page cannot vouch for any of them, so each file must identify itself: the
    caller supplies the codes this exam's own files carry, and anything else is refused and
    returned for the report rather than silently dropped.

    Returns (kept, rejected). A kept paper's contents are `NOT_EXTRACTED` until something
    actually reads it; the entry is the fact that the paper exists and where it is.
    """
    kept: list[OfficialPaper] = []
    rejected: list[tuple[str, str]] = []
    for href in links:
        name = urllib.parse.unquote(href.rsplit('/', 1)[-1])
        upper = name.upper()
        if not any(code.upper() in upper for code in exam_codes):  # noqa: E501 - dict iterates keys
            rejected.append((name, 'the file does not carry this exam’s own code'))
            continue
        if any(bad.upper() in upper for bad in reject_codes):
            rejected.append((name, 'the file carries another examination’s code'))
            continue
        codes = exam_codes if isinstance(exam_codes, dict) else {c: {} for c in exam_codes}
        identity = identity_from_text(name, exam_id=exam_id, codes=codes,
                                      subject=subject_from_name(name))
        if not identity.is_paper_level:
            rejected.append((name, 'the file name does not identify a paper, only a cycle'))
            continue
        paper = OfficialPaper(identity=identity, title=name)
        url = href if href.startswith('http') else ''
        paper.url = Fact.verified(url, _link_evidence(href, doc, page_text)) \
            if url and _link_evidence(href, doc, page_text) else Fact.needs_review(
                url or href, 'the link could not be verified verbatim on the listing page')
        paper.contents = Fact.not_extracted(
            'not transcribed: the file has not been read into questions')
        paper.status = Status.VERIFIED if paper.url.status is Status.VERIFIED \
            else Status.NEEDS_REVIEW
        paper.evidence = list(paper.url.evidence)
        kept.append(paper)
    return kept, rejected


def _link_evidence(href: str, doc: SourceDocument, page_text: str):
    if not page_text:
        return None
    return _evidence(href[-90:], doc, page_text, reading='a paper linked on the listing')


def mark_unreadable(paper: OfficialPaper, *, words: int) -> OfficialPaper:
    """Record *why* a paper's questions are absent.

    "We could not read it" and "the authority published nothing" are different claims, and
    a scan with no text layer is the first. Saying so is what lets a candidate know the
    paper is real and where it is, without GovOS pretending to have read it.
    """
    if words == 0:
        paper.contents = Fact.not_extracted(
            'published as an image scan with no text layer, so its questions cannot be '
            'read without OCR; OCR of a scanned booklet loses word spacing and misreads '
            'option labels, so nothing is transcribed from it here')
        paper.note = 'scan, no text layer'
    return paper


# ================================================================== questions
#: A question opening a line: "1.", "Q.1", "Q 12)", "47)".
_QUESTION_NUMBER = re.compile(
    r'^\s*(?:Q(?:ues(?:tion)?)?\.?\s*)?(?P<number>\d{1,3})\s*[.)\]]\s+(?P<rest>\S.*)$',
    re.I)

#: An option: "(a) text", "1. text", "A) text". The label is kept as printed.
_OPTION = re.compile(
    r'^\s*\(?(?P<label>[a-dA-D1-4])[.)\]]\s*(?P<text>\S.*)$')

#: Marks printed beside a question: "(10 marks)", "10 M", "[15]".
_MARKS = re.compile(r'[\(\[]\s*(\d{1,3})\s*(?:marks?|m)\s*[\)\]]|\b(\d{1,3})\s*marks?\b',
                    re.I)

#: A passage introducing several questions.
_PASSAGE = re.compile(
    r'\b(?:read\s+the\s+following\s+passage|directions?\s*[:(]|'
    r'answer\s+the\s+questions?\s+that\s+follow)\b', re.I)


def _next_option_label(options: list):
    """The label an option would carry if it followed the ones already read."""
    if not options:
        return None
    last = (options[-1].label or '').strip()
    if last.isdigit():
        return str(int(last) + 1)
    if len(last) == 1 and last.isalpha():
        return chr(ord(last) + 1)
    return None


def extract_questions(doc: SourceDocument, text: str, *, paper: PaperIdentity,
                      source_status: SourceStatus = SourceStatus.OFFICIAL_VERIFIED
                      ) -> list:
    """The questions a readable paper contains, bound to the paper handed in.

    The paper identity is the caller's, never guessed from the text: a booklet rarely names
    its own shift, and reading one from the questions would invent it. What is read here is
    the numbering, the wording, the options with their printed labels, and marks where the
    paper prints them.

    No answer is produced. A question paper is not a key, and a question whose answer is
    obvious is still a question whose answer the authority has not published.
    """
    questions: list[OfficialQuestion] = []
    if not text or not paper.exam_id:
        return questions

    cur = _Cursor(text)
    current: OfficialQuestion | None = None
    buffer: list[str] = []
    passage_id, passage_text = '', ''
    last_number = 0

    def finish() -> None:
        nonlocal current, buffer
        if current is None:
            buffer = []
            return
        body = ' '.join(buffer).strip()
        if body and not current.text:
            current.text = body[:1200]
        elif body:
            current.text = (current.text + ' ' + body).strip()[:1200]
        current.text = re.sub(r'\s+', ' ', current.text).strip()
        if current.options:
            current.format = QuestionFormat.MULTIPLE_CHOICE
        elif current.format is QuestionFormat.OTHER:
            current.format = (QuestionFormat.PASSAGE_BASED if current.passage_id
                              else QuestionFormat.DESCRIPTIVE)
        marks = _MARKS.search(current.text)
        if marks:
            value = next(g for g in marks.groups() if g)
            span = marks.group(0)
            evidence = _evidence(span, doc, text, reading=f'marks printed for Q{current.number}')
            current.marks = (Fact.verified(float(value), evidence) if evidence
                             else Fact.needs_review(float(value), 'span not verbatim'))
        questions.append(current)
        current, buffer = None, []

    for index, raw in enumerate(cur.lines):
        line = raw.strip()
        if not line:
            continue
        if _PASSAGE.search(line) and current is None:
            passage_id = f'passage-{_slug(paper.key())[:16]}-{index}'
            passage_text = line
            continue

        option = _OPTION.match(line) if current is not None else None
        number = _QUESTION_NUMBER.match(line)
        if option and number:
            # The label continues one of two sequences. A question number follows the last
            # question; an option label follows the last option. Where it could be either,
            # the question wins -- reading it as an option loses the whole question.
            label = option.group('label')
            continues_questions = label.isdigit() and int(label) == last_number + 1
            expected_option = _next_option_label(current.options)
            continues_options = (expected_option is not None
                                 and label.lower() == expected_option.lower())
            # A first option has nothing to continue: "1." directly under a question is
            # that question's first option, not the question after it.
            first_option = not current.options and label.lower() in ('a', '1', 'i')
            if continues_options or first_option:
                # A label that continues the options belongs to the question in hand. Where
                # it continues the question numbering too -- a paper whose options are
                # numbered, read as flat text -- the document itself is ambiguous at that
                # line, and the question says so rather than the reader picking silently.
                number = None
                if continues_questions:
                    current.note = (current.note + ' this paper numbers its options as it '
                                    'numbers its questions, so the boundary between this '
                                    'question and the next was read from the sequence, '
                                    'not from the page').strip()
            elif continues_questions:
                option = None
        if option and (current.options or not number):
            current.options.append(QuestionOption(label=option.group('label'),
                                                  text=option.group('text').strip()[:400]))
            continue
        if number:
            finish()
            last_number = int(number.group('number'))
            current = OfficialQuestion(
                paper=paper, number=number.group('number'),
                passage_id=passage_id, passage_text=passage_text[:600],
                source_status=source_status)
            evidence = _evidence(line, doc, text,
                                 reading=f'question {number.group("number")} of '
                                         f'{paper.describe()}')
            if evidence:
                current.evidence = [evidence]
                current.status = Status.VERIFIED
            else:
                current.status = Status.NEEDS_REVIEW
                current.source_status = SourceStatus.NEEDS_REVIEW
            buffer = [number.group('rest').strip()]
            continue
        if current is not None:
            buffer.append(line)
    finish()

    for question in questions:
        if question.answer is None:
            question.answer = AnswerEntry(
                question_number=question.number, paper=paper,
                status=AnswerStatus.NOT_PUBLISHED,
                note='this document is a question paper; it publishes no answer')
    return questions


# ================================================================ answer keys
#: What an authority calls a key. "Tentative" is the word one of them uses for what another
#: calls provisional; both are the pre-objection key.
_KEY_KIND = (
    (re.compile(r'\b(?:final)\s+answer\s+keys?\b', re.I), AnswerKeyKind.FINAL),
    (re.compile(r'\b(?:revised|corrected)\s+answer\s+keys?\b', re.I), AnswerKeyKind.REVISED),
    (re.compile(r'\b(?:tentative|provisional|draft)\s+answer\s+keys?\b', re.I),
     AnswerKeyKind.PROVISIONAL),
)
_ANY_KEY = re.compile(r'\banswer\s+keys?\b', re.I)

#: A date in a notice: "17.06.2026", "17/06/2026", "17 June 2026".
_DATE = re.compile(
    r'\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b|'
    r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|'
    r'October|November|December)\s+(20\d{2})\b', re.I)
_MONTHS = {m.lower(): i for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
     'September', 'October', 'November', 'December'], start=1)}

#: How a candidate reaches the key, where the notice says.
_ACCESS = re.compile(
    r'\b(?:by\s+)?logg?ing[\s-]*in[^.]{0,120}|\bthrough\s+(?:their|his/her)\s+'
    r'(?:registered\s+)?(?:id|login)[^.]{0,80}|\bcandidate\s+login[^.]{0,80}', re.I)

#: The window in which a key may be seen or challenged.
_WINDOW = re.compile(
    r'from\s+(\d{1,2}[./-]\d{1,2}[./-]20\d{2})[^.]{0,40}?to\s+'
    r'(\d{1,2}[./-]\d{1,2}[./-]20\d{2})', re.I)


def _iso(match) -> str:
    if match.group(3):
        return f'{match.group(3)}-{int(match.group(2)):02d}-{int(match.group(1)):02d}'
    month = _MONTHS.get((match.group(5) or '').lower())
    if month and match.group(6):
        return f'{match.group(6)}-{month:02d}-{int(match.group(4)):02d}'
    return ''


def _iso_from(value: str) -> str:
    found = _DATE.search(value or '')
    return _iso(found) if found else ''


def read_answer_key_notice(doc: SourceDocument, text: str, *, exam_id: str,
                           headline: str = '', published_at: str = '') -> AnswerKey | None:
    """An answer key an authority has announced, bound to the paper it answers.

    One authority publishes no question papers and every key: a dated notice naming the
    examination and the tier, the kind of key, when it went up, how long a candidate has to
    see or challenge it, and that the key itself is served through the candidate's own
    login. All of that is the key's record; the answers are simply not public, which is
    recorded as such rather than as an absence of a key.

    Returns None where the document is not about a key, or where the paper it answers
    cannot be identified exactly — never the nearest-looking paper.
    """
    body = ' '.join((text or '').split())
    subject = headline or body[:400]
    if not _ANY_KEY.search(subject) and not _ANY_KEY.search(body[:1500]):
        return None

    kind = AnswerKeyKind.UNSPECIFIED
    for pattern, value in _KEY_KIND:
        if pattern.search(subject) or pattern.search(body[:1500]):
            kind = value
            break

    identity = identity_from_text(subject, exam_id=exam_id)
    if not identity.is_paper_level:
        identity = identity_from_text(body[:1500], exam_id=exam_id)
    if not identity.is_paper_level:
        return None

    key = AnswerKey(paper=identity, kind=kind, id=f'key-{_slug(identity.key())[:44]}-'
                                                  f'{kind.value.lower()}')
    url_evidence = _evidence(subject[:160], doc, text,
                             reading=f'a {kind.value.lower()} answer key for '
                                     f'{identity.describe()}')
    if doc.url:
        key.url = Fact.verified(doc.url, url_evidence) if url_evidence \
            else Fact.needs_review(doc.url, 'the notice text could not be verified verbatim')
    stated = published_at or _iso_from(body[:600])
    if stated:
        key.published_at = Fact.verified(stated, url_evidence) if url_evidence \
            else Fact.needs_review(stated, 'span not verbatim')

    window = _WINDOW.search(body)
    if window:
        key.window_opens = _iso_from(window.group(1))
        key.window_closes = _iso_from(window.group(2))
    access = _ACCESS.search(body)
    if access:
        key.access = ' '.join(access.group(0).split())[:200]

    key.evidence = [url_evidence] if url_evidence else []
    key.status = Status.VERIFIED if url_evidence else Status.NEEDS_REVIEW
    key.source_status = (SourceStatus.OFFICIAL_VERIFIED if url_evidence
                         else SourceStatus.NEEDS_REVIEW)
    if not key.entries:
        key.note = ('the authority announced this key; its per-question answers are not '
                    'published publicly' + (f' — {key.access}' if key.access else ''))
    return key


def link_revisions(keys: list) -> list:
    """Point each key at the one it supersedes, for the same paper.

    A final key does not delete the tentative one: a candidate who challenged an answer
    needs to see both. So the later key records what it revises and both are kept, which is
    the same rule the dates and the syllabus follow.
    """
    order = {AnswerKeyKind.PROVISIONAL: 0, AnswerKeyKind.UNSPECIFIED: 1,
             AnswerKeyKind.REVISED: 2, AnswerKeyKind.FINAL: 3}
    by_paper: dict = {}
    for key in keys:
        by_paper.setdefault(key.paper.key(), []).append(key)
    for group in by_paper.values():
        group.sort(key=lambda k: (order.get(k.kind, 1),
                                  k.published_at.value or ''))
        for earlier, later in zip(group, group[1:]):
            if later.kind is not earlier.kind:
                later.revises = earlier.id
    return keys


# ====================================================================== report
def describe_papers(papers: list) -> dict:
    states: dict = {}
    for paper in papers:
        states[paper.status.value] = states.get(paper.status.value, 0) + 1
    readable = sum(1 for p in papers if p.contents.has_value)
    return {'papers': len(papers), 'withContents': readable, 'states': states,
            'cycles': sorted({p.identity.cycle for p in papers if p.identity.cycle})}


def describe_keys(keys: list) -> dict:
    kinds: dict = {}
    for key in keys:
        kinds[key.kind.value] = kinds.get(key.kind.value, 0) + 1
    return {'keys': len(keys), 'kinds': kinds,
            'withEntries': sum(1 for k in keys if k.entries),
            'revisions': sum(1 for k in keys if k.revises),
            'papers': sorted({k.paper.describe() for k in keys})}


def describe_questions(questions: list) -> dict:
    states: dict = {}
    formats: dict = {}
    for question in questions:
        states[question.status.value] = states.get(question.status.value, 0) + 1
        formats[question.format.value] = formats.get(question.format.value, 0) + 1
    return {'questions': len(questions), 'states': states, 'formats': formats,
            'withAnswer': sum(1 for q in questions
                              if q.answer and q.answer.is_publishable),
            'papers': sorted({q.paper.describe() for q in questions})}
