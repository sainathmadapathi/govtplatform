"""Finding the documents an authority publishes *for one exam*.

The fetching is the easy half. The half that matters is deciding whether a document found
on an authority's site belongs to **this** exam, because one authority publishes for many:
ssc.gov.in carries CGL, CHSL, MTS and JE side by side, and upsc.gov.in carries a dozen
examinations whose notices look identical. Attaching another exam's syllabus is precisely
the cross-exam contamination the product forbids, and it is far likelier to happen here —
at discovery — than anywhere downstream.

So every document must earn its place by one of exactly two routes:

    DIRECT     the link's own text or URL carries this exam's distinctive words
    INHERITED  it was found on a page that is itself specific to this exam

and anything that qualifies under neither is **rejected and recorded**. A rejected document
that carries a *different* exam's words is kept in the report as positive evidence that the
gate worked, rather than being silently dropped.

Nothing here is authority-specific. The document kinds below are the vocabulary Indian
recruitment bodies actually share ("advertisement", "admit card", "answer key", "corrigendum"),
not one site's menu.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from ..exam_authoring.sources import Document, FetchError, html_links, load_html
from .resolve import ResolvedExam, distinctive_words


class DocKind(str, Enum):
    EXAM_PAGE = 'EXAM_PAGE'
    NOTIFICATION = 'NOTIFICATION'
    CORRIGENDUM = 'CORRIGENDUM'
    SYLLABUS = 'SYLLABUS'
    EXAM_PATTERN = 'EXAM_PATTERN'
    QUESTION_PAPER = 'QUESTION_PAPER'
    ANSWER_KEY = 'ANSWER_KEY'
    ADMIT_CARD = 'ADMIT_CARD'
    RESULT = 'RESULT'
    APPLICATION_PORTAL = 'APPLICATION_PORTAL'
    CUTOFF = 'CUTOFF'
    CALENDAR = 'CALENDAR'
    UNKNOWN = 'UNKNOWN'


#: Ordered: the first match wins, so the more specific kind is listed before the general
#: one. "Answer key" must beat "key", and "corrigendum to the notification" must be read as
#: a corrigendum rather than as the notification it amends.
_KIND_PATTERNS: list[tuple[DocKind, str]] = [
    (DocKind.CORRIGENDUM, r'corrigend|addend|amendment|errata|revised\s+(notice|notif)'),
    (DocKind.ANSWER_KEY, r'answer\s*-?\s*key|final\s+key|tentative\s+key|response\s+sheet'),
    (DocKind.ADMIT_CARD, r'admit\s*-?\s*card|hall\s*ticket|call\s*letter|e-?admit|intimation\s+slip'),
    (DocKind.CUTOFF, r'cut\s*-?\s*off|qualifying\s+marks|minimum\s+marks'),
    (DocKind.QUESTION_PAPER, r'question\s*paper|previous\s*year|\bpyq\b|\bqp[-_ ]|papers?\s+held'),
    (DocKind.RESULT, r'\bresults?\b|merit\s+list|short\s*-?\s*list|written\s+result|recommend'),
    (DocKind.SYLLABUS, r'syllabus|scheme\s+of\s+exam|course\s+content'),
    (DocKind.EXAM_PATTERN, r'exam(ination)?\s+pattern|scheme\s+and\s+syllabus|marking\s+scheme'),
    (DocKind.CALENDAR, r'calendar|exam\s+schedule|date\s*sheet|time\s*table|programme'),
    (DocKind.APPLICATION_PORTAL, r'apply\s*online|online\s+application|registration|one\s*time\s*reg|\botr\b'),
    (DocKind.NOTIFICATION, r'notification|notice|advertisement|\badvt\b|employment\s+news|recruitment\s+for'),
]


def classify_kind(text: str, url: str = '') -> DocKind:
    """What kind of document a link points at, from its own words.

    The link text is trusted over the URL: authorities name their files cryptically
    ("Notif-CSP-2026-Engl-060226Rev.pdf") but label their links for humans.
    """
    for blob in (text or '', url or ''):
        low = blob.lower()
        for kind, pattern in _KIND_PATTERNS:
            if re.search(pattern, low):
                return kind
    return DocKind.UNKNOWN


class Relevance(str, Enum):
    DIRECT = 'DIRECT'          # the link itself names this exam
    INHERITED = 'INHERITED'    # found on a page that names this exam
    REJECTED = 'REJECTED'      # names neither, or names another exam


@dataclass
class DiscoveredDoc:
    url: str
    kind: DocKind
    title: str
    relevance: Relevance
    matched: list[str] = field(default_factory=list)
    found_on: str = ''
    #: When rejected because it belongs elsewhere, the words that gave it away.
    foreign_words: list[str] = field(default_factory=list)

    @property
    def is_pdf(self) -> bool:
        return self.url.lower().split('?')[0].endswith('.pdf')


@dataclass
class SourceSet:
    exam_id: str
    authority_domain: str
    docs: list[DiscoveredDoc] = field(default_factory=list)
    rejected: list[DiscoveredDoc] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def of_kind(self, kind: DocKind) -> list[DiscoveredDoc]:
        return [d for d in self.docs if d.kind is kind]

    def kinds_found(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for d in self.docs:
            out[d.kind.value] = out.get(d.kind.value, 0) + 1
        return out


def exam_aliases(query: str, official_name: str = '') -> list[str]:
    """Every token that legitimately names this exam, expansion and acronym alike.

    Authorities mix the two freely: the page is titled "Combined Graduate Level
    Examination" and the link beside it says "CGL 2026 Notice". Matching only the words of
    the official name rejected the exam's own documents, and matching only the acronym
    misses the page that spells it out. Both go in the set.

    Acronyms are built from the name the authority prints, never from a table of exams — a
    hand-kept table is the thing this engine exists to avoid.
    """
    words = list(dict.fromkeys(distinctive_words(query) + distinctive_words(official_name)))
    aliases = set(words)

    for source in (official_name, query):
        tokens = distinctive_words(source)
        # "Combined Graduate Level" -> "cgl". Built over runs of 2+ words, and over the run
        # with the leading authority code dropped, since "SSC CGL" acronymises to both.
        for start in (0, 1):
            run = tokens[start:]
            if len(run) >= 2:
                acronym = ''.join(w[0] for w in run)
                if 2 <= len(acronym) <= 6:
                    aliases.add(acronym)
        # An acronym the user typed directly ("CGL", "NTPC", "AAO").
        for raw in re.findall(r'\b[A-Z]{2,6}\b', source or ''):
            aliases.add(raw.lower())

    # Two letters is too little to identify anything; it would match inside other words.
    return sorted(a for a in aliases if len(a) >= 3)


def gate(link_text: str, link_url: str, *, exam_words: list[str],
         page_is_exam_specific: bool, sibling_exam_words: list[str] | None = None
         ) -> tuple[Relevance, list[str], list[str]]:
    """Decide whether a link belongs to this exam. The whole isolation rule lives here.

    `sibling_exam_words` are the distinctive words of *other* exams known to live on the same
    authority. A link carrying one of those and none of this exam's is rejected even when it
    was found on this exam's page, because authorities cross-link freely — SSC's CGL page
    links to the CHSL notice, and inheriting that would file CHSL's rules under CGL.
    """
    # Match on the link's text and the URL's *path* — never its host. The authority's own
    # domain carries the authority's token (ssc.gov.in contains "ssc"), so including the
    # host made every link on the site a DIRECT match and disabled the gate completely:
    # CHSL's answer key, and "Contact Us", both came through as this exam's documents.
    parsed = urlparse(link_url or '')
    path_only = f'{parsed.path} {parsed.query}' if parsed.scheme else (link_url or '')
    blob = f'{link_text} {path_only}'.lower()
    matched = [w for w in exam_words if w in blob]
    foreign = [w for w in (sibling_exam_words or []) if w in blob and w not in exam_words]

    if foreign and not matched:
        return Relevance.REJECTED, matched, foreign
    if matched:
        return Relevance.DIRECT, matched, foreign
    if page_is_exam_specific and not foreign:
        return Relevance.INHERITED, matched, foreign
    return Relevance.REJECTED, matched, foreign


def page_is_specific_to(title: str, url: str, exam_words: list[str], *, need: int = 2) -> bool:
    """Is this page about one exam, rather than the authority's whole site?

    A page must carry at least `need` of the exam's distinctive words before anything is
    allowed to inherit relevance from it. One word is not enough: "Combined" appears in
    Combined Graduate Level, Combined Higher Secondary and Combined Defence Services alike.
    """
    # Path only, for the same reason as `gate`: the host carries the authority's own token
    # and would make every page on the site look exam-specific.
    parsed = urlparse(url or '')
    path_only = parsed.path if parsed.scheme else (url or '')
    blob = f'{title} {path_only}'.lower()
    hits = sum(1 for w in exam_words if w in blob)
    return hits >= min(need, len(exam_words))


def discover(resolved: ResolvedExam, *, exam_id: str, max_pages: int = 6,
             sibling_exam_words: list[str] | None = None) -> SourceSet:
    """Crawl outward from the resolver's seeds, keeping only what belongs to this exam."""
    words = exam_aliases(resolved.query, resolved.official_name)
    host = (urlparse(resolved.authority.domain).hostname or '').replace('www.', '')
    out = SourceSet(exam_id=exam_id, authority_domain=resolved.authority.domain)
    seen_urls: set[str] = set()

    # Visit the most exam-specific seeds first, so inheritance starts from a real exam page.
    seeds = sorted(dict.fromkeys(resolved.seed_urls),
                   key=lambda u: -sum(1 for w in words if w in u.lower()))

    for seed in seeds[:max_pages]:
        if seed in seen_urls:
            continue
        seen_urls.add(seed)
        try:
            page = load_html(seed)
        except FetchError as exc:
            out.log.append(f'could not read {seed}: {exc}')
            continue

        title = _title_of(page)
        specific = page_is_specific_to(title, seed, words)
        out.log.append(f'{"exam-specific" if specific else "general"} page: {seed}')

        if specific:
            out.docs.append(DiscoveredDoc(
                url=seed, kind=DocKind.EXAM_PAGE, title=title,
                relevance=Relevance.DIRECT,
                matched=[w for w in words if w in f'{title} {seed}'.lower()]))

        for text, href in html_links(page, r'.*'):
            if not href or href in seen_urls:
                continue
            link_host = (urlparse(href).hostname or '').replace('www.', '')
            # Stay on the authority's own estate. A link off-site may be the application
            # portal, which is allowed only where the authority itself points at it.
            same_estate = link_host == host or link_host.endswith('.' + host)
            rel, matched, foreign = gate(text, href, exam_words=words,
                                         page_is_exam_specific=specific,
                                         sibling_exam_words=sibling_exam_words)
            kind = classify_kind(text, href)
            doc = DiscoveredDoc(url=href, kind=kind, title=text.strip()[:160],
                                relevance=rel, matched=matched, found_on=seed,
                                foreign_words=foreign)
            if kind is DocKind.UNKNOWN and rel is not Relevance.DIRECT:
                continue                       # navigation chrome, not a document
            if not same_estate and kind is not DocKind.APPLICATION_PORTAL:
                continue                       # off-site, and not the portal
            if rel is Relevance.REJECTED:
                out.rejected.append(doc)
                continue
            out.docs.append(doc)

    _dedupe(out)
    return out


def _title_of(page: Document) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', getattr(page, 'html', ''), re.S | re.I)
    return ' '.join(re.sub(r'<[^>]+>', ' ', m.group(1)).split()) if m else ''


def _dedupe(out: SourceSet) -> None:
    best: dict[str, DiscoveredDoc] = {}
    for d in out.docs:
        prev = best.get(d.url)
        # Keep the better-evidenced copy of a URL seen twice.
        if prev is None or (prev.relevance is Relevance.INHERITED and d.relevance is Relevance.DIRECT):
            best[d.url] = d
    out.docs = list(best.values())
